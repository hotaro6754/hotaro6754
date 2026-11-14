"""HTTP API (FastAPI).

Security posture:
* binds to 127.0.0.1 by default (see ``openmirror.main``);
* only ``localhost``/``127.0.0.1`` Host headers are accepted (DNS-rebinding guard);
* CORS is limited to the local frontend origins;
* request bodies are size-limited while streaming, before the upload is parsed;
* access logs are disabled and message text is never logged.
"""

from __future__ import annotations

import json
import shutil
import sqlite3
import tempfile
from collections.abc import Iterator
from enum import Enum
from pathlib import Path
from typing import Annotated, Any

from fastapi import Depends, FastAPI, File, Form, HTTPException, Query, Request, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from pydantic import BaseModel, Field

from openmirror import __version__, service
from openmirror.config import Settings, load_settings
from openmirror.ingest.sources import UnsafeArchiveError, UnsupportedUploadError
from openmirror.ingest.whatsapp import NotAWhatsAppExportError
from openmirror.storage.db import connect, init_db
from openmirror.storage.importer import ImportFailedError, import_file


class DateOrderOption(str, Enum):
    auto = "auto"
    DMY = "DMY"
    MDY = "MDY"
    YMD = "YMD"


class ConversationOut(BaseModel):
    id: str
    title: str
    source_platform: str
    source_layout: str | None
    imported_at: str
    status: str
    message_count: int
    participant_count: int
    first_ts: str | None
    last_ts: str | None


class ParticipantOut(BaseModel):
    id: int
    display_name: str
    message_count: int


class ConversationDetail(ConversationOut):
    participants: list[ParticipantOut]


class ImportResult(BaseModel):
    conversation: ConversationDetail
    import_job_id: str
    analysis_run_id: str


class MessageOut(BaseModel):
    id: int
    seq: int
    sender_id: int | None
    sender: str | None
    ts_original: str
    ts: str
    text: str
    message_type: str
    media_kind: str | None
    is_edited: bool
    line_start: int
    line_end: int


class MessagePage(BaseModel):
    messages: list[MessageOut]
    total: int
    focus_id: int | None = None


class EvidenceOut(BaseModel):
    role: str
    note: str | None
    message: MessageOut


class FindingDetail(BaseModel):
    id: str
    conversation_id: str
    chapter: str
    finding_type: str
    title: str
    statement: str
    method: str
    confidence: str
    confidence_reason: str
    metrics: Any
    counterexample_note: str | None
    time_start: str | None
    time_end: str | None
    evidence: list[EvidenceOut]


class ReportOut(BaseModel):
    analysis_run_id: str
    created_at: str
    report: dict[str, Any]
    analytics: dict[str, Any]


class AnalyzeRequest(BaseModel):
    session_gap_minutes: int = Field(default=240, ge=15, le=7 * 24 * 60)


class _BodyLimit:
    """ASGI middleware rejecting request bodies larger than ``limit`` bytes."""

    def __init__(self, app: Any, limit: int) -> None:
        self.app = app
        self.limit = limit

    async def __call__(self, scope: dict, receive: Any, send: Any) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return
        headers = dict(scope.get("headers") or [])
        declared = headers.get(b"content-length")
        if declared is not None and declared.isdigit() and int(declared) > self.limit:
            await _send_413(send, self.limit)
            return
        received = 0

        async def limited_receive() -> dict:
            nonlocal received
            message = await receive()
            if message["type"] == "http.request":
                received += len(message.get("body", b""))
                if received > self.limit:
                    raise _TooLarge()
            return message

        try:
            await self.app(scope, limited_receive, send)
        except _TooLarge:
            await _send_413(send, self.limit)


class _TooLarge(Exception):
    pass


async def _send_413(send: Any, limit: int) -> None:
    body = json.dumps({"detail": f"Upload exceeds the {limit // (1024 * 1024)} MB limit."}).encode()
    await send(
        {
            "type": "http.response.start",
            "status": 413,
            "headers": [(b"content-type", b"application/json"), (b"content-length", str(len(body)).encode())],
        }
    )
    await send({"type": "http.response.body", "body": body})


def get_conn(request: Request) -> Iterator[sqlite3.Connection]:
    """One SQLite connection per request (connections are cheap and not shared)."""
    conn = connect(request.app.state.settings.db_path)
    try:
        yield conn
    finally:
        conn.close()


Conn = Annotated[sqlite3.Connection, Depends(get_conn)]


def create_app(settings: Settings | None = None) -> FastAPI:
    settings = settings or load_settings()
    settings.data_dir.mkdir(parents=True, exist_ok=True)
    try:
        settings.data_dir.chmod(0o700)
    except OSError:  # pragma: no cover - e.g. on some Windows filesystems
        pass
    # Remove any temporary upload left behind by a crash.
    shutil.rmtree(settings.data_dir / "tmp", ignore_errors=True)
    boot = connect(settings.db_path)
    init_db(boot)
    boot.close()

    app = FastAPI(
        title="OpenMirror API",
        version=__version__,
        description="Local-first WhatsApp conversation intelligence. Nothing leaves this machine.",
    )
    app.state.settings = settings
    app.add_middleware(
        CORSMiddleware,
        allow_origins=list(settings.cors_origins),
        allow_methods=["GET", "POST", "DELETE"],
        allow_headers=["*"],
    )
    allowed_hosts = sorted({"127.0.0.1", "localhost", "testserver", settings.host})
    app.add_middleware(TrustedHostMiddleware, allowed_hosts=allowed_hosts)
    # Leave head-room for multipart framing around the file itself.
    app.add_middleware(_BodyLimit, limit=settings.max_upload_bytes + 64 * 1024)

    def detail(conn: sqlite3.Connection, conversation_id: str) -> ConversationDetail:
        conv = service.get_conversation(conn, conversation_id)
        parts = [
            ParticipantOut(**dict(r))
            for r in conn.execute(
                "SELECT id, display_name, message_count FROM participants WHERE conversation_id=? "
                "ORDER BY message_count DESC, id",
                (conversation_id,),
            )
        ]
        return ConversationDetail(**conv, participants=parts)

    @app.exception_handler(service.NotFoundError)
    async def _not_found(_: Request, exc: service.NotFoundError):  # type: ignore[no-untyped-def]
        from fastapi.responses import JSONResponse

        return JSONResponse(status_code=404, content={"detail": str(exc)})

    @app.get("/api/health")
    def health() -> dict:
        return {
            "status": "ok",
            "version": __version__,
            "ai_enabled": False,
            "external_services": [],
            "max_upload_mb": settings.max_upload_mb,
        }

    @app.get("/api/conversations", response_model=list[ConversationOut])
    def conversations(conn: Conn) -> list[dict]:
        return service.list_conversations(conn)

    @app.post("/api/imports", response_model=ImportResult, status_code=201)
    def create_import(
        conn: Conn,
        file: Annotated[UploadFile, File(description="WhatsApp export (.txt or .zip)")],
        date_order: Annotated[DateOrderOption, Form()] = DateOrderOption.auto,
        title: Annotated[str | None, Form(max_length=200)] = None,
    ) -> ImportResult:
        name = Path(file.filename or "upload.txt").name
        if not name.lower().endswith((".txt", ".zip")):
            raise HTTPException(415, "Upload a WhatsApp export: a .txt file or a .zip archive.")
        tmp_dir = settings.data_dir / "tmp"
        tmp_dir.mkdir(exist_ok=True)
        with tempfile.NamedTemporaryFile(dir=tmp_dir, delete=False, suffix=".upload") as tmp:
            tmp_path = Path(tmp.name)
            copied = 0
            while chunk := file.file.read(1024 * 1024):
                copied += len(chunk)
                if copied > settings.max_upload_bytes:
                    tmp.close()
                    tmp_path.unlink(missing_ok=True)
                    raise HTTPException(413, f"Upload exceeds the {settings.max_upload_mb} MB limit.")
                tmp.write(chunk)
        try:
            conv_id, job_id = import_file(
                conn,
                tmp_path,
                name,
                max_text_bytes=settings.max_chat_text_bytes,
                max_zip_entries=settings.max_zip_entries,
                date_order=None if date_order == DateOrderOption.auto else date_order.value,  # type: ignore[arg-type]
                title=title.strip() if title and title.strip() else None,
            )
        except ImportFailedError as exc:
            cause = exc.__cause__
            if isinstance(cause, (UnsupportedUploadError, NotAWhatsAppExportError)):
                raise HTTPException(422, str(cause)) from None
            if isinstance(cause, UnsafeArchiveError):
                raise HTTPException(400, str(cause)) from None
            raise HTTPException(500, "The import failed unexpectedly.") from None
        finally:
            tmp_path.unlink(missing_ok=True)
        run_id = service.run_analysis(conn, conv_id)
        return ImportResult(conversation=detail(conn, conv_id), import_job_id=job_id, analysis_run_id=run_id)

    @app.get("/api/conversations/{conversation_id}", response_model=ConversationDetail)
    def get_conversation(conn: Conn, conversation_id: str) -> ConversationDetail:
        return detail(conn, conversation_id)

    @app.delete("/api/conversations/{conversation_id}", status_code=204)
    def delete_conversation(conn: Conn, conversation_id: str) -> None:
        service.delete_conversation(conn, conversation_id)

    @app.get("/api/conversations/{conversation_id}/import")
    def import_audit(conn: Conn, conversation_id: str) -> dict:
        service.get_conversation(conn, conversation_id)
        return service.get_import_audit(conn, conversation_id)

    @app.post("/api/conversations/{conversation_id}/analyze")
    def analyze(conn: Conn, conversation_id: str, body: AnalyzeRequest | None = None) -> dict:
        from openmirror.analytics.engine import AnalysisParams

        params = AnalysisParams(session_gap_minutes=(body or AnalyzeRequest()).session_gap_minutes)
        return {"analysis_run_id": service.run_analysis(conn, conversation_id, params)}

    @app.get("/api/conversations/{conversation_id}/report", response_model=ReportOut)
    def report(conn: Conn, conversation_id: str) -> ReportOut:
        service.get_conversation(conn, conversation_id)
        run = service.latest_run(conn, conversation_id)
        return ReportOut(
            analysis_run_id=run["id"],
            created_at=run["created_at"],
            report=json.loads(run["report_json"]),
            analytics=json.loads(run["analytics_json"]),
        )

    @app.get("/api/conversations/{conversation_id}/findings/{finding_id}", response_model=FindingDetail)
    def finding(conn: Conn, conversation_id: str, finding_id: str) -> dict:
        service.get_conversation(conn, conversation_id)
        return service.get_finding(conn, conversation_id, finding_id)

    @app.get("/api/conversations/{conversation_id}/messages", response_model=MessagePage)
    def messages(
        conn: Conn,
        conversation_id: str,
        around: int | None = None,
        radius: Annotated[int, Query(ge=0, le=50)] = 6,
        q: Annotated[str | None, Query(max_length=200)] = None,
        sender_id: int | None = None,
        start: str | None = None,
        end: str | None = None,
        offset: Annotated[int, Query(ge=0)] = 0,
        limit: Annotated[int, Query(ge=1, le=500)] = 50,
    ) -> dict:
        return service.get_messages(
            conn,
            conversation_id,
            around=around,
            radius=radius,
            query=q,
            sender_id=sender_id,
            start=start,
            end=end,
            offset=offset,
            limit=limit,
        )

    return app

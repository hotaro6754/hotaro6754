"""Import pipeline: uploaded file -> decoded lines -> parsed messages -> SQLite.

Messages are inserted in batches inside a single transaction, so an import
either completes fully or leaves no partial conversation behind. The import
job row and its audit survive failures so the user can see what went wrong.
"""

from __future__ import annotations

import json
import logging
import sqlite3
import uuid
from datetime import UTC, datetime
from pathlib import Path

from openmirror.ingest.decoding import SNIFF_BYTES, DecodeStats, detect_encoding, iter_lines
from openmirror.ingest.sources import ChatSource, open_source
from openmirror.ingest.whatsapp import DateOrder, ParsedMessage, parse_export

log = logging.getLogger(__name__)

BATCH_SIZE = 2000


def _now() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat()


def _epoch(ts: datetime) -> int:
    return int(ts.replace(tzinfo=UTC).timestamp())


def _title_from_filename(name: str) -> str:
    stem = Path(name).stem
    for prefix in ("WhatsApp Chat with ", "WhatsApp Chat - ", "WhatsApp Chat "):
        if stem.startswith(prefix):
            return stem[len(prefix) :].strip() or stem
    return stem


class ImportFailedError(Exception):
    def __init__(self, message: str, job_id: str) -> None:
        super().__init__(message)
        self.job_id = job_id


def import_file(
    conn: sqlite3.Connection,
    path: Path,
    original_filename: str,
    *,
    max_text_bytes: int,
    max_zip_entries: int,
    date_order: DateOrder | None = None,
    title: str | None = None,
) -> tuple[str, str]:
    """Import an export file. Returns ``(conversation_id, import_job_id)``."""
    job_id = uuid.uuid4().hex
    safe_name = Path(original_filename).name[:255] or "upload"
    conn.execute(
        "INSERT INTO import_jobs(id, status, original_filename, file_size, started_at) VALUES (?,?,?,?,?)",
        (job_id, "running", safe_name, path.stat().st_size, _now()),
    )
    try:
        source = open_source(
            path, safe_name, max_text_bytes=max_text_bytes, max_zip_entries=max_zip_entries
        )
        conv_id = _import_source(conn, job_id, source, date_order=date_order, title=title, upload_name=safe_name)
        return conv_id, job_id
    except Exception as exc:
        # Never log message contents: only the exception type and our own message.
        log.warning("import %s failed: %s", job_id, type(exc).__name__)
        # The failure is reported to the caller; no row (and so no file name) is kept.
        conn.execute("DELETE FROM import_jobs WHERE id=?", (job_id,))
        raise ImportFailedError(str(exc), job_id) from exc


def _import_source(
    conn: sqlite3.Connection,
    job_id: str,
    source: ChatSource,
    *,
    date_order: DateOrder | None,
    title: str | None,
    upload_name: str,
) -> str:
    with source.opener() as fh:
        prefix = fh.read(SNIFF_BYTES)
    enc = detect_encoding(prefix)
    stats = DecodeStats()
    first_pass = True

    def lines():
        nonlocal first_pass
        # Replacement characters are only counted once (on the second pass).
        counting = not first_pass
        first_pass = False
        return iter_lines(source.opener, enc, stats if counting else None)

    audit, messages = parse_export(lines, date_order=date_order)

    conv_id = uuid.uuid4().hex
    conv_title = title or _title_from_filename(upload_name if source.container == "zip" else source.display_name)
    conn.execute("BEGIN")
    try:
        conn.execute(
            "INSERT INTO conversations(id, title, source_layout, imported_at, status) VALUES (?,?,?,?,?)",
            (conv_id, conv_title[:200], audit.layout, _now(), "importing"),
        )
        participant_ids: dict[str, int] = {}
        batch: list[tuple] = []
        first_ts: datetime | None = None
        last_ts: datetime | None = None

        def participant_id(name: str) -> int:
            pid = participant_ids.get(name)
            if pid is None:
                cur = conn.execute(
                    "INSERT INTO participants(conversation_id, display_name) VALUES (?,?)", (conv_id, name)
                )
                pid = int(cur.lastrowid)  # type: ignore[arg-type]
                participant_ids[name] = pid
            return pid

        def row(m: ParsedMessage) -> tuple:
            return (
                conv_id,
                m.seq,
                participant_id(m.sender) if m.sender is not None else None,
                m.ts_original,
                m.timestamp.isoformat(),
                _epoch(m.timestamp),
                m.text,
                m.message_type,
                m.media_kind,
                int(m.is_edited),
                m.line_start,
                m.line_end,
            )

        insert_sql = (
            "INSERT INTO messages(conversation_id, seq, sender_id, ts_original, ts, ts_epoch, text, "
            "message_type, media_kind, is_edited, line_start, line_end) VALUES (?,?,?,?,?,?,?,?,?,?,?,?)"
        )
        for m in messages:
            if first_ts is None or m.timestamp < first_ts:
                first_ts = m.timestamp
            if last_ts is None or m.timestamp > last_ts:
                last_ts = m.timestamp
            batch.append(row(m))
            if len(batch) >= BATCH_SIZE:
                conn.executemany(insert_sql, batch)
                batch.clear()
        if batch:
            conn.executemany(insert_sql, batch)

        conn.execute(
            """UPDATE participants SET message_count = (
                   SELECT COUNT(*) FROM messages WHERE messages.sender_id = participants.id)
               WHERE conversation_id = ?""",
            (conv_id,),
        )
        conn.execute(
            """UPDATE conversations SET status='ready', message_count=?, participant_count=?,
                   first_ts=?, last_ts=? WHERE id=?""",
            (
                audit.messages_parsed,
                len(participant_ids),
                first_ts.isoformat() if first_ts else None,
                last_ts.isoformat() if last_ts else None,
                conv_id,
            ),
        )
        notes = list(source.notes)
        if stats.replacement_chars:
            notes.append(
                f"{stats.replacement_chars} undecodable byte sequence(s) were replaced with U+FFFD."
            )
        conn.execute(
            """UPDATE import_jobs SET conversation_id=?, status='succeeded', container=?, encoding=?,
                   encoding_reason=?, replacement_chars=?, layout=?, layout_reason=?, date_order=?,
                   date_order_reason=?, date_order_ambiguous=?, lines_total=?, header_lines=?,
                   continuation_lines=?, messages_parsed=?, system_messages=?, archive_media_count=?,
                   issue_counts_json=?, notes_json=?, finished_at=? WHERE id=?""",
            (
                conv_id,
                source.container,
                enc.encoding,
                enc.reason,
                stats.replacement_chars,
                audit.layout,
                audit.layout_reason,
                audit.date_order,
                audit.date_order_reason,
                int(audit.date_order_ambiguous),
                audit.lines_total,
                audit.header_lines,
                audit.continuation_lines,
                audit.messages_parsed,
                audit.system_messages,
                source.archive_media_count,
                json.dumps(dict(audit.issue_counts)),
                json.dumps(notes),
                _now(),
                job_id,
            ),
        )
        conn.executemany(
            "INSERT INTO import_issues(import_job_id, line_no, kind, detail, excerpt) VALUES (?,?,?,?,?)",
            [(job_id, i.line_no, i.kind, i.detail, i.excerpt) for i in audit.issues],
        )
        conn.execute("COMMIT")
    except BaseException:
        conn.execute("ROLLBACK")
        raise
    log.info("import %s succeeded: %d messages", job_id, audit.messages_parsed)
    return conv_id

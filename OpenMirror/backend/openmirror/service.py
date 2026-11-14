"""Application services shared by the API and the CLI."""

from __future__ import annotations

import json
import logging
import sqlite3
import uuid
from datetime import UTC, datetime

from openmirror.analytics.engine import ENGINE_VERSION, AnalysisParams, compute, load_frames
from openmirror.evidence.findings import build_findings, validate_findings
from openmirror.report.builder import build_report

log = logging.getLogger(__name__)


def _now() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat()


class NotFoundError(LookupError):
    pass


def get_conversation(conn: sqlite3.Connection, conversation_id: str) -> dict:
    row = conn.execute("SELECT * FROM conversations WHERE id=?", (conversation_id,)).fetchone()
    if row is None:
        raise NotFoundError("conversation not found")
    return dict(row)


def list_conversations(conn: sqlite3.Connection) -> list[dict]:
    return [dict(r) for r in conn.execute("SELECT * FROM conversations ORDER BY imported_at DESC")]


def get_import_audit(conn: sqlite3.Connection, conversation_id: str) -> dict:
    row = conn.execute(
        "SELECT * FROM import_jobs WHERE conversation_id=? ORDER BY started_at DESC LIMIT 1", (conversation_id,)
    ).fetchone()
    if row is None:
        raise NotFoundError("import job not found")
    job = dict(row)
    job["issue_counts"] = json.loads(job.pop("issue_counts_json") or "{}")
    job["notes"] = json.loads(job.pop("notes_json") or "[]")
    job["date_order_ambiguous"] = bool(job["date_order_ambiguous"])
    job["issues"] = [
        dict(r)
        for r in conn.execute(
            "SELECT line_no, kind, detail, excerpt FROM import_issues WHERE import_job_id=? ORDER BY line_no, id",
            (job["id"],),
        )
    ]
    return job


def run_analysis(conn: sqlite3.Connection, conversation_id: str, params: AnalysisParams | None = None) -> str:
    """Compute analytics, findings and the report; persist them as a new run."""
    params = params or AnalysisParams()
    conversation = get_conversation(conn, conversation_id)
    audit = get_import_audit(conn, conversation_id)
    run_id = uuid.uuid4().hex
    conn.execute(
        "INSERT INTO analysis_runs(id, conversation_id, engine_version, params_json, status, created_at) "
        "VALUES (?,?,?,?,?,?)",
        (run_id, conversation_id, ENGINE_VERSION, json.dumps(params.as_dict()), "running", _now()),
    )
    try:
        frames = load_frames(conn, conversation_id, params)
        analytics = compute(frames, params)
        findings = build_findings(frames, analytics, audit)
        validate_findings(conn, conversation_id, findings)
        report = build_report(conversation, analytics, findings, audit)
    except Exception as exc:
        log.warning("analysis %s failed: %s", run_id, type(exc).__name__)
        conn.execute(
            "UPDATE analysis_runs SET status='failed', error=?, finished_at=? WHERE id=?",
            (f"{type(exc).__name__}: {exc}"[:500], _now(), run_id),
        )
        raise

    conn.execute("BEGIN")
    try:
        conn.executemany(
            """INSERT INTO findings(id, analysis_run_id, conversation_id, chapter, finding_type, title, statement,
                   method, confidence, confidence_reason, metrics_json, counterexample_note, time_start, time_end)
               VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            [
                (
                    f.id, run_id, conversation_id, f.chapter, f.finding_type, f.title, f.statement, f.method,
                    f.confidence, f.confidence_reason, json.dumps(f.metrics, default=str), f.counterexample_note,
                    f.time_start, f.time_end,
                )
                for f in findings
            ],
        )
        conn.executemany(
            "INSERT INTO evidence_references(analysis_run_id, finding_id, message_id, role, note) VALUES (?,?,?,?,?)",
            [(run_id, f.id, e.message_id, e.role, e.note) for f in findings for e in f.evidence],
        )
        conn.execute(
            "UPDATE analysis_runs SET status='succeeded', analytics_json=?, report_json=?, finished_at=? WHERE id=?",
            (json.dumps(analytics, default=str), json.dumps(report, default=str), _now(), run_id),
        )
        # Older runs are superseded; keep storage lean and avoid stale evidence.
        conn.execute(
            "DELETE FROM analysis_runs WHERE conversation_id=? AND id<>?", (conversation_id, run_id)
        )
        conn.execute("COMMIT")
    except BaseException:
        conn.execute("ROLLBACK")
        raise
    return run_id


def latest_run(conn: sqlite3.Connection, conversation_id: str) -> sqlite3.Row:
    row = conn.execute(
        "SELECT * FROM analysis_runs WHERE conversation_id=? AND status='succeeded' ORDER BY created_at DESC LIMIT 1",
        (conversation_id,),
    ).fetchone()
    if row is None:
        raise NotFoundError("no analysis available")
    return row


MESSAGE_COLUMNS = """m.id, m.seq, m.sender_id, p.display_name AS sender, m.ts_original, m.ts, m.text,
    m.message_type, m.media_kind, m.is_edited, m.line_start, m.line_end"""


def _msg(row: sqlite3.Row) -> dict:
    d = dict(row)
    d["is_edited"] = bool(d["is_edited"])
    return d


def get_finding(conn: sqlite3.Connection, conversation_id: str, finding_id: str) -> dict:
    run = latest_run(conn, conversation_id)
    row = conn.execute(
        "SELECT * FROM findings WHERE analysis_run_id=? AND id=?", (run["id"], finding_id)
    ).fetchone()
    if row is None:
        raise NotFoundError("finding not found")
    f = dict(row)
    f["metrics"] = json.loads(f.pop("metrics_json"))
    f.pop("analysis_run_id")
    evidence = conn.execute(
        f"""SELECT e.role, e.note, {MESSAGE_COLUMNS}
            FROM evidence_references e
            JOIN messages m ON m.id = e.message_id
            LEFT JOIN participants p ON p.id = m.sender_id
            WHERE e.analysis_run_id=? AND e.finding_id=? AND m.conversation_id=?
            ORDER BY e.role DESC, m.seq""",
        (run["id"], finding_id, conversation_id),
    ).fetchall()
    f["evidence"] = [
        {"role": r["role"], "note": r["note"], "message": _msg(r)} for r in evidence
    ]
    return f


def get_messages(
    conn: sqlite3.Connection,
    conversation_id: str,
    *,
    around: int | None = None,
    radius: int = 6,
    query: str | None = None,
    sender_id: int | None = None,
    start: str | None = None,
    end: str | None = None,
    offset: int = 0,
    limit: int = 50,
) -> dict:
    get_conversation(conn, conversation_id)
    limit = max(1, min(limit, 500))
    radius = max(0, min(radius, 50))
    if around is not None:
        row = conn.execute(
            "SELECT seq FROM messages WHERE id=? AND conversation_id=?", (around, conversation_id)
        ).fetchone()
        if row is None:
            raise NotFoundError("message not found")
        rows = conn.execute(
            f"""SELECT {MESSAGE_COLUMNS} FROM messages m LEFT JOIN participants p ON p.id=m.sender_id
                WHERE m.conversation_id=? AND m.seq BETWEEN ? AND ? ORDER BY m.seq""",
            (conversation_id, row["seq"] - radius, row["seq"] + radius),
        ).fetchall()
        return {"messages": [_msg(r) for r in rows], "total": len(rows), "focus_id": around}

    where = ["m.conversation_id = ?"]
    args: list = [conversation_id]
    join = ""
    if query:
        join = "JOIN messages_fts ON messages_fts.rowid = m.id"
        where.append("messages_fts MATCH ?")
        args.append(_fts_query(query))
    if sender_id is not None:
        where.append("m.sender_id = ?")
        args.append(sender_id)
    if start:
        where.append("m.ts >= ?")
        args.append(start)
    if end:
        where.append("m.ts < ?")
        args.append(end)
    clause = " AND ".join(where)
    total = conn.execute(f"SELECT COUNT(*) FROM messages m {join} WHERE {clause}", args).fetchone()[0]
    rows = conn.execute(
        f"""SELECT {MESSAGE_COLUMNS} FROM messages m {join} LEFT JOIN participants p ON p.id=m.sender_id
            WHERE {clause} ORDER BY m.seq LIMIT ? OFFSET ?""",
        (*args, limit, max(offset, 0)),
    ).fetchall()
    return {"messages": [_msg(r) for r in rows], "total": total}


def _fts_query(q: str) -> str:
    """Turn free text into a safe FTS5 query: each word quoted, all required."""
    words = [w.replace('"', '""') for w in q.split() if w.strip()][:12]
    return " ".join(f'"{w}"' for w in words) or '""'


def delete_conversation(conn: sqlite3.Connection, conversation_id: str) -> None:
    get_conversation(conn, conversation_id)
    conn.execute("BEGIN")
    try:
        conn.execute(
            "DELETE FROM evidence_references WHERE analysis_run_id IN "
            "(SELECT id FROM analysis_runs WHERE conversation_id=?)",
            (conversation_id,),
        )
        conn.execute("DELETE FROM conversations WHERE id=?", (conversation_id,))
        conn.execute("COMMIT")
    except BaseException:
        conn.execute("ROLLBACK")
        raise
    # Flush the write-ahead log so deleted rows do not linger on disk.
    conn.execute("PRAGMA wal_checkpoint(TRUNCATE)")

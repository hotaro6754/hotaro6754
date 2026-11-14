"""SQLite schema and connection management.

One local SQLite file holds everything. Foreign keys cascade so that deleting
a conversation removes its participants, messages, full-text index entries,
import audit, analysis runs, findings and evidence references.
"""

from __future__ import annotations

import sqlite3
from pathlib import Path

SCHEMA_VERSION = 1

SCHEMA = """
CREATE TABLE IF NOT EXISTS schema_meta (
    key   TEXT PRIMARY KEY,
    value TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS conversations (
    id                TEXT PRIMARY KEY,
    title             TEXT NOT NULL,
    source_platform   TEXT NOT NULL DEFAULT 'whatsapp',
    source_layout     TEXT,            -- android | ios
    imported_at       TEXT NOT NULL,
    status            TEXT NOT NULL,   -- importing | ready | failed
    message_count     INTEGER NOT NULL DEFAULT 0,
    participant_count INTEGER NOT NULL DEFAULT 0,
    first_ts          TEXT,
    last_ts           TEXT
);

CREATE TABLE IF NOT EXISTS participants (
    id              INTEGER PRIMARY KEY,
    conversation_id TEXT NOT NULL REFERENCES conversations(id) ON DELETE CASCADE,
    display_name    TEXT NOT NULL,
    message_count   INTEGER NOT NULL DEFAULT 0,
    UNIQUE (conversation_id, display_name)
);

CREATE TABLE IF NOT EXISTS messages (
    id              INTEGER PRIMARY KEY,
    conversation_id TEXT NOT NULL REFERENCES conversations(id) ON DELETE CASCADE,
    seq             INTEGER NOT NULL,          -- 1-based order in the source file
    sender_id       INTEGER REFERENCES participants(id) ON DELETE CASCADE,  -- NULL = system notice
    ts_original     TEXT NOT NULL,             -- timestamp exactly as written in the export
    ts              TEXT NOT NULL,             -- parsed, ISO-8601, local time of the exporting device
    ts_epoch        INTEGER NOT NULL,          -- seconds, treating ts as UTC (ordering/arithmetic only)
    text            TEXT NOT NULL,             -- original body, continuation lines joined with \\n
    message_type    TEXT NOT NULL,             -- text|media|deleted|system|location|contact|poll|call
    media_kind      TEXT,
    is_edited       INTEGER NOT NULL DEFAULT 0,
    line_start      INTEGER NOT NULL,          -- 1-based source line numbers (inclusive)
    line_end        INTEGER NOT NULL,
    UNIQUE (conversation_id, seq)
);
CREATE INDEX IF NOT EXISTS idx_messages_conv_ts ON messages(conversation_id, ts_epoch);
CREATE INDEX IF NOT EXISTS idx_messages_sender ON messages(sender_id);

CREATE VIRTUAL TABLE IF NOT EXISTS messages_fts USING fts5(
    text, content='messages', content_rowid='id', tokenize='unicode61 remove_diacritics 2'
);
CREATE TRIGGER IF NOT EXISTS messages_ai AFTER INSERT ON messages BEGIN
    INSERT INTO messages_fts(rowid, text) VALUES (new.id, new.text);
END;
CREATE TRIGGER IF NOT EXISTS messages_ad AFTER DELETE ON messages BEGIN
    INSERT INTO messages_fts(messages_fts, rowid, text) VALUES ('delete', old.id, old.text);
END;

CREATE TABLE IF NOT EXISTS import_jobs (
    id                    TEXT PRIMARY KEY,
    conversation_id       TEXT REFERENCES conversations(id) ON DELETE CASCADE,
    status                TEXT NOT NULL,      -- running | succeeded | failed
    original_filename     TEXT NOT NULL,
    container             TEXT,               -- txt | zip
    file_size             INTEGER,
    encoding              TEXT,
    encoding_reason       TEXT,
    replacement_chars     INTEGER NOT NULL DEFAULT 0,
    layout                TEXT,
    layout_reason         TEXT,
    date_order            TEXT,
    date_order_reason     TEXT,
    date_order_ambiguous  INTEGER NOT NULL DEFAULT 0,
    lines_total           INTEGER NOT NULL DEFAULT 0,
    header_lines          INTEGER NOT NULL DEFAULT 0,
    continuation_lines    INTEGER NOT NULL DEFAULT 0,
    messages_parsed       INTEGER NOT NULL DEFAULT 0,
    system_messages       INTEGER NOT NULL DEFAULT 0,
    archive_media_count   INTEGER NOT NULL DEFAULT 0,
    issue_counts_json     TEXT NOT NULL DEFAULT '{}',
    notes_json            TEXT NOT NULL DEFAULT '[]',
    started_at            TEXT NOT NULL,
    finished_at           TEXT,
    error                 TEXT
);

CREATE TABLE IF NOT EXISTS import_issues (
    id            INTEGER PRIMARY KEY,
    import_job_id TEXT NOT NULL REFERENCES import_jobs(id) ON DELETE CASCADE,
    line_no       INTEGER NOT NULL,
    kind          TEXT NOT NULL,
    detail        TEXT NOT NULL,
    excerpt       TEXT
);

CREATE TABLE IF NOT EXISTS analysis_runs (
    id              TEXT PRIMARY KEY,
    conversation_id TEXT NOT NULL REFERENCES conversations(id) ON DELETE CASCADE,
    engine_version  TEXT NOT NULL,
    params_json     TEXT NOT NULL,
    status          TEXT NOT NULL,     -- running | succeeded | failed
    created_at      TEXT NOT NULL,
    finished_at     TEXT,
    analytics_json  TEXT,              -- deterministic metric tables
    report_json     TEXT,              -- structured report
    error           TEXT
);

CREATE TABLE IF NOT EXISTS findings (
    id                 TEXT NOT NULL,
    analysis_run_id    TEXT NOT NULL REFERENCES analysis_runs(id) ON DELETE CASCADE,
    conversation_id    TEXT NOT NULL REFERENCES conversations(id) ON DELETE CASCADE,
    chapter            TEXT NOT NULL,
    finding_type       TEXT NOT NULL,
    title              TEXT NOT NULL,
    statement          TEXT NOT NULL,
    method             TEXT NOT NULL,
    confidence         TEXT NOT NULL,   -- high | medium | low
    confidence_reason  TEXT NOT NULL,
    metrics_json       TEXT NOT NULL,
    counterexample_note TEXT,
    time_start         TEXT,
    time_end           TEXT,
    PRIMARY KEY (analysis_run_id, id)
);

CREATE TABLE IF NOT EXISTS evidence_references (
    id              INTEGER PRIMARY KEY,
    analysis_run_id TEXT NOT NULL,
    finding_id      TEXT NOT NULL,
    message_id      INTEGER NOT NULL REFERENCES messages(id) ON DELETE CASCADE,
    role            TEXT NOT NULL,      -- support | counterexample
    note            TEXT,
    FOREIGN KEY (analysis_run_id, finding_id) REFERENCES findings(analysis_run_id, id) ON DELETE CASCADE
);
CREATE INDEX IF NOT EXISTS idx_evidence_finding ON evidence_references(analysis_run_id, finding_id);
"""


def connect(db_path: Path) -> sqlite3.Connection:
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(db_path, check_same_thread=False, isolation_level=None)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    conn.execute("PRAGMA journal_mode = WAL")
    conn.execute("PRAGMA synchronous = NORMAL")
    # Freed pages are zeroed so deleted conversations do not linger in the file.
    conn.execute("PRAGMA secure_delete = ON")
    return conn


def init_db(conn: sqlite3.Connection) -> None:
    conn.executescript(SCHEMA)
    conn.execute(
        "INSERT OR REPLACE INTO schema_meta(key, value) VALUES ('schema_version', ?)",
        (str(SCHEMA_VERSION),),
    )

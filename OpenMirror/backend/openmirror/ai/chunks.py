"""Split a conversation into model-sized excerpts.

Excerpts follow session boundaries (a session never straddles two excerpts
unless it is itself too long), so the model reads whole conversations. Each
line carries its message id (``#1234``) so the model can cite it.
"""

from __future__ import annotations

import hashlib
import sqlite3
from dataclasses import dataclass, field
from datetime import datetime

MAX_LINE_CHARS = 400
PLACEHOLDERS = {
    "media": "[media]",
    "deleted": "[deleted message]",
    "location": "[shared a location]",
    "contact": "[shared a contact]",
    "call": "[call]",
    "poll": "[poll]",
}


@dataclass
class Message:
    id: int
    ts: datetime
    sender: str
    text: str
    kind: str


@dataclass
class Chunk:
    index: int
    messages: list[Message] = field(default_factory=list)
    chars: int = 0

    @property
    def ids(self) -> set[int]:
        return {m.id for m in self.messages}

    @property
    def start(self) -> datetime:
        return self.messages[0].ts

    @property
    def end(self) -> datetime:
        return self.messages[-1].ts

    def render(self) -> str:
        return "\n".join(format_line(m) for m in self.messages)


def format_line(m: Message) -> str:
    body = PLACEHOLDERS.get(m.kind) or m.text.replace("\r", "").replace("\n", " / ")
    if len(body) > MAX_LINE_CHARS:
        body = body[:MAX_LINE_CHARS] + "…"
    return f"#{m.id} {m.ts:%Y-%m-%d %H:%M} {m.sender}: {body}"


def load_messages(conn: sqlite3.Connection, conversation_id: str) -> list[Message]:
    rows = conn.execute(
        """SELECT m.id, m.ts, p.display_name, m.text, m.message_type
           FROM messages m JOIN participants p ON p.id = m.sender_id
           WHERE m.conversation_id = ? ORDER BY m.seq""",
        (conversation_id,),
    ).fetchall()
    return [Message(r[0], datetime.fromisoformat(r[1]), r[2], r[3], r[4]) for r in rows]


def build_chunks(messages: list[Message], max_chars: int = 9000, session_gap_minutes: int = 240) -> list[Chunk]:
    # Group into sessions first.
    sessions: list[list[Message]] = []
    for m in messages:
        if sessions and (m.ts - sessions[-1][-1].ts).total_seconds() <= session_gap_minutes * 60:
            sessions[-1].append(m)
        else:
            sessions.append([m])

    chunks: list[Chunk] = []
    current = Chunk(0)

    def push(m: Message) -> None:
        nonlocal current
        size = len(format_line(m)) + 1
        if current.messages and current.chars + size > max_chars:
            chunks.append(current)
            current = Chunk(len(chunks))
        current.messages.append(m)
        current.chars += size

    for s in sessions:
        size = sum(len(format_line(m)) + 1 for m in s)
        if current.messages and current.chars + size > max_chars and size <= max_chars:
            chunks.append(current)
            current = Chunk(len(chunks))
        for m in s:
            push(m)
    if current.messages:
        chunks.append(current)
    return chunks


def select_chunks(chunks: list[Chunk], limit: int | None) -> list[Chunk]:
    """Evenly spaced subset for a quick read (deterministic)."""
    if not limit or limit >= len(chunks):
        return chunks
    if limit == 1:
        return [chunks[len(chunks) // 2]]
    step = (len(chunks) - 1) / (limit - 1)
    picked = sorted({round(i * step) for i in range(limit)})
    return [chunks[i] for i in picked]


def chunking_key(model: str, max_chars: int, gap: int, prompt_version: str, chunk: Chunk) -> str:
    """Cache key for one excerpt's notes: same model, prompt and content → reuse."""
    h = hashlib.sha256()
    h.update(f"{model}|{max_chars}|{gap}|{prompt_version}|".encode())
    h.update(chunk.render().encode())
    return h.hexdigest()

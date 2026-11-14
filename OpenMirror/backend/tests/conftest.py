from __future__ import annotations

import sys
from collections.abc import Callable, Iterable
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from openmirror.ingest.whatsapp import ParsedMessage, ParseAudit, parse_export  # noqa: E402
from openmirror.storage.db import connect, init_db  # noqa: E402


def lines_of(text: str) -> Callable[[], Iterable[str]]:
    rows = text.replace("\r\n", "\n").split("\n")
    if rows and rows[-1] == "":
        rows = rows[:-1]
    return lambda: iter(rows)


def parse_text(text: str, **kw) -> tuple[ParseAudit, list[ParsedMessage]]:
    audit, it = parse_export(lines_of(text), **kw)
    return audit, list(it)


@pytest.fixture
def conn(tmp_path: Path):
    c = connect(tmp_path / "test.sqlite3")
    init_db(c)
    yield c
    c.close()

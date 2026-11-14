"""Encoding detection and upload/ZIP safety tests (fictional data only)."""

from __future__ import annotations

import codecs
import io
import zipfile
from pathlib import Path

import pytest

from openmirror.ingest.decoding import detect_encoding
from openmirror.ingest.sources import UnsafeArchiveError, UnsupportedUploadError, open_source
from openmirror.storage.importer import ImportFailedError, import_file
from openmirror.synthetic import generate_two_person, render_android, render_ios, write_zip

SMALL = "12/01/2024, 21:04 - Asha: héllo ✨\n12/01/2024, 21:05 - Ravi: नमस्ते, ఎలా ఉన్నావు?\nsecond line\n"
LIMITS = dict(max_text_bytes=50 * 1024 * 1024, max_zip_entries=100)


@pytest.mark.parametrize(
    "encoded,expected",
    [
        (SMALL.encode("utf-8"), "utf-8"),
        (codecs.BOM_UTF8 + SMALL.encode("utf-8"), "utf-8-sig"),
        (SMALL.encode("utf-16"), "utf-16"),
        (codecs.BOM_UTF16_BE + SMALL.encode("utf-16-be"), "utf-16"),
        (SMALL.encode("utf-16-le"), "utf-16-le"),
        (SMALL.encode("utf-16-be"), "utf-16-be"),
    ],
)
def test_encodings_round_trip(conn, tmp_path: Path, encoded: bytes, expected: str):
    assert detect_encoding(encoded).encoding == expected
    path = tmp_path / "chat.txt"
    path.write_bytes(encoded)
    conv_id, _ = import_file(conn, path, "WhatsApp Chat with Ravi.txt", **LIMITS)
    rows = conn.execute("SELECT text FROM messages WHERE conversation_id=? ORDER BY seq", (conv_id,)).fetchall()
    assert [r[0] for r in rows] == ["héllo ✨", "नमस्ते, ఎలా ఉన్నావు?\nsecond line"]


def test_invalid_utf8_bytes_are_counted_not_dropped(conn, tmp_path: Path):
    path = tmp_path / "chat.txt"
    path.write_bytes(b"12/01/2024, 21:04 - Asha: bad \xff\xfe byte\n12/01/2024, 21:05 - Ravi: ok\n")
    conv_id, job_id = import_file(conn, path, "chat.txt", **LIMITS)
    job = conn.execute("SELECT replacement_chars, notes_json FROM import_jobs WHERE id=?", (job_id,)).fetchone()
    assert job["replacement_chars"] == 2
    assert "undecodable" in job["notes_json"]
    assert conn.execute("SELECT COUNT(*) FROM messages WHERE conversation_id=?", (conv_id,)).fetchone()[0] == 2


def test_ios_zip_import(conn, tmp_path: Path):
    path = tmp_path / "WhatsApp Chat - Ravi.zip"
    write_zip(path, render_ios(generate_two_person()))
    conv_id, job_id = import_file(conn, path, path.name, **LIMITS)
    conv = conn.execute("SELECT * FROM conversations WHERE id=?", (conv_id,)).fetchone()
    assert conv["title"] == "Ravi"
    assert conv["message_count"] == len(generate_two_person())
    job = conn.execute("SELECT * FROM import_jobs WHERE id=?", (job_id,)).fetchone()
    assert job["container"] == "zip" and job["archive_media_count"] == 1 and job["layout"] == "ios"


def _zip(entries: dict[str, bytes]) -> bytes:
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        for name, data in entries.items():
            zf.writestr(name, data)
    return buf.getvalue()


@pytest.mark.parametrize("bad_name", ["../evil.txt", "/etc/passwd", "a/../../b.txt", "C:/windows/x.txt"])
def test_zip_path_traversal_rejected(tmp_path: Path, bad_name: str):
    path = tmp_path / "x.zip"
    path.write_bytes(_zip({"_chat.txt": SMALL.encode(), bad_name: b"x"}))
    with pytest.raises(UnsafeArchiveError):
        open_source(path, "x.zip", **LIMITS)


def test_zip_without_chat_rejected(tmp_path: Path):
    path = tmp_path / "x.zip"
    path.write_bytes(_zip({"photo.jpg": b"x"}))
    with pytest.raises(UnsupportedUploadError):
        open_source(path, "x.zip", **LIMITS)


def test_zip_with_ambiguous_text_files_rejected(tmp_path: Path):
    path = tmp_path / "x.zip"
    path.write_bytes(_zip({"notes.txt": b"a", "other.txt": b"b"}))
    with pytest.raises(UnsupportedUploadError):
        open_source(path, "x.zip", **LIMITS)


def test_zip_bomb_ratio_rejected(tmp_path: Path):
    path = tmp_path / "x.zip"
    path.write_bytes(_zip({"_chat.txt": b"\n" * (20 * 1024 * 1024)}))
    with pytest.raises(UnsafeArchiveError):
        open_source(path, "x.zip", **LIMITS)


def test_zip_too_many_entries_rejected(tmp_path: Path):
    path = tmp_path / "x.zip"
    path.write_bytes(_zip({f"f{i}.jpg": b"x" for i in range(5)} | {"_chat.txt": SMALL.encode()}))
    with pytest.raises(UnsafeArchiveError):
        open_source(path, "x.zip", max_text_bytes=10**6, max_zip_entries=3)


def test_fake_zip_rejected(tmp_path: Path):
    path = tmp_path / "x.zip"
    path.write_bytes(b"not a zip at all")
    with pytest.raises(UnsupportedUploadError):
        open_source(path, "x.zip", **LIMITS)


def test_text_over_limit_rejected(tmp_path: Path):
    path = tmp_path / "chat.txt"
    path.write_text(render_android(generate_two_person()))
    with pytest.raises(UnsupportedUploadError):
        open_source(path, "chat.txt", max_text_bytes=1000, max_zip_entries=10)


def test_failed_import_leaves_nothing_behind(conn, tmp_path: Path):
    path = tmp_path / "notes.txt"
    path.write_text("shopping list\nmilk\n")
    with pytest.raises(ImportFailedError):
        import_file(conn, path, "notes.txt", **LIMITS)
    for table in ("conversations", "messages", "participants", "import_jobs"):
        assert conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0] == 0

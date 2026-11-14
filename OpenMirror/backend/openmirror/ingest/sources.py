"""Resolve an uploaded file into a re-readable chat-text source.

Uploads are either a bare ``.txt`` export or a ``.zip`` produced by
"Export chat" (iOS always zips; Android zips when media is included).

Archive members are *never* extracted to disk and never executed. We only
open the single chat-text member as a read-only stream. Member names are still
validated so that a malicious archive is rejected rather than half-processed.
"""

from __future__ import annotations

import io
import zipfile
from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path, PurePosixPath
from typing import BinaryIO


class UnsafeArchiveError(ValueError):
    """Raised when an uploaded archive is malformed or potentially malicious."""


class UnsupportedUploadError(ValueError):
    """Raised when an upload is not a recognisable WhatsApp export."""


@dataclass
class ChatSource:
    opener: Callable[[], BinaryIO]
    display_name: str
    container: str  # "txt" or "zip"
    uncompressed_size: int
    archive_member_count: int = 0
    archive_media_count: int = 0
    notes: list[str] = field(default_factory=list)


MEDIA_SUFFIXES = {
    ".jpg", ".jpeg", ".png", ".webp", ".gif", ".heic", ".mp4", ".mov", ".3gp", ".opus",
    ".ogg", ".m4a", ".mp3", ".aac", ".pdf", ".vcf", ".docx", ".doc", ".xlsx", ".pptx", ".txt",
}

ZIP_MAGIC = b"PK\x03\x04"
ZIP_EMPTY_MAGIC = b"PK\x05\x06"


def _is_unsafe_member_name(name: str) -> bool:
    if "\x00" in name:
        return True
    normalised = name.replace("\\", "/")
    if normalised.startswith("/") or (len(normalised) > 1 and normalised[1] == ":"):
        return True
    return any(part == ".." for part in PurePosixPath(normalised).parts)


def _choose_chat_member(names: list[str]) -> str:
    txt = [n for n in names if n.lower().endswith(".txt") and not n.endswith("/")]
    if not txt:
        raise UnsupportedUploadError("The ZIP archive does not contain a chat .txt file.")
    # iOS names the transcript "_chat.txt"; Android uses "WhatsApp Chat with X.txt".
    preferred = [n for n in txt if PurePosixPath(n).name.lower() == "_chat.txt"]
    if not preferred:
        preferred = [n for n in txt if PurePosixPath(n).name.lower().startswith("whatsapp chat")]
    if len(preferred) == 1:
        return preferred[0]
    if len(txt) == 1:
        return txt[0]
    raise UnsupportedUploadError(
        "The ZIP archive contains several .txt files and none is clearly the chat transcript."
    )


def open_source(
    path: Path,
    original_filename: str,
    *,
    max_text_bytes: int,
    max_zip_entries: int,
) -> ChatSource:
    """Inspect an uploaded file on disk and return a :class:`ChatSource`."""
    with path.open("rb") as fh:
        magic = fh.read(4)

    if magic in (ZIP_MAGIC, ZIP_EMPTY_MAGIC):
        return _open_zip(path, max_text_bytes=max_text_bytes, max_zip_entries=max_zip_entries)

    if original_filename.lower().endswith(".zip"):
        raise UnsupportedUploadError("The file has a .zip name but is not a valid ZIP archive.")

    size = path.stat().st_size
    if size == 0:
        raise UnsupportedUploadError("The uploaded file is empty.")
    if size > max_text_bytes:
        raise UnsupportedUploadError("The chat text exceeds the configured size limit.")
    return ChatSource(
        opener=lambda: path.open("rb"),
        display_name=Path(original_filename).name,
        container="txt",
        uncompressed_size=size,
    )


def _open_zip(path: Path, *, max_text_bytes: int, max_zip_entries: int) -> ChatSource:
    try:
        zf = zipfile.ZipFile(path)
    except zipfile.BadZipFile as exc:
        raise UnsafeArchiveError("The ZIP archive is corrupt or unreadable.") from exc

    with zf:
        infos = zf.infolist()
        if len(infos) > max_zip_entries:
            raise UnsafeArchiveError(f"The ZIP archive has more than {max_zip_entries} entries.")
        for info in infos:
            if _is_unsafe_member_name(info.filename):
                raise UnsafeArchiveError(
                    "The ZIP archive contains an unsafe path (absolute path or '..' traversal)."
                )
        names = [i.filename for i in infos]
        member = _choose_chat_member(names)
        info = zf.getinfo(member)
        if info.flag_bits & 0x1:
            raise UnsafeArchiveError("Encrypted ZIP archives are not supported.")
        if info.file_size > max_text_bytes:
            raise UnsafeArchiveError("The chat text inside the ZIP exceeds the configured size limit.")
        # Guard against decompression bombs that lie about their declared size.
        if info.compress_size and info.file_size / max(info.compress_size, 1) > 1000:
            raise UnsafeArchiveError("The chat text has a suspicious compression ratio.")
        media = sum(
            1
            for n in names
            if n != member and PurePosixPath(n).suffix.lower() in MEDIA_SUFFIXES
        )
        declared = info.file_size

    def opener() -> BinaryIO:
        archive = zipfile.ZipFile(path)
        raw = archive.open(member)
        return io.BufferedReader(_BoundedZipStream(archive, raw, limit=max(declared, 1)))

    return ChatSource(
        opener=opener,
        display_name=PurePosixPath(member).name,
        container="zip",
        uncompressed_size=declared,
        archive_member_count=len(names),
        archive_media_count=media,
        notes=[f"{media} media file(s) in the archive were not read (media analysis is out of scope)."]
        if media
        else [],
    )


class _BoundedZipStream(io.RawIOBase):
    """A read-only stream over a ZIP member that refuses to exceed its declared size."""

    def __init__(self, archive: zipfile.ZipFile, raw: BinaryIO, limit: int) -> None:
        super().__init__()
        self._archive = archive
        self._raw = raw
        self._limit = limit
        self._read = 0

    def readable(self) -> bool:
        return True

    def readinto(self, b) -> int:  # type: ignore[no-untyped-def]
        data = self._raw.read(len(b))
        self._read += len(data)
        if self._read > self._limit:
            raise UnsafeArchiveError("The ZIP member decompressed beyond its declared size.")
        b[: len(data)] = data
        return len(data)

    def close(self) -> None:
        if not self.closed:
            self._raw.close()
            self._archive.close()
        super().close()

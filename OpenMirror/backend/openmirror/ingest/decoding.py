"""Text-encoding detection and streaming line iteration.

WhatsApp exports are normally UTF-8 (sometimes with a BOM). Some tools and
older Windows workflows re-save them as UTF-16. We detect the encoding from a
small prefix of the file and then stream the file line by line, so large
exports are never fully loaded into memory.
"""

from __future__ import annotations

import codecs
import io
from collections.abc import Callable, Iterator
from dataclasses import dataclass
from typing import BinaryIO

SNIFF_BYTES = 64 * 1024


@dataclass
class EncodingInfo:
    encoding: str
    had_bom: bool
    reason: str


def detect_encoding(prefix: bytes) -> EncodingInfo:
    """Detect the text encoding of an export from its first bytes."""
    if prefix.startswith(codecs.BOM_UTF8):
        return EncodingInfo("utf-8-sig", True, "UTF-8 byte-order mark")
    if prefix.startswith(codecs.BOM_UTF16_LE):
        return EncodingInfo("utf-16", True, "UTF-16 little-endian byte-order mark")
    if prefix.startswith(codecs.BOM_UTF16_BE):
        return EncodingInfo("utf-16", True, "UTF-16 big-endian byte-order mark")

    sample = prefix[:4096]
    if len(sample) >= 4:
        even_nuls = sample[0::2].count(0)
        odd_nuls = sample[1::2].count(0)
        half = len(sample) / 2
        # Mostly-ASCII UTF-16 text has a NUL in every other byte.
        if odd_nuls > 0.3 * half and even_nuls < 0.05 * half:
            return EncodingInfo("utf-16-le", False, "UTF-16LE detected from NUL byte pattern")
        if even_nuls > 0.3 * half and odd_nuls < 0.05 * half:
            return EncodingInfo("utf-16-be", False, "UTF-16BE detected from NUL byte pattern")

    try:
        # A truncated multi-byte sequence at the end of the sniff window is fine.
        codecs.getincrementaldecoder("utf-8")("strict").decode(prefix, final=False)
        return EncodingInfo("utf-8", False, "valid UTF-8")
    except UnicodeDecodeError:
        return EncodingInfo(
            "utf-8", False, "invalid UTF-8 bytes found; undecodable bytes are replaced and counted"
        )


@dataclass
class DecodeStats:
    replacement_chars: int = 0


def iter_lines(
    opener: Callable[[], BinaryIO], info: EncodingInfo, stats: DecodeStats | None = None
) -> Iterator[str]:
    """Yield decoded lines (without line terminators) from a binary stream.

    Universal newline handling converts CRLF/CR to LF. Unicode line separators
    (U+2028) inside messages are *not* treated as line breaks, matching how
    WhatsApp writes multiline messages with real newlines.
    """
    raw = opener()
    try:
        text = io.TextIOWrapper(raw, encoding=info.encoding, errors="replace", newline=None)
        for line in text:
            if line.endswith("\n"):
                line = line[:-1]
            if stats is not None and "�" in line:
                stats.replacement_chars += line.count("�")
            yield line
    finally:
        raw.close()

"""WhatsApp chat-export parser.

Supported layouts
-----------------
Android::

    31/12/2023, 22:15 - Alice: Hello
    12/31/23, 10:15 PM - Alice: Hello
    31.12.23, 22:15 - Alice: Hello

iOS::

    [31/12/2023, 22:15:03] Alice: Hello
    [12/31/23, 10:15:03 PM] Alice: Hello

Design rules
------------
* The parser streams the file twice: a cheap first pass inspects only the
  headers (to infer layout and day/month order); the second pass yields
  messages. Nothing but a bounded sample of dates is held in memory.
* Lines that do not start a new message are continuation lines of the previous
  message (multiline messages). Text that appears before the first message is
  never dropped: it is reported as an "orphan" import issue.
* Anything ambiguous (day/month order, header-like lines with impossible
  dates, out-of-order timestamps, suspicious sender names) is recorded in the
  import audit rather than silently resolved.
"""

from __future__ import annotations

import re
from collections import Counter
from collections.abc import Callable, Iterable, Iterator
from dataclasses import dataclass, field
from datetime import datetime
from typing import Literal

DateOrder = Literal["DMY", "MDY", "YMD"]
Layout = Literal["android", "ios"]

_BIDI = "‎‏‪‫‬‭‮⁦⁧⁨⁩﻿"
_BIDI_RE = re.compile(f"[{_BIDI}]")
_SPACE = r"[   ]"
_DATE = r"(?P<date>\d{1,4}[./\-]\d{1,2}[./\-]\d{1,4})\.?"
_TIME = (
    r"(?P<time>\d{1,2}[:.]\d{2}(?:[:.]\d{2})?"
    rf"(?:{_SPACE}?(?P<ampm>[AaPp]\.?{_SPACE}?[Mm]\.?))?)"
)

ANDROID_HEADER = re.compile(rf"^[{_BIDI}]*{_DATE},?{_SPACE}{_TIME}{_SPACE}[-–]{_SPACE}(?P<rest>.*)$")
IOS_HEADER = re.compile(rf"^[{_BIDI}]*\[{_DATE},?{_SPACE}{_TIME}\]{_SPACE}(?P<rest>.*)$")
_TIME_PARTS = re.compile(r"(\d{1,2})[:.](\d{2})(?:[:.](\d{2}))?")
_DATE_PARTS = re.compile(r"(\d{1,4})[./\-](\d{1,2})[./\-](\d{1,4})")

# --- Message classification -------------------------------------------------

_EDITED_RE = re.compile(r"\s*[‎]?<This message was edited>\s*$")

_MEDIA_PATTERNS: list[tuple[re.Pattern[str], str]] = [
    (re.compile(r"^<Media omitted>$", re.I), "unknown"),
    (re.compile(r"^image omitted$", re.I), "image"),
    (re.compile(r"^video omitted$", re.I), "video"),
    (re.compile(r"^audio omitted$", re.I), "audio"),
    (re.compile(r"^sticker omitted$", re.I), "sticker"),
    (re.compile(r"^GIF omitted$", re.I), "gif"),
    (re.compile(r"^document omitted$", re.I), "document"),
    (re.compile(r"^<View once (?:voice )?message omitted>$", re.I), "view_once"),
    (re.compile(r"^.*\.(?:jpe?g|png|webp|heic)\s*\(file attached\)", re.I), "image"),
    (re.compile(r"^.*\.(?:mp4|mov|3gp)\s*\(file attached\)", re.I), "video"),
    (re.compile(r"^.*\.(?:opus|ogg|m4a|mp3|aac)\s*\(file attached\)", re.I), "audio"),
    (re.compile(r"^.*\.webp\s*\(file attached\)", re.I), "sticker"),
    (re.compile(r"^.*\(file attached\)", re.I), "document"),
    (re.compile(r"^<attached: .*-PHOTO-.*>$", re.I), "image"),
    (re.compile(r"^<attached: .*-VIDEO-.*>$", re.I), "video"),
    (re.compile(r"^<attached: .*-AUDIO-.*>$", re.I), "audio"),
    (re.compile(r"^<attached: .*-STICKER-.*>$", re.I), "sticker"),
    (re.compile(r"^<attached: .*>$", re.I), "document"),
    (re.compile(r"^null$"), "unavailable"),
]

_DELETED_RE = re.compile(
    r"^(?:This message was deleted|You deleted this message)\.?$", re.I
)
_CONTACT_RE = re.compile(r"^(?:Contact card omitted|.*\.vcf\s*\(file attached\))$", re.I)
_LOCATION_RE = re.compile(r"^(?:(?:live )?location: https?://|live location shared$|live location ended$)", re.I)
_POLL_RE = re.compile(r"^POLL:", re.I)
_CALL_RE = re.compile(
    r"^(?:Missed (?:voice|video|group voice|group video) call|(?:Voice|Video) call(?:, .*)?|"
    r"(?:Silenced|Declined) (?:voice|video) call.*)$",
    re.I,
)

# Notices WhatsApp writes into the transcript. Matched against the full "rest"
# of an Android line, or against the body of an iOS line.
_SYSTEM_PHRASES = re.compile(
    r"(?:Messages (?:and calls )?(?:to this group )?are (?:now )?(?:end-to-end encrypted|secured with end-to-end encryption)"
    r"|end-to-end encrypted\. No one outside of this chat"
    r"|created (?:group|this group)|created the group"
    r"|\badded\b|\bremoved\b|\bleft$|\bjoined using\b|\bjoined\b.*\binvite link\b"
    r"|changed the (?:subject|group description|group name|settings)"
    r"|changed (?:this|the) group'?s? (?:icon|settings|description|name)|deleted this group'?s? icon"
    r"|changed (?:their|his|her) phone number|changed to \+?\d"
    r"|Your security code with .* changed|security code changed"
    r"|is now an admin|You're now an admin|no longer an admin"
    r"|turned (?:on|off) disappearing messages|Disappearing messages"
    r"|This chat is with a business account|This business (?:account|is)"
    r"|pinned a message|unpinned a message"
    r"|Tap to learn more|Tap for more info"
    r"|You blocked this contact|You unblocked this contact"
    r"|Waiting for this message|Missed (?:voice|video) call)",
    re.I,
)
# Phrases that indicate the text before ": " is part of a notice, not a name.
_SYSTEM_SENDER_HINT = re.compile(
    r"(?:\bchanged\b|\bcreated\b|\badded\b|\bremoved\b|\bjoined\b|\bleft\b|\bturned\b|\bpinned\b|\")",
    re.I,
)

MAX_SENDER_LEN = 80
# Issue kinds that are expected quirks of WhatsApp exports rather than problems.
NOTICE_KINDS = frozenset({"out_of_order_timestamp"})
MAX_STORED_ISSUES_PER_KIND = 200
DATE_SAMPLE_LIMIT = 50_000


# --- Data structures ----------------------------------------------------------


@dataclass
class ParsedMessage:
    seq: int
    sender: str | None
    ts_original: str
    timestamp: datetime
    text: str
    message_type: str
    media_kind: str | None
    is_edited: bool
    line_start: int
    line_end: int


@dataclass
class ImportIssue:
    line_no: int
    kind: str
    detail: str
    excerpt: str | None = None


@dataclass
class ParseAudit:
    layout: Layout | None = None
    layout_reason: str = ""
    date_order: DateOrder | None = None
    date_order_reason: str = ""
    date_order_ambiguous: bool = False
    lines_total: int = 0
    header_lines: int = 0
    continuation_lines: int = 0
    messages_parsed: int = 0
    system_messages: int = 0
    issue_counts: Counter[str] = field(default_factory=Counter)
    issues: list[ImportIssue] = field(default_factory=list)
    sender_counts: Counter[str] = field(default_factory=Counter)

    def add_issue(self, issue: ImportIssue) -> None:
        self.issue_counts[issue.kind] += 1
        if self.issue_counts[issue.kind] <= MAX_STORED_ISSUES_PER_KIND:
            self.issues.append(issue)


class NotAWhatsAppExportError(ValueError):
    """Raised when no WhatsApp message headers can be found."""


# --- Header scanning and date-order inference ----------------------------------


@dataclass
class _HeaderScan:
    android: int = 0
    ios: int = 0
    android_dates: list[tuple[str, str, str]] = field(default_factory=list)
    ios_dates: list[tuple[str, str, str]] = field(default_factory=list)


def _scan_headers(lines: Iterable[str]) -> _HeaderScan:
    scan = _HeaderScan()
    for line in lines:
        m = IOS_HEADER.match(line)
        if m:
            scan.ios += 1
            if len(scan.ios_dates) < DATE_SAMPLE_LIMIT:
                dm = _DATE_PARTS.match(m.group("date"))
                if dm:
                    scan.ios_dates.append(dm.groups())  # type: ignore[arg-type]
            continue
        m = ANDROID_HEADER.match(line)
        if m:
            scan.android += 1
            if len(scan.android_dates) < DATE_SAMPLE_LIMIT:
                dm = _DATE_PARTS.match(m.group("date"))
                if dm:
                    scan.android_dates.append(dm.groups())  # type: ignore[arg-type]
    return scan


def _year(raw: str) -> int:
    y = int(raw)
    return 2000 + y if len(raw) <= 2 else y


def _make_date(parts: tuple[str, str, str], order: DateOrder) -> tuple[int, int, int] | None:
    a, b, c = parts
    if order == "YMD":
        y, mo, d = _year(a), int(b), int(c)
    elif order == "DMY":
        d, mo, y = int(a), int(b), _year(c)
    else:
        mo, d, y = int(a), int(b), _year(c)
    try:
        datetime(y, mo, d)
    except ValueError:
        return None
    return (y, mo, d)


def infer_date_order(samples: list[tuple[str, str, str]]) -> tuple[DateOrder, str, bool]:
    """Infer the day/month order of a set of date strings.

    Returns ``(order, reason, ambiguous)``. The reasoning is deliberately
    simple and reported to the user verbatim.
    """
    if not samples:
        return "DMY", "no dates found; defaulted to day/month/year", True
    if all(len(s[0]) == 4 for s in samples):
        return "YMD", "dates start with a four-digit year", False

    first_gt12 = sum(1 for s in samples if int(s[0]) > 12)
    second_gt12 = sum(1 for s in samples if int(s[1]) > 12)
    if first_gt12 and not second_gt12:
        return "DMY", f"{first_gt12} date(s) have a first component above 12, so it must be the day", False
    if second_gt12 and not first_gt12:
        return "MDY", f"{second_gt12} date(s) have a second component above 12, so it must be the day", False

    # Either no disambiguating values, or contradictory ones. Fall back to the
    # interpretation under which the transcript is most chronological.
    def score(order: DateOrder) -> tuple[int, int]:
        invalid = 0
        backwards = 0
        prev: tuple[int, int, int] | None = None
        for s in samples:
            d = _make_date(s, order)
            if d is None:
                invalid += 1
                continue
            if prev is not None and d < prev:
                backwards += 1
            prev = d
        return invalid, backwards

    dmy, mdy = score("DMY"), score("MDY")
    if dmy == mdy:
        return (
            "DMY",
            "day and month cannot be distinguished from the data; defaulted to day/month/year "
            "(override with date order MDY if this is wrong)",
            True,
        )
    order: DateOrder = "DMY" if dmy < mdy else "MDY"
    other = mdy if order == "DMY" else dmy
    chosen = dmy if order == "DMY" else mdy
    contradictory = bool(first_gt12 and second_gt12)
    reason = (
        f"chose {order}: {chosen[0]} invalid and {chosen[1]} backwards date step(s) versus "
        f"{other[0]} invalid and {other[1]} backwards for the alternative"
    )
    return order, reason, contradictory or chosen[1] > 0


# --- Field parsing ----------------------------------------------------------------


def _parse_time(raw: str, ampm: str | None) -> tuple[int, int, int] | None:
    m = _TIME_PARTS.match(raw)
    if not m:
        return None
    h, mi, s = int(m.group(1)), int(m.group(2)), int(m.group(3) or 0)
    if ampm:
        marker = ampm.lower().replace(".", "").replace(" ", "").replace(" ", "").replace(" ", "")
        if h < 1 or h > 12:
            return None
        if marker == "pm" and h != 12:
            h += 12
        elif marker == "am" and h == 12:
            h = 0
    if h > 23 or mi > 59 or s > 59:
        return None
    return h, mi, s


def clean_name(raw: str) -> str:
    return _BIDI_RE.sub("", raw).strip()


def classify_body(body: str) -> tuple[str, str | None, bool]:
    """Return ``(message_type, media_kind, is_edited)`` for a message body."""
    is_edited = bool(_EDITED_RE.search(body))
    core = _EDITED_RE.sub("", body) if is_edited else body
    core = _BIDI_RE.sub("", core).strip()

    if _DELETED_RE.match(core):
        return "deleted", None, is_edited
    if _CONTACT_RE.match(core):
        return "contact", None, is_edited
    for pattern, kind in _MEDIA_PATTERNS:
        if pattern.match(core):
            return "media", kind, is_edited
    if _LOCATION_RE.match(core):
        return "location", None, is_edited
    if _POLL_RE.match(core):
        return "poll", None, is_edited
    if _CALL_RE.match(core):
        return "call", None, is_edited
    return "text", None, is_edited


def _split_sender(rest: str, layout: Layout) -> tuple[str | None, str, str | None]:
    """Split the part after the timestamp into ``(sender, body, issue_kind)``.

    ``sender`` is ``None`` for WhatsApp system notices.
    """
    idx = rest.find(": ")
    if idx == -1 and rest.endswith(":"):
        idx = len(rest) - 1
    if idx == -1:
        # No "Name: " prefix at all: a notice such as "Alice created group".
        return None, rest, None

    candidate = clean_name(rest[:idx])
    body = rest[idx + 2 :] if idx + 2 <= len(rest) else ""

    if layout == "android" and _SYSTEM_SENDER_HINT.search(candidate) and _SYSTEM_PHRASES.search(rest):
        # e.g. 'Alice changed the subject to "Re: plans"'
        return None, rest, None
    if not candidate:
        return None, rest, "empty_sender"
    if len(candidate) > MAX_SENDER_LEN:
        return None, rest, "suspicious_sender"

    # iOS writes notices as if sent by the chat itself, prefixed with U+200E.
    if layout == "ios":
        stripped = body.lstrip()
        if stripped.startswith("‎") and _SYSTEM_PHRASES.search(stripped) and not _CALL_RE.match(
            _BIDI_RE.sub("", stripped).strip()
        ):
            return None, body, None
    return candidate, body, None


# --- Main parse loop -------------------------------------------------------------------


def parse_export(
    line_source: Callable[[], Iterable[str]],
    *,
    date_order: DateOrder | None = None,
) -> tuple[ParseAudit, Iterator[ParsedMessage]]:
    """Parse a WhatsApp export.

    ``line_source`` must return a fresh iterable of decoded lines each time it
    is called (the export is read twice). Returns the audit (populated fully
    once the message iterator is exhausted) and a lazy message iterator.
    """
    audit = ParseAudit()
    scan = _scan_headers(line_source())
    if scan.android == 0 and scan.ios == 0:
        raise NotAWhatsAppExportError(
            "No WhatsApp message headers were found. Is this a WhatsApp 'Export chat' file?"
        )

    layout: Layout = "ios" if scan.ios > scan.android else "android"
    audit.layout = layout
    audit.layout_reason = (
        f"{max(scan.ios, scan.android)} header lines matched the {layout} layout "
        f"(vs {min(scan.ios, scan.android)} for the other layout)"
    )
    samples = scan.ios_dates if layout == "ios" else scan.android_dates
    if date_order is None:
        order, reason, ambiguous = infer_date_order(samples)
    else:
        order, reason, ambiguous = date_order, "set explicitly by the user", False
    audit.date_order = order
    audit.date_order_reason = reason
    audit.date_order_ambiguous = ambiguous

    header_re = IOS_HEADER if layout == "ios" else ANDROID_HEADER
    return audit, _iter_messages(line_source, header_re, layout, order, audit)


def _iter_messages(
    line_source: Callable[[], Iterable[str]],
    header_re: re.Pattern[str],
    layout: Layout,
    order: DateOrder,
    audit: ParseAudit,
) -> Iterator[ParsedMessage]:
    seq = 0
    current: dict | None = None
    last_ts: datetime | None = None

    def finish(cur: dict) -> ParsedMessage:
        text = "\n".join(cur["lines"])
        if cur["sender"] is None:
            mtype, media_kind, edited = "system", None, False
        else:
            mtype, media_kind, edited = classify_body(text)
        return ParsedMessage(
            seq=cur["seq"],
            sender=cur["sender"],
            ts_original=cur["ts_original"],
            timestamp=cur["timestamp"],
            text=text,
            message_type=mtype,
            media_kind=media_kind,
            is_edited=edited,
            line_start=cur["line_start"],
            line_end=cur["line_end"],
        )

    line_no = 0
    for line in line_source():
        line_no += 1
        m = header_re.match(line)
        parsed_ts: datetime | None = None
        if m:
            dm = _DATE_PARTS.match(m.group("date"))
            date = _make_date(dm.groups(), order) if dm else None  # type: ignore[arg-type]
            time = _parse_time(m.group("time"), m.group("ampm"))
            if date is not None and time is not None:
                parsed_ts = datetime(*date, *time)
            else:
                audit.add_issue(
                    ImportIssue(
                        line_no,
                        "invalid_header_date",
                        f"Line looks like a message header but its date/time is impossible under {order} order; "
                        "kept as text of the previous message.",
                        excerpt=_excerpt(line),
                    )
                )

        if parsed_ts is not None and m is not None:
            if current is not None:
                yield _count(finish(current), audit)
            audit.header_lines += 1
            seq += 1
            sender, body, issue = _split_sender(m.group("rest"), layout)
            if issue:
                audit.add_issue(
                    ImportIssue(
                        line_no,
                        issue,
                        "Could not identify a plausible sender; stored as a system notice for review.",
                        excerpt=_excerpt(line),
                    )
                )
            if last_ts is not None and parsed_ts < last_ts:
                audit.add_issue(
                    ImportIssue(
                        line_no,
                        "out_of_order_timestamp",
                        f"Timestamp is earlier than the previous message ({last_ts.isoformat()}). "
                        "File order is preserved.",
                    )
                )
            last_ts = parsed_ts
            ts_original = f"{m.group('date')}, {m.group('time')}"
            current = {
                "seq": seq,
                "sender": sender,
                "ts_original": ts_original,
                "timestamp": parsed_ts,
                "lines": [body],
                "line_start": line_no,
                "line_end": line_no,
            }
        elif current is not None:
            audit.continuation_lines += 1
            current["lines"].append(line)
            current["line_end"] = line_no
        elif line.strip():
            audit.add_issue(
                ImportIssue(
                    line_no,
                    "orphan_line",
                    "Text appears before the first message header and could not be attributed.",
                    excerpt=_excerpt(line),
                )
            )

    audit.lines_total = line_no
    if current is not None:
        yield _count(finish(current), audit)

    # Single-message senders are a classic sign of a notice that was parsed as
    # a name. They are kept, but flagged for the user to verify.
    if len(audit.sender_counts) > 2:
        for name, count in audit.sender_counts.items():
            if count == 1:
                audit.add_issue(
                    ImportIssue(
                        0,
                        "rare_sender",
                        f"Participant '{name}' has exactly one message; verify it is a real participant.",
                    )
                )


def _count(msg: ParsedMessage, audit: ParseAudit) -> ParsedMessage:
    audit.messages_parsed += 1
    if msg.sender is None:
        audit.system_messages += 1
    else:
        audit.sender_counts[msg.sender] += 1
    return msg


def _excerpt(line: str, limit: int = 120) -> str:
    return line if len(line) <= limit else line[:limit] + "…"

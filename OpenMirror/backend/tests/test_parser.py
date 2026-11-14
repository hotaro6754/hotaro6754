"""Parser tests: layouts, dates, multiline messages, attribution and edge cases.

All conversations here are fictional.
"""

from __future__ import annotations

from collections import Counter
from datetime import datetime

import pytest

from openmirror.ingest.whatsapp import (
    NotAWhatsAppExportError,
    _parse_time,
    classify_body,
    infer_date_order,
)
from openmirror.synthetic import generate_group, generate_two_person, render_android, render_ios

from .conftest import parse_text

# --- Date and time parsing ------------------------------------------------------------


@pytest.mark.parametrize(
    "raw,ampm,expected",
    [
        ("10:15", None, (10, 15, 0)),
        ("22:15:09", None, (22, 15, 9)),
        ("22.15", None, (22, 15, 0)),
        ("12:05", "AM", (0, 5, 0)),
        ("12:05", "PM", (12, 5, 0)),
        ("1:05", "pm", (13, 5, 0)),
        ("11:59", "p. m.", (23, 59, 0)),
        ("9:03", "a.m.", (9, 3, 0)),
        ("13:00", "PM", None),  # impossible 12-hour value
        ("24:00", None, None),
        ("10:61", None, None),
    ],
)
def test_parse_time(raw, ampm, expected):
    assert _parse_time(raw, ampm) == expected


def test_infer_date_order_dmy_from_day_above_12():
    order, reason, ambiguous = infer_date_order([("01", "02", "23"), ("25", "02", "23")])
    assert order == "DMY" and not ambiguous and "first component" in reason


def test_infer_date_order_mdy_from_day_above_12():
    order, _, ambiguous = infer_date_order([("1", "2", "23"), ("2", "25", "23")])
    assert order == "MDY" and not ambiguous


def test_infer_date_order_ymd():
    assert infer_date_order([("2023", "12", "31")])[0] == "YMD"


def test_infer_date_order_fully_ambiguous_is_flagged():
    order, reason, ambiguous = infer_date_order([("01", "02", "23"), ("01", "02", "23")])
    assert order == "DMY" and ambiguous and "override" in reason


def test_infer_date_order_uses_chronology_when_ambiguous():
    # Read as MDY these are Jan 2, Jan 3, Feb 1 (chronological); as DMY they jump backwards.
    samples = [("01", "02", "23"), ("01", "03", "23"), ("02", "01", "23")]
    order, _, _ = infer_date_order(samples)
    assert order == "MDY"


# --- Layouts ---------------------------------------------------------------------------------

ANDROID = """\
12/01/2024, 21:03 - Messages and calls are end-to-end encrypted. No one outside of this chat, not even WhatsApp, can read or listen to them. Tap to learn more.
12/01/2024, 21:04 - Asha: Hi! Are we still on for Saturday?
12/01/2024, 21:05 - Ravi: Yes
second line of Ravi's message
third line: with a colon
12/01/2024, 21:06 - Asha: <Media omitted>
13/01/2024, 08:00 - Ravi: This message was deleted
13/01/2024, 08:01 - Asha: Note: bring the tickets <This message was edited>
13/01/2024, 08:02 - Ravi: location: https://maps.google.com/?q=1,2
13/01/2024, 08:03 - Asha: IMG-20240113-WA0001.jpg (file attached)
13/01/2024, 08:04 - Ravi:
"""


def test_android_basic_layout_and_types():
    audit, msgs = parse_text(ANDROID)
    assert audit.layout == "android"
    assert audit.date_order == "DMY"
    assert [m.sender for m in msgs] == [None, "Asha", "Ravi", "Asha", "Ravi", "Asha", "Ravi", "Asha", "Ravi"]
    assert msgs[0].message_type == "system"
    assert msgs[2].text == "Yes\nsecond line of Ravi's message\nthird line: with a colon"
    assert (msgs[2].line_start, msgs[2].line_end) == (3, 5)
    assert msgs[3].message_type == "media"
    assert msgs[4].message_type == "deleted"
    assert msgs[5].is_edited and msgs[5].message_type == "text"
    assert msgs[5].text.startswith("Note: bring")  # colon in body does not move the sender
    assert msgs[6].message_type == "location"
    assert (msgs[7].message_type, msgs[7].media_kind) == ("media", "image")
    assert msgs[8].sender == "Ravi" and msgs[8].text == ""
    assert msgs[1].timestamp == datetime(2024, 1, 12, 21, 4)
    assert audit.continuation_lines == 2
    assert audit.messages_parsed == 9 and audit.system_messages == 1
    assert not audit.issues


IOS = (
    "‎[1/12/24, 9:03:11 PM] Ravi: ‎Messages and calls are end-to-end encrypted. No one outside of "
    "this chat, not even WhatsApp, can read or listen to them.\r\n"
    "[1/12/24, 9:04:00 PM] Asha: Hello there\r\n"
    "‎[1/12/24, 9:05:00 PM] Ravi: ‎image omitted\r\n"
    "[1/12/24, 9:06:00 PM] Ravi: Two\r\nlines\r\n"
    "‎[1/13/24, 12:01:00 AM] Asha: ‎This message was deleted.\r\n"
    "‎[1/13/24, 12:02:00 AM] Asha: ‎Missed voice call\r\n"
    "‎[1/13/24, 12:03:00 AM] Ravi: ‎<attached: 00000012-PHOTO-2024-01-13-00-03-00.jpg>\r\n"
)


def test_ios_layout_with_bidi_marks():
    audit, msgs = parse_text(IOS)
    assert audit.layout == "ios"
    assert audit.date_order == "MDY"
    assert msgs[0].sender is None and msgs[0].message_type == "system"
    assert msgs[1].sender == "Asha" and msgs[1].timestamp == datetime(2024, 1, 12, 21, 4)
    assert (msgs[2].message_type, msgs[2].media_kind) == ("media", "image")
    assert msgs[3].text == "Two\nlines"
    assert msgs[4].message_type == "deleted" and msgs[4].timestamp.hour == 0
    assert msgs[5].message_type == "call" and msgs[5].sender == "Asha"
    assert (msgs[6].message_type, msgs[6].media_kind) == ("media", "image")


def test_group_system_messages_with_colon_in_subject():
    audit, msgs = parse_text(render_android(generate_group()))
    system = [m.text for m in msgs if m.sender is None]
    assert 'Kiran changed the subject from "Weekend Plans" to "Re: Goa"' in system
    assert "Farah left" in system
    assert set(m.sender for m in msgs if m.sender) == {"Meera", "Kiran", "Dev", "Farah"}


def test_phone_number_sender_with_bidi_wrapping():
    text = "05/03/2024, 10:00 - ‪+91 98765 43210‬: hello\n05/03/2024, 10:01 - Asha: hi\n"
    _, msgs = parse_text(text)
    assert msgs[0].sender == "+91 98765 43210"


def test_orphan_lines_before_first_header_are_reported_not_dropped():
    text = "garbage at the top\n12/01/2024, 21:04 - Asha: hi\n"
    audit, msgs = parse_text(text)
    assert len(msgs) == 1
    assert audit.issue_counts["orphan_line"] == 1
    assert audit.issues[0].line_no == 1


def test_header_like_line_with_impossible_date_is_kept_as_text():
    text = "25/01/2024, 21:04 - Asha: list:\n31/02/2024, 10:00 - not a real date\n26/01/2024, 09:00 - Ravi: ok\n"
    audit, msgs = parse_text(text)
    assert len(msgs) == 2
    assert "31/02/2024, 10:00 - not a real date" in msgs[0].text
    assert audit.issue_counts["invalid_header_date"] == 1


def test_out_of_order_timestamps_flagged_and_file_order_kept():
    text = "25/01/2024, 21:04 - Asha: one\n25/01/2024, 20:00 - Ravi: two\n"
    audit, msgs = parse_text(text)
    assert [m.seq for m in msgs] == [1, 2]
    assert audit.issue_counts["out_of_order_timestamp"] == 1


def test_not_whatsapp_raises():
    with pytest.raises(NotAWhatsAppExportError):
        parse_text("just some notes\nnothing here\n")


def test_explicit_date_order_override():
    text = "01/02/2024, 10:00 - Asha: hi\n01/02/2024, 10:05 - Ravi: hey\n"
    audit, msgs = parse_text(text, date_order="MDY")
    assert msgs[0].timestamp == datetime(2024, 1, 2, 10, 0)
    assert audit.date_order_reason == "set explicitly by the user"


def test_rare_sender_is_flagged_for_review():
    text = (
        "01/02/2024, 10:00 - Asha: a\n01/02/2024, 10:01 - Ravi: b\n"
        "01/02/2024, 10:02 - Asha: c\n01/02/2024, 10:03 - Ravi: d\n01/02/2024, 10:04 - Odd One: e\n"
    )
    audit, _ = parse_text(text)
    assert audit.issue_counts["rare_sender"] == 1


@pytest.mark.parametrize(
    "body,expected",
    [
        ("<Media omitted>", ("media", "unknown", False)),
        ("sticker omitted", ("media", "sticker", False)),
        ("‎GIF omitted", ("media", "gif", False)),
        ("You deleted this message", ("deleted", None, False)),
        ("POLL:\nWhere?\nOPTION: Goa", ("poll", None, False)),
        ("Contact card omitted", ("contact", None, False)),
        ("hello <This message was edited>", ("text", None, True)),
        ("Missed video call", ("call", None, False)),
        ("just text", ("text", None, False)),
    ],
)
def test_classify_body(body, expected):
    assert classify_body(body) == expected


# --- Round trip: attribution must match the generator exactly ------------------------------


@pytest.mark.parametrize(
    "render",
    [
        lambda m: render_android(m, "DMY", False),
        lambda m: render_android(m, "MDY", True),
        lambda m: render_android(m, "DOT", False),
        lambda m: render_ios(m, h12=True),
        lambda m: render_ios(m, h12=False),
    ],
    ids=["android-dmy-24h", "android-mdy-12h", "android-dotted", "ios-12h", "ios-24h"],
)
def test_synthetic_round_trip_attribution(render):
    truth = generate_two_person()
    audit, msgs = parse_text(render(truth))
    assert len(msgs) == len(truth)
    assert Counter(m.sender for m in msgs) == Counter(t.sender for t in truth)
    for got, exp in zip(msgs, truth, strict=True):
        assert got.sender == exp.sender
        assert got.timestamp.replace(second=0) == exp.ts.replace(second=0)
    assert sum(audit.issue_counts.values()) == 0

"""Analytics and evidence tests against a tiny conversation whose metrics are
worked out by hand in the comments below."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from openmirror import service
from openmirror.analytics.engine import AnalysisParams, compute, load_frames
from openmirror.evidence.findings import EvidenceIntegrityError, Evidence, build_findings, validate_findings
from openmirror.storage.importer import import_file
from openmirror.synthetic import generate_two_person, render_android

# Session gap is 4 h.
#  #  time              sender  note
#  1  01/03 09:00       A       session 1 start (A initiates)       "hello there?"
#  2  01/03 09:02       B       reply by B after 120 s
#  3  01/03 09:03       B       same turn as #2 (not a reply)
#  4  01/03 09:10       A       reply by A after 420 s
#  5  01/03 20:00       B       gap 10h50m -> session 2, B initiates "dinner tonight?"
#  6  01/03 20:30       A       reply by A after 1800 s
#  7  02/03 08:00       A       gap 11h30m -> session 3, A initiates
#  8  04/03 10:00       B       gap 2 d 2 h (180000 s) -> session 4, B initiates
#  9  04/03 10:01       A       reply by A after 60 s (media)
TINY = """\
01/03/2024, 09:00 - Anu: hello there?
01/03/2024, 09:02 - Bala: hi
01/03/2024, 09:03 - Bala: how are you
01/03/2024, 09:10 - Anu: good thanks
01/03/2024, 20:00 - Bala: dinner tonight?
01/03/2024, 20:30 - Anu: yes
02/03/2024, 08:00 - Anu: morning
04/03/2024, 10:00 - Bala: back
04/03/2024, 10:01 - Anu: <Media omitted>
"""
LIMITS = dict(max_text_bytes=10**8, max_zip_entries=100)


@pytest.fixture
def tiny(conn, tmp_path: Path):
    p = tmp_path / "tiny.txt"
    p.write_text(TINY)
    conv_id, _ = import_file(conn, p, "tiny.txt", **LIMITS)
    params = AnalysisParams()
    frames = load_frames(conn, conv_id, params)
    return conv_id, frames, compute(frames, params)


def person(a: dict, name: str) -> dict:
    return next(p for p in a["participants"] if p["name"] == name)


def test_overview(tiny):
    _, _, a = tiny
    ov = a["overview"]
    assert ov["participant_messages"] == 9
    assert ov["sessions"] == 4
    assert ov["span_days"] == 4 and ov["active_days"] == 3
    assert ov["busiest_day"] == {"day": "2024-03-01", "messages": 6}


def test_initiation_and_replies(tiny):
    _, _, a = tiny
    anu, bala = person(a, "Anu"), person(a, "Bala")
    assert (anu["sessions_initiated"], bala["sessions_initiated"]) == (2, 2)
    assert anu["replies"] == 3 and bala["replies"] == 1
    # nearest-rank median of [60, 420, 1800] is 420
    assert anu["reply_median_s"] == 420
    assert bala["reply_median_s"] == 120


def test_turns_words_questions(tiny):
    _, _, a = tiny
    anu, bala = person(a, "Anu"), person(a, "Bala")
    assert anu["turns"] == 5 and anu["messages_per_turn"] == 1.0
    assert bala["turns"] == 3 and bala["messages_per_turn"] == pytest.approx(4 / 3)
    assert anu["words"] == 6 and anu["media"] == 1  # hello there / good thanks / yes / morning
    assert anu["questions"] == 1 and bala["questions"] == 1
    assert anu["hour_histogram"][9] == 2 and anu["peak_hour"] == 9


def test_streaks_and_gaps(tiny):
    _, frames, a = tiny
    assert a["streaks"]["longest"][0] == {"start": "2024-03-01", "end": "2024-03-02", "days": 2}
    top_gap = a["gaps"]["longest"][0]
    assert top_gap["gap_s"] == 180000
    msgs = frames.messages
    assert msgs.filter(msgs["id"] == top_gap["id"])["text"][0] == "back"


def test_activity_series_sum_to_total(tiny):
    _, _, a = tiny
    for key in ("daily", "weekly", "monthly"):
        assert sum(r["total"] for r in a["activity"][key]) == 9
    assert sum(a["activity"]["hour_of_day"]) == 9


def test_session_gap_parameter_changes_sessions(conn, tiny):
    conv_id, _, _ = tiny
    params = AnalysisParams(session_gap_minutes=24 * 60)
    a = compute(load_frames(conn, conv_id, params), params)
    assert a["overview"]["sessions"] == 2  # only the 2-day gap splits


def test_findings_reference_real_messages(conn, tmp_path: Path):
    p = tmp_path / "pair.txt"
    p.write_text(render_android(generate_two_person()))
    conv_id, _ = import_file(conn, p, "pair.txt", **LIMITS)
    service.run_analysis(conn, conv_id)
    report = json.loads(service.latest_run(conn, conv_id)["report_json"])
    findings = report["findings"]
    assert len(findings) >= 20
    valid = {r[0] for r in conn.execute("SELECT id FROM messages WHERE conversation_id=?", (conv_id,))}
    for f in findings:
        assert f["method"] and f["confidence"] in {"high", "medium", "low"} and f["confidence_reason"]
        for e in f["evidence"]:
            assert e["message_id"] in valid
    # Every chapter that is about the data has at least one finding with evidence.
    chapters = {f["chapter"] for f in findings if f["evidence"]}
    assert {"overview", "people", "dynamics", "timeline", "moments", "topics", "shifts"} <= chapters
    # Initiation carries counterexamples; the synthetic chat's initiation flip is detected.
    init = next(f for f in findings if f["id"] == "F-DY-initiation")
    assert any(e["role"] == "counterexample" for e in init["evidence"])
    assert any(f["finding_type"] == "initiation_shift" for f in findings)
    # The August silence in the synthetic chat is the longest gap.
    gap = next(f for f in findings if f["id"] == "F-TL-gap-1")
    assert gap["metrics"]["gap_s"] > 30 * 86400


def test_finding_detail_returns_message_text_verbatim(conn, tmp_path: Path):
    p = tmp_path / "tiny.txt"
    p.write_text(TINY)
    conv_id, _ = import_file(conn, p, "tiny.txt", **LIMITS)
    service.run_analysis(conn, conv_id)
    f = service.get_finding(conn, conv_id, "F-TL-gap-1")
    texts = [e["message"]["text"] for e in f["evidence"]]
    assert texts == ["morning", "back"]


def test_validator_rejects_foreign_message_ids(conn, tiny):
    conv_id, frames, a = tiny
    findings = build_findings(frames, a, {"issue_counts": {}})
    validate_findings(conn, conv_id, findings)
    findings[0].evidence.append(Evidence(999_999, "support"))
    with pytest.raises(EvidenceIntegrityError):
        validate_findings(conn, conv_id, findings)


def test_delete_removes_everything(conn, tmp_path: Path):
    p = tmp_path / "tiny.txt"
    p.write_text(TINY)
    conv_id, _ = import_file(conn, p, "tiny.txt", **LIMITS)
    service.run_analysis(conn, conv_id)
    service.delete_conversation(conn, conv_id)
    for table in (
        "conversations", "participants", "messages", "import_jobs", "import_issues",
        "analysis_runs", "findings", "evidence_references",
    ):
        assert conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0] == 0, table
    assert conn.execute("SELECT COUNT(*) FROM messages_fts WHERE messages_fts MATCH 'morning'").fetchone()[0] == 0

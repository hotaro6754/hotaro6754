"""Regressions found by importing a real export (reproduced with fictional data).

* lowercase am/pm separated by U+202F NARROW NO-BREAK SPACE, two-digit years
* "live location shared" placeholders
* minute-resolution timestamps: same-minute replies must not read as "0 s"
* romanised Telugu/Hindi fillers and elongated words must not become "topics"
* delivery-order timestamp steps are notices, not problems
* skewed word counts: report median and p90, not the mean
"""

from __future__ import annotations

import json
from pathlib import Path

from openmirror import service
from openmirror.analytics.text import topic_terms
from openmirror.ingest.whatsapp import classify_body
from openmirror.storage.importer import import_file

from .conftest import parse_text

NNBSP = " "


def test_lowercase_ampm_with_narrow_space():
    text = (
        f"31/12/25, 12:38{NNBSP}pm - Asha: noon-ish\n"
        f"31/12/25, 12:05{NNBSP}am - Ravi: just after midnight\n"
        f"31/12/25, 11:59{NNBSP}pm - Asha: last minute\n"
    )
    audit, msgs = parse_text(text)
    assert [m.timestamp.hour for m in msgs] == [12, 0, 23]
    assert audit.date_order == "DMY"


def test_live_location_is_a_placeholder():
    assert classify_body("live location shared")[0] == "location"
    assert classify_body("Live location ended")[0] == "location"


def test_romanised_fillers_and_elongations_are_not_topics():
    assert topic_terms("haaaa raa anna chepu nuvvu ledhu kya yaar hiiii exam goa") == ["exam", "goa"]


def _chat(lines: list[str]) -> str:
    return "\n".join(lines) + "\n"


def test_minute_resolution_and_notices(conn, tmp_path: Path):
    lines = []
    for d in range(1, 21):
        day = f"{d:02d}/03/26"
        lines += [
            f"{day}, 9:00{NNBSP}pm - Asha: question {d}?",
            f"{day}, 9:00{NNBSP}pm - Ravi: answer",  # same-minute reply
            f"{day}, 9:04{NNBSP}pm - Asha: ok",
            f"{day}, 9:03{NNBSP}pm - Ravi: delivered late",  # delivery-order step back
            f"{day}, 9:20{NNBSP}pm - Asha: " + " ".join(["word"] * (400 if d == 5 else 2)),
        ]
    p = tmp_path / "chat.txt"
    p.write_text(_chat(lines), encoding="utf-8")
    conv_id, _ = import_file(conn, p, "chat.txt", max_text_bytes=10**8, max_zip_entries=10)
    service.run_analysis(conn, conv_id)
    run = service.latest_run(conn, conv_id)
    a, report = json.loads(run["analytics_json"]), json.loads(run["report_json"])
    assert a["overview"]["timestamp_resolution_s"] == 60

    findings = {f["id"]: f for f in report["findings"]}
    reply = findings["F-DY-reply"]["statement"]
    assert "0 s" not in reply and "under 1 min" in reply and "within 5 minutes" in reply

    imp = findings["F-LI-import"]
    assert imp["confidence"] == "high"
    assert "delivery order" in imp["statement"] and "No import problems" in imp["statement"]

    asha = next(p for p in a["participants"] if p["name"] == "Asha")
    style = findings[f"F-PE-{asha['id']}-style"]["statement"]
    assert "Half of Asha" in style and "90%" in style

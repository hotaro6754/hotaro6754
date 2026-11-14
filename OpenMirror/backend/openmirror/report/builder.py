"""Deterministic report builder.

Turns analytics + findings into a chaptered report. The prose is assembled
from templates filled with computed values, so it is reproducible and needs
no language model. Each chapter lists the findings it is built on, and the UI
links every statement back to its evidence.
"""

from __future__ import annotations

from datetime import UTC, datetime

from openmirror.evidence.findings import Finding, fmt_date, fmt_duration, fmt_int, fmt_pct

CHAPTER_META = [
    ("overview", "The Overview", "What defines this conversation?", ["monthly_activity"]),
    ("people", "The People", "How does each person communicate?", ["participant_table", "length_distribution"]),
    ("dynamics", "The Dynamics", "Who starts, who answers, and how fast?", ["initiation_by_month", "reply_distribution"]),
    ("timeline", "The Timeline", "When does this conversation happen?", ["daily_calendar", "weekday_hour"]),
    ("moments", "The Moments", "Which days and conversations stand out?", ["volume_changes"]),
    ("topics", "The Recurring Threads", "What keeps coming up?", ["topic_table"]),
    ("shifts", "The Shifts", "How has the conversation changed?", ["period_comparison", "participation_by_month"]),
    ("limitations", "The Fine Print", "What this report can and cannot tell you.", ["import_audit"]),
]


def _names(people: list[dict]) -> str:
    names = [p["name"] for p in people]
    if len(names) <= 1:
        return names[0] if names else "Nobody"
    if len(names) <= 4:
        return ", ".join(names[:-1]) + " and " + names[-1]
    return f"{', '.join(names[:3])} and {len(names) - 3} others"


def build_report(conversation: dict, a: dict, findings: list[Finding], audit: dict) -> dict:
    by_chapter: dict[str, list[Finding]] = {}
    for f in findings:
        by_chapter.setdefault(f.chapter, []).append(f)

    people = sorted(
        [p for p in a.get("participants", []) if p.get("messages", 0) > 0], key=lambda p: (-p["messages"], p["id"])
    )
    ov = a.get("overview", {})
    paragraphs = _paragraphs(a, people, by_chapter) if not a.get("empty") else {}

    chapters = []
    for i, (key, title, question, figures) in enumerate(CHAPTER_META, start=1):
        fs = by_chapter.get(key, [])
        chapters.append(
            {
                "key": key,
                "number": f"{i:02d}",
                "title": title,
                "question": question,
                "paragraphs": paragraphs.get(key, []),
                "figures": figures,
                "finding_ids": [f.id for f in fs],
            }
        )

    headline = []
    if not a.get("empty"):
        headline = [
            {"label": "Messages", "value": fmt_int(ov["participant_messages"])},
            {"label": "Days covered", "value": fmt_int(ov["span_days"])},
            {"label": "Active days", "value": fmt_pct(ov["active_day_share"])},
            {"label": "Sessions", "value": fmt_int(ov["sessions"])},
            {"label": "Participants", "value": fmt_int(len(people))},
        ]

    return {
        "title": conversation["title"],
        "subtitle": "A personalised, evidence-backed conversation report",
        "generated_at": datetime.now(UTC).replace(microsecond=0).isoformat(),
        "engine_version": a.get("engine_version"),
        "ai_used": False,
        "participants": [{"id": p["id"], "name": p["name"], "messages": p["messages"]} for p in people],
        "headline": headline,
        "chapters": chapters,
        "findings": [f.as_dict() for f in findings],
        "disclaimer": (
            "Generated locally from deterministic statistics. No AI model was used and nothing left this device. "
            "The report describes observable messaging behaviour only."
        ),
    }


def _paragraphs(a: dict, people: list[dict], by: dict[str, list[Finding]]) -> dict[str, list[str]]:
    ov = a["overview"]
    out: dict[str, list[str]] = {}

    out["overview"] = [
        f"Between {fmt_date(ov['first_ts'])} and {fmt_date(ov['last_ts'])}, {_names(people)} exchanged "
        f"{fmt_int(ov['participant_messages'])} messages across {fmt_int(ov['sessions'])} separate sessions. "
        f"Someone wrote on {fmt_pct(ov['active_day_share'])} of the {fmt_int(ov['span_days'])} days in that window, "
        f"averaging {ov['messages_per_active_day']:.1f} messages on the days they did.",
    ]
    if len(people) >= 2:
        shares = ", ".join(f"{p['name']} {fmt_pct(p['share'])}" for p in people[:6])
        out["overview"].append(f"By volume the split is {shares}.")
    out["overview"].append(
        f"The busiest single day was {fmt_date(ov['busiest_day']['day'])} "
        f"({fmt_int(ov['busiest_day']['messages'])} messages) and the busiest month was "
        f"{datetime.fromisoformat(ov['busiest_month']['month']):%B %Y}."
    )

    ppl = []
    for p in people[:8]:
        bits = [
            f"{p['name']} sent {fmt_int(p['messages'])} messages, typically {p['median_words']:.0f} word"
            + ("" if p["median_words"] == 1 else "s")
            + " long",
            f"most often around {p['peak_hour']:02d}:00",
        ]
        if p["messages_per_turn"] >= 1.3:
            bits.append(f"and often sends several messages in a row ({p['messages_per_turn']:.2f} per turn)")
        else:
            bits.append("and usually one message per turn")
        ppl.append(", ".join(bits) + ".")
    out["people"] = ppl

    dyn = []
    if len(people) >= 2:
        top = max(people, key=lambda p: p["sessions_initiated"])
        dyn.append(
            f"{top['name']} opens conversations most often, starting {fmt_pct(top['initiation_share'])} of sessions. "
            "A new session begins after a pause of more than "
            f"{a['params']['session_gap_minutes'] // 60} hours."
        )
        rp = [p for p in people if p["replies"] >= 5 and p["reply_median_s"] is not None]
        if rp:
            dyn.append(
                "Typical (median) reply times within a session: "
                + "; ".join(
                    f"{p['name']} {fmt_duration(p['reply_median_s'], ov.get('timestamp_resolution_s', 1))}"
                    f" ({fmt_pct(p['reply_within_5min'] / p['replies'])} within 5 min)"
                    for p in rp
                )
                + ". Slow replies are normal in any chat and are not, on their own, a sign of disinterest."
            )
    out["dynamics"] = dyn

    st = a["streaks"]["longest"][0] if a["streaks"]["longest"] else None
    tl = []
    if st:
        tl.append(
            f"The longest streak of daily contact ran {st['days']} days, from {fmt_date(st['start'])} to "
            f"{fmt_date(st['end'])}."
        )
    if a["gaps"]["longest"]:
        g = a["gaps"]["longest"][0]
        tl.append(f"The longest silence lasted {fmt_duration(g['gap_s'])}, ending on {fmt_date(g['ts'])}.")
    hours = a["activity"]["hour_of_day"]
    peak = max(range(24), key=lambda h: (hours[h], -h))
    tl.append(f"Across everyone, the busiest hour of the day is {peak:02d}:00.")
    out["timeline"] = tl

    mo = []
    ch = a["volume_changes"]
    if ch:
        ups = [c for c in ch if c["direction"] == "up"]
        downs = [c for c in ch if c["direction"] == "down"]
        mo.append(
            f"{len(ch)} month(s) stand out against the previous three: {len(ups)} surge(s) and {len(downs)} drop(s)."
        )
    else:
        mo.append("No month differed from its recent average by 50% or more; activity was comparatively steady.")
    out["moments"] = mo

    terms = a["topics"]["terms"][:6]
    if terms:
        out["topics"] = [
            "Measured by how many separate sessions they appear in, the most recurring words are "
            + ", ".join(f"“{t['term']}” ({t['sessions']})" for t in terms)
            + ". Word counts are lexical and cannot tell apart different meanings of the same word."
        ]
    else:
        out["topics"] = ["There is not enough text to identify recurring words."]

    sh = [f.statement for f in by.get("shifts", [])][:4]
    out["shifts"] = sh or ["No substantial change in pace, initiation, reply time or share was detected between the early and late periods."]

    out["limitations"] = [f.statement for f in by.get("limitations", [])]
    return out

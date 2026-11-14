"""Evidence engine: turn deterministic analytics into evidence-linked findings.

Every finding states *what* was observed, *how* it was computed, *how sure*
we are, and *which messages* support or complicate it. Statements are built
only from computed numbers; message text is never paraphrased or quoted here,
the UI shows the referenced messages verbatim instead.

Confidence levels
-----------------
* ``high``   – an exact count/measurement over enough events, or a comparison
  that is very unlikely to be chance (|z| ≥ 3 with ≥ 100 events).
* ``medium`` – a moderate sample (≥ 30 events) or a difference with |z| ≥ 2.
* ``low``    – small samples, or differences that could easily be noise.
The *interpretation* of any pattern (why it happens) is never rated: the
report says explicitly that the data cannot show motive.
"""

from __future__ import annotations

import math
import sqlite3
from dataclasses import dataclass, field
from datetime import date, datetime

import polars as pl

from openmirror.analytics.engine import Frames

CHAPTERS = ["overview", "people", "dynamics", "timeline", "moments", "topics", "shifts", "limitations"]
MAX_PEOPLE_FINDINGS = 8


@dataclass
class Evidence:
    message_id: int
    role: str  # support | counterexample
    note: str | None = None


@dataclass
class Finding:
    id: str
    chapter: str
    finding_type: str
    title: str
    statement: str
    method: str
    confidence: str
    confidence_reason: str
    metrics: dict = field(default_factory=dict)
    evidence: list[Evidence] = field(default_factory=list)
    counterexample_note: str | None = None
    time_start: str | None = None
    time_end: str | None = None

    def support(self, ids: list[int], note: str | None = None) -> None:
        self.evidence.extend(Evidence(int(i), "support", note) for i in ids)

    def counter(self, ids: list[int], note: str | None = None) -> None:
        self.evidence.extend(Evidence(int(i), "counterexample", note) for i in ids)

    def as_dict(self) -> dict:
        return {
            "id": self.id,
            "chapter": self.chapter,
            "finding_type": self.finding_type,
            "title": self.title,
            "statement": self.statement,
            "method": self.method,
            "confidence": self.confidence,
            "confidence_reason": self.confidence_reason,
            "metrics": self.metrics,
            "counterexample_note": self.counterexample_note,
            "time_start": self.time_start,
            "time_end": self.time_end,
            "evidence": [e.__dict__ for e in self.evidence],
        }


# --- Formatting helpers ----------------------------------------------------------


def fmt_int(n: int | float) -> str:
    return f"{int(n):,}"


def fmt_pct(x: float) -> str:
    return f"{x * 100:.0f}%"


def fmt_duration(seconds: float | None, resolution: int = 1) -> str:
    if seconds is None:
        return "n/a"
    s = float(seconds)
    if resolution >= 60 and s < 60:
        return "under 1 min"
    if s < 60:
        return f"{s:.0f} s"
    if s < 3600:
        m = s / 60
        return f"{m:.0f} min" if m >= 10 or m == int(m) else f"{m:.1f} min"
    if s < 86400 * 2:
        return f"{s / 3600:.1f} h"
    return f"{s / 86400:.1f} days"


def fmt_date(v: str | date | datetime) -> str:
    if isinstance(v, str):
        v = datetime.fromisoformat(v)
    return f"{v.day} {v:%b %Y}"


def fmt_month(v: str) -> str:
    return f"{datetime.fromisoformat(v):%B %Y}"


def spread(ids: list[int], k: int) -> list[int]:
    """Pick ``k`` items evenly spaced across a list (deterministic)."""
    if len(ids) <= k:
        return list(ids)
    if k == 1:
        return [ids[0]]
    step = (len(ids) - 1) / (k - 1)
    return [ids[round(i * step)] for i in range(k)]


def z_proportion(k: int, n: int, p0: float) -> float:
    if n == 0 or p0 <= 0 or p0 >= 1:
        return 0.0
    return (k / n - p0) / math.sqrt(p0 * (1 - p0) / n)


def z_two_proportions(k1: int, n1: int, k2: int, n2: int) -> float:
    if n1 == 0 or n2 == 0:
        return 0.0
    p = (k1 + k2) / (n1 + n2)
    if p in (0, 1):
        return 0.0
    return (k1 / n1 - k2 / n2) / math.sqrt(p * (1 - p) * (1 / n1 + 1 / n2))


def confidence_from_z(z: float, n: int) -> tuple[str, str]:
    az = abs(z)
    if n >= 100 and az >= 3:
        return "high", f"{fmt_int(n)} events; the difference is far larger than chance variation (|z| = {az:.1f})."
    if n >= 30 and az >= 2:
        return "medium", f"{fmt_int(n)} events; the difference is unlikely to be chance alone (|z| = {az:.1f})."
    return "low", f"Only {fmt_int(n)} events or a small difference (|z| = {az:.1f}); this could be noise."


def confidence_from_n(n: int, what: str) -> tuple[str, str]:
    if n >= 100:
        return "high", f"Measured directly over {fmt_int(n)} {what}."
    if n >= 30:
        return "medium", f"Measured over {fmt_int(n)} {what}; a moderate sample."
    return "low", f"Only {fmt_int(n)} {what}; treat as indicative."


EXACT = ("high", "Exact value read from the parsed transcript.")


# --- Builder --------------------------------------------------------------------------------


def build_findings(frames: Frames, a: dict, import_audit: dict) -> list[Finding]:
    if a.get("empty"):
        return [
            Finding(
                "F-LI-empty",
                "limitations",
                "no_participant_messages",
                "No participant messages",
                "The export contains no messages from participants, so no analysis is possible.",
                "Count of messages with a sender.",
                *EXACT,
            )
        ]
    b = _Builder(frames, a, import_audit)
    b.overview()
    b.people()
    b.dynamics()
    b.timeline()
    b.moments()
    b.topics()
    b.shifts()
    b.limitations()
    return b.findings


class _Builder:
    def __init__(self, frames: Frames, a: dict, import_audit: dict) -> None:
        self.f = frames
        self.a = a
        self.audit = import_audit
        self.names = frames.names
        self.pm = frames.messages
        self.findings: list[Finding] = []
        self.ppl = sorted(
            [p for p in a["participants"] if p["messages"] > 0], key=lambda p: (-p["messages"], p["id"])
        )

    def add(self, f: Finding) -> Finding:
        self.findings.append(f)
        return f

    def ids(self, df: pl.DataFrame) -> list[int]:
        return df["id"].to_list()

    # -- 1. Overview -------------------------------------------------------------------
    def overview(self) -> None:
        ov = self.a["overview"]
        f = self.add(
            Finding(
                "F-OV-span",
                "overview",
                "span",
                "How long and how much",
                f"{fmt_int(ov['participant_messages'])} participant messages over {fmt_int(ov['span_days'])} days "
                f"({fmt_date(ov['first_ts'])} – {fmt_date(ov['last_ts'])}), grouped into "
                f"{fmt_int(ov['sessions'])} sessions. Messages were sent on {fmt_int(ov['active_days'])} of those days "
                f"({fmt_pct(ov['active_day_share'])}).",
                "Counts of parsed participant messages, calendar days between the first and last message, days with "
                "at least one message, and sessions (runs with no gap longer than "
                f"{self.a['params']['session_gap_minutes']} minutes).",
                *EXACT,
                metrics={k: ov[k] for k in ("participant_messages", "span_days", "active_days", "sessions")},
                time_start=ov["first_ts"],
                time_end=ov["last_ts"],
            )
        )
        f.support([self.pm["id"][0]], "first participant message")
        f.support([self.pm["id"][-1]], "last participant message")

        if len(self.ppl) >= 2:
            top = self.ppl[0]
            n = ov["participant_messages"]
            p0 = 1 / len(self.ppl)
            z = z_proportion(top["messages"], n, p0)
            conf, why = confidence_from_z(z, n)
            even = abs(top["share"] - p0) < 0.05
            title = "Message volume is fairly even" if even else f"{top['name']} sends the most messages"
            stmt = (
                f"{top['name']} sent {fmt_pct(top['share'])} of participant messages "
                f"({fmt_int(top['messages'])} of {fmt_int(n)}); an equal split would be {fmt_pct(p0)} each."
            )
            f = self.add(
                Finding(
                    "F-OV-volume",
                    "overview",
                    "participation_share",
                    title,
                    stmt,
                    "Share of participant messages per sender, compared to an equal split with a one-sample "
                    "proportion z-test.",
                    conf,
                    why,
                    metrics={"shares": {p["name"]: round(p["share"], 4) for p in self.ppl}, "z": round(z, 2)},
                )
            )
            mine = self.pm.filter(pl.col("sender_id") == top["id"])
            f.support(spread(self.ids(mine), 6), f"message by {top['name']}")
            # Counterexamples: months in which someone else out-sent the top sender.
            flips = []
            for row in self.a["activity"]["monthly"]:
                by = row["by"]
                mine_n = by.get(str(top["id"]), 0)
                other = max(((int(k), v) for k, v in by.items() if int(k) != top["id"]), key=lambda x: x[1], default=None)
                if other and other[1] > mine_n:
                    flips.append((row["month"], other[0]))
            if flips:
                f.counterexample_note = (
                    f"In {len(flips)} of {len(self.a['activity']['monthly'])} active months someone else sent more "
                    f"messages than {top['name']} (e.g. {', '.join(fmt_month(m) for m, _ in flips[:3])})."
                )
                for month, pid in flips[:4]:
                    start = datetime.fromisoformat(month)
                    first = self.pm.filter(
                        (pl.col("sender_id") == pid) & (pl.col("ts").dt.truncate("1mo") == start)
                    ).head(1)
                    f.counter(self.ids(first), f"{self.names[pid]} led in {fmt_month(month)}")
            else:
                f.counterexample_note = f"No month in which someone else out-sent {top['name']}."

        bd = ov["busiest_day"]
        day = date.fromisoformat(bd["day"])
        on_day = self.pm.filter(pl.col("ts").dt.date() == day)
        f = self.add(
            Finding(
                "F-OV-busiest-day",
                "overview",
                "busiest_day",
                "The busiest day",
                f"{fmt_date(day)} was the busiest day with {fmt_int(bd['messages'])} participant messages "
                f"(the average active day has {ov['messages_per_active_day']:.1f}).",
                "Participant messages grouped by calendar date; the day with the highest count (earliest wins ties).",
                *EXACT,
                metrics={"day": bd["day"], "messages": bd["messages"]},
                time_start=on_day["ts"].min().isoformat(),  # type: ignore[union-attr]
                time_end=on_day["ts"].max().isoformat(),  # type: ignore[union-attr]
            )
        )
        f.support(spread(self.ids(on_day), 8), "sent on the busiest day")

    # -- 2. People -----------------------------------------------------------------------
    def people(self) -> None:
        for p in self.ppl[:MAX_PEOPLE_FINDINGS]:
            pid, name = p["id"], p["name"]
            mine = self.pm.filter(pl.col("sender_id") == pid)
            text = mine.filter(pl.col("message_type") == "text")
            conf, why = confidence_from_n(p["text_messages"], "text messages")
            q_share = p["questions"] / p["text_messages"] if p["text_messages"] else 0
            f = self.add(
                Finding(
                    f"F-PE-{pid}-style",
                    "people",
                    "writing_style",
                    f"How {name} writes",
                    f"Half of {name}'s text messages are {p['median_words']:.0f} word(s) or shorter and 90% are "
                    f"{p['p90_words']:.0f} or shorter (the mean, {p['mean_words']:.1f}, is pulled up by a few long messages). "
                    f"{fmt_pct(q_share)} contain a question mark, {fmt_int(p['media'])} are media and "
                    f"{fmt_int(p['emoji_total'])} emoji were used in total.",
                    "Word counts of text messages; questions are text messages containing '?'; emoji counted by "
                    "Unicode range.",
                    conf,
                    why,
                    metrics={
                        k: p[k]
                        for k in ("text_messages", "mean_words", "median_words", "p90_words", "questions", "media", "emoji_total", "deleted", "edited")
                    },
                )
            )
            if p["longest_message_id"]:
                f.support([p["longest_message_id"]], f"{name}'s longest text message ({p['longest_message_words']} words)")
            questions = text.filter(pl.col("is_question"))
            f.support(spread(self.ids(questions), 3), "a question")
            f.support(spread(self.ids(text), 4), "typical text message")

            peak = p["peak_hour"]
            at_peak = mine.filter(pl.col("ts").dt.hour() == peak)
            conf, why = confidence_from_n(p["messages"], "messages")
            f = self.add(
                Finding(
                    f"F-PE-{pid}-rhythm",
                    "people",
                    "daily_rhythm",
                    f"When {name} is active",
                    f"{name} sends the most messages in the {peak:02d}:00 hour "
                    f"({fmt_int(p['hour_histogram'][peak])} messages). {fmt_pct(p['late_night_share'])} of "
                    f"{name}'s messages were sent late at night ("
                    f"{self.a['params']['late_night_start_hour']:02d}:00–{self.a['params']['late_night_end_hour'] - 1:02d}:59).",
                    "Messages per hour of day in the exporting phone's local time.",
                    conf,
                    why,
                    metrics={"peak_hour": peak, "hour_histogram": p["hour_histogram"], "late_night_share": p["late_night_share"]},
                )
            )
            f.support(spread(self.ids(at_peak), 5), f"sent in the {peak:02d}:00 hour")

            turns = mine.group_by("turn", maintain_order=True).agg(n=pl.len(), ids=pl.col("id"))
            if turns.height:
                biggest = turns.sort(["n", "turn"], descending=[True, False]).row(0, named=True)
                conf, why = confidence_from_n(p["turns"], "turns")
                f = self.add(
                    Finding(
                        f"F-PE-{pid}-turns",
                        "people",
                        "turn_taking",
                        f"{name}'s turns",
                        f"When it is {name}'s turn, they send {p['messages_per_turn']:.2f} messages on average before "
                        f"someone else replies; the longest uninterrupted run is {biggest['n']} messages.",
                        "A turn is a run of consecutive messages by one sender within a session.",
                        conf,
                        why,
                        metrics={"turns": p["turns"], "messages_per_turn": p["messages_per_turn"], "longest_burst": biggest["n"]},
                    )
                )
                f.support(spread(list(biggest["ids"]), 8), "part of the longest run")

    # -- 3. Dynamics ----------------------------------------------------------------------
    def dynamics(self) -> None:
        s = self.f.sessions
        if len(self.ppl) >= 2 and s.height:
            top = max(self.ppl, key=lambda p: (p["sessions_initiated"], -p["id"]))
            n = s.height
            p0 = 1 / len(self.ppl)
            z = z_proportion(top["sessions_initiated"], n, p0)
            conf, why = confidence_from_z(z, n)
            f = self.add(
                Finding(
                    "F-DY-initiation",
                    "dynamics",
                    "initiation",
                    "Who starts conversations",
                    f"{top['name']} started {fmt_int(top['sessions_initiated'])} of {fmt_int(n)} sessions "
                    f"({fmt_pct(top['initiation_share'])}); an equal split would be {fmt_pct(p0)}. "
                    + "; ".join(
                        f"{p['name']}: {fmt_pct(p['initiation_share'])}" for p in self.ppl if p["id"] != top["id"]
                    )
                    + ".",
                    "The sender of the first message after a gap longer than "
                    f"{self.a['params']['session_gap_minutes']} minutes is counted as the initiator; compared to an "
                    "equal split with a one-sample proportion z-test.",
                    conf,
                    why,
                    metrics={"initiated": {p["name"]: p["sessions_initiated"] for p in self.ppl}, "sessions": n, "z": round(z, 2)},
                )
            )
            f.support(spread(s.filter(pl.col("initiator") == top["id"])["start_id"].to_list(), 8), f"{top['name']} opens a session")
            others = s.filter(pl.col("initiator") != top["id"])["start_id"].to_list()
            f.counter(spread(others, 5), "session started by someone else")
            periods = self.a.get("periods") or []
            if periods:
                late = periods[-1]["by"].get(str(top["id"]), {})
                note = f"{fmt_int(len(others))} sessions were started by others."
                if late and late.get("initiation_share", 0) < p0:
                    note += (
                        f" In the late period {top['name']} started only {fmt_pct(late['initiation_share'])} "
                        "of sessions, so the overall figure hides a change (see Shifts)."
                    )
                f.counterexample_note = note

        rp = [p for p in self.ppl if p["replies"] >= 5]
        res = self.a["overview"].get("timestamp_resolution_s", 1)
        if len(rp) >= 2:
            # Rank by the share of replies sent within five minutes: unlike the
            # median it stays informative when most replies are near-instant
            # and timestamps only have minute resolution.
            rp.sort(key=lambda p: (-(p["reply_within_5min"] / p["replies"]), p["id"]))
            fast, slow = rp[0], rp[-1]
            k1, n1, k2, n2 = fast["reply_within_5min"], fast["replies"], slow["reply_within_5min"], slow["replies"]
            z = z_two_proportions(k1, n1, k2, n2)
            conf, why = confidence_from_z(z, n1 + n2)
            similar = abs(k1 / n1 - k2 / n2) < 0.05
            res_note = (
                " Timestamps in this export have one-minute resolution, so faster replies cannot be told apart."
                if res >= 60
                else ""
            )
            f = self.add(
                Finding(
                    "F-DY-reply",
                    "dynamics",
                    "reply_time",
                    "Reply speed is similar" if similar else f"{fast['name']} tends to reply faster",
                    "Share of replies sent within 5 minutes: "
                    + ", ".join(f"{p['name']} {fmt_pct(p['reply_within_5min'] / p['replies'])}" for p in rp)
                    + ". Median reply: "
                    + ", ".join(f"{p['name']} {fmt_duration(p['reply_median_s'], res)}" for p in rp)
                    + "; 90th percentile: "
                    + ", ".join(f"{p['name']} {fmt_duration(p['reply_p90_s'], res)}" for p in rp)
                    + "."
                    + res_note,
                    "For every reply (a message following someone else's message in the same session) the gap is "
                    "measured. People are compared on the share of replies within 5 minutes using a two-proportion "
                    "z-test; medians and 90th percentiles are shown for context.",
                    conf,
                    why,
                    metrics={
                        p["name"]: {
                            k: p[k]
                            for k in ("replies", "reply_within_5min", "reply_p25_s", "reply_median_s", "reply_p75_s", "reply_p90_s")
                        }
                        for p in rp
                    }
                    | {"z": round(z, 2), "timestamp_resolution_s": res},
                )
            )
            mine = self.f.replies.filter(pl.col("responder") == fast["id"])
            quick = mine.filter(pl.col("reply_s") < 300).sort("ts")
            f.support(spread(self.ids(quick), 6), f"{fast['name']} replying within 5 minutes")
            threshold = max(slow["reply_p75_s"] or 0, 300)
            slow_ones = mine.filter(pl.col("reply_s") > threshold).sort("ts")
            f.counter(spread(self.ids(slow_ones), 5), f"{fast['name']} taking longer than {fmt_duration(threshold, res)}")
            f.counterexample_note = (
                f"{fmt_int(slow_ones.height)} of {fast['name']}'s replies took longer than {fmt_duration(threshold, res)}. "
                "Reply time depends on what was asked and when; it is not a measure of interest."
            )

    # -- 4. Timeline -----------------------------------------------------------------------
    def timeline(self) -> None:
        streaks = self.a["streaks"]["longest"]
        if streaks:
            st = streaks[0]
            lo, hi = date.fromisoformat(st["start"]), date.fromisoformat(st["end"])
            in_streak = self.pm.filter((pl.col("ts").dt.date() >= lo) & (pl.col("ts").dt.date() <= hi))
            firsts = in_streak.group_by(pl.col("ts").dt.date().alias("d"), maintain_order=True).agg(id=pl.col("id").first())
            f = self.add(
                Finding(
                    "F-TL-streak",
                    "timeline",
                    "streak",
                    "The longest unbroken run",
                    f"The longest run of consecutive days with messages lasted {st['days']} days "
                    f"({fmt_date(lo)} – {fmt_date(hi)}), with {fmt_int(in_streak.height)} messages.",
                    "Consecutive calendar dates that each contain at least one participant message.",
                    *EXACT,
                    metrics=st,
                    time_start=st["start"],
                    time_end=st["end"],
                )
            )
            f.support(spread(firsts["id"].to_list(), 10), "first message of a day in the streak")

        for i, g in enumerate(self.a["gaps"]["longest"][:3], start=1):
            f = self.add(
                Finding(
                    f"F-TL-gap-{i}",
                    "timeline",
                    "silence",
                    "The longest silence" if i == 1 else f"Silence #{i}",
                    f"{fmt_duration(g['gap_s'])} passed without any message, ending on {fmt_date(g['ts'])}.",
                    "Time between consecutive participant messages, largest first.",
                    *EXACT,
                    metrics={"gap_s": g["gap_s"]},
                    time_end=g["ts"],
                )
            )
            f.support([g["prev_id"]], "last message before the silence")
            f.support([g["id"]], "first message after the silence")

    # -- 5. Moments --------------------------------------------------------------------------
    def moments(self) -> None:
        first = self.pm.head(1).row(0, named=True)
        f = self.add(
            Finding(
                "F-MO-first",
                "moments",
                "first_message",
                "Where the transcript begins",
                f"The export begins on {fmt_date(first['ts'])} with a message from {first['sender']}. "
                "Earlier history, if any, is not in the file.",
                "First participant message in file order.",
                *EXACT,
                time_start=first["ts"].isoformat(),
            )
        )
        f.support([first["id"]], "first participant message")

        for i, s in enumerate(self.a["sessions"]["largest"][:3], start=1):
            sess = self.pm.filter(pl.col("session") == s["session"])
            init = self.names.get(s["initiator"], "?")
            f = self.add(
                Finding(
                    f"F-MO-session-{i}",
                    "moments",
                    "large_session",
                    "The biggest conversation" if i == 1 else f"Big conversation #{i}",
                    f"On {fmt_date(s['start'])}, a session of {fmt_int(s['messages'])} messages lasted "
                    f"{fmt_duration(s['duration_s'])}; {init} started it.",
                    "Sessions ranked by message count.",
                    *EXACT,
                    metrics={k: s[k] for k in ("messages", "duration_s")},
                    time_start=s["start"],
                    time_end=s["end"],
                )
            )
            f.support(spread(self.ids(sess), 10), "message in this session")

        for i, ch in enumerate(self.a["volume_changes"][:6], start=1):
            month = datetime.fromisoformat(ch["month"])
            in_month = self.pm.filter(pl.col("ts").dt.truncate("1mo") == month)
            pct = "" if ch["relative_change"] is None else f" ({ch['relative_change'] * 100:+.0f}%)"
            f = self.add(
                Finding(
                    f"F-MO-change-{i}",
                    "moments",
                    "volume_change",
                    f"{'Surge' if ch['direction'] == 'up' else 'Drop'} in {fmt_month(ch['month'])}",
                    f"{fmt_month(ch['month'])} had {fmt_int(ch['messages'])} messages versus an average of "
                    f"{ch['trailing_mean']:.0f} over the previous three months{pct}.",
                    "Monthly participant-message count compared with the mean of the preceding three months; "
                    "changes of 50% or more are reported.",
                    "high",
                    "The counts are exact. Why the volume changed is not visible in the data.",
                    metrics=ch,
                    time_start=ch["month"],
                )
            )
            if in_month.height:
                f.support(spread(self.ids(in_month), 6), f"sent in {fmt_month(ch['month'])}")
            else:
                before = self.pm.filter(pl.col("ts") < month).tail(1)
                after = self.pm.filter(pl.col("ts") >= month).head(1)
                f.support(self.ids(before), "last message before the silent month")
                f.support(self.ids(after), "first message after it")

    # -- 6. Topics ---------------------------------------------------------------------------
    def topics(self) -> None:
        t = self.a["topics"]
        for i, term in enumerate(t["terms"][:8], start=1):
            ids = self.f.term_messages.get(term["term"], [])
            leader = max(self.ppl, key=lambda p: (term["by"].get(str(p["id"]), 0), -p["id"]))
            conf, why = ("medium", "Counts are exact, but word matches are lexical: the same word can mean different things and synonyms are missed.")
            if term["sessions"] < 10:
                conf, why = "low", f"Appears in only {term['sessions']} sessions; matches are lexical."
            f = self.add(
                Finding(
                    f"F-TO-term-{i}",
                    "topics",
                    "recurring_term",
                    f"“{term['term']}” keeps coming back",
                    f"“{term['term']}” appears in {fmt_int(term['sessions'])} sessions "
                    f"({fmt_pct(term['session_share'])} of all) and {fmt_int(term['messages'])} messages, from "
                    f"{fmt_date(term['first_ts'])} to {fmt_date(term['last_ts'])}. {leader['name']} uses it most "
                    f"({fmt_int(term['by'].get(str(leader['id']), 0))} messages).",
                    t["method"] + "; ranked by the number of sessions containing the term.",
                    conf,
                    why,
                    metrics=term,
                    time_start=term["first_ts"],
                    time_end=term["last_ts"],
                    counterexample_note="Lexical matching only: synonyms, misspellings and other languages are not "
                    "grouped, and unrelated uses of the same word are counted.",
                )
            )
            f.support(spread(ids, 8), f"mentions “{term['term']}”")

        periods = self.a.get("periods") or []
        for i, terms in enumerate(t["distinctive_by_period"]):
            if not terms or i >= len(periods):
                continue
            per = periods[i]
            lo, hi = datetime.fromisoformat(per["start"]), datetime.fromisoformat(per["end"])
            top = terms[:5]
            words = [x["term"] for x in top]
            text = self.pm.filter(
                (pl.col("message_type") == "text") & (pl.col("ts") >= lo) & (pl.col("ts") <= hi)
            )
            hits = text.filter(
                pl.col("text").str.to_lowercase().str.contains("|".join(rf"\b{_re_escape(w)}\b" for w in words))
            )
            f = self.add(
                Finding(
                    f"F-TO-period-{i + 1}",
                    "topics",
                    "distinctive_terms",
                    f"What marked the {per['label'].lower()} period",
                    f"Between {fmt_date(lo)} and {fmt_date(hi)}, these words were used unusually often compared with the "
                    "rest of the conversation: "
                    + ", ".join(f"“{x['term']}” ({x['in_period']} vs {x['elsewhere']} elsewhere)" for x in top)
                    + ".",
                    "Log-odds ratio with an informative Dirichlet prior comparing this third of the timeline with the "
                    "other two thirds (z ≥ 1.96).",
                    "medium" if top[0]["z"] >= 3 else "low",
                    f"Strongest term z = {top[0]['z']}; lexical matching only.",
                    metrics={"terms": top},
                    time_start=per["start"],
                    time_end=per["end"],
                )
            )
            f.support(spread(self.ids(hits), 8), "uses a distinctive word")

    # -- 7. Shifts ----------------------------------------------------------------------------
    def shifts(self) -> None:
        periods = self.a.get("periods") or []
        if len(periods) < 3:
            return
        early, mid, late = periods
        e_rate, l_rate = early["messages_per_day"], late["messages_per_day"]
        if e_rate > 0:
            change = (l_rate - e_rate) / e_rate
            direction = "rose" if change > 0 else "fell"
            steady = abs(change) < 0.2
            mid_note = None
            if (mid["messages_per_day"] - e_rate) * (l_rate - mid["messages_per_day"]) < 0:
                mid_note = (
                    f"The path was not straight: the middle period averaged {mid['messages_per_day']:.1f} messages/day."
                )
            f = self.add(
                Finding(
                    "F-SH-volume",
                    "shifts",
                    "volume_trend",
                    "Overall pace held steady" if steady else f"The pace {direction}",
                    f"Early on the conversation averaged {e_rate:.1f} messages/day; in the late period "
                    f"{l_rate:.1f} ({change * 100:+.0f}%). Middle period: {mid['messages_per_day']:.1f}/day.",
                    "Participant messages per calendar day in each third of the timeline.",
                    "high" if min(early["messages"], late["messages"]) >= 100 else "medium",
                    "Exact counts; daily averages smooth over individual busy or quiet days.",
                    metrics={"early": e_rate, "middle": mid["messages_per_day"], "late": l_rate},
                    counterexample_note=mid_note,
                    time_start=early["start"],
                    time_end=late["end"],
                )
            )
            s = self.f.sessions
            for per, label in ((early, "early"), (late, "late")):
                lo, hi = datetime.fromisoformat(per["start"]), datetime.fromisoformat(per["end"])
                starts = s.filter((pl.col("start") >= lo) & (pl.col("start") <= hi))["start_id"].to_list()
                f.support(spread(starts, 4), f"session start in the {label} period")
            if mid_note:
                lo, hi = datetime.fromisoformat(mid["start"]), datetime.fromisoformat(mid["end"])
                starts = s.filter((pl.col("start") >= lo) & (pl.col("start") <= hi))["start_id"].to_list()
                f.counter(spread(starts, 3), "session start in the middle period")

        s = self.f.sessions
        for p in self.ppl[:MAX_PEOPLE_FINDINGS]:
            pid, key = p["id"], str(p["id"])
            e, l = early["by"].get(key), late["by"].get(key)
            if not e or not l:
                continue
            # Initiation shift
            if early["sessions"] >= 10 and late["sessions"] >= 10:
                diff = l["initiation_share"] - e["initiation_share"]
                if abs(diff) >= 0.15:
                    z = z_two_proportions(l["initiated"], late["sessions"], e["initiated"], early["sessions"])
                    conf, why = confidence_from_z(z, early["sessions"] + late["sessions"])
                    f = self.add(
                        Finding(
                            f"F-SH-{pid}-initiation",
                            "shifts",
                            "initiation_shift",
                            f"{p['name']} {'started more' if diff > 0 else 'stopped starting as many'} conversations",
                            f"{p['name']} started {fmt_pct(e['initiation_share'])} of sessions in the early period "
                            f"and {fmt_pct(l['initiation_share'])} in the late period "
                            f"(middle: {fmt_pct(mid['by'][key]['initiation_share'])}).",
                            "Initiation share in the first and last third of the timeline, compared with a "
                            "two-proportion z-test.",
                            conf,
                            why,
                            metrics={"early": e, "middle": mid["by"][key], "late": l},
                            time_start=early["start"],
                            time_end=late["end"],
                        )
                    )
                    for per, label in ((early, "early"), (late, "late")):
                        lo, hi = datetime.fromisoformat(per["start"]), datetime.fromisoformat(per["end"])
                        mine = s.filter(
                            (pl.col("start") >= lo) & (pl.col("start") <= hi) & (pl.col("initiator") == pid)
                        )["start_id"].to_list()
                        f.support(spread(mine, 4), f"{p['name']} opens a session ({label} period)")
            # Reply-time shift
            if e["replies"] >= 20 and l["replies"] >= 20 and e["reply_median_s"] and l["reply_median_s"]:
                ratio = l["reply_median_s"] / e["reply_median_s"]
                if ratio >= 1.5 or ratio <= 1 / 1.5:
                    f = self.add(
                        Finding(
                            f"F-SH-{pid}-reply",
                            "shifts",
                            "reply_time_shift",
                            f"{p['name']} replies {'more slowly' if ratio > 1 else 'faster'} than before",
                            f"{p['name']}'s median reply time went from {fmt_duration(e['reply_median_s'])} (early, "
                            f"n = {e['replies']}) to {fmt_duration(l['reply_median_s'])} (late, n = {l['replies']}).",
                            "Median within-session reply time in the first and last third of the timeline.",
                            "medium" if min(e["replies"], l["replies"]) >= 50 else "low",
                            "Medians of moderate samples; a change in reply time can have many everyday causes.",
                            metrics={"early": e["reply_median_s"], "late": l["reply_median_s"], "ratio": ratio},
                            time_start=early["start"],
                            time_end=late["end"],
                        )
                    )
                    lo = datetime.fromisoformat(late["start"])
                    ex = self.f.replies.filter((pl.col("responder") == pid) & (pl.col("ts") >= lo)).sort("ts")
                    f.support(spread(self.ids(ex), 5), f"{p['name']} replying in the late period")
            # Share shift (only meaningful with 2+ people)
            if len(self.ppl) >= 2 and abs(l["share"] - e["share"]) >= 0.1:
                f = self.add(
                    Finding(
                        f"F-SH-{pid}-share",
                        "shifts",
                        "share_shift",
                        f"{p['name']}'s share of the conversation changed",
                        f"{p['name']} wrote {fmt_pct(e['share'])} of messages early on and {fmt_pct(l['share'])} later.",
                        "Share of participant messages in the first versus last third of the timeline.",
                        "medium",
                        "Exact counts; share depends on how many others were active.",
                        metrics={"early": e["share"], "late": l["share"]},
                    )
                )
                lo = datetime.fromisoformat(late["start"])
                ex = self.pm.filter((pl.col("sender_id") == pid) & (pl.col("ts") >= lo))
                f.support(spread(self.ids(ex), 5), f"{p['name']} in the late period")

    # -- 8. Limitations -----------------------------------------------------------------------
    def limitations(self) -> None:
        ov = self.a["overview"]
        audit = self.audit
        from openmirror.ingest.whatsapp import NOTICE_KINDS

        all_counts = audit.get("issue_counts", {})
        issues = {k: v for k, v in all_counts.items() if k not in NOTICE_KINDS}
        notices = {k: v for k, v in all_counts.items() if k in NOTICE_KINDS}
        total_issues = sum(issues.values())
        parts = [
            f"{fmt_int(audit.get('messages_parsed', 0))} messages were parsed from "
            f"{fmt_int(audit.get('lines_total', 0))} lines ({fmt_int(audit.get('continuation_lines', 0))} continuation lines "
            "joined into multiline messages)."
        ]
        if total_issues:
            parts.append(
                f"{fmt_int(total_issues)} import issue(s) were recorded: "
                + ", ".join(f"{k.replace('_', ' ')} × {v}" for k, v in sorted(issues.items()))
                + ". See the import audit."
            )
        else:
            parts.append("No import problems were recorded.")
        if notices.get("out_of_order_timestamp"):
            parts.append(
                f"{fmt_int(notices['out_of_order_timestamp'])} message(s) carry a timestamp slightly earlier than the "
                "message before them. This is normal: WhatsApp lists messages in delivery order. File order is kept "
                "and negative gaps are treated as zero."
            )
        if audit.get("date_order_ambiguous"):
            parts.append(
                f"Day/month order was ambiguous; {audit.get('date_order')} was assumed ({audit.get('date_order_reason')})."
            )
        self.add(
            Finding(
                "F-LI-import",
                "limitations",
                "import_quality",
                "How cleanly the export was read",
                " ".join(parts),
                "Import audit produced by the parser.",
                "high" if not total_issues and not audit.get("date_order_ambiguous") else "medium",
                "Every line is accounted for: as a message header, a continuation line, or a recorded issue.",
                metrics={"issue_counts": issues, "notice_counts": notices, "date_order": audit.get("date_order")},
            )
        )

        non_text = {k: v for k, v in ov["by_type"].items() if k not in ("text", "system")}
        f = self.add(
            Finding(
                "F-LI-content",
                "limitations",
                "unanalysed_content",
                "What the analysis cannot see",
                "Media, voice notes, calls and deleted messages appear only as placeholders: "
                + (", ".join(f"{k} × {fmt_int(v)}" for k, v in sorted(non_text.items())) or "none in this export")
                + ". Their content is not analysed. Timestamps are the exporting phone's local time, and the export "
                "contains only what WhatsApp included (it may be truncated for very long chats).",
                "Counts of non-text message types.",
                *EXACT,
                metrics=non_text,
            )
        )
        placeholders = self.pm.filter(pl.col("message_type").is_in(["media", "deleted", "call"]))
        f.support(spread(self.ids(placeholders), 5), "placeholder message")

        self.add(
            Finding(
                "F-LI-interpretation",
                "limitations",
                "interpretation",
                "Patterns are not motives",
                "These findings describe observable behaviour (who wrote what, when and how quickly). They do not "
                "reveal feelings, intentions or the relationship outside this chat, which may also happen in person, "
                "by phone or on other apps.",
                "Scope statement.",
                "high",
                "Applies to every finding in this report.",
            )
        )


def _re_escape(word: str) -> str:
    import re

    return re.escape(word)


# --- Validation and persistence ------------------------------------------------------------


class EvidenceIntegrityError(ValueError):
    pass


def validate_findings(conn: sqlite3.Connection, conversation_id: str, findings: list[Finding]) -> None:
    """Ensure every referenced message exists and belongs to the conversation."""
    ids = {e.message_id for f in findings for e in f.evidence}
    seen_ids: set[str] = set()
    for f in findings:
        if f.id in seen_ids:
            raise EvidenceIntegrityError(f"duplicate finding id {f.id}")
        seen_ids.add(f.id)
        if f.chapter not in CHAPTERS:
            raise EvidenceIntegrityError(f"unknown chapter {f.chapter}")
        if f.confidence not in ("high", "medium", "low"):
            raise EvidenceIntegrityError(f"bad confidence on {f.id}")
    if not ids:
        return
    found: set[int] = set()
    id_list = list(ids)
    for i in range(0, len(id_list), 900):
        chunk = id_list[i : i + 900]
        q = f"SELECT id FROM messages WHERE conversation_id=? AND id IN ({','.join('?' * len(chunk))})"
        found.update(r[0] for r in conn.execute(q, (conversation_id, *chunk)))
    missing = ids - found
    if missing:
        raise EvidenceIntegrityError(f"{len(missing)} evidence reference(s) point to unknown messages")

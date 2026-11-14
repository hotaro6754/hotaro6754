"""Deterministic conversation analytics.

All metrics are computed from the stored messages with plain counting and
order statistics; no model is involved. Each metric is defined in
``docs/METRICS.md`` and the definitions are repeated in the ``definitions``
block of the output so the report can show them next to the numbers.

Conventions
-----------
* *Participant messages* exclude WhatsApp system notices.
* Ordering follows the export file (``seq``), which is WhatsApp's own order.
* Timestamps are local time of the exporting phone; no time-zone conversion.
* A *session* is a run of participant messages where no gap between
  consecutive messages exceeds ``session_gap_minutes``.
* A *reply* is a participant message whose previous participant message, in
  the same session, came from someone else. Its *reply time* is the gap
  between the two.
"""

from __future__ import annotations

import math
import sqlite3
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from datetime import date, datetime

import polars as pl

from openmirror.analytics.text import emojis, topic_terms, word_count

ENGINE_VERSION = "1.0.0"

REPLY_BUCKETS = [
    ("< 1 min", 0, 60),
    ("1–5 min", 60, 300),
    ("5–30 min", 300, 1800),
    ("30 min–2 h", 1800, 7200),
    ("2 h+", 7200, None),
]
LENGTH_BUCKETS = [("1 word", 1, 1), ("2–5", 2, 5), ("6–10", 6, 10), ("11–20", 11, 20), ("21–50", 21, 50), ("51+", 51, None)]
WEEKDAYS = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]


@dataclass
class AnalysisParams:
    session_gap_minutes: int = 240
    top_terms: int = 25
    late_night_start_hour: int = 0  # inclusive
    late_night_end_hour: int = 5  # exclusive

    def as_dict(self) -> dict:
        return dict(self.__dict__)


@dataclass
class Frames:
    """Intermediate tables needed by the evidence engine."""

    messages: pl.DataFrame  # participant messages, file order, with session/turn columns
    all_messages: pl.DataFrame
    sessions: pl.DataFrame
    replies: pl.DataFrame
    gaps: pl.DataFrame
    names: dict[int, str]
    term_messages: dict[str, list[int]] = field(default_factory=dict)


def load_frames(conn: sqlite3.Connection, conversation_id: str, params: AnalysisParams) -> Frames:
    rows = conn.execute(
        """SELECT m.id, m.seq, m.sender_id, p.display_name AS sender, m.ts, m.message_type,
                  m.media_kind, m.is_edited, m.text
           FROM messages m LEFT JOIN participants p ON p.id = m.sender_id
           WHERE m.conversation_id = ? ORDER BY m.seq""",
        (conversation_id,),
    ).fetchall()
    schema = {
        "id": pl.Int64,
        "seq": pl.Int64,
        "sender_id": pl.Int64,
        "sender": pl.Utf8,
        "ts": pl.Utf8,
        "message_type": pl.Utf8,
        "media_kind": pl.Utf8,
        "is_edited": pl.Int64,
        "text": pl.Utf8,
    }
    df = pl.DataFrame([tuple(r) for r in rows], schema=schema, orient="row")
    df = df.with_columns(pl.col("ts").str.to_datetime("%Y-%m-%dT%H:%M:%S", strict=True))
    names = {
        int(r["id"]): r["display_name"]
        for r in conn.execute(
            "SELECT id, display_name FROM participants WHERE conversation_id=? ORDER BY id", (conversation_id,)
        )
    }

    gap_s = params.session_gap_minutes * 60
    pm = df.filter(pl.col("sender_id").is_not_null())
    pm = pm.with_columns(
        words=pl.col("text").map_elements(word_count, return_dtype=pl.Int64),
        is_question=pl.col("text").str.contains(r"\?") & (pl.col("message_type") == "text"),
        is_link=pl.col("text").str.contains(r"(?i)https?://|www\."),
    )
    pm = pm.with_columns(
        words=pl.when(pl.col("message_type") == "text").then(pl.col("words")).otherwise(0),
        prev_sender=pl.col("sender_id").shift(1),
        prev_id=pl.col("id").shift(1),
        gap_s=(pl.col("ts") - pl.col("ts").shift(1)).dt.total_seconds().clip(lower_bound=0),
    )
    pm = pm.with_columns(new_session=pl.col("gap_s").is_null() | (pl.col("gap_s") > gap_s))
    pm = pm.with_columns(
        session=pl.col("new_session").cast(pl.Int64).cum_sum(),
        new_turn=pl.col("new_session") | (pl.col("sender_id") != pl.col("prev_sender")),
    )
    pm = pm.with_columns(turn=pl.col("new_turn").cast(pl.Int64).cum_sum())

    sessions = (
        pm.group_by("session", maintain_order=True)
        .agg(
            start_id=pl.col("id").first(),
            end_id=pl.col("id").last(),
            start=pl.col("ts").first(),
            end=pl.col("ts").last(),
            initiator=pl.col("sender_id").first(),
            messages=pl.len(),
            participants=pl.col("sender_id").n_unique(),
        )
        .with_columns(duration_s=(pl.col("end") - pl.col("start")).dt.total_seconds())
    )
    replies = pm.filter(
        (~pl.col("new_session")) & pl.col("prev_sender").is_not_null() & (pl.col("sender_id") != pl.col("prev_sender"))
    ).select(
        "id", "prev_id", "ts", responder="sender_id", to="prev_sender", reply_s="gap_s"
    )
    gaps = (
        pm.filter(pl.col("gap_s").is_not_null())
        .select("id", "prev_id", "ts", "gap_s")
        .sort("gap_s", descending=True)
        .head(10)
    )
    return Frames(messages=pm, all_messages=df, sessions=sessions, replies=replies, gaps=gaps, names=names)


def _q(values: list[float], q: float) -> float | None:
    if not values:
        return None
    s = sorted(values)
    idx = min(len(s) - 1, max(0, math.ceil(q * len(s)) - 1))
    return float(s[idx])


def _iso(v: object) -> object:
    if isinstance(v, (datetime, date)):
        return v.isoformat()
    return v


def _records(df: pl.DataFrame) -> list[dict]:
    return [{k: _iso(v) for k, v in row.items()} for row in df.iter_rows(named=True)]


def compute(frames: Frames, params: AnalysisParams) -> dict:
    pm = frames.messages
    df = frames.all_messages
    names = frames.names
    pids = list(names)
    out: dict = {"engine_version": ENGINE_VERSION, "params": params.as_dict()}

    if pm.height == 0:
        out["empty"] = True
        out["overview"] = {"total_messages": df.height, "participant_messages": 0}
        return out

    first, last = pm["ts"].min(), pm["ts"].max()
    span_days = (last.date() - first.date()).days + 1  # type: ignore[union-attr]
    active_days = pm["ts"].dt.date().n_unique()
    by_type = dict(Counter(df["message_type"].to_list()))
    daily_total = pm.group_by(pl.col("ts").dt.date().alias("day")).agg(n=pl.len()).sort("day")
    busiest_day = daily_total.sort(["n", "day"], descending=[True, False]).row(0, named=True)
    monthly_total = pm.group_by(pl.col("ts").dt.truncate("1mo").alias("month")).agg(n=pl.len()).sort("month")
    busiest_month = monthly_total.sort(["n", "month"], descending=[True, False]).row(0, named=True)

    # Android exports record minutes only; iOS records seconds. Reply times
    # shorter than the resolution cannot be distinguished.
    resolution_s = 60 if int((pm["ts"].dt.second() != 0).sum()) == 0 else 1

    out["overview"] = {
        "timestamp_resolution_s": resolution_s,
        "total_messages": df.height,
        "participant_messages": pm.height,
        "system_messages": by_type.get("system", 0),
        "by_type": by_type,
        "participants": len(pids),
        "first_ts": first.isoformat(),  # type: ignore[union-attr]
        "last_ts": last.isoformat(),  # type: ignore[union-attr]
        "span_days": span_days,
        "active_days": active_days,
        "active_day_share": active_days / span_days if span_days else 0,
        "messages_per_active_day": pm.height / active_days if active_days else 0,
        "busiest_day": {"day": busiest_day["day"].isoformat(), "messages": busiest_day["n"]},
        "busiest_month": {"month": busiest_month["month"].date().isoformat(), "messages": busiest_month["n"]},
        "sessions": frames.sessions.height,
    }

    # --- Per participant -----------------------------------------------------------
    reply_by: dict[int, list[float]] = defaultdict(list)
    for r in frames.replies.iter_rows(named=True):
        reply_by[r["responder"]].append(r["reply_s"])
    initiated = Counter(frames.sessions["initiator"].to_list())
    turns = pm.group_by("turn").agg(sender=pl.col("sender_id").first(), n=pl.len())
    turn_stats = {
        r["sender"]: r
        for r in turns.group_by("sender")
        .agg(turns=pl.len(), msgs_per_turn=pl.col("n").mean(), max_burst=pl.col("n").max())
        .iter_rows(named=True)
    }
    hour_counts = pm.group_by(["sender_id", pl.col("ts").dt.hour().alias("hour")]).agg(n=pl.len())
    people = []
    for pid in pids:
        mine = pm.filter(pl.col("sender_id") == pid)
        if mine.height == 0:
            people.append({"id": pid, "name": names[pid], "messages": 0})
            continue
        text_msgs = mine.filter(pl.col("message_type") == "text")
        words = text_msgs["words"].to_list()
        emoji_counter: Counter[str] = Counter()
        for t in text_msgs["text"].to_list():
            emoji_counter.update(emojis(t))
        hours = {r["hour"]: r["n"] for r in hour_counts.filter(pl.col("sender_id") == pid).iter_rows(named=True)}
        hist = [hours.get(h, 0) for h in range(24)]
        late = sum(hist[params.late_night_start_hour : params.late_night_end_hour])
        longest = text_msgs.sort(["words", "seq"], descending=[True, False]).head(1)
        rs = reply_by.get(pid, [])
        ts_ = turn_stats.get(pid, {})
        people.append(
            {
                "id": pid,
                "name": names[pid],
                "messages": mine.height,
                "share": mine.height / pm.height,
                "text_messages": text_msgs.height,
                "words": int(sum(words)),
                "mean_words": (sum(words) / len(words)) if words else 0,
                "median_words": _q(words, 0.5) or 0,
                "p90_words": _q(words, 0.9) or 0,
                "media": int((mine["message_type"] == "media").sum()),
                "deleted": int((mine["message_type"] == "deleted").sum()),
                "edited": int(mine["is_edited"].sum()),
                "questions": int(mine["is_question"].sum()),
                "links": int(mine["is_link"].sum()),
                "emoji_total": sum(emoji_counter.values()),
                "top_emojis": [{"emoji": e, "count": c} for e, c in emoji_counter.most_common(5)],
                "hour_histogram": hist,
                "peak_hour": max(range(24), key=lambda h: (hist[h], -h)),
                "late_night_messages": late,
                "late_night_share": late / mine.height,
                "sessions_initiated": initiated.get(pid, 0),
                "initiation_share": initiated.get(pid, 0) / frames.sessions.height if frames.sessions.height else 0,
                "turns": ts_.get("turns", 0),
                "messages_per_turn": ts_.get("msgs_per_turn", 0) or 0,
                "longest_burst": ts_.get("max_burst", 0) or 0,
                "replies": len(rs),
                "reply_median_s": _q(rs, 0.5),
                "reply_p25_s": _q(rs, 0.25),
                "reply_p75_s": _q(rs, 0.75),
                "reply_p90_s": _q(rs, 0.9),
                "reply_within_resolution": sum(1 for x in rs if x < resolution_s),
                "reply_within_5min": sum(1 for x in rs if x < 300),
                "longest_message_id": longest["id"][0] if longest.height else None,
                "longest_message_words": longest["words"][0] if longest.height else 0,
                "first_message_id": mine["id"][0],
                "last_message_id": mine["id"][-1],
            }
        )
    out["participants"] = people

    # --- Activity series ----------------------------------------------------------------
    def series(trunc: str | None, key: str) -> list[dict]:
        col = pl.col("ts").dt.date() if trunc is None else pl.col("ts").dt.truncate(trunc).dt.date()
        g = pm.group_by([col.alias(key), "sender_id"]).agg(n=pl.len())
        rows: dict[str, dict] = {}
        for r in g.iter_rows(named=True):
            k = r[key].isoformat()
            rows.setdefault(k, {key: k, "total": 0, "by": {}})
            rows[k]["by"][str(r["sender_id"])] = r["n"]
            rows[k]["total"] += r["n"]
        return [rows[k] for k in sorted(rows)]

    out["activity"] = {
        "daily": series(None, "day"),
        "weekly": series("1w", "week"),
        "monthly": series("1mo", "month"),
    }
    hm = pm.group_by([pl.col("ts").dt.weekday().alias("wd"), pl.col("ts").dt.hour().alias("h")]).agg(n=pl.len())
    grid = [[0] * 24 for _ in range(7)]
    for r in hm.iter_rows(named=True):
        grid[r["wd"] - 1][r["h"]] = r["n"]
    out["activity"]["weekday_hour"] = {"weekdays": WEEKDAYS, "grid": grid}
    out["activity"]["hour_of_day"] = [int(sum(grid[d][h] for d in range(7))) for h in range(24)]

    # --- Message length distribution ------------------------------------------------------
    lengths = []
    for pid in pids:
        w = pm.filter((pl.col("sender_id") == pid) & (pl.col("message_type") == "text"))["words"].to_list()
        counts = []
        for label, lo, hi in LENGTH_BUCKETS:
            counts.append({"bucket": label, "n": sum(1 for x in w if x >= lo and (hi is None or x <= hi))})
        lengths.append({"participant_id": pid, "buckets": counts})
    out["length_distribution"] = lengths

    # --- Reply times ------------------------------------------------------------------------
    reply_dist = []
    for pid in pids:
        rs = reply_by.get(pid, [])
        reply_dist.append(
            {
                "participant_id": pid,
                "n": len(rs),
                "buckets": [
                    {"bucket": label, "n": sum(1 for x in rs if x >= lo and (hi is None or x < hi))}
                    for label, lo, hi in REPLY_BUCKETS
                ],
            }
        )
    out["reply_times"] = reply_dist

    # --- Sessions and initiation ------------------------------------------------------------
    s = frames.sessions
    monthly_init = (
        s.group_by([pl.col("start").dt.truncate("1mo").dt.date().alias("month"), "initiator"]).agg(n=pl.len())
    )
    init_rows: dict[str, dict] = {}
    for r in monthly_init.iter_rows(named=True):
        k = r["month"].isoformat()
        init_rows.setdefault(k, {"month": k, "total": 0, "by": {}})
        init_rows[k]["by"][str(r["initiator"])] = r["n"]
        init_rows[k]["total"] += r["n"]
    durations = s["duration_s"].to_list()
    sizes = s["messages"].to_list()
    out["sessions"] = {
        "count": s.height,
        "gap_threshold_minutes": params.session_gap_minutes,
        "median_messages": _q(sizes, 0.5),
        "median_duration_s": _q(durations, 0.5),
        "initiation_by_month": [init_rows[k] for k in sorted(init_rows)],
        "largest": _records(
            s.sort(["messages", "session"], descending=[True, False]).head(10).select(
                "session", "start_id", "end_id", "start", "end", "messages", "duration_s", "initiator"
            )
        ),
    }

    # --- Streaks and gaps -----------------------------------------------------------------------
    days = sorted(set(pm["ts"].dt.date().to_list()))
    streaks: list[dict] = []
    run_start = prev = days[0]
    for d in days[1:] + [None]:  # type: ignore[list-item]
        if d is not None and (d - prev).days == 1:
            prev = d
            continue
        streaks.append({"start": run_start.isoformat(), "end": prev.isoformat(), "days": (prev - run_start).days + 1})
        if d is not None:
            run_start = prev = d
    streaks.sort(key=lambda x: (-x["days"], x["start"]))
    out["streaks"] = {"longest": streaks[:5], "count": len(streaks)}
    out["gaps"] = {"longest": _records(frames.gaps)}

    # --- Participation over time -----------------------------------------------------------------
    out["participation_by_month"] = [
        {"month": r["month"], "total": r["total"], "share": {k: v / r["total"] for k, v in r["by"].items()}}
        for r in out["activity"]["monthly"]
    ]
    out["periods"] = _period_comparison(frames, pids)
    out["volume_changes"] = _volume_changes(out["activity"]["monthly"])

    # --- Topics --------------------------------------------------------------------------------------
    out["topics"] = _topics(frames, params, pids)

    out["definitions"] = DEFINITIONS
    return out


def _period_comparison(frames: Frames, pids: list[int]) -> list[dict]:
    """Split the timeline into three equal-length periods and compare them."""
    pm = frames.messages
    first, last = pm["ts"].min(), pm["ts"].max()
    span = (last - first).total_seconds()  # type: ignore[operator]
    if span <= 0:
        return []
    bounds = [first + (last - first) * i / 3 for i in range(4)]  # type: ignore[operator]
    labels = ["Early", "Middle", "Late"]
    periods = []
    for i in range(3):
        lo, hi = bounds[i], bounds[i + 1]
        cond = (pl.col("ts") >= lo) & ((pl.col("ts") < hi) if i < 2 else (pl.col("ts") <= hi))
        chunk = pm.filter(cond)
        sess = frames.sessions.filter(
            (pl.col("start") >= lo) & ((pl.col("start") < hi) if i < 2 else (pl.col("start") <= hi))
        )
        reps = frames.replies.filter(
            (pl.col("ts") >= lo) & ((pl.col("ts") < hi) if i < 2 else (pl.col("ts") <= hi))
        )
        days = max((hi - lo).total_seconds() / 86400, 1e-9)  # type: ignore[operator]
        by = {}
        for pid in pids:
            n = int((chunk["sender_id"] == pid).sum())
            init = int((sess["initiator"] == pid).sum())
            rs = reps.filter(pl.col("responder") == pid)["reply_s"].to_list()
            by[str(pid)] = {
                "messages": n,
                "share": n / chunk.height if chunk.height else 0,
                "initiated": init,
                "initiation_share": init / sess.height if sess.height else 0,
                "reply_median_s": _q(rs, 0.5),
                "replies": len(rs),
            }
        periods.append(
            {
                "label": labels[i],
                "start": lo.isoformat(),  # type: ignore[union-attr]
                "end": hi.isoformat(),  # type: ignore[union-attr]
                "messages": chunk.height,
                "messages_per_day": chunk.height / days,
                "sessions": sess.height,
                "by": by,
            }
        )
    return periods


def _volume_changes(monthly: list[dict]) -> list[dict]:
    """Months whose volume differs from the trailing 3-month mean by ≥ 50%.

    Months with no messages are filled in so that a silent month counts as 0.
    """
    if len(monthly) < 4:
        return []
    totals = {r["month"]: r["total"] for r in monthly}
    start = date.fromisoformat(monthly[0]["month"])
    end = date.fromisoformat(monthly[-1]["month"])
    months = []
    y, m = start.year, start.month
    while (y, m) <= (end.year, end.month):
        months.append(date(y, m, 1).isoformat())
        y, m = (y + 1, 1) if m == 12 else (y, m + 1)
    vals = [totals.get(k, 0) for k in months]
    changes = []
    for i in range(3, len(vals)):
        base = sum(vals[i - 3 : i]) / 3
        if base < 10 and vals[i] < 10:
            continue
        change = (vals[i] - base) / base if base else math.inf
        if abs(change) >= 0.5:
            changes.append(
                {
                    "month": months[i],
                    "messages": vals[i],
                    "trailing_mean": round(base, 1),
                    "relative_change": None if math.isinf(change) else round(change, 3),
                    "direction": "up" if vals[i] > base else "down",
                }
            )
    return changes


def _topics(frames: Frames, params: AnalysisParams, pids: list[int]) -> dict:
    pm = frames.messages.filter(pl.col("message_type") == "text")
    session_terms: dict[str, set[int]] = defaultdict(set)
    term_count: Counter[str] = Counter()
    term_by_person: dict[str, Counter[int]] = defaultdict(Counter)
    term_msgs: dict[str, list[int]] = defaultdict(list)
    term_first: dict[str, str] = {}
    term_last: dict[str, str] = {}
    period_counts: list[Counter[str]] = [Counter(), Counter(), Counter()]
    first, last = frames.messages["ts"].min(), frames.messages["ts"].max()
    span = max((last - first).total_seconds(), 1)  # type: ignore[operator]

    for r in pm.select("id", "sender_id", "ts", "session", "text").iter_rows(named=True):
        terms = set(topic_terms(r["text"]))
        if not terms:
            continue
        period = min(2, int(3 * (r["ts"] - first).total_seconds() / span))
        iso = r["ts"].isoformat()
        for t in terms:
            term_count[t] += 1
            session_terms[t].add(r["session"])
            term_by_person[t][r["sender_id"]] += 1
            term_msgs[t].append(r["id"])
            term_first.setdefault(t, iso)
            term_last[t] = iso
            period_counts[period][t] += 1

    total_sessions = max(frames.sessions.height, 1)
    # Rank by the number of sessions a term appears in (recurrence), then by
    # message count. Terms in only one session are not "recurring".
    ranked = sorted(
        (t for t in term_count if len(session_terms[t]) >= 2),
        key=lambda t: (-len(session_terms[t]), -term_count[t], t),
    )[: params.top_terms]
    frames.term_messages = {t: term_msgs[t] for t in ranked}
    terms_out = [
        {
            "term": t,
            "messages": term_count[t],
            "sessions": len(session_terms[t]),
            "session_share": len(session_terms[t]) / total_sessions,
            "by": {str(p): term_by_person[t].get(p, 0) for p in pids},
            "first_ts": term_first[t],
            "last_ts": term_last[t],
            "by_period": [period_counts[i].get(t, 0) for i in range(3)],
        }
        for t in ranked
    ]

    # Distinctive terms per period: log-odds ratio with an informative
    # Dirichlet prior (Monroe, Colaresi & Quinn 2008), z-scored.
    distinctive = []
    total = Counter()
    for c in period_counts:
        total.update(c)
    n_total = sum(total.values())
    alpha0 = n_total * 0.01 if n_total else 1.0
    for i, c in enumerate(period_counts):
        n_i = sum(c.values())
        rest = total - c
        n_j = sum(rest.values())
        scored = []
        for t, y_i in c.items():
            if y_i < 3:
                continue
            a_w = alpha0 * total[t] / n_total
            y_j = rest.get(t, 0)
            delta = math.log((y_i + a_w) / (n_i + alpha0 - y_i - a_w)) - math.log(
                (y_j + a_w) / (n_j + alpha0 - y_j - a_w)
            )
            var = 1 / (y_i + a_w) + 1 / (y_j + a_w)
            scored.append((delta / math.sqrt(var), t, y_i, y_j))
        scored.sort(key=lambda x: (-x[0], x[1]))
        distinctive.append(
            [
                {"term": t, "z": round(z, 2), "in_period": yi, "elsewhere": yj}
                for z, t, yi, yj in scored[:8]
                if z >= 1.96
            ]
        )
    return {
        "method": "session recurrence of non-stopword terms (≥3 letters) in text messages",
        "total_sessions": total_sessions,
        "terms": terms_out,
        "distinctive_by_period": distinctive,
    }


DEFINITIONS = {
    "participant_message": "Any message with a sender. WhatsApp system notices are excluded.",
    "session": "A run of participant messages in which no gap between consecutive messages exceeds the session gap threshold.",
    "initiation": "The sender of the first message of a session started that session.",
    "reply": "A participant message whose previous participant message in the same session was sent by someone else.",
    "reply_time": "Time between a reply and the message immediately before it. Replies across sessions are not counted.",
    "turn": "A run of consecutive messages by the same sender within a session.",
    "words": "Count of letter-based tokens in a text message (URLs and the edited marker removed). Media, deleted and other non-text messages count 0.",
    "question": "A text message containing a question mark.",
    "late_night": "Messages sent between the configured late-night hours (default 00:00–04:59, device local time).",
    "active_day": "A calendar day with at least one participant message.",
    "streak": "Consecutive calendar days that each contain at least one participant message.",
    "gap": "Time between two consecutive participant messages.",
    "recurring_term": "A non-stopword term of at least three letters appearing in text messages in at least two sessions; ranked by the number of sessions it appears in.",
    "distinctive_term": "Terms over-represented in one third of the timeline relative to the other two thirds, using a log-odds ratio with an informative Dirichlet prior; z ≥ 1.96 shown.",
    "volume_change": "A calendar month whose participant-message count differs from the mean of the previous three months by at least 50%.",
    "periods": "The time between the first and last participant message split into three equal-length periods.",
}

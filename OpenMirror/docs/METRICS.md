# Metric definitions

Every number in a report is computed by `backend/openmirror/analytics/engine.py` from stored messages,
without sampling or models. The same definitions are embedded in each analysis (`analytics.definitions`).

## Conventions

* **Participant message:** any message with a sender. WhatsApp system notices are excluded everywhere
  except the total count.
* **Order:** file order (`seq`), which is WhatsApp's own order. Exports list messages in *delivery*
  order, so a message can carry a timestamp a minute or two earlier than the one before it. Such steps are
  recorded as notices, and the negative gap is treated as 0.
* **Time:** local time of the exporting phone, with no time-zone conversion. Android exports have
  **one-minute resolution**, so durations under a minute display as "under 1 min".
* **Quantiles:** nearest-rank (`ceil(q·n)`-th smallest value).

## Metrics

| Metric | Definition |
|---|---|
| Span | Calendar days from the first to the last participant message, inclusive |
| Active day | A calendar day with ≥ 1 participant message |
| Session | A maximal run of participant messages with no gap above the *session gap* (default 240 min, adjustable in the UI: 1–24 h) |
| Initiation | The sender of a session's first message |
| Turn | A run of consecutive messages by one sender inside a session |
| Messages per turn | Messages ÷ turns for that sender |
| Reply | A participant message whose previous participant message, in the same session, came from someone else |
| Reply time | Gap between a reply and the preceding message. Replies across sessions are not counted |
| Within 5 min | Share of a person's replies with reply time < 300 s (robust to minute resolution) |
| Words | Letter-based tokens in a *text* message (any script, URLs and the edited marker removed). Non-text messages count 0 |
| Median / p90 words | Order statistics of words over text messages |
| Question | Text message containing `?` |
| Late night | Messages sent 00:00–04:59 |
| Streak | Consecutive calendar days that are all active |
| Gap / silence | Time between consecutive participant messages |
| Hour / weekday distributions | Counts by `hour(ts)` and ISO weekday |
| Daily / weekly / monthly series | Counts per calendar day, ISO week (Monday start) and month, per sender |
| Volume change | A month whose count differs from the mean of the previous three months by ≥ 50% (months with no messages count as 0; ignored when both values are < 10) |
| Periods | The span from the first to the last message split into three equal stretches of time: Early / Middle / Late |
| Recurring term | Lower-cased token, ≥ 3 letters, not a stopword, letters repeated 3+ times folded to 2, found in text messages of ≥ 2 sessions. Ranked by number of sessions, then messages |
| Distinctive term | Log-odds ratio with an informative Dirichlet prior (Monroe, Colaresi & Quinn, 2008) comparing one period with the other two. z ≥ 1.96 shown, term must occur ≥ 3 times in the period |

Stopwords (`analytics/stopwords.py`) cover English function words, chat fillers, WhatsApp placeholders and
romanised Telugu, Hindi and Tamil particles, pronouns and terms of address. They're plain text and meant
to be extended.

## Findings and confidence

A finding is a statement built only from the numbers above, together with:

* `method`: how it was computed;
* `evidence`: supporting message IDs (spread evenly across the relevant messages, deterministic) and
  **counterexample** message IDs where they exist, plus a `counterexample_note`;
* `confidence` and `confidence_reason`.

| Level | Rule |
|---|---|
| high | Exact counts over ≥ 100 events, or a comparison with \|z\| ≥ 3 over ≥ 100 events |
| medium | ≥ 30 events with \|z\| ≥ 2, or exact counts whose interpretation is lexical (topics) |
| low | Fewer events, or a difference that could be noise |

Tests: one-sample proportion z-test against an equal split (volume share, initiation), two-proportion
z-test (initiation shifts, replies within 5 minutes). Confidence describes the measurement only. Why a
pattern exists is never rated, because the data can't show it.

Before a run is saved, `validate_findings` checks that every referenced message exists and belongs to the
conversation. The UI loads message text from the database by ID, so quotations can't be invented.

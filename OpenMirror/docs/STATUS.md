# Status: Phase 1 (WhatsApp Intelligence Engine)

## Completed

1. **Working frontend and backend.** Next.js 15 + TypeScript + Tailwind + shadcn/ui, and FastAPI + Pydantic.
2. **WhatsApp TXT/ZIP import.** Android and iOS layouts; UTF-8/UTF-8-BOM/UTF-16; 12/24 h; `am/pm` variants
   with narrow no-break spaces; `/ . -` dates; DMY/MDY/YMD inference with a user override; multiline
   messages; system notices; media/deleted/edited/location/contact/poll/call placeholders; streaming
   two-pass parsing; a full import audit (every line is a header, a continuation, or a recorded issue).
3. **Normalised SQLite storage.** Conversations, participants, messages (with source line references),
   import jobs and issues, analysis runs, findings, evidence references; FTS5 search; cascading delete.
4. **Deterministic analytics** in Polars (see `METRICS.md`).
5. **Evidence engine.** Findings carry ID, type, supporting and counterexample message IDs, time window,
   method, confidence and its reason; integrity is validated before saving.
6. **Evidence-linked report** in eight chapters, usable without any AI, with a data-generated cover,
   interactive charts, a case-file drawer, in-context message view, a month/day browser and full-text search.
7. **Light and dark themes**, responsive down to phone width.
8. **Automated tests.** 84 pytest tests (dates, layouts, multiline, attribution round-trips, encodings,
   ZIP attacks, hand-verified analytics, evidence integrity, API, real-world quirks) and 2 Playwright
   end-to-end tests covering the full definition of done.
9. **Documentation.** README, architecture, metrics, design research, dependency inventory.

## Validated on a real export

A real 13,240-message Android export (1.2 MB, 37,026 lines, Telugu–English) was imported locally in under
a second. An independent count of header lines matched the stored message count exactly (13,240 headers,
23,786 continuation lines, nothing dropped). That run exposed issues the synthetic data had missed, and
all of them were fixed and covered by regression tests with fictional data:

* minute-resolution timestamps made median reply times read "0 s" → reply speed now compares the share
  of replies within 5 minutes and prints "under 1 min";
* romanised Telugu/Hindi particles and elongated spellings dominated the "topics" → multilingual
  stopwords and repeated-letter folding;
* `live location shared` wasn't recognised as a placeholder;
* delivery-order timestamp steps were reported as "issues" → now explained as notices;
* heavily skewed word counts → statements use median and 90th percentile instead of the mean.

The real export was never committed, copied into the repository or sent anywhere.

## Known limitations

* **Languages:** placeholders and system-notice detection target English-language exports. WhatsApp set
  to another UI language writes e.g. `<Medien ausgeschlossen>`, which is stored as text. Message text in
  any language and script is fine.
* **Topics are lexical.** Synonyms, spelling variants beyond letter elongation, and code-switching aren't
  grouped. This is the main motivation for Phase 2.
* **Time zones:** times are the exporting phone's local time. Travel or DST changes aren't corrected.
* **Media** content, reactions, replies-to-message links and poll results aren't in the export or aren't analysed.
* **Very large chats:** parsing streams, but analytics load messages into memory (about 1 M messages is
  comfortable on 16 GB of RAM). Imports run synchronously in the request.
* **Single user, single machine.** No authentication, by design for a loopback service. Don't expose it on a network.
* The sender-name heuristic flags participants with a single message for review. It doesn't auto-merge
  renamed contacts.

## Next milestones

* **Phase 2: AI intelligence (optional, local).** Ollama/llama.cpp adapter behind a provider interface;
  topic clustering with multilingual embeddings; LLM narrative that may only cite existing findings and
  message IDs (validated like today's evidence); alternative explanations generated alongside each claim.
* **Phase 3: Brandon-style chapters.** The Verdict, The Compatibility, The Complications, The Next
  Chapter; per-person deep dives in group chats; turning-point detection with change-point models.
* **Phase 4: interactive investigation.** Ask questions; answers come with evidence; save answers as new chapters.
* **Phase 5: release.** Single-command launcher, Windows installer/portable build, PDF/HTML export,
  localisation of WhatsApp placeholders, contribution guide.

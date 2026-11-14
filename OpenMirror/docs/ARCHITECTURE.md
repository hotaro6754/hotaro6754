# Architecture

```
 browser (Next.js, 127.0.0.1:3000) ──fetch──▶ FastAPI (127.0.0.1:8000) ──▶ SQLite (+FTS5)
                                                    │
   upload ─▶ ingest/sources  (TXT or ZIP; safe member selection, size/ratio limits)
          ─▶ ingest/decoding (BOM / UTF-16 / UTF-8 detection, streaming lines)
          ─▶ ingest/whatsapp (2-pass parser + import audit)
          ─▶ storage/importer (one transaction, batched inserts)
          ─▶ analytics/engine (Polars, deterministic metrics)
          ─▶ evidence/findings (findings + message references + validation)
          ─▶ report/builder (chapters, template prose)
```

Each layer only depends on the ones above it. The parser knows nothing about SQLite, and the analytics
know nothing about HTTP. AI (Phase 2) will plug in after `evidence/` and consume findings, not raw text.

## Backend modules (`backend/openmirror/`)

| Module | Responsibility |
|---|---|
| `config.py` | Environment-driven settings with private defaults |
| `ingest/sources.py` | Turns an upload into a re-readable stream. ZIPs are never extracted: names are validated (no absolute paths, `..`, NUL), the chat member is chosen deterministically, entry count, declared size and compression ratio are bounded, and the member stream refuses to decompress past its declared size |
| `ingest/decoding.py` | Detects UTF-8 / UTF-8-BOM / UTF-16 (with or without BOM) from a 64 KB prefix and streams decoded lines. Undecodable bytes are replaced and counted |
| `ingest/whatsapp.py` | Parser. Pass 1 scans headers only, to pick the layout (Android or iOS) and infer day/month order. Pass 2 yields messages. Handles 12/24 h, `am/pm/a.m./p. m.`, U+202F/U+00A0 spaces, `.`/`-`/`/` dates, 2/4-digit years, multiline messages, iOS bidi marks, system notices (including colons inside group subjects), media/deleted/edited/location/contact/poll/call placeholders |
| `storage/db.py` | Schema, pragmas (`foreign_keys`, `WAL`, `secure_delete`) |
| `storage/importer.py` | Import job lifecycle; one transaction per import |
| `analytics/engine.py` | Polars metrics (see `METRICS.md`) |
| `analytics/text.py`, `stopwords.py` | Tokeniser (any script, Indic combining marks, elongation folding), multilingual stopword lists |
| `evidence/findings.py` | Builds findings with supporting and counterexample message IDs, method and confidence. `validate_findings` checks every reference exists in the conversation before anything is saved |
| `report/builder.py` | Eight chapters of deterministic prose and figure keys |
| `service.py` | Use cases shared by API and tests: run analysis, fetch finding with messages, search/browse, delete |
| `api/app.py` | FastAPI routes, Pydantic models, body-size middleware, Host and CORS checks |
| `synthetic.py` | Deterministic fictional exports for tests and demos |

## Data model

```
conversations 1─* participants
conversations 1─* messages ──(FTS5 external content: messages_fts)
conversations 1─* import_jobs 1─* import_issues
conversations 1─* analysis_runs 1─* findings 1─* evidence_references *─1 messages
```

`messages` keeps, per message: stable integer `id`, `conversation_id`, `seq` (1-based file order),
`sender_id` (NULL for system notices), `ts_original` (exactly as written), `ts` (parsed ISO local time),
`ts_epoch`, original `text` (continuation lines joined with `\n`), `message_type`, `media_kind`,
`is_edited`, and `line_start`/`line_end` in the source file. All foreign keys cascade on delete.
Only the latest analysis run per conversation is kept.

## API

| Method | Path | Purpose |
|---|---|---|
| GET | `/api/health` | Version, limits, confirms no external services |
| POST | `/api/imports` | Multipart upload (`file`, optional `date_order` = auto/DMY/MDY/YMD, `title`). Imports and analyses |
| GET | `/api/conversations` | List |
| GET/DELETE | `/api/conversations/{id}` | Detail with participants / delete everything |
| GET | `/api/conversations/{id}/import` | Import audit and issues |
| POST | `/api/conversations/{id}/analyze` | Recompute with `{session_gap_minutes}` |
| GET | `/api/conversations/{id}/report` | Report + analytics |
| GET | `/api/conversations/{id}/findings/{fid}` | Finding with its evidence messages |
| GET | `/api/conversations/{id}/messages` | `around` + `radius` context, `q` (FTS5, every word quoted), `sender_id`, `start`/`end`, paging |

## Frontend (`frontend/src/`)

* `app/page.tsx`: upload and library. `app/c/[id]/page.tsx`: the report. `app/c/[id]/audit/page.tsx`: the colophon.
* `components/charts/`: hand-written SVG charts (cover fingerprint, monthly bars, initiation share,
  heatmap, daily calendar, bucket bars, moments axis) with one shared tooltip layer.
* `components/report/evidence.tsx`: the evidence drawer (case file), message citations, in-context view, message browser.
* `lib/api.ts`: typed client. Timestamps are parsed by hand so the browser time zone never shifts them.
* `next.config.ts`: CSP restricting all network access to the app and the local API.

## Security model

| Threat | Mitigation |
|---|---|
| Network exposure | Loopback bind by default; warning on non-loopback host |
| DNS rebinding / foreign sites | `TrustedHostMiddleware` (localhost only), CORS limited to the local UI |
| Oversized uploads | Streaming body limit (413) before parsing, plus a copy limit |
| Zip slip / zip bombs | No extraction; name validation; entry/size/ratio limits; bounded decompression |
| Code execution | Uploaded content is only decoded as text; nothing is executed or rendered as HTML (React escapes all text) |
| FTS injection | User queries become quoted FTS5 phrases |
| Data leakage | No telemetry, no third-party assets, CSP `connect-src` = self + local API, logs without content, access logs off |
| Data remanence | `secure_delete`, WAL truncation after delete, temp upload removed, failed imports leave no rows |

## Charts

Participant identity uses a fixed categorical order validated for colour-vision deficiency in light and
dark modes (blue, orange, aqua, yellow, magenta, green, violet, red; the first three are safe on any
chart form). Magnitude uses a single-hue blue ramp. Every multi-series chart has a legend, every mark
has a hover tooltip, and every figure has a text or table equivalent in its chapter.

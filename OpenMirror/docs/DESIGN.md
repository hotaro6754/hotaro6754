# OpenMirror design direction

Research date: 14 Nov 2026. References were studied for their principles only; no code, assets, copy or
branding was copied.

## What we looked at

| Reference | What it does well | What we take | What we leave |
|---|---|---|---|
| **cosmos.so** (visual bookmarking) | Warm off-white paper (`#f7f5f3`) and near-black ink (`#0d0d0d`); one heavy, tightly tracked grotesk at display sizes (72 px, weight 700, −2 % tracking); a mono face for small labels; pill-shaped black primary buttons; square-cornered content; huge **lists of names in grey with one active item in black**; content (images) carries the page, chrome stays quiet. | Paper/ink palette, heavy display grotesk, mono labels, pill CTAs, 0–2 px radius on content, the giant grey "index list" for chapters, restraint. | Its proprietary typefaces (we use OFL alternatives), the image-collage hero. |
| **What Brandon Thinks** (paid AI chat reports) | A single friendly CTA ("upload a chat"); a chat-bubble preview in the hero so you instantly know what the product reads; report promise is concrete: *a verdict, the real dynamic, when things changed, what to do next, a follow-up question*; colourful stat tiles; a persona voice. | The report arc (verdict → dynamic → change → next steps → follow-up), a chat-bubble motif, one obvious upload action, big numbers. | Cloud upload, paywall, persona that asserts motives without evidence. |
| **App-store "red flag" analyzers** (WhatsAI, Gasp, Decoded, Red Flag…) | Interest scores, response-time charts, compatibility percentages. | Nothing directly: they are the anti-pattern. | Opaque scores presented as fact, "cheater detection", sending other people's messages to third-party servers. |
| **mlomb/chat-analytics** (open source) | Local processing, single-file HTML report, tabbed statistics. | Local-first proof that rich reports need no server. | Dashboard-of-tabs layout; stats without narrative. |
| **Feltron annual reports** | Personal data as a designed publication: big numbers, small captions, consistent typographic system, design in service of content. | The "personal annual report" register: numerals as headlines, captions that define. | Print-only density. |

## Cosmos search: what the boards show

We ran eight searches on Cosmos (`/search/elements/<query>`) and read the results as mood boards:
*editorial report design, data visualization editorial, annual report layout, chat message ui design, timeline
infographic, dark editorial web design, magazine typography grotesk, personal data visualization*. Patterns that
came up again and again:

| Pattern seen | Where | How OpenMirror uses it |
|---|---|---|
| **Numbered index pages**: oversized `01 03 05 07` numerals on hairline rows, the table of contents treated as a design piece in its own right | annual report, magazine | The report opens with a full-width chapter index, large numerals and titles, hairline rules, and the current chapter in ink. |
| **Giant numerals as headlines** (`64K`, `4,678`, `75%`) with tiny mono captions | data viz editorial, annual report | Cover stats are set at display size with mono captions that define them. |
| **Mostly greyscale spreads with one fluorescent accent** | data viz editorial, dark editorial | Charts stay greyscale until something matters. Vermilion marks the finding and participant colour marks identity. Nothing else gets colour. |
| **Data used as the cover art** (radial bursts, dot fields, line stacks) | personal data visualization | Each report gets a **cover generated from its own data**: a 24-hour radial "fingerprint" of when each person writes. No two conversations share a cover. |
| **Bubble and dot timelines**: a horizontal axis with proportional circles and sparse labels | timeline infographic | The Moments chapter plots surges, drops and big sessions as proportional dots on one time axis. |
| **List-as-navigation** in dark editorial sites: big type, one row per item, no boxes | dark editorial web | The library and the chapter index are lists, not cards. |
| **Extreme scale contrast**: a 100 px headline next to 11 px captions | magazine typography | Display at 5–6 rem against 11 px mono labels. Long-form prose sits in between, in a serif at 18–19 px. |
| Chat UIs are generic and interchangeable (bubbles, gradients, avatars) | chat message ui | We **don't** look like a messenger. Evidence is shown as a *citation*: sender, original timestamp, source line, verbatim text. |

## Where OpenMirror goes beyond

1. **Receipts, not vibes.** Every claim opens an evidence drawer with the actual messages (verbatim), the
   method, a confidence level with its reason, and counterexamples. Competitors show a verdict; we show the
   verdict *and the case file*.
2. **Disagreeable by design.** Counterexamples are first-class, styled as distinctly as support. The reader is
   invited to argue with the report.
3. **Private by construction.** Runs on 127.0.0.1, no account, no upload, no AI required. The header says so
   at all times.
4. **Investigative, not horoscope.** No interest score, no attachment-style label, no "red flag" verdict on a
   person. Behavioural facts first; interpretation is reserved for Phase 2 and must cite findings.
5. **A publication, not a dashboard.** A cover, a giant chapter index, long-form chapters with figures inline,
   and a colophon (the import audit).

## System

* **Type.** Display and UI: *Instrument Sans* (OFL), weights 600–700 at display sizes, tracking −0.035 em.
  Long-form reading: *Newsreader* (OFL, optical sizes) for chapter prose only. Labels, figures and
  timestamps: *IBM Plex Mono* (OFL), uppercase, wide tracking. All self-hosted via Fontsource — no request
  to any font CDN at runtime.
* **Colour.** Light: paper `#f7f5f3`, surface `#fcfbfa`, ink `#0d0d0d`, warm greys. Dark: `#121110` /
  `#1a1918` with ink `#efece4`. One mark colour (vermilion, `#bd3c1f` light / `#ef7759` dark) for
  emphasis and focus. Participant identity uses the validated categorical order (blue, orange, aqua, …);
  magnitude uses a single-hue blue ramp. Text never takes a series colour.
* **Shape.** Content and cards: 2 px radius, hairline rules instead of boxes. Buttons: pills. No gradients,
  no glass, no drop shadows except the evidence drawer.
* **Motifs.** The giant grey chapter index (active chapter in ink). Evidence rendered as restrained message
  bubbles with sender, original timestamp and source line number — clearly a *citation*, not a WhatsApp clone.
* **Charts.** Thin marks, 2 px gaps between fills, legends for ≥ 2 series plus direct labels, hover tooltips
  on every mark, a table/text equivalent for each figure.

## Sources

- https://www.cosmos.so (visual inspection and public CSS tokens)
- Cosmos searches, e.g. https://www.cosmos.so/search/elements/annual%20report%20layout,
  https://www.cosmos.so/search/elements/data%20visualization%20editorial,
  https://www.cosmos.so/search/elements/timeline%20infographic,
  https://www.cosmos.so/search/elements/personal%20data%20visualization
  (boards of third-party work; used as mood reference only, nothing reproduced)
- https://www.whatbrandonthinks.com and https://www.whatbrandonthinks.com/about
- https://huntscreens.com/products/what-brandon-thinks, https://moge.ai/product/what-brandon-thinks
- https://apps.apple.com/us/app/id6744169392 (WhatsAI), https://mwm.ai/apps/the-gasp/6788742116 (Gasp),
  https://apps.apple.com/us/app/decoded-chat-text-analyzer/id6759509185 (Decoded),
  https://apps.apple.com/app/id6754659207 (Red Flag)
- https://github.com/mlomb/chat-analytics
- https://www.moma.org/interactives/exhibitions/2011/talktome/blog/2010/04/the-2009-feltron-annual-report/

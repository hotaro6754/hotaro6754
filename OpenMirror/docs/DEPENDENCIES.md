# Dependency and license inventory

Original OpenMirror code is MIT-licensed. All direct dependencies are permissive (MIT, BSD, Apache-2.0, ISC)
or, for fonts, SIL OFL 1.1, so none of them imposes copyleft obligations. No code was copied from
ChatLab (AGPL-3.0), whatstk (GPL-3.0) or any other project. Those were used as architectural references only.

Checked on 14 Nov 2026 from installed package metadata.

## Backend (Python)

| Package | Version | License | Use |
|---|---|---|---|
| fastapi | 0.162.7 | MIT | HTTP API |
| starlette | 1.10.0 | BSD-3-Clause | (via FastAPI) |
| uvicorn | 0.54.0 | BSD-3-Clause | ASGI server |
| pydantic | 2.14.3 | MIT | API models / validation |
| python-multipart | 0.0.33 | Apache-2.0 | Upload parsing |
| polars | 1.44.2 | MIT | Analytics |
| pytest *(dev)* | 9.2.0 | MIT | Tests |
| httpx *(dev)* | 0.28.1 | BSD-3-Clause | API test client |

SQLite and FTS5 ship with Python (public domain).

## Frontend (npm)

| Package | Version | License | Use |
|---|---|---|---|
| next | 15.5.29 | MIT | App framework |
| react / react-dom | 19.1.0 | MIT | UI |
| radix-ui | 1.8.1 | MIT | Accessible primitives (via shadcn/ui) |
| class-variance-authority | 0.7.1 | Apache-2.0 | Component variants (shadcn/ui) |
| cn | 0.5.2 | MIT | Class merging (shadcn/ui) |
| lucide-react | 1.72.0 | ISC | Icons |
| @fontsource-variable/newsreader | 5.2.10 | OFL-1.1 | Reading serif (self-hosted) |
| @fontsource-variable/instrument-sans | 5.3.0 | OFL-1.1 | Display / UI sans (self-hosted) |
| @fontsource/ibm-plex-mono | 5.3.0 | OFL-1.1 | Labels and figures (self-hosted) |
| tailwindcss, @tailwindcss/postcss *(dev)* | 4.3.5 | MIT | Styling |
| tw-animate-css *(dev)* | 1.4.0 | MIT | Animations (shadcn/ui) |
| shadcn *(dev)* | 4.23.0 | MIT | Component generator; components are vendored in `src/components/ui` |
| typescript *(dev)* | 5.9.3 | Apache-2.0 | Types |
| eslint, eslint-config-next, @eslint/eslintrc *(dev)* | 9 / 15.5.29 / 3 | MIT | Linting |
| @playwright/test *(dev)* | 1.63.0 | Apache-2.0 | End-to-end tests |
| @types/* *(dev)* | — | MIT | Type definitions |

Fonts are bundled at build time and served by the app itself. The browser makes no font-CDN requests.

## AI models (Phase 2, not yet used)

Candidates are Qwen3 (Apache-2.0) via Ollama (MIT) or llama.cpp (MIT). Model weights will be optional
downloads, never bundled, and their licenses will be listed here before integration.

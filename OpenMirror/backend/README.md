# OpenMirror backend

Local-first WhatsApp conversation intelligence: parser, SQLite storage, deterministic analytics,
evidence engine and FastAPI service. See the [project README](../README.md) for setup and privacy notes.

```bash
python -m venv .venv && .venv/bin/pip install -e ".[dev]"
.venv/bin/python -m openmirror     # API on http://127.0.0.1:8000
.venv/bin/pytest
```

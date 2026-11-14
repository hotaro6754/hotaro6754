"""Runtime configuration, read from environment variables.

Every setting has a privacy-preserving default: the server binds to the
loopback interface, nothing is sent anywhere, and data lives in a local
directory the user controls.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path


def _env_int(name: str, default: int) -> int:
    raw = os.environ.get(name)
    if raw is None or raw.strip() == "":
        return default
    try:
        return int(raw)
    except ValueError as exc:  # pragma: no cover - configuration error
        raise ValueError(f"{name} must be an integer, got {raw!r}") from exc


def _default_data_dir() -> Path:
    return Path(os.environ.get("OPENMIRROR_DATA_DIR", Path.home() / ".openmirror")).expanduser()


@dataclass(frozen=True)
class Settings:
    data_dir: Path = field(default_factory=_default_data_dir)
    host: str = field(default_factory=lambda: os.environ.get("OPENMIRROR_HOST", "127.0.0.1"))
    port: int = field(default_factory=lambda: _env_int("OPENMIRROR_PORT", 8000))
    # Maximum size of an uploaded file (TXT or ZIP), in megabytes.
    max_upload_mb: int = field(default_factory=lambda: _env_int("OPENMIRROR_MAX_UPLOAD_MB", 200))
    # Maximum uncompressed size of the chat text inside a ZIP, in megabytes.
    max_chat_text_mb: int = field(default_factory=lambda: _env_int("OPENMIRROR_MAX_CHAT_TEXT_MB", 500))
    # Maximum number of entries accepted in a ZIP archive.
    max_zip_entries: int = field(default_factory=lambda: _env_int("OPENMIRROR_MAX_ZIP_ENTRIES", 20000))
    # Browser origins allowed to call the API (the local frontend).
    cors_origins: tuple[str, ...] = field(
        default_factory=lambda: tuple(
            o.strip()
            for o in os.environ.get(
                "OPENMIRROR_CORS_ORIGINS", "http://localhost:3000,http://127.0.0.1:3000"
            ).split(",")
            if o.strip()
        )
    )

    @property
    def db_path(self) -> Path:
        return self.data_dir / "openmirror.sqlite3"

    @property
    def max_upload_bytes(self) -> int:
        return self.max_upload_mb * 1024 * 1024

    @property
    def max_chat_text_bytes(self) -> int:
        return self.max_chat_text_mb * 1024 * 1024


def load_settings() -> Settings:
    return Settings()

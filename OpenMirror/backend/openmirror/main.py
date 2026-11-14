"""Entry point: ``openmirror-server`` or ``python -m openmirror.main``."""

from __future__ import annotations

import ipaddress
import logging

import uvicorn

from openmirror.api.app import create_app
from openmirror.config import load_settings


def _is_loopback(host: str) -> bool:
    if host == "localhost":
        return True
    try:
        return ipaddress.ip_address(host).is_loopback
    except ValueError:
        return False


def run() -> None:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
    settings = load_settings()
    if not _is_loopback(settings.host):
        logging.getLogger("openmirror").warning(
            "OPENMIRROR_HOST=%s is not a loopback address: other devices on your network may reach "
            "your conversations. Use 127.0.0.1 unless you know you need this.",
            settings.host,
        )
    logging.getLogger("openmirror").info("data directory: %s", settings.data_dir)
    # Access logs are off: URLs can contain search terms from your messages.
    uvicorn.run(create_app(settings), host=settings.host, port=settings.port, access_log=False)


if __name__ == "__main__":
    run()

"""HTTP API tests using FastAPI's TestClient (fictional data only)."""

from __future__ import annotations

import io
import zipfile
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from openmirror.api.app import create_app
from openmirror.config import Settings
from openmirror.synthetic import generate_two_person, render_android


@pytest.fixture
def client(tmp_path: Path):
    settings = Settings(data_dir=tmp_path / "data", max_upload_mb=2)
    with TestClient(create_app(settings)) as c:
        yield c


def upload(client: TestClient, name: str, data: bytes, **form):
    return client.post("/api/imports", files={"file": (name, data, "application/octet-stream")}, data=form)


@pytest.fixture
def imported(client: TestClient):
    text = render_android(generate_two_person()).encode()
    r = upload(client, "WhatsApp Chat with Ravi.txt", text)
    assert r.status_code == 201, r.text
    return r.json()


def test_health_reports_no_external_services(client):
    body = client.get("/api/health").json()
    assert body["status"] == "ok" and body["external_services"] == [] and body["ai_enabled"] is False


def test_import_counts_and_participants(client, imported):
    conv = imported["conversation"]
    truth = generate_two_person()
    assert conv["title"] == "Ravi"
    assert conv["message_count"] == len(truth)
    counts = {p["display_name"]: p["message_count"] for p in conv["participants"]}
    assert counts == {"Asha": sum(m.sender == "Asha" for m in truth), "Ravi": sum(m.sender == "Ravi" for m in truth)}
    assert client.get("/api/conversations").json()[0]["id"] == conv["id"]


def test_report_finding_and_messages(client, imported):
    cid = imported["conversation"]["id"]
    rep = client.get(f"/api/conversations/{cid}/report").json()
    assert [c["number"] for c in rep["report"]["chapters"]] == [f"{i:02d}" for i in range(1, 9)]
    assert rep["report"]["ai_used"] is False
    fid = rep["report"]["chapters"][2]["finding_ids"][0]
    f = client.get(f"/api/conversations/{cid}/findings/{fid}").json()
    assert f["evidence"] and all(e["message"]["text"] is not None for e in f["evidence"])
    mid = f["evidence"][0]["message"]["id"]
    ctx = client.get(f"/api/conversations/{cid}/messages", params={"around": mid, "radius": 3}).json()
    assert ctx["focus_id"] == mid and any(m["id"] == mid for m in ctx["messages"])
    hits = client.get(f"/api/conversations/{cid}/messages", params={"q": "goa"}).json()
    assert hits["total"] > 0 and all("goa" in m["text"].lower() for m in hits["messages"])
    # FTS syntax in user input is treated as plain words, not an injection.
    weird = client.get(f"/api/conversations/{cid}/messages", params={"q": 'goa" OR "x'})
    assert weird.status_code == 200
    audit = client.get(f"/api/conversations/{cid}/import").json()
    assert audit["layout"] == "android" and audit["messages_parsed"] == imported["conversation"]["message_count"]


def test_reanalyze_with_custom_gap(client, imported):
    cid = imported["conversation"]["id"]
    before = client.get(f"/api/conversations/{cid}/report").json()["analytics"]["overview"]["sessions"]
    r = client.post(f"/api/conversations/{cid}/analyze", json={"session_gap_minutes": 24 * 60})
    assert r.status_code == 200
    after = client.get(f"/api/conversations/{cid}/report").json()["analytics"]["overview"]["sessions"]
    assert after < before


def test_delete(client, imported):
    cid = imported["conversation"]["id"]
    assert client.delete(f"/api/conversations/{cid}").status_code == 204
    assert client.get(f"/api/conversations/{cid}").status_code == 404
    assert client.get(f"/api/conversations/{cid}/report").status_code == 404
    assert client.get("/api/conversations").json() == []


def test_rejects_wrong_extension(client):
    assert upload(client, "chat.exe", b"MZ").status_code == 415


def test_rejects_non_whatsapp_text(client):
    r = upload(client, "notes.txt", b"just a shopping list\n")
    assert r.status_code == 422 and "WhatsApp" in r.json()["detail"]


def test_rejects_traversal_zip(client):
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        zf.writestr("_chat.txt", "12/01/2024, 21:04 - Asha: hi\n")
        zf.writestr("../../escape.txt", "x")
    assert upload(client, "x.zip", buf.getvalue()).status_code == 400


def test_rejects_oversized_upload(client):
    r = upload(client, "big.txt", b"x" * (3 * 1024 * 1024))
    assert r.status_code == 413


def test_rejects_foreign_host_header(client):
    r = client.get("/api/health", headers={"host": "evil.example.com"})
    assert r.status_code == 400


def test_date_order_override(client):
    text = b"01/02/2024, 10:00 - Asha: hi\n01/02/2024, 10:05 - Ravi: hey\n"
    r = upload(client, "chat.txt", text, date_order="MDY")
    assert r.status_code == 201
    assert r.json()["conversation"]["first_ts"] == "2024-01-02T10:00:00"

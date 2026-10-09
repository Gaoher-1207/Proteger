import io
import json
import sqlite3
import sys
import zipfile
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from fastapi.testclient import TestClient

from app.config import LIBRARY_PATH
from app.database import database
from app.main import app
from app.services.c_engine_service import scan_metrics
from app.services.extractors import extract_content
from detection.pii_detector import detect
from detection.risk_engine import assess, risk_level_for_score

ROOT = Path(__file__).resolve().parents[2]
client = TestClient(app)


def test_signatures_extensions_and_malformed_unknown_inputs():
    cases = [
        ("empty.txt", b"", "TEXT"), ("tiny.txt", b"x", "TEXT"),
        ("unicode name.txt", "Contact: üser@example.test and café".encode(), "TEXT"),
        ("long.log", ("x" * 200_000 + " test@example.test").encode(), "LOG"),
        ("payload.pdf", b"%PDF-broken", "PDF"), ("work.docx", b"PK\x03\x04broken", "ZIP"),
        ("data.xlsx", b"PK\x03\x04broken", "ZIP"), ("slides.pptx", b"PK\x03\x04broken", "ZIP"),
        ("unknown.mystery", b"plain readable test@example.test", "UNKNOWN"),
        ("binary.bin", b"\x00\x01 readable test@example.test \xff", "BINARY"),
    ]
    for name, data, expected in cases:
        result = extract_content(data, name)
        assert result.file_type == expected
        assert result.method and result.status
        if name in {"unicode name.txt", "long.log", "unknown.mystery", "binary.bin"}:
            assert "@example.test" in result.text


def test_all_sample_upload_categories_take_real_scan_pipeline():
    names = ["sample_data.txt", "sample_data.csv", "sample_data.json", "sample_code.py",
             "sample_document.pdf", "sample_document.docx", "sample_workbook.xlsx",
             "sample_presentation.pptx", "sample_archive.zip", "sample_image.png"]
    for name in names:
        response = client.post("/api/scan/file/stream", files={"file": (name, (ROOT / "sample_data" / name).read_bytes())})
        assert response.status_code == 200, name
        events = [json.loads(line) for line in response.text.splitlines()]
        result = events[-1]["result"]
        assert result["file_type"] and result["analysis_method"] and result["extraction_status"]
        assert result["engine_metrics"]["engine"] in {"c-ctypes", "python-fallback"}
        assert client.get(f"/api/scans/{result['id']}").json()["file_type"] == result["file_type"]
        assert client.delete(f"/api/scans/{result['id']}").status_code == 200


def test_large_text_upload_and_zero_findings_complete():
    response = client.post("/api/scan/file", files={"file": ("large empty-findings.txt", b"x" * (2 * 1024 * 1024), "text/plain")})
    assert response.status_code == 200
    result = response.json()
    assert result["total_findings"] == 0
    assert result["risk_score"] == 0 and result["risk_level"] == "LOW"
    assert result["engine_metrics"]["engine"] in {"c-ctypes", "python-fallback"}
    assert client.delete(f"/api/scans/{result['id']}").status_code == 200


def test_detection_categories_masking_and_database_privacy():
    raw = "person@example.test 9876543210 1234 5678 9012 4111111111111111 API_KEY=fake_demo_key_123456789 SECRET_TOKEN=demo_token_12345678 password:fakepass123 secret=fake_secret_987654321 192.168.1.20 https://example.test/a"
    findings = detect(raw)
    kinds = {f["type"] for f in findings}
    assert {"EMAIL", "PHONE", "AADHAAR_LIKE", "CARD_LIKE", "API_KEY", "SECRET_TOKEN", "PASSWORD_LIKE", "IP_ADDRESS", "URL"} <= kinds
    assert all(f["value"] not in raw for f in findings)
    response = client.post("/api/scan/text", json={"text": raw})
    assert response.status_code == 200
    body = response.text
    for value in ("person@example.test", "9876543210", "4111111111111111", "fake_demo_key_123456789", "fakepass123", "fake_secret_987654321"):
        assert value not in body
    db = database.connect()
    stored = " ".join(row[0] for row in db.execute("SELECT masked_value FROM findings WHERE scan_id=?", (response.json()["id"],)))
    db.close()
    assert all(value not in stored for value in ("person@example.test", "9876543210", "4111111111111111", "fake_demo_key_123456789", "fakepass123"))
    assert client.delete(f"/api/scans/{response.json()['id']}").status_code == 200
    assert not {f["type"] for f in detect("999.999.1.1 1234567890123456")} & {"IP_ADDRESS", "CARD_LIKE"}


def test_risk_threshold_boundaries_and_stable_scoring():
    for score, level in [(0, "LOW"), (24, "LOW"), (25, "MEDIUM"), (49, "MEDIUM"),
                         (50, "HIGH"), (74, "HIGH"), (75, "CRITICAL"), (100, "CRITICAL")]:
        assert risk_level_for_score(score) == level
    assert assess([]) == {"risk_score": 0, "risk_level": "LOW"}
    findings = detect("API_KEY=fake_demo_key_123456789")
    assert assess(findings) == assess(findings)


def test_zip_recursion_limits_zip_slip_and_bomb_metadata():
    nested = io.BytesIO()
    with zipfile.ZipFile(nested, "w") as zf:
        zf.writestr("nested.txt", "nested@example.test")
    outer = io.BytesIO()
    with zipfile.ZipFile(outer, "w") as zf:
        zf.writestr("../escape.txt", "must_not_scan@example.test")
        zf.writestr("nested.zip", nested.getvalue())
        zf.writestr("safe.txt", "safe@example.test")
    result = extract_content(outer.getvalue(), "archive.zip")
    assert "safe@example.test" in result.text
    assert "nested@example.test" in result.text
    assert "must_not_scan@example.test" not in result.text
    assert not (ROOT / "escape.txt").exists()
    too_many = io.BytesIO()
    with zipfile.ZipFile(too_many, "w") as zf:
        for i in range(101):
            zf.writestr(f"{i}.txt", "x")
    limited = extract_content(too_many.getvalue(), "too-many.zip")
    assert "entry count" in limited.status.lower()


def test_upload_temp_cleanup_cors_and_multipart_errors(tmp_path, monkeypatch):
    import app.routes.scan_routes as scan_routes
    monkeypatch.setattr(scan_routes, "TEMP_DIR", tmp_path)
    response = client.post("/api/scan/file", files={"file": ("name with spaces.txt", b"hello@example.test")})
    assert response.status_code == 200
    assert not list(tmp_path.glob("proteger-*.upload"))
    assert client.delete(f"/api/scans/{response.json()['id']}").status_code == 200
    assert client.post("/api/scan/file", files={"file": ("empty.txt", b"")}).status_code == 400
    assert client.post("/api/scan/file", data={"file": "not multipart"}).status_code == 422
    malformed = client.post("/api/scan/file/stream", files={"file": ("corrupt.pdf", b"%PDF-corrupt")})
    assert malformed.status_code == 200
    assert json.loads(malformed.text.splitlines()[-1])["result"]["extraction_status"].startswith("Malformed")
    for origin in ("http://localhost:5173", "http://127.0.0.1:5173"):
        preflight = client.options("/api/health", headers={"Origin": origin, "Access-Control-Request-Method": "GET"})
        assert preflight.headers.get("access-control-allow-origin") == origin
    rejected = client.options("/api/health", headers={"Origin": "https://attacker.invalid", "Access-Control-Request-Method": "GET"})
    assert "access-control-allow-origin" not in rejected.headers


def test_history_pagination_edges_and_sequential_concurrent_scans():
    scans = []
    for i in range(3):
        response = client.post("/api/scan/text", json={"text": f"person{i}@example.test"})
        assert response.status_code == 200
        scans.append(response.json())
    scan_id = scans[-1]["id"]
    assert client.get("/api/scans/99999999").status_code == 404
    assert client.get(f"/api/scans/{scan_id}/findings?offset=1").json()["findings"] == []
    assert client.get(f"/api/scans/{scan_id}/findings?offset=-1").status_code == 422
    assert client.get(f"/api/scans/{scan_id}/findings?limit=51").status_code == 422
    history = client.get("/api/scans").json()
    assert all(item["total_findings"] == 1 for item in history)

    def scan(index):
        return client.post("/api/scan/file/stream", files={"file": (f"parallel-{index}.txt", f"parallel{index}@example.test".encode())}).status_code
    with ThreadPoolExecutor(max_workers=3) as pool:
        assert list(pool.map(scan, range(3))) == [200, 200, 200]
    for scan in scans:
        assert client.delete(f"/api/scans/{scan['id']}").status_code == 200
    for item in client.get("/api/scans").json():
        if item["filename"].startswith("parallel-"):
            client.delete(f"/api/scans/{item['id']}")


def test_additive_migration_preserves_old_scan_rows(tmp_path, monkeypatch):
    legacy = tmp_path / "legacy.sqlite"
    with sqlite3.connect(legacy) as db:
        db.execute("CREATE TABLE scans (id INTEGER PRIMARY KEY, filename TEXT NOT NULL, created_at TEXT NOT NULL, risk_score INTEGER NOT NULL, risk_level TEXT NOT NULL, total_findings INTEGER NOT NULL)")
        db.execute("CREATE TABLE findings (id INTEGER PRIMARY KEY, scan_id INTEGER NOT NULL REFERENCES scans(id) ON DELETE CASCADE, type TEXT NOT NULL, severity TEXT NOT NULL, confidence REAL NOT NULL, masked_value TEXT NOT NULL, location TEXT NOT NULL)")
        db.execute("INSERT INTO scans VALUES (7,'old.txt','2024-01-01',12,'LOW',0)")
    monkeypatch.setattr(database, "DB_PATH", legacy)
    migrated = database.connect()
    row = migrated.execute("SELECT * FROM scans WHERE id=7").fetchone()
    migrated.close()
    assert row["filename"] == "old.txt"
    assert (row["file_type"], row["mime_type"], row["analysis_method"], row["extraction_status"]) == ("TEXT", "text/plain", "Text input", "Complete")


def test_database_failure_returns_safe_error(monkeypatch):
    import app.services.scan_service as scan_service
    def fail_connection():
        raise OSError("private database path should not be returned")
    monkeypatch.setattr(scan_service, "connect", fail_connection)
    response = TestClient(app, raise_server_exceptions=False).post("/api/scan/text", json={"text": "test@example.test"})
    assert response.status_code == 500
    assert "private database path" not in response.text
    assert response.json() == {"detail": "The request could not be processed."}


def test_real_c_scanner_empty_unicode_long_and_invalid_boundary():
    if not LIBRARY_PATH.is_file():
        import pytest
        pytest.skip("Build the C scanner to run native integration checks")
    assert scan_metrics("")["engine"] == "c-ctypes"
    metrics = scan_metrics(("user@example.test " + "x" * 100_000 + " 123 https://example.test/ ü") * 50)
    assert metrics["engine"] == "c-ctypes"
    assert metrics["email_markers"] == 50
    assert metrics["urls"] == 50
    _, function = __import__("app.services.c_engine_service", fromlist=["_load_scanner"])._load_scanner()
    import ctypes
    a = ctypes.c_size_t(1); b = ctypes.c_size_t(1); c = ctypes.c_size_t(1)
    assert function(None, 0, ctypes.byref(a), ctypes.byref(b), ctypes.byref(c)) == -1

import json
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[2] / "backend"))
sys.path.insert(0,str(Path(__file__).resolve().parents[2]))
from fastapi.testclient import TestClient
from app.main import app
from app.config import MAX_FILE_BYTES

def test_health_and_text_scan():
    client=TestClient(app)
    assert client.get("/api/health").status_code==200
    response=client.post("/api/scan/text",json={"text":"Email: test@example.com"})
    assert response.status_code==200
    assert response.json()["findings"][0]["value"].startswith("t")
    assert client.delete(f"/api/scans/{response.json()['id']}").status_code==200

def test_arbitrary_binary_upload_uses_safe_string_analysis_and_history():
    client=TestClient(app)
    response=client.post("/api/scan/file",files={"file":("demo.exe",b"MZ\x00FAKE DEMO test@example.com\x00")})
    assert response.status_code==200
    scan=response.json()
    assert scan["file_type"]=="BINARY"
    assert scan["analysis_method"]=="Binary/String Analysis"
    assert any(f["type"]=="EMAIL" for f in scan["findings"])
    assert all(f["value"]!="test@example.com" for f in scan["findings"])
    assert 0<=scan["risk_score"]<=100 and scan["risk_level"] in {"LOW","MEDIUM","HIGH","CRITICAL"}
    assert scan["recommendations"]
    assert scan["engine_metrics"]["engine"] in {"c-ctypes","python-fallback"}
    assert any(item["id"]==scan["id"] and item["file_type"]=="BINARY" for item in client.get("/api/scans").json())
    assert client.get(f"/api/scans/{scan['id']}").json()["extraction_status"]=="Complete"
    assert client.delete(f"/api/scans/{scan['id']}").status_code==200

def test_malformed_pdf_is_reported_without_rejecting_extension():
    response=TestClient(app).post("/api/scan/file",files={"file":("broken.pdf",b"%PDF-not-a-valid-document")})
    assert response.status_code==200
    assert response.json()["file_type"]=="PDF"
    assert response.json()["extraction_status"]=="Malformed, unreadable, or over-limit PDF; no text was extracted."
    TestClient(app).delete(f"/api/scans/{response.json()['id']}")

def test_streamed_pipeline_reports_stages_and_sample_pdf_extracts():
    client=TestClient(app)
    path=Path(__file__).resolve().parents[2]/"sample_data"/"sample_document.pdf"
    response=client.post("/api/scan/file/stream",files={"file":(path.name,path.read_bytes(),"application/pdf")})
    assert response.status_code==200
    events=[json.loads(line) for line in response.text.splitlines() if line]
    assert [event["stage"] for event in events]==["Detecting type","Extracting","Scanning","Analyzing","Complete"]
    scan=events[-1]["result"]
    assert scan["file_type"]=="PDF" and scan["analysis_method"]=="PDF text extraction"
    assert any(item["type"]=="EMAIL" for item in scan["findings"])
    assert scan["engine_metrics"]["engine"] in {"c-ctypes","python-fallback"}
    assert any(item["id"]==scan["id"] and item["file_type"]=="PDF" for item in client.get("/api/scans").json())
    client.delete(f"/api/scans/{scan['id']}")

def test_streamed_txt_upload_and_bounded_findings_pages():
    client=TestClient(app)
    content=" ".join(f"person{index}@example.test" for index in range(120)).encode()
    response=client.post("/api/scan/file/stream",files={"file":("many.txt",content,"text/plain")})
    assert response.status_code==200
    events=[json.loads(line) for line in response.text.splitlines() if line]
    scan=events[-1]["result"]
    assert scan["file_type"]=="TEXT" and scan["total_findings"]==120
    assert len(scan["findings"])==50
    page=client.get(f"/api/scans/{scan['id']}/findings?offset=50&limit=50").json()
    assert len(page["findings"])==50 and page["total_findings"]==120
    final=client.get(f"/api/scans/{scan['id']}/findings?offset=100&limit=50").json()
    assert len(final["findings"])==20
    client.delete(f"/api/scans/{scan['id']}")

def test_upload_body_limit_rejects_oversized_multipart():
    response=TestClient(app).post("/api/scan/file/stream",files={"file":("large.bin",b"x"*(MAX_FILE_BYTES+70*1024))})
    assert response.status_code==413

def test_large_pdf_result_is_bounded_for_frontend():
    client=TestClient(app)
    path=Path(__file__).resolve().parents[2]/"sample_data"/"sample_stress_findings.pdf"
    response=client.post("/api/scan/file/stream",files={"file":(path.name,path.read_bytes(),"application/pdf")})
    assert response.status_code==200
    events=[json.loads(line) for line in response.text.splitlines() if line]
    scan=events[-1]["result"]
    assert scan["total_findings"]==2500
    assert len(scan["findings"])==50
    assert scan["findings"][0]["value"]!="person0@example.test"
    assert client.delete(f"/api/scans/{scan['id']}").status_code==200

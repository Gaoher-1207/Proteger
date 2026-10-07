from datetime import datetime, timezone
from app.database.database import connect
from app.services.c_engine_service import scan_metrics
from detection.pii_detector import detect
from detection.risk_engine import assess
from app.config import RESULT_FINDINGS_PAGE_SIZE

def create_scan(text, filename="Pasted text", metadata=None, precomputed=None):
    metadata = metadata or {"file_type": "TEXT", "mime_type": "text/plain", "analysis_method": "Pasted text analysis", "extraction_status": "Complete"}
    precomputed = precomputed or {}
    metrics = precomputed.get("engine_metrics") or scan_metrics(text)
    findings = precomputed.get("findings") if precomputed.get("findings") is not None else detect(text)
    risk = precomputed.get("risk") or assess(findings)
    db = connect()
    created_at = datetime.now(timezone.utc).isoformat()
    cur = db.execute("INSERT INTO scans(filename,created_at,risk_score,risk_level,total_findings,file_type,mime_type,analysis_method,extraction_status) VALUES(?,?,?,?,?,?,?,?,?)", (filename, created_at, risk["risk_score"], risk["risk_level"], len(findings), metadata["file_type"], metadata["mime_type"], metadata["analysis_method"], metadata["extraction_status"]))
    scan_id = cur.lastrowid
    db.executemany("INSERT INTO findings(scan_id,type,severity,confidence,masked_value,location) VALUES(?,?,?,?,?,?)", [(scan_id,f["type"],f["severity"],f["confidence"],f["value"],f["location"]) for f in findings])
    db.commit(); db.close()
    return {"id": scan_id, "filename": filename, "created_at": created_at, **metadata, **risk, "total_findings": len(findings), "finding_categories": sorted({f["type"] for f in findings}), "findings": findings[:RESULT_FINDINGS_PAGE_SIZE], "findings_page_size": RESULT_FINDINGS_PAGE_SIZE, "engine_metrics": metrics, "recommendations": recommendations(findings)}

def recommendations(findings):
    if not findings: return ["No matching patterns were found. Review manually before sharing; pattern-based scanning can miss sensitive data."]
    rec = []
    kinds = {f["type"] for f in findings}
    if kinds & {"API_KEY", "SECRET_TOKEN", "PASSWORD_LIKE"}: rec.append("Revoke exposed credentials and replace them with secrets stored outside the document.")
    if kinds & {"AADHAAR_LIKE", "CARD_LIKE", "PHONE", "EMAIL"}: rec.append("Remove or redact personal identifiers before sharing this file.")
    if "IP_ADDRESS" in kinds: rec.append("Check whether the listed network addresses reveal internal infrastructure.")
    rec.append("Confirm findings in context; this rule-based result is not a security certification.")
    return rec

def get_scan(scan_id, offset=0, limit=RESULT_FINDINGS_PAGE_SIZE):
    db=connect(); row=db.execute("SELECT * FROM scans WHERE id=?",(scan_id,)).fetchone()
    if not row: db.close(); return None
    data=dict(row); data["findings"]=[dict(x) for x in db.execute("SELECT type,severity,confidence,masked_value AS value,location FROM findings WHERE scan_id=? ORDER BY id LIMIT ? OFFSET ?",(scan_id,limit,offset))]
    kinds=[x[0] for x in db.execute("SELECT DISTINCT type FROM findings WHERE scan_id=?",(scan_id,))]; db.close()
    from app.services.file_analysis import recommendations as file_recommendations
    data["findings_page_size"]=limit; data["finding_categories"]=sorted(kinds)
    data["recommendations"]=file_recommendations([{"type":kind} for kind in kinds],data["extraction_status"]); return data

def get_findings_page(scan_id, offset=0, limit=RESULT_FINDINGS_PAGE_SIZE):
    db=connect()
    exists=db.execute("SELECT 1 FROM scans WHERE id=?",(scan_id,)).fetchone()
    if not exists: db.close(); return None
    rows=[dict(x) for x in db.execute("SELECT type,severity,confidence,masked_value AS value,location FROM findings WHERE scan_id=? ORDER BY id LIMIT ? OFFSET ?",(scan_id,limit,offset))]
    total=db.execute("SELECT total_findings FROM scans WHERE id=?",(scan_id,)).fetchone()[0]
    db.close()
    return {"scan_id":scan_id,"offset":offset,"limit":limit,"total_findings":total,"findings":rows}

def list_scans():
    db=connect(); rows=[dict(x) for x in db.execute("SELECT * FROM scans ORDER BY id DESC")]; db.close(); return rows

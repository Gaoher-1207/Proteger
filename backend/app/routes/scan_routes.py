import tempfile
from pathlib import Path
import asyncio
import json
from fastapi import APIRouter, HTTPException, UploadFile, File, Query
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from app.config import MAX_FILE_BYTES, TEMP_DIR
from app.services.scan_service import create_scan, get_scan, get_findings_page
from app.database.database import connect
from app.services.extractors import extract_content
from app.services.file_type_detector import safe_filename
from app.services.file_analysis import recommendations as file_recommendations
from app.services.file_type_detector import detect_file_type
from app.services.c_engine_service import scan_metrics
from detection.pii_detector import detect
from detection.risk_engine import assess
from app.config import RESULT_FINDINGS_PAGE_SIZE
router=APIRouter()
class TextRequest(BaseModel):
    text: str = Field(min_length=1, max_length=2_000_000)
@router.post("/scan/text")
def scan_text(body: TextRequest):
    if not body.text.strip(): raise HTTPException(400,"Text cannot be empty")
    return create_scan(body.text)
async def _read_upload(file):
    name=safe_filename(file.filename)
    temp_path=None
    try:
        TEMP_DIR.mkdir(parents=True, exist_ok=True)
        with tempfile.NamedTemporaryFile(prefix="proteger-", suffix=".upload", dir=TEMP_DIR, delete=False) as tmp:
            temp_path=tmp.name
            size=0
            while True:
                chunk=await file.read(64*1024)
                if not chunk: break
                size+=len(chunk)
                if size>MAX_FILE_BYTES: raise HTTPException(413,f"File exceeds the configured {MAX_FILE_BYTES // (1024*1024)} MB limit")
                tmp.write(chunk)
        if size==0: raise HTTPException(400,"File is empty")
        raw=await asyncio.to_thread(Path(temp_path).read_bytes)
        return name,raw,file.content_type or ""
    finally:
        await file.close()
        if temp_path:
            try: Path(temp_path).unlink(missing_ok=True)
            except OSError: pass

@router.post("/scan/file")
async def scan_file(file: UploadFile = File(...)):
    try:
        name,raw,supplied_mime=await _read_upload(file)
        extracted=await asyncio.to_thread(extract_content,raw,name,supplied_mime)
        metadata={"file_type":extracted.file_type,"mime_type":extracted.mime_type,"analysis_method":extracted.method,"extraction_status":extracted.status}
        result=await asyncio.to_thread(create_scan,extracted.text,name,metadata)
        result["recommendations"]=file_recommendations(result["findings"],extracted.status)
        return result
    except HTTPException: raise
    except Exception: raise HTTPException(422,"The file could not be safely analyzed. Check that it is well-formed and try again.")

@router.post("/scan/file/stream")
async def scan_file_stream(file: UploadFile = File(...)):
    try: name,raw,supplied_mime=await _read_upload(file)
    except HTTPException: raise
    except Exception: raise HTTPException(422,"The file upload could not be safely processed.")
    async def events():
        try:
            kind,mime=detect_file_type(raw,name,supplied_mime)
            yield json.dumps({"stage":"Detecting type","file_type":kind,"mime_type":mime})+"\n"
            await asyncio.sleep(0)
            yield json.dumps({"stage":"Extracting"})+"\n"
            extracted=await asyncio.to_thread(extract_content,raw,name,supplied_mime)
            yield json.dumps({"stage":"Scanning"})+"\n"
            metrics=await asyncio.to_thread(scan_metrics,extracted.text)
            yield json.dumps({"stage":"Analyzing"})+"\n"
            findings=await asyncio.to_thread(detect,extracted.text)
            risk=await asyncio.to_thread(assess,findings)
            metadata={"file_type":extracted.file_type,"mime_type":extracted.mime_type,"analysis_method":extracted.method,"extraction_status":extracted.status}
            result=await asyncio.to_thread(create_scan,extracted.text,name,metadata,{"engine_metrics":metrics,"findings":findings,"risk":risk})
            result["recommendations"]=file_recommendations(findings,extracted.status)
            yield json.dumps({"stage":"Complete","result":result})+"\n"
        except Exception:
            yield json.dumps({"error":"The file could not be safely analyzed. Check that it is well-formed and try again."})+"\n"
    return StreamingResponse(events(),media_type="application/x-ndjson",headers={"Cache-Control":"no-store","X-Content-Type-Options":"nosniff"})
@router.get("/scans/{scan_id}")
def scan_detail(scan_id:int):
    data=get_scan(scan_id)
    if not data: raise HTTPException(404,"Scan not found")
    return data
@router.get("/scans/{scan_id}/findings")
def scan_findings(scan_id:int, offset:int=Query(0,ge=0), limit:int=Query(RESULT_FINDINGS_PAGE_SIZE,ge=1,le=RESULT_FINDINGS_PAGE_SIZE)):
    data=get_findings_page(scan_id,offset,limit)
    if not data: raise HTTPException(404,"Scan not found")
    return data
@router.delete("/scans/{scan_id}")
def delete_scan(scan_id:int):
    db=connect(); cur=db.execute("DELETE FROM scans WHERE id=?",(scan_id,)); db.commit(); db.close()
    if not cur.rowcount: raise HTTPException(404,"Scan not found")
    return {"deleted":True}

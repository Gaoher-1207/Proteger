import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from app.middleware import UploadSizeLimitMiddleware, _UploadTooLarge
from app.routes import health_routes, scan_routes, history_routes
app=FastAPI(title="Proteger API", version="1.0.0")
app.add_middleware(UploadSizeLimitMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_methods=["GET", "POST", "DELETE", "OPTIONS"],
    allow_headers=["Accept", "Content-Type"],
)
app.include_router(health_routes.router,prefix="/api")
app.include_router(scan_routes.router,prefix="/api")
app.include_router(history_routes.router,prefix="/api")
@app.exception_handler(Exception)
async def safe_error(request, exc):
    return JSONResponse(status_code=500,content={"detail":"The request could not be processed."})
@app.exception_handler(_UploadTooLarge)
async def oversized_upload(request, exc):
    from app.config import MAX_FILE_BYTES
    return JSONResponse(status_code=413,content={"detail":f"Upload request exceeds the configured {MAX_FILE_BYTES // (1024*1024)} MB file limit."})

from starlette.responses import JSONResponse
from app.config import MAX_FILE_BYTES

class UploadSizeLimitMiddleware:
    """Caps multipart request bodies before Starlette spools uploaded parts."""
    def __init__(self, app):
        self.app=app
        # Multipart boundaries and headers require a small bounded amount beyond the file bytes.
        self.max_body_bytes=MAX_FILE_BYTES + 64*1024

    async def __call__(self, scope, receive, send):
        if scope["type"]!="http" or scope.get("method")!="POST" or scope.get("path") not in {"/api/scan/file", "/api/scan/file/stream"}:
            await self.app(scope,receive,send); return
        headers={key.lower():value for key,value in scope.get("headers",[])}
        length=headers.get(b"content-length")
        if length:
            try:
                if int(length)>self.max_body_bytes:
                    await JSONResponse(status_code=413,content={"detail":f"Upload request exceeds the configured {MAX_FILE_BYTES // (1024*1024)} MB file limit."})(scope,receive,send)
                    return
            except ValueError: pass
        total=0
        async def limited_receive():
            nonlocal total
            message=await receive()
            if message.get("type")=="http.request":
                total+=len(message.get("body",b""))
                if total>self.max_body_bytes:
                    raise _UploadTooLarge()
            return message
        try:
            await self.app(scope,limited_receive,send)
        except _UploadTooLarge:
            await JSONResponse(status_code=413,content={"detail":f"Upload request exceeds the configured {MAX_FILE_BYTES // (1024*1024)} MB file limit."})(scope,receive,send)

class _UploadTooLarge(Exception): pass

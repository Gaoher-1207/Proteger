"""Signature-first file classification. Extensions and client MIME are hints only."""
from pathlib import PurePath
import mimetypes
import re

TEXT_EXTENSIONS = {
    ".txt": ("TEXT", "text/plain"), ".csv": ("CSV", "text/csv"), ".json": ("JSON", "application/json"),
    ".xml": ("XML", "application/xml"), ".html": ("HTML", "text/html"), ".htm": ("HTML", "text/html"),
    ".log": ("LOG", "text/plain"), ".md": ("MARKDOWN", "text/markdown"), ".yaml": ("YAML", "application/yaml"), ".yml": ("YAML", "application/yaml"),
    ".c": ("SOURCE_CODE", "text/x-c"), ".h": ("SOURCE_CODE", "text/x-c"), ".cc": ("SOURCE_CODE", "text/x-c++"), ".cpp": ("SOURCE_CODE", "text/x-c++"),
    ".hpp": ("SOURCE_CODE", "text/x-c++"), ".java": ("SOURCE_CODE", "text/x-java"), ".py": ("SOURCE_CODE", "text/x-python"),
    ".js": ("SOURCE_CODE", "text/javascript"), ".jsx": ("SOURCE_CODE", "text/javascript"), ".ts": ("SOURCE_CODE", "text/typescript"), ".tsx": ("SOURCE_CODE", "text/typescript"),
    ".go": ("SOURCE_CODE", "text/x-go"), ".rs": ("SOURCE_CODE", "text/x-rust"), ".cs": ("SOURCE_CODE", "text/x-csharp"), ".php": ("SOURCE_CODE", "text/x-php"),
    ".sh": ("SOURCE_CODE", "text/x-shellscript"), ".sql": ("SOURCE_CODE", "application/sql"), ".rb": ("SOURCE_CODE", "text/x-ruby"),
}
BINARY_EXTENSIONS={".exe", ".dll", ".bin", ".so", ".dylib", ".sys", ".dat", ".class"}

def safe_filename(filename):
    name = str(filename or "upload").replace("\\", "/").split("/")[-1]
    name = re.sub(r"[^A-Za-z0-9._ -]", "_", name).strip(" .")
    return (name or "upload")[:180]

def detect_file_type(data: bytes, filename: str, supplied_mime: str = ""):
    ext = PurePath(safe_filename(filename)).suffix.lower()
    # Magic bytes take precedence over a misleading suffix or client MIME.
    if data.startswith(b"%PDF-"): return "PDF", "application/pdf"
    if data.startswith(b"\x89PNG\r\n\x1a\n"): return "IMAGE_PNG", "image/png"
    if data.startswith(b"\xff\xd8\xff"): return "IMAGE_JPEG", "image/jpeg"
    if data.startswith(b"MZ"): return "BINARY", "application/vnd.microsoft.portable-executable"
    if data.startswith(b"\x7fELF"): return "BINARY", "application/x-elf"
    if data.startswith((b"PK\x03\x04", b"PK\x05\x06", b"PK\x07\x08")):
        kind = _zip_kind(data)
        mime = {"DOCX":"application/vnd.openxmlformats-officedocument.wordprocessingml.document", "XLSX":"application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", "PPTX":"application/vnd.openxmlformats-officedocument.presentationml.presentation", "ZIP":"application/zip"}[kind]
        return kind, mime
    if data.startswith(bytes.fromhex("D0CF11E0A1B11AE1")): return "BINARY", "application/x-ole-storage"
    if ext in BINARY_EXTENSIONS: return "BINARY", mimetypes.guess_type(safe_filename(filename))[0] or "application/octet-stream"
    if b"\x00" in data: return "BINARY", "application/octet-stream"
    if ext in TEXT_EXTENSIONS:
        kind, mime = TEXT_EXTENSIONS[ext]
        return kind, mime
    guessed, _ = mimetypes.guess_type(safe_filename(filename))
    if guessed and guessed.startswith("image/"): return "IMAGE_UNSUPPORTED", guessed
    # A client-supplied MIME is reported only for unknown bytes and never enables execution.
    if supplied_mime and supplied_mime not in {"application/octet-stream", "binary/octet-stream"}:
        return "UNKNOWN", supplied_mime.split(";")[0][:120]
    return "UNKNOWN", guessed or "application/octet-stream"

def _zip_kind(data):
    try:
        import io, zipfile
        with zipfile.ZipFile(io.BytesIO(data)) as zf:
            names = set(zf.namelist())
            if "[Content_Types].xml" in names:
                if "word/document.xml" in names: return "DOCX"
                if "xl/workbook.xml" in names: return "XLSX"
                if any(n.startswith("ppt/slides/slide") for n in names): return "PPTX"
    except (OSError, zipfile.BadZipFile, RuntimeError):
        pass
    return "ZIP"

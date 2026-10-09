import os
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
def _path_setting(name, default):
    value = Path(os.environ.get(name, str(default))).expanduser()
    return value if value.is_absolute() else ROOT / value

DB_PATH = _path_setting("PROTEGER_DB_PATH", ROOT / "database" / "proteger.db")
_default_library = {"win32": "scanner.dll", "darwin": "libscanner.dylib"}.get(sys.platform, "libscanner.so")
LIBRARY_PATH = _path_setting("PROTEGER_C_LIBRARY", ROOT / "core_engine" / "build" / _default_library)
MAX_FILE_BYTES = int(os.environ.get("PROTEGER_MAX_FILE_BYTES", str(10 * 1024 * 1024)))
MAX_ARCHIVE_BYTES = int(os.environ.get("PROTEGER_MAX_ARCHIVE_BYTES", str(20 * 1024 * 1024)))
MAX_ARCHIVE_MEMBER_BYTES = int(os.environ.get("PROTEGER_MAX_ARCHIVE_MEMBER_BYTES", str(5 * 1024 * 1024)))
MAX_ARCHIVE_ENTRIES = int(os.environ.get("PROTEGER_MAX_ARCHIVE_ENTRIES", "100"))
MAX_ARCHIVE_DEPTH = int(os.environ.get("PROTEGER_MAX_ARCHIVE_DEPTH", "2"))
RESULT_FINDINGS_PAGE_SIZE = int(os.environ.get("PROTEGER_FINDINGS_PAGE_SIZE", "50"))
TEMP_DIR = _path_setting("PROTEGER_TEMP_DIR", Path(os.environ.get("TMPDIR") or os.environ.get("TEMP") or os.environ.get("TMP") or "/tmp"))

def csv_env(name, default):
    return [item.strip() for item in os.environ.get(name, default).split(",") if item.strip()]

DEV_CORS_ORIGINS = ["http://localhost:5173", "http://127.0.0.1:5173"]
CORS_ORIGINS = csv_env("PROTEGER_CORS_ORIGINS", ",".join(DEV_CORS_ORIGINS))

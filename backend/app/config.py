import os
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DB_PATH = ROOT / "database" / "proteger.db"
LIBRARY_PATH = ROOT / "core_engine" / "build" / "scanner.dll"
MAX_FILE_BYTES = int(os.environ.get("PROTEGER_MAX_FILE_BYTES", str(10 * 1024 * 1024)))
MAX_ARCHIVE_BYTES = 20 * 1024 * 1024
MAX_ARCHIVE_MEMBER_BYTES = 5 * 1024 * 1024
MAX_ARCHIVE_ENTRIES = 100
MAX_ARCHIVE_DEPTH = 2
RESULT_FINDINGS_PAGE_SIZE = 50

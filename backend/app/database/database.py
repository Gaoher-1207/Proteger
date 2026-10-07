import sqlite3
from app.config import DB_PATH

def connect():
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    db = sqlite3.connect(DB_PATH)
    db.row_factory = sqlite3.Row
    db.execute("PRAGMA foreign_keys=ON")
    db.executescript("""
    CREATE TABLE IF NOT EXISTS scans (id INTEGER PRIMARY KEY, filename TEXT NOT NULL, created_at TEXT NOT NULL, risk_score INTEGER NOT NULL, risk_level TEXT NOT NULL, total_findings INTEGER NOT NULL, file_type TEXT NOT NULL DEFAULT 'TEXT', mime_type TEXT NOT NULL DEFAULT 'text/plain', analysis_method TEXT NOT NULL DEFAULT 'Text input', extraction_status TEXT NOT NULL DEFAULT 'Complete');
    CREATE TABLE IF NOT EXISTS findings (id INTEGER PRIMARY KEY, scan_id INTEGER NOT NULL REFERENCES scans(id) ON DELETE CASCADE, type TEXT NOT NULL, severity TEXT NOT NULL, confidence REAL NOT NULL, masked_value TEXT NOT NULL, location TEXT NOT NULL);
    """)
    columns = {row[1] for row in db.execute("PRAGMA table_info(scans)")}
    for name, definition in (("file_type", "TEXT NOT NULL DEFAULT 'TEXT'"), ("mime_type", "TEXT NOT NULL DEFAULT 'text/plain'"), ("analysis_method", "TEXT NOT NULL DEFAULT 'Text input'"), ("extraction_status", "TEXT NOT NULL DEFAULT 'Complete'")):
        if name not in columns:
            db.execute(f"ALTER TABLE scans ADD COLUMN {name} {definition}")
    return db

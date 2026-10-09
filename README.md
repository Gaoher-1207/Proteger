# Proteger — Privacy & Data Exposure Analyzer

Proteger is a local-first final-year CSE project MVP for **broad file-type analysis with format-specific extraction and safe fallback handling**. It scans pasted text, common text/source formats, PDF and Office documents, ZIP archives, images (with explicit OCR-unavailable status), and printable strings from binaries for common personal data and secrets. It provides masked findings, deterministic project-defined risk scoring, recommendations, dashboard totals and local scan history. It makes no external AI/API calls and never executes uploaded files.

## Architecture and stack

React, JavaScript, Vite and CSS provide the dashboard. FastAPI/Python validate uploads, identify file types using signatures and hints, coordinate modular extractors, the existing C scanner and Python detection/risk modules. Extracted text passes through the C `ctypes` scanner, then Python regex rules classify and mask values. SQLite stores scan metadata and masked findings.

## Start locally

Requirements: Python 3.10+, Node.js 18+, npm. Backend requirements include pypdf, python-docx, openpyxl and python-pptx for PDF and Office extraction. GCC/MinGW builds the C library; without it, the documented Python fallback remains available.

1. Compile from `core_engine/` with `make`. The Makefile emits `build/scanner.dll` on Windows, `build/libscanner.so` on Linux, or `build/libscanner.dylib` on macOS. On Windows MinGW: `gcc -shared -O2 -Wall -Wextra -std=c11 -o build/scanner.dll src/scanner.c -Iinclude`.
2. In `backend/`: `python -m pip install -r requirements.txt`, then `python -m uvicorn app.main:app --reload`.
3. In `frontend/`: `npm install`, then `npm run dev`; open the URL shown (normally `http://localhost:5173`).
4. Tests from the root: install `pytest` and `httpx`, then run `python -m pytest tests`.

## API

`GET /api/health`, `POST /api/scan/text` with `{"text":"..."}`, `POST /api/scan/file` multipart `file`, and `POST /api/scan/file/stream` for live pipeline stages. History uses `GET /api/scans`, `GET /api/scans/{id}`, `DELETE /api/scans/{id}`; `GET /api/dashboard` provides aggregates. Interactive API docs are at `/docs`.

## Project map

`frontend/src` contains the React UI. `backend/app/routes` contains HTTP endpoints. `backend/app/services/file_type_detector.py` performs signature-first classification; `extractors.py` safely extracts content; `file_analysis.py` builds extraction-aware recommendations; other services coordinate scans and C. `detection` holds rules and risk scoring; `core_engine` contains the integrated C API; `database` documents SQLite; `reports` builds summaries; `sample_data` and `generate_samples.py` provide fake fixtures; `tests` contains detector, extractor and API checks; `docs` explains design.

## Security and limitations

Uploads default to a configurable 10 MB limit (`PROTEGER_MAX_FILE_BYTES`). A random temporary filename is used while each upload is streamed to `PROTEGER_TEMP_DIR`, size-checked, and removed. ZIP/Office members are inspected without extracting paths to disk. Archive limits are 100 entries, 5 MB per member, 20 MB total uncompressed content and two nested archive levels. Images are detected, but OCR is not currently available. Malformed and unsupported content receives an explicit extraction status and safe printable-string fallback where possible. Raw uploads are not logged or sent externally; SQLite persists masked findings and file metadata. SQLite is not encrypted. Regex rules can miss data or produce false positives. The risk score is project-defined and not scientifically validated or a security certification.

## Deployment preparation (not deployed)

Build the C library for the backend operating system and architecture, install `backend/requirements.txt`, and run `python -m uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}` from `backend/` on Linux (in PowerShell use `--port $env:PORT`, defaulting to 8000). Provide `PROTEGER_C_LIBRARY` for a non-default library location and `PROTEGER_DB_PATH` pointing to persistent storage. Set `PROTEGER_CORS_ORIGINS` to the exact HTTPS frontend origin(s), comma-separated; do not use `*`. Configure the frontend build's `VITE_API_BASE_URL` to the API origin, or leave it empty and route `/api` to FastAPI through a same-origin reverse proxy. `frontend/.env.example` and `backend/.env.example` list supported settings. Vite embeds `VITE_API_BASE_URL` at build time, so configure it before `npm run build`. The backend still serves `/api/health` for platform health checks. The temporary directory must be writable, private to the service, and have enough space for an upload up to the configured limit. Use a persistent volume for SQLite and back it up; a single SQLite file is intended for a single backend instance, not multi-replica shared writes.

**Access control:** the API currently has no built-in authentication or authorization. CORS only controls browser origins and does not protect the API from direct clients. Keep deployment private or put the frontend and API behind an authenticated access gateway before exposing them publicly. Do not store real sensitive files in a public unauthenticated deployment.

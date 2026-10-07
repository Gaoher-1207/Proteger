# Backend

FastAPI serves local scan, streaming file-analysis, history, dashboard, health and delete endpoints. Run `python -m pip install -r requirements.txt`, then `python -m uvicorn app.main:app --reload` from this folder. The SQLite database is created in the project `database/` folder and existing tables receive additive metadata columns automatically. Set `PROTEGER_MAX_FILE_BYTES` to configure the upload limit; archive limits live in `app/config.py`.

Uploads use a random temporary filename while streamed and size-checked, then are deleted in a `finally` block. Extractors never execute content. ZIP and Office packages are read without extracting paths to disk. PDF uses pypdf; DOCX/XLSX/PPTX use python-docx/openpyxl/python-pptx when installed with standard-library OOXML fallback. OCR is not yet available for images.

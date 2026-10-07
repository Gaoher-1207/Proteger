# Architecture

React calls FastAPI over localhost. The scan service calls the C byte-scanning library through ctypes, then Python detection and risk modules. It inserts scan metadata and masked findings into SQLite, and returns JSON for the UI. No external service is involved.

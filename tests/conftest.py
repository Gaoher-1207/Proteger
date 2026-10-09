import shutil
import sys
import tempfile
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))


def pytest_configure(config):
    """Give each run a fresh workspace-local base, even if an older one is locked."""
    temp_root = Path(__file__).resolve().parents[1] / ".pytest-tmp"
    temp_root.mkdir(parents=True, exist_ok=True)
    for old_run in temp_root.glob("run-*"):
        shutil.rmtree(old_run, ignore_errors=True)
    config.option.basetemp = tempfile.mkdtemp(prefix="run-", dir=temp_root)


@pytest.fixture(autouse=True)
def isolated_sqlite_database(tmp_path, monkeypatch):
    """Keep API tests from reading or mutating the user's persistent scan history."""
    from app.database import database
    monkeypatch.setattr(database, "DB_PATH", tmp_path / "test-proteger.db")

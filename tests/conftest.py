import pytest
import tempfile
from pathlib import Path

from core.database import Database
from core.config import Config


@pytest.fixture
def temp_db_dir(monkeypatch):
    """Create a temp directory for test database files."""
    with tempfile.TemporaryDirectory() as tmpdir:
        monkeypatch.setenv("DATA_DIR", tmpdir)
        yield Path(tmpdir)


@pytest.fixture
def db(temp_db_dir):
    """Create a Database instance backed by a temp file."""
    db = Database()
    conn = db._get_conn()
    try:
        conn.execute("DELETE FROM seen_papers")
        conn.execute("DELETE FROM digest_runs")
        conn.commit()
    finally:
        conn.close()
    return db

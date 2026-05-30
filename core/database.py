import sqlite3
import threading
import os
from datetime import datetime, timezone
from typing import Optional

from core.config import Config
from core.models import DigestRun


class Database:
    def __init__(self) -> None:
        data_dir = Config().DATA_DIR
        os.makedirs(data_dir, exist_ok=True)
        self.db_path = os.path.join(data_dir, "digest.db")
        self._conn = sqlite3.connect(self.db_path, check_same_thread=False)
        self._conn.row_factory = sqlite3.Row
        self._lock: threading.Lock = threading.Lock()
        self._init_db()

    def close(self) -> None:
        with self._lock:
            if self._conn:
                self._conn.close()
                self._conn = None

    def _init_db(self) -> None:
        with self._lock:
            conn = self._get_conn()
            conn.executescript("""
                CREATE TABLE IF NOT EXISTS seen_papers (
                    id TEXT PRIMARY KEY,
                    first_seen_at TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS digest_runs (
                    run_id TEXT PRIMARY KEY,
                    started_at TEXT NOT NULL,
                    finished_at TEXT,
                    paper_count INTEGER DEFAULT 0,
                    top_n INTEGER DEFAULT 10,
                    topics TEXT DEFAULT '',
                    categories TEXT DEFAULT '',
                    json_path TEXT DEFAULT '',
                    md_path TEXT DEFAULT '',
                    status TEXT DEFAULT 'running'
                );
            """)
            conn.commit()

    def _get_conn(self) -> sqlite3.Connection:
        if self._conn is None:
            raise RuntimeError("Database is closed")
        return self._conn

    def is_seen(self, paper_id: str) -> bool:
        with self._lock:
            conn = self._get_conn()
            row = conn.execute(
                "SELECT 1 FROM seen_papers WHERE id = ?", (paper_id,)
            ).fetchone()
            return row is not None

    def mark_seen(self, ids: list[str]) -> None:
        with self._lock:
            conn = self._get_conn()
            now = datetime.now(timezone.utc).isoformat()
            conn.executemany(
                "INSERT OR IGNORE INTO seen_papers (id, first_seen_at) VALUES (?, ?)",
                [(pid, now) for pid in ids],
            )
            conn.commit()

    def save_run(self, run: DigestRun) -> None:
        with self._lock:
            conn = self._get_conn()
            conn.execute(
                """
                INSERT INTO digest_runs
                    (run_id, started_at, finished_at, paper_count, top_n,
                     topics, categories, json_path, md_path, status)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    run.run_id,
                    run.started_at.isoformat(),
                    run.finished_at.isoformat() if run.finished_at else None,
                    run.paper_count,
                    run.top_n,
                    ",".join(run.topics),
                    ",".join(run.categories),
                    run.json_path,
                    run.md_path,
                    run.status,
                ),
            )
            conn.commit()

    def update_run(self, run: DigestRun) -> None:
        with self._lock:
            conn = self._get_conn()
            conn.execute(
                """
                UPDATE digest_runs SET
                    finished_at = ?,
                    paper_count = ?,
                    top_n = ?,
                    topics = ?,
                    categories = ?,
                    json_path = ?,
                    md_path = ?,
                    status = ?
                WHERE run_id = ?
                """,
                (
                    run.finished_at.isoformat() if run.finished_at else None,
                    run.paper_count,
                    run.top_n,
                    ",".join(run.topics),
                    ",".join(run.categories),
                    run.json_path,
                    run.md_path,
                    run.status,
                    run.run_id,
                ),
            )
            conn.commit()

    def delete_run(self, run_id: str) -> None:
        with self._lock:
            conn = self._get_conn()
            conn.execute("DELETE FROM digest_runs WHERE run_id = ?", (run_id,))
            conn.commit()

    def get_run(self, run_id: str) -> Optional[DigestRun]:
        with self._lock:
            conn = self._get_conn()
            row = conn.execute(
                "SELECT * FROM digest_runs WHERE run_id = ?", (run_id,)
            ).fetchone()
            if row is None:
                return None
            return self._row_to_digest_run(row)

    def get_all_runs(self) -> list[DigestRun]:
        with self._lock:
            conn = self._get_conn()
            rows = conn.execute(
                "SELECT * FROM digest_runs ORDER BY started_at DESC"
            ).fetchall()
            return [self._row_to_digest_run(row) for row in rows]

    def get_total_papers(self) -> int:
        with self._lock:
            conn = self._get_conn()
            row = conn.execute("SELECT COUNT(*) as cnt FROM seen_papers").fetchone()
            return row["cnt"] if row else 0

    def get_last_run(self) -> Optional[DigestRun]:
        with self._lock:
            conn = self._get_conn()
            row = conn.execute(
                "SELECT * FROM digest_runs ORDER BY started_at DESC LIMIT 1"
            ).fetchone()
            if row is None:
                return None
            return self._row_to_digest_run(row)

    @staticmethod
    def _row_to_digest_run(row: sqlite3.Row) -> DigestRun:
        return DigestRun(
            run_id=row["run_id"],
            started_at=datetime.fromisoformat(row["started_at"]),
            finished_at=datetime.fromisoformat(row["finished_at"]) if row["finished_at"] else None,
            paper_count=row["paper_count"],
            top_n=row["top_n"],
            topics=row["topics"].split(",") if row["topics"] else [],
            categories=row["categories"].split(",") if row["categories"] else [],
            json_path=row["json_path"],
            md_path=row["md_path"],
            status=row["status"],
        )

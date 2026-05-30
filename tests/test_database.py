from datetime import datetime, timezone
import pytest
from core.database import Database
from core.models import DigestRun


class TestDatabase:
    def test_is_seen_false_for_new(self, db: Database):
        assert not db.is_seen("test-123")

    def test_mark_seen_and_is_seen(self, db: Database):
        db.mark_seen(["test-123"])
        assert db.is_seen("test-123")

    def test_mark_seen_multiple(self, db: Database):
        db.mark_seen(["a", "b", "c"])
        assert db.is_seen("a")
        assert db.is_seen("b")
        assert db.is_seen("c")
        assert not db.is_seen("d")

    def test_save_and_get_run(self, db: Database):
        run = DigestRun(
            run_id="run-1",
            started_at=datetime.now(timezone.utc),
            top_n=10,
            topics=["AI"],
            categories=["cs.AI"],
            status="running",
        )
        db.save_run(run)
        loaded = db.get_run("run-1")
        assert loaded is not None
        assert loaded.run_id == "run-1"
        assert loaded.status == "running"
        assert loaded.top_n == 10

    def test_update_run(self, db: Database):
        run = DigestRun(
            run_id="run-2",
            started_at=datetime.now(timezone.utc),
        )
        db.save_run(run)
        updated = DigestRun(
            run_id="run-2",
            started_at=run.started_at,
            finished_at=datetime.now(timezone.utc),
            paper_count=5,
            status="success",
        )
        db.update_run(updated)
        loaded = db.get_run("run-2")
        assert loaded.status == "success"
        assert loaded.paper_count == 5

    def test_get_all_runs_returns_sorted(self, db: Database):
        r1 = DigestRun(run_id="r1", started_at=datetime(2026, 1, 2, tzinfo=timezone.utc))
        r2 = DigestRun(run_id="r2", started_at=datetime(2026, 1, 3, tzinfo=timezone.utc))
        db.save_run(r1)
        db.save_run(r2)
        all_runs = db.get_all_runs()
        assert all_runs[0].run_id == "r2"  # newest first

    def test_delete_run(self, db: Database):
        run = DigestRun(run_id="del-me", started_at=datetime.now(timezone.utc))
        db.save_run(run)
        assert db.get_run("del-me") is not None
        db.delete_run("del-me")
        assert db.get_run("del-me") is None

    def test_get_last_run(self, db: Database):
        r1 = DigestRun(run_id="old", started_at=datetime(2026, 1, 1, tzinfo=timezone.utc))
        r2 = DigestRun(run_id="new", started_at=datetime(2026, 1, 5, tzinfo=timezone.utc))
        db.save_run(r1)
        db.save_run(r2)
        last = db.get_last_run()
        assert last.run_id == "new"

    def test_get_total_papers(self, db: Database):
        assert db.get_total_papers() == 0
        db.mark_seen(["p1", "p2"])
        assert db.get_total_papers() == 2

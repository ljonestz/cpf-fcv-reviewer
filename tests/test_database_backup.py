"""Backups preserve committed WAL state and durable admission counters."""
import sqlite3
import pytest
from cpf_fcv_reviewer.database_backup import backup_database


def test_backup_restores_committed_wal_state_and_quota(tmp_path):
    source = tmp_path / "reviews.sqlite3"
    destination = tmp_path / "backup.sqlite3"
    with sqlite3.connect(source) as live:
        live.execute("PRAGMA journal_mode=WAL")
        live.execute("CREATE TABLE public_admissions (count INTEGER)")
        live.execute("INSERT INTO public_admissions VALUES (4)")
        live.commit()
        backup_database(source, destination)
        with sqlite3.connect(destination) as restored:
            assert restored.execute("PRAGMA integrity_check").fetchone() == ("ok",)
            assert restored.execute("SELECT count FROM public_admissions").fetchone() == (4,)


def test_backup_never_overwrites_existing_destination(tmp_path):
    destination = tmp_path / "existing.sqlite3"
    destination.write_bytes(b"retain this file")
    with pytest.raises(FileExistsError):
        backup_database(tmp_path / "source.sqlite3", destination)
    assert destination.read_bytes() == b"retain this file"


def test_backup_rejects_missing_source_without_creating_database(tmp_path):
    with pytest.raises(FileNotFoundError):
        backup_database(tmp_path / "missing.sqlite3", tmp_path / "backup.sqlite3")

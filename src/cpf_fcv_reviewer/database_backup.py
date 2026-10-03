"""Create a consistent SQLite backup including WAL state and admission quotas.

Usage: python -m cpf_fcv_reviewer.database_backup SOURCE NEW_DESTINATION
Backups contain uploaded documents and must be stored outside the public repository.
"""
from __future__ import annotations

import argparse
import sqlite3
from pathlib import Path


def backup_database(source: Path, destination: Path) -> None:
    """Use SQLite's backup API; never overwrite a previous backup."""
    source, destination = Path(source), Path(destination)
    if destination.exists():
        raise FileExistsError(destination)
    if not source.is_file():
        raise FileNotFoundError(source)
    destination.parent.mkdir(parents=True, exist_ok=True)
    # Exclusive creation reserves the destination before SQLite opens it.
    with destination.open("xb"):
        pass
    with sqlite3.connect(source.resolve().as_uri() + "?mode=ro", uri=True) as live:
        with sqlite3.connect(destination) as backup:
            live.backup(backup)
            if backup.execute("PRAGMA integrity_check").fetchone() != ("ok",):
                raise RuntimeError("Backup integrity check failed.")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", type=Path)
    parser.add_argument("destination", type=Path)
    args = parser.parse_args()
    backup_database(args.source, args.destination)
    print("SQLite backup integrity check passed.")


if __name__ == "__main__":
    main()

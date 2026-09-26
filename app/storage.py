"""SQLite persistence for capture sessions and packet metadata."""

import sqlite3
from collections.abc import Iterable
from datetime import datetime, timezone
from pathlib import Path

from app.parser import PacketRecord

SCHEMA = """
CREATE TABLE IF NOT EXISTS capture_sessions (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    source          TEXT    NOT NULL,
    bpf_filter      TEXT,
    started_at      TEXT    NOT NULL,
    finished_at     TEXT,
    packets_stored  INTEGER NOT NULL DEFAULT 0,
    packets_ignored INTEGER NOT NULL DEFAULT 0
);

CREATE TABLE IF NOT EXISTS packets (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id   INTEGER NOT NULL REFERENCES capture_sessions(id),
    captured_at  TEXT    NOT NULL,
    ip_version   INTEGER NOT NULL CHECK (ip_version IN (4, 6)),
    src_ip       TEXT    NOT NULL,
    dst_ip       TEXT    NOT NULL,
    protocol     TEXT    NOT NULL,
    protocol_num INTEGER NOT NULL,
    length       INTEGER NOT NULL CHECK (length >= 0)
);

CREATE INDEX IF NOT EXISTS idx_packets_session  ON packets(session_id);
CREATE INDEX IF NOT EXISTS idx_packets_protocol ON packets(protocol);
CREATE INDEX IF NOT EXISTS idx_packets_src_ip   ON packets(src_ip);
CREATE INDEX IF NOT EXISTS idx_packets_dst_ip   ON packets(dst_ip);
"""

INSERT_PACKET = """
INSERT INTO packets (
    session_id, captured_at, ip_version, src_ip, dst_ip,
    protocol, protocol_num, length
) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
"""


def utc_now() -> str:
    """Current time as an ISO 8601 UTC string."""
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


class Storage:
    """Repository for capture sessions and packets in a SQLite database."""

    def __init__(self, db_path: Path) -> None:
        db_path.parent.mkdir(parents=True, exist_ok=True)
        self.connection = sqlite3.connect(db_path)
        self.connection.execute("PRAGMA foreign_keys = ON")
        self.connection.executescript(SCHEMA)

    def start_session(self, source: str, bpf_filter: str | None = None) -> int:
        """Register a new capture session and return its id."""
        with self.connection:
            cursor = self.connection.execute(
                "INSERT INTO capture_sessions (source, bpf_filter, started_at) "
                "VALUES (?, ?, ?)",
                (source, bpf_filter, utc_now()),
            )
        return cursor.lastrowid

    def insert_packets(self, session_id: int, records: Iterable[PacketRecord]) -> int:
        """Insert a batch of packet records in a single transaction."""
        rows = [
            (
                session_id,
                record.captured_at.isoformat(),
                record.ip_version,
                record.src_ip,
                record.dst_ip,
                record.protocol,
                record.protocol_num,
                record.length,
            )
            for record in records
        ]
        with self.connection:
            self.connection.executemany(INSERT_PACKET, rows)
        return len(rows)

    def finish_session(
        self, session_id: int, packets_stored: int, packets_ignored: int
    ) -> None:
        """Close a capture session with its final counters."""
        with self.connection:
            self.connection.execute(
                "UPDATE capture_sessions "
                "SET finished_at = ?, packets_stored = ?, packets_ignored = ? "
                "WHERE id = ?",
                (utc_now(), packets_stored, packets_ignored, session_id),
            )

    def close(self) -> None:
        self.connection.close()

    def __enter__(self) -> "Storage":
        return self

    def __exit__(self, *exc_info) -> None:
        self.close()

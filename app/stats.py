"""Traffic statistics computed with SQL queries over the stored packets.

Every query accepts an optional session id: None means all sessions.
The "(? IS NULL OR session_id = ?)" pattern keeps the queries static and
fully parameterized (no SQL built from strings).
"""

import sqlite3
from dataclasses import dataclass

TOP_LIMIT = 5

TOTALS_QUERY = """
SELECT COUNT(*), COALESCE(SUM(length), 0)
FROM packets
WHERE (? IS NULL OR session_id = ?)
"""

IGNORED_QUERY = """
SELECT COALESCE(SUM(packets_ignored), 0)
FROM capture_sessions
WHERE (? IS NULL OR id = ?)
"""

PROTOCOL_QUERY = """
SELECT protocol, COUNT(*) AS packets, SUM(length) AS bytes
FROM packets
WHERE (? IS NULL OR session_id = ?)
GROUP BY protocol
ORDER BY packets DESC, protocol
"""

TOP_QUERIES = {
    ("src_ip", "packets"): """
        SELECT src_ip, COUNT(*) AS packets, SUM(length) AS bytes
        FROM packets WHERE (? IS NULL OR session_id = ?)
        GROUP BY src_ip ORDER BY packets DESC, bytes DESC, src_ip LIMIT ?
    """,
    ("src_ip", "bytes"): """
        SELECT src_ip, COUNT(*) AS packets, SUM(length) AS bytes
        FROM packets WHERE (? IS NULL OR session_id = ?)
        GROUP BY src_ip ORDER BY bytes DESC, packets DESC, src_ip LIMIT ?
    """,
    ("dst_ip", "packets"): """
        SELECT dst_ip, COUNT(*) AS packets, SUM(length) AS bytes
        FROM packets WHERE (? IS NULL OR session_id = ?)
        GROUP BY dst_ip ORDER BY packets DESC, bytes DESC, dst_ip LIMIT ?
    """,
    ("dst_ip", "bytes"): """
        SELECT dst_ip, COUNT(*) AS packets, SUM(length) AS bytes
        FROM packets WHERE (? IS NULL OR session_id = ?)
        GROUP BY dst_ip ORDER BY bytes DESC, packets DESC, dst_ip LIMIT ?
    """,
}

SESSIONS_QUERY = """
SELECT id, source, bpf_filter, started_at, finished_at,
       packets_stored, packets_ignored
FROM capture_sessions
ORDER BY id
"""


@dataclass(frozen=True)
class Ranking:
    """One row of a ranking: a protocol or an IP with its traffic."""

    key: str
    packets: int
    bytes: int


@dataclass(frozen=True)
class TrafficStats:
    """Statistics of one session or of all sessions."""

    session_id: int | None
    total_packets: int
    total_bytes: int
    packets_ignored: int
    by_protocol: list[Ranking]
    top_sources_by_packets: list[Ranking]
    top_sources_by_bytes: list[Ranking]
    top_destinations_by_packets: list[Ranking]
    top_destinations_by_bytes: list[Ranking]


def session_exists(connection: sqlite3.Connection, session_id: int) -> bool:
    row = connection.execute(
        "SELECT 1 FROM capture_sessions WHERE id = ?", (session_id,)
    ).fetchone()
    return row is not None


def _rankings(rows) -> list[Ranking]:
    return [Ranking(key, packets, total) for key, packets, total in rows]


def _top(
    connection: sqlite3.Connection,
    column: str,
    order: str,
    session_id: int | None,
    limit: int,
) -> list[Ranking]:
    query = TOP_QUERIES[(column, order)]
    return _rankings(connection.execute(query, (session_id, session_id, limit)))


def compute_stats(
    connection: sqlite3.Connection,
    session_id: int | None = None,
    limit: int = TOP_LIMIT,
) -> TrafficStats:
    """Compute the traffic statistics required by the challenge."""
    params = (session_id, session_id)
    total_packets, total_bytes = connection.execute(TOTALS_QUERY, params).fetchone()
    (packets_ignored,) = connection.execute(IGNORED_QUERY, params).fetchone()

    return TrafficStats(
        session_id=session_id,
        total_packets=total_packets,
        total_bytes=total_bytes,
        packets_ignored=packets_ignored,
        by_protocol=_rankings(connection.execute(PROTOCOL_QUERY, params)),
        top_sources_by_packets=_top(connection, "src_ip", "packets", session_id, limit),
        top_sources_by_bytes=_top(connection, "src_ip", "bytes", session_id, limit),
        top_destinations_by_packets=_top(
            connection, "dst_ip", "packets", session_id, limit
        ),
        top_destinations_by_bytes=_top(
            connection, "dst_ip", "bytes", session_id, limit
        ),
    )


def list_sessions(connection: sqlite3.Connection) -> list[tuple]:
    """Return all capture sessions, oldest first."""
    return connection.execute(SESSIONS_QUERY).fetchall()

"""Terminal rendering of statistics and sessions with Rich tables."""

from rich.console import Console
from rich.table import Table

from app.stats import Ranking, TrafficStats


def _percent(part: int, total: int) -> str:
    return f"{part / total:.1%}" if total else "0.0%"


def _ranking_table(title: str, key_header: str, rows: list[Ranking]) -> Table:
    table = Table(title=title, title_justify="left")
    table.add_column("#", justify="right")
    table.add_column(key_header)
    table.add_column("Packets", justify="right")
    table.add_column("Bytes", justify="right")
    for position, row in enumerate(rows, start=1):
        table.add_row(str(position), row.key, f"{row.packets:,}", f"{row.bytes:,}")
    return table


def render_stats(console: Console, stats: TrafficStats) -> None:
    scope = f"session {stats.session_id}" if stats.session_id else "all sessions"
    console.rule(f"[bold]Traffic statistics — {scope}")

    summary = Table(title="Summary", title_justify="left", show_header=False)
    summary.add_column("Metric")
    summary.add_column("Value", justify="right")
    summary.add_row("Total packets captured (IP)", f"{stats.total_packets:,}")
    summary.add_row("Total bytes", f"{stats.total_bytes:,}")
    summary.add_row("Non-IP packets ignored", f"{stats.packets_ignored:,}")
    console.print(summary)

    protocols = Table(title="Packets by protocol", title_justify="left")
    protocols.add_column("Protocol")
    protocols.add_column("Packets", justify="right")
    protocols.add_column("%", justify="right")
    protocols.add_column("Bytes", justify="right")
    for row in stats.by_protocol:
        protocols.add_row(
            row.key,
            f"{row.packets:,}",
            _percent(row.packets, stats.total_packets),
            f"{row.bytes:,}",
        )
    console.print(protocols)

    console.print(
        _ranking_table(
            "Top 5 source IPs (by packets)", "Source IP", stats.top_sources_by_packets
        )
    )
    console.print(
        _ranking_table(
            "Top 5 source IPs (by bytes)", "Source IP", stats.top_sources_by_bytes
        )
    )
    console.print(
        _ranking_table(
            "Top 5 destination IPs (by packets)",
            "Destination IP",
            stats.top_destinations_by_packets,
        )
    )
    console.print(
        _ranking_table(
            "Top 5 destination IPs (by bytes)",
            "Destination IP",
            stats.top_destinations_by_bytes,
        )
    )


def _short_time(value: str | None) -> str:
    """Format an ISO 8601 UTC timestamp as 'YYYY-MM-DD HH:MM:SS'."""
    return value.replace("T", " ")[:19] if value else "-"


def render_sessions(console: Console, sessions: list[tuple]) -> None:
    table = Table(title="Capture sessions", title_justify="left")
    for header in ("ID", "Source", "Filter", "Started (UTC)", "Finished (UTC)"):
        table.add_column(header, no_wrap=True)
    table.add_column("Stored", justify="right")
    table.add_column("Ignored", justify="right")
    for session_id, source, bpf, started, finished, stored, ignored in sessions:
        table.add_row(
            str(session_id),
            source,
            bpf or "-",
            _short_time(started),
            _short_time(finished),
            f"{stored:,}",
            f"{ignored:,}",
        )
    console.print(table)

"""Testes das estatísticas e dos comandos stats e sessions.

A base de teste faz o líder por pacotes ser diferente do líder por bytes.
"""

from datetime import UTC, datetime
from pathlib import Path

import pytest
from rich.console import Console

from app.capture import read_pcap
from app.cli import main
from app.parser import PacketRecord
from app.report import render_sessions, render_stats
from app.stats import compute_stats, list_sessions
from app.storage import Storage

SAMPLE_PCAP = Path(__file__).resolve().parent.parent / "samples" / "demo.pcap"


def record(src: str, dst: str, protocol: str, length: int) -> PacketRecord:
    """Cria um registro de pacote com os campos que interessam às estatísticas."""
    return PacketRecord(
        captured_at=datetime(2026, 9, 25, 12, 0, tzinfo=UTC),
        ip_version=4,
        src_ip=src,
        dst_ip=dst,
        protocol=protocol,
        protocol_num={"TCP": 6, "UDP": 17, "ICMP": 1}[protocol],
        length=length,
    )


@pytest.fixture
def storage(tmp_path):
    """Base com valores conhecidos para os testes de estatística.

    Sessão 1: 3 pacotes pequenos de 10.0.0.1 e 1 pacote grande de 10.0.0.2
    (o primeiro lidera por pacotes, o segundo por bytes); 2 não-IP ignorados.
    Sessão 2: 1 pacote UDP.
    """
    with Storage(tmp_path / "test.db") as db:
        first = db.start_session("pcap:first.pcap")
        db.insert_packets(
            first,
            [
                record("10.0.0.1", "10.0.0.9", "TCP", 60),
                record("10.0.0.1", "10.0.0.9", "TCP", 60),
                record("10.0.0.1", "10.0.0.8", "ICMP", 60),
                record("10.0.0.2", "10.0.0.8", "TCP", 1500),
            ],
        )
        db.finish_session(first, packets_stored=4, packets_ignored=2)

        second = db.start_session("pcap:second.pcap")
        db.insert_packets(second, [record("10.0.0.3", "10.0.0.9", "UDP", 100)])
        db.finish_session(second, packets_stored=1, packets_ignored=0)
        yield db


def test_totals_for_all_sessions(storage):
    """Os totais somam todas as sessões, incluindo os não-IP ignorados."""
    stats = compute_stats(storage.connection)

    assert stats.total_packets == 5
    assert stats.total_bytes == 1780
    assert stats.packets_ignored == 2


def test_totals_for_one_session(storage):
    """Com uma sessão informada, somente os dados dela são considerados."""
    stats = compute_stats(storage.connection, session_id=2)

    assert stats.total_packets == 1
    assert stats.packets_ignored == 0
    assert stats.by_protocol[0].key == "UDP"


def test_packets_by_protocol(storage):
    """A contagem por protocolo corresponde aos pacotes gravados."""
    stats = compute_stats(storage.connection, session_id=1)
    counts = {row.key: row.packets for row in stats.by_protocol}

    assert counts == {"TCP": 3, "ICMP": 1}


def test_top_sources_differ_by_packets_and_bytes(storage):
    """O líder por pacotes é diferente do líder por bytes."""
    stats = compute_stats(storage.connection, session_id=1)

    assert stats.top_sources_by_packets[0].key == "10.0.0.1"
    assert stats.top_sources_by_packets[0].packets == 3
    assert stats.top_sources_by_bytes[0].key == "10.0.0.2"
    assert stats.top_sources_by_bytes[0].bytes == 1500


def test_top_destinations(storage):
    """Os rankings de destino seguem os mesmos critérios dos de origem."""
    stats = compute_stats(storage.connection)

    assert stats.top_destinations_by_packets[0].key == "10.0.0.9"
    assert stats.top_destinations_by_packets[0].packets == 3
    assert stats.top_destinations_by_bytes[0].key == "10.0.0.8"


def test_top_is_limited_to_five(tmp_path):
    """Com 10 IPs diferentes, o ranking exibe apenas 5."""
    with Storage(tmp_path / "many.db") as db:
        session = db.start_session("pcap:many.pcap")
        db.insert_packets(
            session, [record(f"10.0.0.{n}", "10.0.1.1", "TCP", 60) for n in range(10)]
        )
        stats = compute_stats(db.connection)

    assert len(stats.top_sources_by_packets) == 5


def test_empty_database(tmp_path):
    """Um banco vazio produz zeros, sem erro."""
    with Storage(tmp_path / "empty.db") as db:
        stats = compute_stats(db.connection)

    assert stats.total_packets == 0
    assert stats.by_protocol == []


def test_report_rendering(storage):
    """As tabelas do terminal exibem os títulos e as sessões esperados."""
    console = Console(record=True, width=120)
    render_stats(console, compute_stats(storage.connection))
    render_sessions(console, list_sessions(storage.connection))
    output = console.export_text()

    total_line = next(
        line for line in output.splitlines() if "Total packets captured" in line
    )
    stored_line = next(
        line for line in output.splitlines() if "IP packets stored" in line
    )
    ignored_line = next(
        line for line in output.splitlines() if "Non-IP packets ignored" in line
    )

    assert total_line.split()[-2] == "7"
    assert stored_line.split()[-2] == "5"
    assert ignored_line.split()[-2] == "2"
    assert "Packets by protocol" in output
    assert "Top 5 source IPs (by packets)" in output
    assert "Top 5 destination IPs (by bytes)" in output
    assert "pcap:second.pcap" in output


@pytest.mark.skipif(not SAMPLE_PCAP.exists(), reason="samples/demo.pcap not found")
def test_demo_pcap_statistics(tmp_path):
    """Estatísticas da amostra real iguais aos números de referência."""
    with Storage(tmp_path / "demo.db") as db:
        result = read_pcap(db, SAMPLE_PCAP)
        stats = compute_stats(db.connection, result.session_id)

    protocols = {row.key: row.packets for row in stats.by_protocol}
    assert stats.total_packets == 284
    assert stats.packets_ignored == 16
    assert protocols == {"TCP": 234, "UDP": 30, "ICMP": 20}
    assert stats.top_sources_by_packets[0].key == "172.19.40.48"
    assert stats.top_sources_by_packets[0].packets == 146
    assert stats.top_destinations_by_packets[0].key == "172.19.40.48"
    assert stats.top_destinations_by_packets[0].packets == 116


def test_cli_stats_and_sessions(tmp_path, storage):
    """Os comandos stats e sessions terminam com sucesso."""
    db_path = str(tmp_path / "test.db")

    assert main(["--db", db_path, "stats"]) == 0
    assert main(["--db", db_path, "stats", "--session", "1"]) == 0
    assert main(["--db", db_path, "sessions"]) == 0


def test_cli_stats_unknown_session_returns_error(tmp_path, storage):
    """Pedir uma sessão inexistente termina com código 1 (erro)."""
    assert main(["--db", str(tmp_path / "test.db"), "stats", "--session", "99"]) == 1

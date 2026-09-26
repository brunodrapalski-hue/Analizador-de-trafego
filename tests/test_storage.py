"""Testes do armazenamento em SQLite.

Cada teste usa um banco temporário (tmp_path do pytest), que é descartado ao
final: os testes nunca tocam no banco real em data/.
"""

import sqlite3
from datetime import UTC, datetime

import pytest

from app.parser import PacketRecord
from app.storage import Storage


def make_record(src_ip: str = "10.0.0.1", protocol: str = "TCP") -> PacketRecord:
    """Cria um registro de pacote com valores fixos para os testes."""
    return PacketRecord(
        captured_at=datetime(2026, 9, 25, 12, 0, tzinfo=UTC),
        ip_version=4,
        src_ip=src_ip,
        dst_ip="10.0.0.2",
        protocol=protocol,
        protocol_num=6,
        length=60,
    )


@pytest.fixture
def storage(tmp_path):
    """Banco temporário e vazio para cada teste."""
    with Storage(tmp_path / "test.db") as db:
        yield db


def test_schema_is_created(storage):
    """As duas tabelas são criadas automaticamente ao abrir o banco."""
    tables = {
        row[0]
        for row in storage.connection.execute(
            "SELECT name FROM sqlite_master WHERE type = 'table'"
        )
    }
    assert {"capture_sessions", "packets"} <= tables


def test_opening_existing_database_keeps_data(tmp_path):
    """Reabrir um banco existente preserva os dados já gravados."""
    db_path = tmp_path / "test.db"
    with Storage(db_path) as db:
        session_id = db.start_session("pcap:demo.pcap")
        db.insert_packets(session_id, [make_record()])

    with Storage(db_path) as db:
        count = db.connection.execute("SELECT COUNT(*) FROM packets").fetchone()[0]
    assert count == 1


def test_session_lifecycle(storage):
    """Uma sessão registra origem, filtro, horário de fim e contadores."""
    session_id = storage.start_session("iface:eth0", "tcp or udp")
    inserted = storage.insert_packets(session_id, [make_record(), make_record()])
    storage.finish_session(session_id, packets_stored=2, packets_ignored=1)

    row = storage.connection.execute(
        "SELECT source, bpf_filter, finished_at, packets_stored, packets_ignored "
        "FROM capture_sessions WHERE id = ?",
        (session_id,),
    ).fetchone()

    assert inserted == 2
    assert row[0] == "iface:eth0"
    assert row[1] == "tcp or udp"
    assert row[2] is not None
    assert row[3:] == (2, 1)


def test_packet_fields_are_persisted(storage):
    """Todos os campos do pacote são gravados exatamente como recebidos."""
    session_id = storage.start_session("pcap:demo.pcap")
    storage.insert_packets(session_id, [make_record(src_ip="192.168.0.10")])

    row = storage.connection.execute(
        "SELECT captured_at, ip_version, src_ip, dst_ip, protocol, length FROM packets"
    ).fetchone()

    assert row == (
        "2026-09-25T12:00:00+00:00",
        4,
        "192.168.0.10",
        "10.0.0.2",
        "TCP",
        60,
    )


def test_packet_requires_existing_session(storage):
    """A chave estrangeira impede gravar pacote de sessão inexistente."""
    with pytest.raises(sqlite3.IntegrityError):
        storage.insert_packets(999, [make_record()])

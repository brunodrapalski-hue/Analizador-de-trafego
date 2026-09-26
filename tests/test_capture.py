"""Testes da captura e do comando capture.

A leitura de .pcap é testada de ponta a ponta. A captura ao vivo depende de
tráfego real, então aqui é testada a validação da interface; o funcionamento
ao vivo foi verificado manualmente (docs/evidencias/03-captura-ao-vivo.txt).
"""

from pathlib import Path

import pytest
from scapy.layers.inet import IP, TCP, UDP
from scapy.layers.l2 import ARP, Ether
from scapy.utils import wrpcap

from app.capture import capture_live, read_pcap
from app.cli import build_parser, main
from app.storage import Storage

SAMPLE_PCAP = Path(__file__).resolve().parent.parent / "samples" / "demo.pcap"


@pytest.fixture
def small_pcap(tmp_path):
    """Arquivo .pcap temporário com 3 TCP, 2 UDP e 1 ARP (não-IP)."""
    packets = (
        [Ether() / IP(src="10.0.0.1", dst="10.0.0.2") / TCP()] * 3
        + [Ether() / IP(src="10.0.0.3", dst="10.0.0.2") / UDP()] * 2
        + [Ether() / ARP()]
    )
    path = tmp_path / "small.pcap"
    wrpcap(str(path), packets)
    return path


def count_packets(storage: Storage) -> int:
    """Conta quantos pacotes foram gravados no banco."""
    return storage.connection.execute("SELECT COUNT(*) FROM packets").fetchone()[0]


def test_read_pcap_stores_ip_packets_in_batches(tmp_path, small_pcap):
    """Com lotes de 2, os 5 pacotes IP são gravados e o ARP é contado."""
    with Storage(tmp_path / "test.db") as storage:
        result = read_pcap(storage, small_pcap, batch_size=2)

        assert result.packets_stored == 5
        assert result.packets_ignored == 1
        assert count_packets(storage) == 5


def test_session_counters_are_saved(tmp_path, small_pcap):
    """A sessão é encerrada com a origem e os contadores corretos."""
    with Storage(tmp_path / "test.db") as storage:
        result = read_pcap(storage, small_pcap)
        row = storage.connection.execute(
            "SELECT source, packets_stored, packets_ignored, finished_at "
            "FROM capture_sessions WHERE id = ?",
            (result.session_id,),
        ).fetchone()

    assert row[0] == "pcap:small.pcap"
    assert row[1:3] == (5, 1)
    assert row[3] is not None


def test_read_missing_pcap_raises(tmp_path):
    """Um arquivo .pcap inexistente gera erro claro."""
    with Storage(tmp_path / "test.db") as storage:
        with pytest.raises(FileNotFoundError):
            read_pcap(storage, tmp_path / "missing.pcap")


def test_live_capture_rejects_unknown_interface(tmp_path):
    """Uma interface inexistente é recusada antes de iniciar a captura."""
    with Storage(tmp_path / "test.db") as storage:
        with pytest.raises(ValueError, match="not found"):
            capture_live(storage, interface="does-not-exist0")


@pytest.mark.skipif(not SAMPLE_PCAP.exists(), reason="samples/demo.pcap not found")
def test_demo_pcap_end_to_end(tmp_path):
    """A amostra real, do arquivo ao banco: 284 pacotes IP e 16 não-IP."""
    with Storage(tmp_path / "test.db") as storage:
        result = read_pcap(storage, SAMPLE_PCAP)

    assert result.packets_stored == 284
    assert result.packets_ignored == 16


def test_cli_capture_pcap_returns_success(tmp_path, small_pcap):
    """O comando capture termina com código de saída 0 (sucesso)."""
    exit_code = main(
        ["--db", str(tmp_path / "cli.db"), "capture", "--pcap", str(small_pcap)]
    )
    assert exit_code == 0


def test_cli_missing_pcap_returns_error(tmp_path):
    """O comando capture com arquivo ausente termina com código 1 (erro)."""
    exit_code = main(
        ["--db", str(tmp_path / "cli.db"), "capture", "--pcap", "missing.pcap"]
    )
    assert exit_code == 1


@pytest.mark.parametrize(
    "extra_option",
    [
        ["--count", "1"],
        ["--duration", "1"],
        ["--filter", "tcp"],
    ],
)
def test_cli_pcap_rejects_live_capture_options(tmp_path, small_pcap, extra_option):
    """Opções exclusivas da captura ao vivo são recusadas com --pcap."""
    db_path = tmp_path / "invalid.db"

    exit_code = main(
        [
            "--db",
            str(db_path),
            "capture",
            "--pcap",
            str(small_pcap),
            *extra_option,
        ]
    )

    assert exit_code == 1
    assert not db_path.exists()


@pytest.mark.parametrize(
    ("option", "value"),
    [
        ("--count", "0"),
        ("--count", "-1"),
        ("--duration", "0"),
        ("--duration", "-1"),
    ],
)
def test_cli_rejects_non_positive_capture_limits(option, value):
    """Count e duration aceitam somente inteiros maiores que zero."""
    parser = build_parser()

    with pytest.raises(SystemExit) as error:
        parser.parse_args(["capture", "--iface", "eth0", option, value])

    assert error.value.code == 2


@pytest.mark.parametrize("batch_size", ["abc", "0", "-1"])
def test_cli_invalid_batch_size_returns_error(
    tmp_path, small_pcap, monkeypatch, batch_size
):
    """Batch size inválido termina com erro tratado, sem executar a captura."""
    monkeypatch.setenv("TRAFFIC_BATCH_SIZE", batch_size)

    exit_code = main(
        [
            "--db",
            str(tmp_path / "invalid-batch.db"),
            "capture",
            "--pcap",
            str(small_pcap),
        ]
    )

    assert exit_code == 1

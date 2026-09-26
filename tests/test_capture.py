"""Tests for app.capture and the capture command."""

from pathlib import Path

import pytest
from scapy.layers.inet import IP, TCP, UDP
from scapy.layers.l2 import ARP, Ether
from scapy.utils import wrpcap

from app.capture import capture_live, read_pcap
from app.cli import main
from app.storage import Storage

SAMPLE_PCAP = Path(__file__).resolve().parent.parent / "samples" / "demo.pcap"


@pytest.fixture
def small_pcap(tmp_path):
    """3 TCP + 2 UDP + 1 ARP packets."""
    packets = (
        [Ether() / IP(src="10.0.0.1", dst="10.0.0.2") / TCP()] * 3
        + [Ether() / IP(src="10.0.0.3", dst="10.0.0.2") / UDP()] * 2
        + [Ether() / ARP()]
    )
    path = tmp_path / "small.pcap"
    wrpcap(str(path), packets)
    return path


def count_packets(storage: Storage) -> int:
    return storage.connection.execute("SELECT COUNT(*) FROM packets").fetchone()[0]


def test_read_pcap_stores_ip_packets_in_batches(tmp_path, small_pcap):
    with Storage(tmp_path / "test.db") as storage:
        result = read_pcap(storage, small_pcap, batch_size=2)

        assert result.packets_stored == 5
        assert result.packets_ignored == 1
        assert count_packets(storage) == 5


def test_session_counters_are_saved(tmp_path, small_pcap):
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
    with Storage(tmp_path / "test.db") as storage:
        with pytest.raises(FileNotFoundError):
            read_pcap(storage, tmp_path / "missing.pcap")


def test_live_capture_rejects_unknown_interface(tmp_path):
    with Storage(tmp_path / "test.db") as storage:
        with pytest.raises(ValueError, match="not found"):
            capture_live(storage, interface="does-not-exist0")


@pytest.mark.skipif(not SAMPLE_PCAP.exists(), reason="samples/demo.pcap not found")
def test_demo_pcap_end_to_end(tmp_path):
    with Storage(tmp_path / "test.db") as storage:
        result = read_pcap(storage, SAMPLE_PCAP)

    assert result.packets_stored == 284
    assert result.packets_ignored == 16


def test_cli_capture_pcap_returns_success(tmp_path, small_pcap):
    exit_code = main(
        ["--db", str(tmp_path / "cli.db"), "capture", "--pcap", str(small_pcap)]
    )
    assert exit_code == 0


def test_cli_missing_pcap_returns_error(tmp_path):
    exit_code = main(
        ["--db", str(tmp_path / "cli.db"), "capture", "--pcap", "missing.pcap"]
    )
    assert exit_code == 1

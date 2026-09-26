"""Packet capture from a network interface or from a pcap file.

Both sources share the same pipeline: parse each packet, buffer the records
and write them to the database in batches (D11). Pending records are always
flushed when the capture ends, including on Ctrl+C.
"""

import logging
from dataclasses import dataclass
from pathlib import Path

from scapy.interfaces import get_if_list
from scapy.packet import Packet
from scapy.sendrecv import sniff
from scapy.utils import PcapReader

from app.parser import PacketRecord, parse_packet
from app.storage import Storage

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class CaptureResult:
    """Summary of a finished capture session."""

    session_id: int
    packets_stored: int
    packets_ignored: int


class PacketCollector:
    """Parse packets and store them in batches for one capture session."""

    def __init__(self, storage: Storage, session_id: int, batch_size: int) -> None:
        self.storage = storage
        self.session_id = session_id
        self.batch_size = batch_size
        self.buffer: list[PacketRecord] = []
        self.packets_stored = 0
        self.packets_ignored = 0

    def handle(self, packet: Packet) -> None:
        record = parse_packet(packet)
        if record is None:
            self.packets_ignored += 1
            return
        self.buffer.append(record)
        if len(self.buffer) >= self.batch_size:
            self.flush()

    def flush(self) -> None:
        if self.buffer:
            self.packets_stored += self.storage.insert_packets(
                self.session_id, self.buffer
            )
            self.buffer.clear()

    def finish(self) -> CaptureResult:
        self.flush()
        self.storage.finish_session(
            self.session_id, self.packets_stored, self.packets_ignored
        )
        return CaptureResult(self.session_id, self.packets_stored, self.packets_ignored)


def capture_live(
    storage: Storage,
    interface: str,
    count: int = 0,
    duration: int | None = None,
    bpf_filter: str | None = None,
    batch_size: int = 100,
) -> CaptureResult:
    """Capture packets from a network interface until count, duration or Ctrl+C."""
    available = get_if_list()
    if interface not in available:
        raise ValueError(
            f"Interface '{interface}' not found. Available: {', '.join(available)}"
        )

    session_id = storage.start_session(f"iface:{interface}", bpf_filter)
    collector = PacketCollector(storage, session_id, batch_size)
    logger.info("Capturing on %s (press Ctrl+C to stop)...", interface)
    try:
        sniff(
            iface=interface,
            prn=collector.handle,
            store=False,
            count=count,
            timeout=duration,
            filter=bpf_filter,
        )
    except KeyboardInterrupt:
        logger.info("Capture interrupted by user.")
    finally:
        result = collector.finish()
    return result


def read_pcap(
    storage: Storage, pcap_path: Path, batch_size: int = 100
) -> CaptureResult:
    """Read packets from a pcap file, streaming it to keep memory usage low."""
    if not pcap_path.is_file():
        raise FileNotFoundError(f"pcap file not found: {pcap_path}")

    session_id = storage.start_session(f"pcap:{pcap_path.name}")
    collector = PacketCollector(storage, session_id, batch_size)
    logger.info("Reading %s...", pcap_path)
    try:
        with PcapReader(str(pcap_path)) as reader:
            for packet in reader:
                collector.handle(packet)
    finally:
        result = collector.finish()
    return result

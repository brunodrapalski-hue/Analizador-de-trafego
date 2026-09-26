"""Convert raw Scapy packets into normalized packet records.

Design decisions (see docs):
- D6: only IPv4 and IPv6 packets are kept; non-IP frames (e.g. ARP) are discarded.
- D7: the protocol is classified by the IP protocol number (IPv4 "proto",
  IPv6 "nh"), mapped to TCP, UDP, ICMP, ICMPv6 or OTHER.
- D8: the size is the full frame length in bytes, as reported by Wireshark.
- D10: only metadata is extracted; the packet payload is never stored.
"""

from dataclasses import dataclass
from datetime import UTC, datetime

from scapy.layers.inet import IP
from scapy.layers.inet6 import IPv6
from scapy.packet import Packet

PROTOCOL_NAMES = {
    1: "ICMP",
    6: "TCP",
    17: "UDP",
    58: "ICMPv6",
}
OTHER_PROTOCOL = "OTHER"


@dataclass(frozen=True)
class PacketRecord:
    """Metadata of a single captured packet."""

    captured_at: datetime
    ip_version: int
    src_ip: str
    dst_ip: str
    protocol: str
    protocol_num: int
    length: int


def classify_protocol(protocol_num: int) -> str:
    """Return the protocol name for an IP protocol number."""
    return PROTOCOL_NAMES.get(protocol_num, OTHER_PROTOCOL)


def frame_length(packet: Packet) -> int:
    """Return the original frame length in bytes.

    Packets read from a pcap file keep the original size in "wirelen",
    even if the capture was truncated. Live packets use len(packet).
    """
    wirelen = getattr(packet, "wirelen", None)
    return wirelen if wirelen else len(packet)


def parse_packet(packet: Packet) -> PacketRecord | None:
    """Extract the metadata of an IP packet, or return None if it is not IP."""
    if packet.haslayer(IP):
        layer = packet[IP]
        ip_version = 4
        protocol_num = int(layer.proto)
    elif packet.haslayer(IPv6):
        layer = packet[IPv6]
        ip_version = 6
        protocol_num = int(layer.nh)
    else:
        return None

    return PacketRecord(
        captured_at=datetime.fromtimestamp(float(packet.time), tz=UTC),
        ip_version=ip_version,
        src_ip=layer.src,
        dst_ip=layer.dst,
        protocol=classify_protocol(protocol_num),
        protocol_num=protocol_num,
        length=frame_length(packet),
    )

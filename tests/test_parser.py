"""Tests for app.parser."""

from collections import Counter
from pathlib import Path

import pytest
from scapy.layers.inet import ICMP, IP, TCP, UDP
from scapy.layers.inet6 import ICMPv6EchoRequest, IPv6
from scapy.layers.l2 import ARP, Ether
from scapy.utils import rdpcap

from app.parser import parse_packet

SAMPLE_PCAP = Path(__file__).resolve().parent.parent / "samples" / "demo.pcap"


@pytest.mark.parametrize(
    ("packet", "expected_protocol"),
    [
        (Ether() / IP(src="10.0.0.1", dst="10.0.0.2") / TCP(), "TCP"),
        (Ether() / IP(src="10.0.0.1", dst="10.0.0.2") / UDP(), "UDP"),
        (Ether() / IP(src="10.0.0.1", dst="10.0.0.2") / ICMP(), "ICMP"),
        (Ether() / IP(src="10.0.0.1", dst="10.0.0.2", proto=47), "OTHER"),
    ],
)
def test_ipv4_protocol_classification(packet, expected_protocol):
    record = parse_packet(packet)

    assert record is not None
    assert record.ip_version == 4
    assert record.src_ip == "10.0.0.1"
    assert record.dst_ip == "10.0.0.2"
    assert record.protocol == expected_protocol


def test_ipv6_packet():
    packet = Ether() / IPv6(src="2001:db8::1", dst="2001:db8::2") / ICMPv6EchoRequest()
    record = parse_packet(packet)

    assert record is not None
    assert record.ip_version == 6
    assert record.src_ip == "2001:db8::1"
    assert record.protocol == "ICMPv6"
    assert record.protocol_num == 58


def test_non_ip_packet_is_discarded():
    assert parse_packet(Ether() / ARP()) is None


def test_length_is_full_frame_size():
    packet = Ether() / IP() / UDP() / (b"x" * 100)
    record = parse_packet(packet)

    assert record.length == len(packet)  # 14 + 20 + 8 + 100 = 142


@pytest.mark.skipif(not SAMPLE_PCAP.exists(), reason="samples/demo.pcap not found")
def test_demo_pcap_matches_reference_numbers():
    """Reference numbers verified independently (Wireshark / Scapy)."""
    packets = rdpcap(str(SAMPLE_PCAP))
    records = [parse_packet(p) for p in packets]
    ip_records = [r for r in records if r is not None]
    protocols = Counter(r.protocol for r in ip_records)

    assert len(packets) == 300
    assert len(ip_records) == 284
    assert protocols["TCP"] == 234
    assert protocols["UDP"] == 30
    assert protocols["ICMP"] == 20

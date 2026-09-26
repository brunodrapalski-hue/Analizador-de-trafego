"""Converte pacotes Scapy em PacketRecord.

Somente pacotes com camada IPv4 ou IPv6 geram registro; os demais retornam
None e devem ser contabilizados por quem chama. O payload não é lido.
"""

from dataclasses import dataclass
from datetime import UTC, datetime

from scapy.layers.inet import IP
from scapy.layers.inet6 import IPv6
from scapy.packet import Packet

# Números de protocolo IANA. Valores fora da tabela viram OTHER; o número
# original fica em protocol_num.
PROTOCOL_NAMES = {
    1: "ICMP",
    6: "TCP",
    17: "UDP",
    58: "ICMPv6",
}
OTHER_PROTOCOL = "OTHER"


@dataclass(frozen=True)
class PacketRecord:
    """Metadados de um pacote capturado, prontos para gravação no banco."""

    captured_at: datetime  # UTC
    ip_version: int
    src_ip: str
    dst_ip: str
    protocol: str  # TCP, UDP, ICMP, ICMPv6 ou OTHER
    protocol_num: int
    length: int  # bytes do frame completo (ver frame_length)


def classify_protocol(protocol_num: int) -> str:
    """Converte o número de protocolo do cabeçalho IP em um nome legível."""
    return PROTOCOL_NAMES.get(protocol_num, OTHER_PROTOCOL)


def frame_length(packet: Packet) -> int:
    """Tamanho do frame em bytes.

    Usa wirelen quando disponível: pacotes lidos de .pcap preservam o tamanho
    original mesmo se a gravação foi truncada (snaplen). Caso contrário, usa
    len(packet).
    """
    wirelen = getattr(packet, "wirelen", None)
    return wirelen if wirelen else len(packet)


def parse_packet(packet: Packet) -> PacketRecord | None:
    """Retorna o registro do pacote ou None se não houver camada IPv4/IPv6.

    Quem chama deve contabilizar os retornos None.
    """
    # A ordem importa: com IPv4 e IPv6 no mesmo pacote (túneis), prevalece a IPv4.
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
        # packet.time é o horário da captura em epoch; convertido para UTC.
        captured_at=datetime.fromtimestamp(float(packet.time), tz=UTC),
        ip_version=ip_version,
        src_ip=layer.src,
        dst_ip=layer.dst,
        protocol=classify_protocol(protocol_num),
        protocol_num=protocol_num,
        length=frame_length(packet),
    )

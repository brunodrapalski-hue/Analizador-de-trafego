"""Captura ao vivo (sniff) e leitura de .pcap (PcapReader).

Os dois modos usam o mesmo PacketCollector. count, duration e filtro BPF
existem apenas na captura ao vivo. Com interface "auto", é usada a interface
da rota padrão da máquina. O buffer pendente é gravado e a sessão
é encerrada no finally de cada função.
"""

import logging
from dataclasses import dataclass
from pathlib import Path

from scapy.config import conf
from scapy.interfaces import get_if_list
from scapy.packet import Packet
from scapy.sendrecv import sniff
from scapy.utils import PcapReader

from app.parser import PacketRecord, parse_packet
from app.storage import Storage

logger = logging.getLogger(__name__)

AUTO_INTERFACE = "auto"


@dataclass(frozen=True)
class CaptureResult:
    """Resumo de uma sessão de captura encerrada, usado para exibir o resultado."""

    session_id: int
    packets_stored: int
    packets_ignored: int


class PacketCollector:
    """Acumula os registros de uma sessão, grava em lotes e mantém os contadores."""

    def __init__(self, storage: Storage, session_id: int, batch_size: int) -> None:
        self.storage = storage
        self.session_id = session_id
        self.batch_size = batch_size
        self.buffer: list[PacketRecord] = []
        self.packets_stored = 0
        self.packets_ignored = 0

    def handle(self, packet: Packet) -> None:
        """Normaliza e acumula o pacote; grava ao atingir batch_size.

        Pacotes sem IP só incrementam packets_ignored.
        """
        record = parse_packet(packet)
        if record is None:
            self.packets_ignored += 1
            return
        self.buffer.append(record)
        if len(self.buffer) >= self.batch_size:
            self.flush()

    def flush(self) -> None:
        """Grava no banco os registros acumulados e esvazia o buffer."""
        if self.buffer:
            self.packets_stored += self.storage.insert_packets(
                self.session_id, self.buffer
            )
            self.buffer.clear()

    def finish(self) -> CaptureResult:
        """Grava o que restou no buffer e encerra a sessão com os contadores."""
        self.flush()
        self.storage.finish_session(
            self.session_id, self.packets_stored, self.packets_ignored
        )
        return CaptureResult(self.session_id, self.packets_stored, self.packets_ignored)


def resolve_interface(interface: str) -> str:
    """Retorna a interface informada ou, com "auto", a da rota padrão.

    O nome da interface principal muda entre máquinas (ex.: eth0 no WSL2
    padrão, enP15180p0s0 no modo espelhado), por isso "auto" usa a escolha
    do Scapy, que segue a rota padrão, como o comando "ip route".
    """
    if interface != AUTO_INTERFACE:
        return interface

    default = getattr(conf.iface, "name", None) or str(conf.iface or "")
    if not default or default == "lo":
        raise ValueError(
            "Could not detect the default interface. "
            "Use --iface with one of: " + ", ".join(get_if_list())
        )
    logger.info("Interface detected automatically: %s", default)
    return default


def capture_live(
    storage: Storage,
    interface: str,
    count: int = 0,
    duration: int | None = None,
    bpf_filter: str | None = None,
    batch_size: int = 100,
) -> CaptureResult:
    """Captura da interface até count, duration ou Ctrl+C.

    count conta todos os pacotes recebidos após o filtro BPF, inclusive não-IP.
    """
    interface = resolve_interface(interface)
    # Validada antes de criar a sessão: interface inexistente não gera registro.
    available = get_if_list()
    if interface not in available:
        raise ValueError(
            f"Interface '{interface}' not found. Available: {', '.join(available)}"
        )

    session_id = storage.start_session(f"iface:{interface}", bpf_filter)
    collector = PacketCollector(storage, session_id, batch_size)
    logger.info("Capturing on %s (press Ctrl+C to stop)...", interface)
    try:
        # store=False: o Scapy não guarda os pacotes; cada um é processado e descartado.
        sniff(
            iface=interface,
            prn=collector.handle,
            store=False,
            count=count,  # 0 = sem limite de quantidade
            timeout=duration,  # None = sem limite de tempo
            filter=bpf_filter,
        )
    except KeyboardInterrupt:
        logger.info("Capture interrupted by user.")
    finally:
        # Executa também em Ctrl+C e em erro do sniff: grava o buffer e fecha a sessão.
        result = collector.finish()
    return result


def read_pcap(
    storage: Storage, pcap_path: Path, batch_size: int = 100
) -> CaptureResult:
    """Lê o .pcap em streaming (PcapReader).

    Arquivo inexistente levanta FileNotFoundError antes de criar a sessão.
    """
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
        # Grava o buffer e fecha a sessão mesmo se a leitura falhar.
        result = collector.finish()
    return result

"""Comandos capture, stats e sessions.

FileNotFoundError, ValueError, PermissionError e Scapy_Exception viram uma
linha "ERROR: ..." e código de saída 1. Outras exceções não são tratadas aqui.
"""

import argparse
import logging
from pathlib import Path

from rich.console import Console
from scapy.error import Scapy_Exception

from app import config
from app.capture import CaptureResult, capture_live, read_pcap
from app.report import render_sessions, render_stats
from app.stats import compute_stats, list_sessions, session_exists
from app.storage import Storage

logger = logging.getLogger(__name__)
console = Console()


def _positive_int(value: str) -> int:
    """Converte para inteiro positivo para uso nas opções da CLI."""
    try:
        number = int(value)
    except ValueError:
        raise argparse.ArgumentTypeError(
            "must be an integer greater than zero"
        ) from None

    if number <= 0:
        raise argparse.ArgumentTypeError("must be greater than zero")
    return number


def build_parser() -> argparse.ArgumentParser:
    """Monta os comandos, as opções e os textos de ajuda (--help)."""
    parser = argparse.ArgumentParser(
        prog="traffic-analyzer",
        description=(
            "Capture network packets, store their metadata in SQLite "
            "and display traffic statistics."
        ),
    )
    parser.add_argument(
        "--db",
        type=Path,
        default=config.DB_PATH,
        help="SQLite database file (default: %(default)s)",
    )
    commands = parser.add_subparsers(dest="command", required=True)

    capture = commands.add_parser(
        "capture", help="capture packets from an interface or read a pcap file"
    )
    source = capture.add_mutually_exclusive_group(required=True)
    source.add_argument("-i", "--iface", help="network interface, e.g. eth0")
    source.add_argument("-r", "--pcap", type=Path, help="pcap file to read")
    capture.add_argument(
        "-c",
        "--count",
        type=_positive_int,
        default=0,
        help="live capture: stop after N packets (default: unlimited)",
    )
    capture.add_argument(
        "-t",
        "--duration",
        type=_positive_int,
        help="live capture: stop after N seconds",
    )
    capture.add_argument(
        "-f",
        "--filter",
        dest="bpf_filter",
        help='live capture: BPF filter, e.g. "tcp or udp"',
    )

    stats = commands.add_parser("stats", help="show traffic statistics")
    stats.add_argument(
        "-s",
        "--session",
        type=int,
        help="session id (default: all sessions)",
    )

    commands.add_parser("sessions", help="list capture sessions")
    return parser


def _validate_capture_options(args: argparse.Namespace) -> None:
    """Rejeita opções de captura ao vivo quando a origem é um arquivo .pcap."""
    if args.command != "capture" or args.pcap is None:
        return

    invalid = []
    if args.count:
        invalid.append("--count")
    if args.duration is not None:
        invalid.append("--duration")
    if args.bpf_filter is not None:
        invalid.append("--filter")

    if invalid:
        options = ", ".join(invalid)
        raise ValueError(f"{options} can only be used with --iface.")


def run_capture(args: argparse.Namespace, storage: Storage) -> CaptureResult:
    """Escolhe a fonte de pacotes conforme a opção informada."""
    batch_size = config.get_batch_size()

    if args.pcap:
        return read_pcap(storage, args.pcap, batch_size)
    return capture_live(
        storage,
        interface=args.iface,
        count=args.count,
        duration=args.duration,
        bpf_filter=args.bpf_filter,
        batch_size=batch_size,
    )


def command_capture(args: argparse.Namespace, storage: Storage) -> None:
    """Executa a captura e, ao final, exibe as estatísticas da sessão."""
    result = run_capture(args, storage)
    logger.info(
        "Session %d finished: %d packets stored, %d non-IP packets ignored.",
        result.session_id,
        result.packets_stored,
        result.packets_ignored,
    )
    render_stats(console, compute_stats(storage.connection, result.session_id))


def command_stats(args: argparse.Namespace, storage: Storage) -> None:
    """Exibe as estatísticas de uma sessão ou, sem --session, de todas."""
    # Sessão inexistente vira erro, não tabelas vazias (que pareceriam "sem tráfego").
    if args.session is not None and not session_exists(
        storage.connection, args.session
    ):
        raise ValueError(f"Session {args.session} not found.")
    render_stats(console, compute_stats(storage.connection, args.session))


def command_sessions(args: argparse.Namespace, storage: Storage) -> None:
    """Lista as sessões de captura registradas no banco."""
    render_sessions(console, list_sessions(storage.connection))


COMMANDS = {
    "capture": command_capture,
    "stats": command_stats,
    "sessions": command_sessions,
}


def main(argv: list[str] | None = None) -> int:
    """Executa o comando e retorna 0 (sucesso) ou 1 (erro tratado).

    argv permite chamar a aplicação a partir dos testes.
    """
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
    args = build_parser().parse_args(argv)

    try:
        _validate_capture_options(args)
        with Storage(args.db) as storage:
            COMMANDS[args.command](args, storage)
    except (FileNotFoundError, ValueError, PermissionError, Scapy_Exception) as error:
        logger.error(error)
        return 1
    return 0

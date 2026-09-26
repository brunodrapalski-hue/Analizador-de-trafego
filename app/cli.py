"""Command-line interface."""

import argparse
import logging
from pathlib import Path

from scapy.error import Scapy_Exception

from app import config
from app.capture import CaptureResult, capture_live, read_pcap
from app.storage import Storage

logger = logging.getLogger(__name__)


def build_parser() -> argparse.ArgumentParser:
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
        type=int,
        default=0,
        help="live capture: stop after N packets (default: unlimited)",
    )
    capture.add_argument(
        "-t",
        "--duration",
        type=int,
        help="live capture: stop after N seconds",
    )
    capture.add_argument(
        "-f",
        "--filter",
        dest="bpf_filter",
        help='live capture: BPF filter, e.g. "tcp or udp"',
    )
    return parser


def run_capture(args: argparse.Namespace, storage: Storage) -> CaptureResult:
    if args.pcap:
        return read_pcap(storage, args.pcap, config.BATCH_SIZE)
    return capture_live(
        storage,
        interface=args.iface,
        count=args.count,
        duration=args.duration,
        bpf_filter=args.bpf_filter,
        batch_size=config.BATCH_SIZE,
    )


def main(argv: list[str] | None = None) -> int:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
    args = build_parser().parse_args(argv)

    try:
        with Storage(args.db) as storage:
            result = run_capture(args, storage)
    except (FileNotFoundError, ValueError, PermissionError, Scapy_Exception) as error:
        logger.error(error)
        return 1

    logger.info(
        "Session %d finished: %d packets stored, %d non-IP packets ignored.",
        result.session_id,
        result.packets_stored,
        result.packets_ignored,
    )
    return 0

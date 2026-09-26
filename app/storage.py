"""Schema e escrita no SQLite: sessões de captura e pacotes.

As consultas de estatística ficam em stats.py. Modelo em docs/banco-de-dados.md.
"""

import sqlite3
from collections.abc import Iterable
from datetime import UTC, datetime
from pathlib import Path

from app.parser import PacketRecord

# IF NOT EXISTS: cria na primeira execução e preserva dados existentes.
# Os índices seguem os filtros e agrupamentos de stats.py.
SCHEMA = """
CREATE TABLE IF NOT EXISTS capture_sessions (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    source          TEXT    NOT NULL,
    bpf_filter      TEXT,
    started_at      TEXT    NOT NULL,
    finished_at     TEXT,
    packets_stored  INTEGER NOT NULL DEFAULT 0,
    packets_ignored INTEGER NOT NULL DEFAULT 0
);

CREATE TABLE IF NOT EXISTS packets (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id   INTEGER NOT NULL REFERENCES capture_sessions(id),
    captured_at  TEXT    NOT NULL,
    ip_version   INTEGER NOT NULL CHECK (ip_version IN (4, 6)),
    src_ip       TEXT    NOT NULL,
    dst_ip       TEXT    NOT NULL,
    protocol     TEXT    NOT NULL,
    protocol_num INTEGER NOT NULL,
    length       INTEGER NOT NULL CHECK (length >= 0)
);

CREATE INDEX IF NOT EXISTS idx_packets_session  ON packets(session_id);
CREATE INDEX IF NOT EXISTS idx_packets_protocol ON packets(protocol);
CREATE INDEX IF NOT EXISTS idx_packets_src_ip   ON packets(src_ip);
CREATE INDEX IF NOT EXISTS idx_packets_dst_ip   ON packets(dst_ip);
"""

INSERT_PACKET = """
INSERT INTO packets (
    session_id, captured_at, ip_version, src_ip, dst_ip,
    protocol, protocol_num, length
) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
"""


def utc_now() -> str:
    """Retorna o horário atual em UTC no formato ISO 8601.

    Exemplo: 2026-09-25T12:00:00+00:00
    """
    return datetime.now(UTC).isoformat(timespec="seconds")


class Storage:
    """Sessões e pacotes no SQLite.

    Use com "with": a conexão é fechada ao sair do bloco, inclusive em exceção.
    """

    def __init__(self, db_path: Path) -> None:
        # Cria o diretório do banco se não existir (ex.: clone sem data/).
        db_path.parent.mkdir(parents=True, exist_ok=True)
        self.connection = sqlite3.connect(db_path)
        # No SQLite a verificação de chave estrangeira vem desligada por
        # padrão; ela precisa ser ativada a cada conexão.
        self.connection.execute("PRAGMA foreign_keys = ON")
        self.connection.executescript(SCHEMA)

    def start_session(self, source: str, bpf_filter: str | None = None) -> int:
        """Insere a sessão (origem, filtro, início em UTC) e retorna o id.

        Fim e contadores são gravados por finish_session.
        """
        with self.connection:
            cursor = self.connection.execute(
                "INSERT INTO capture_sessions (source, bpf_filter, started_at) "
                "VALUES (?, ?, ?)",
                (source, bpf_filter, utc_now()),
            )
        return cursor.lastrowid

    def insert_packets(self, session_id: int, records: Iterable[PacketRecord]) -> int:
        """Grava os registros em uma única transação e retorna a quantidade enviada.

        Em erro, nenhum registro do lote é gravado.
        """
        rows = [
            (
                session_id,
                record.captured_at.isoformat(),
                record.ip_version,
                record.src_ip,
                record.dst_ip,
                record.protocol,
                record.protocol_num,
                record.length,
            )
            for record in records
        ]
        # Commit ao sair do bloco, rollback em exceção. Não fecha a conexão.
        with self.connection:
            self.connection.executemany(INSERT_PACKET, rows)
        return len(rows)

    def finish_session(
        self, session_id: int, packets_stored: int, packets_ignored: int
    ) -> None:
        """Registra o fim (UTC) e os contadores da sessão.

        packets_ignored = pacotes sem IP descartados pelo parser.
        """
        with self.connection:
            self.connection.execute(
                "UPDATE capture_sessions "
                "SET finished_at = ?, packets_stored = ?, packets_ignored = ? "
                "WHERE id = ?",
                (utc_now(), packets_stored, packets_ignored, session_id),
            )

    def close(self) -> None:
        self.connection.close()

    def __enter__(self) -> "Storage":
        return self

    def __exit__(self, *exc_info) -> None:
        self.close()

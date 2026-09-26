"""Configuração por variáveis de ambiente, com valores padrão que dispensam ajuste."""

import os
from pathlib import Path

# Relativo ao diretório de trabalho (/app no container), onde data/ é um volume.
DB_PATH = Path(os.environ.get("TRAFFIC_DB_PATH", "data/traffic.db"))


def get_batch_size() -> int:
    """Retorna o tamanho do lote configurado por ambiente."""
    raw_value = os.environ.get("TRAFFIC_BATCH_SIZE", "100")

    try:
        batch_size = int(raw_value)
    except ValueError:
        raise ValueError(
            "TRAFFIC_BATCH_SIZE must be an integer greater than zero."
        ) from None

    if batch_size <= 0:
        raise ValueError("TRAFFIC_BATCH_SIZE must be greater than zero.")

    return batch_size

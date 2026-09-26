"""Application settings, overridable through environment variables."""

import os
from pathlib import Path

DB_PATH = Path(os.environ.get("TRAFFIC_DB_PATH", "data/traffic.db"))
BATCH_SIZE = int(os.environ.get("TRAFFIC_BATCH_SIZE", "100"))

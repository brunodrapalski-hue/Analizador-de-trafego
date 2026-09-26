FROM python:3.13-slim AS base

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

# tcpdump brings libpcap, used by Scapy to compile BPF capture filters
RUN apt-get update \
    && apt-get install -y --no-install-recommends tcpdump \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app/ ./app/

# Test image: base + dev tools, tests, sample data and quality script
FROM base AS test
COPY requirements-dev.txt pyproject.toml ./
RUN pip install --no-cache-dir -r requirements-dev.txt
COPY tests/ ./tests/
COPY samples/ ./samples/
COPY scripts/ ./scripts/
ENTRYPOINT ["python", "-m", "pytest", "-v"]

# Runtime image (default). pip is only needed at build time: removing it
# reduces the attack surface (it vendors msgpack and setuptools code).
FROM base AS runtime
RUN pip uninstall -y pip
ENTRYPOINT ["python", "-m", "app"]

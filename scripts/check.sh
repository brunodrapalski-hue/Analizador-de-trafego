#!/bin/sh
# Portão de qualidade e segurança: executa as cinco verificações em sequência.
# Qualquer falha interrompe o script (set -e) — localmente e no CI.
# Uso: docker compose run --rm --build quality
set -e

echo "==> [1/5] Lint (ruff)"
ruff check app tests

echo "==> [2/5] Formatting (ruff)"
ruff format --check app tests

# Testes automatizados, incluindo a validação com samples/demo.pcap.
echo "==> [3/5] Tests (pytest)"
python -m pytest -v

echo "==> [4/5] Static security analysis (bandit)"
bandit -r app

# Vulnerabilidades conhecidas nas bibliotecas de produção.
echo "==> [5/5] Dependency vulnerabilities (pip-audit)"
pip-audit -r requirements.txt

echo "==> All checks passed."

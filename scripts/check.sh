#!/bin/sh
# Quality and security gate: lint, format, tests, SAST and dependency audit.
# Runs inside the test image: docker compose run --rm --build quality
set -e

echo "==> [1/5] Lint (ruff)"
ruff check app tests

echo "==> [2/5] Formatting (ruff)"
ruff format --check app tests

echo "==> [3/5] Tests (pytest)"
python -m pytest -v

echo "==> [4/5] Static security analysis (bandit)"
bandit -r app

echo "==> [5/5] Dependency vulnerabilities (pip-audit)"
pip-audit -r requirements.txt

echo "==> All checks passed."

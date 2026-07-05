#!/usr/bin/env bash
set -euo pipefail

cd /workspaces/salesperson

pip install --upgrade pip
pip install -r requirements-dev.txt

python -m unittest discover -s tests -v

echo ""
echo "Dev container ready."
echo "  make serve   — run platform API on :8000"
echo "  make test    — run unit tests"
echo "  make docs    — preview GitHub Pages site on :8080"
echo "  make deploy  — build and run production container"

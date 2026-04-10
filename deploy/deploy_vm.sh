#!/usr/bin/env bash
set -euo pipefail

APP_DIR="${APP_DIR:-/var/www/rag-portal}"
PYTHON_BIN="${PYTHON_BIN:-python3}"

cd "$APP_DIR"

if ! command -v "$PYTHON_BIN" >/dev/null 2>&1; then
  echo "python3 not found. Install: sudo apt install -y python3 python3-venv python3-pip"
  exit 1
fi

if [[ ! -d ".venv" ]]; then
  "$PYTHON_BIN" -m venv .venv
fi

source .venv/bin/activate
python -m pip install --upgrade pip >/dev/null
pip install -r requirements.txt

python manage.py migrate --noinput
python manage.py collectstatic --noinput
python manage.py setup_search_index

# Restart service if installed; otherwise run a hint.
if command -v systemctl >/dev/null 2>&1 && systemctl list-unit-files | grep -q '^rag-portal\.service'; then
  sudo systemctl restart rag-portal
  sudo systemctl restart nginx || true
  echo "Deployed and restarted rag-portal."
else
  echo "Deployment done. Install systemd unit + nginx to run as a service."
  echo "See deploy/gunicorn.service.example and deploy/nginx.conf.example"
fi


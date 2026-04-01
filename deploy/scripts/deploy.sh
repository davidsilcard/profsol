#!/usr/bin/env bash
set -euo pipefail

APP_DIR="/srv/profsol/current"

cd "$APP_DIR"

export UV_CACHE_DIR="$APP_DIR/.uv-cache"
export DJANGO_SETTINGS_MODULE="config.settings.production"

uv sync --frozen
uv run python manage.py migrate
uv run python manage.py collectstatic --noinput
systemctl restart profsol

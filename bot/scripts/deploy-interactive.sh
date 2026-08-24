#!/usr/bin/env bash
# Деплой с запросом пароля root (пароль не сохраняется на диск)
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
DEPLOY_CFG="$ROOT/.deploy.local"

if [[ ! -f "$DEPLOY_CFG" ]]; then
  cp "$ROOT/.deploy.local.example" "$DEPLOY_CFG"
fi

# shellcheck disable=SC1090
source "$DEPLOY_CFG"

if [[ -z "${VPS_PASSWORD:-}" ]]; then
  read -rsp "Пароль root@${VPS_HOST:-VPS}: " VPS_PASSWORD
  echo
  export VPS_PASSWORD
fi

exec "$ROOT/scripts/deploy.sh"

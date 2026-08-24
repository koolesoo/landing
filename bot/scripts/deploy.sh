#!/usr/bin/env bash
# Деплой бота на VPS. Секреты не коммитятся — только локальный .env и .deploy.local
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
DEPLOY_CFG="$ROOT/.deploy.local"

if [[ ! -f "$DEPLOY_CFG" ]]; then
  echo "Создай $DEPLOY_CFG (см. .deploy.local.example)" >&2
  exit 1
fi

# shellcheck disable=SC1090
source "$DEPLOY_CFG"

: "${VPS_HOST:?VPS_HOST не задан в .deploy.local}"
VPS_USER="${VPS_USER:-root}"
REMOTE_DIR="${REMOTE_DIR:-/opt/growcareer-bot}"

if [[ ! -f "$ROOT/.env" ]]; then
  echo "Нет $ROOT/.env" >&2
  exit 1
fi

SSH_OPTS=(-o StrictHostKeyChecking=accept-new -o ConnectTimeout=15)
RSYNC_SSH="ssh ${SSH_OPTS[*]}"

run_ssh() {
  if [[ -n "${VPS_PASSWORD:-}" ]] && command -v sshpass >/dev/null 2>&1; then
    sshpass -p "$VPS_PASSWORD" ssh "${SSH_OPTS[@]}" "$VPS_USER@$VPS_HOST" "$@"
  else
    ssh "${SSH_OPTS[@]}" "$VPS_USER@$VPS_HOST" "$@"
  fi
}

run_rsync() {
  if [[ -n "${VPS_PASSWORD:-}" ]] && command -v sshpass >/dev/null 2>&1; then
    sshpass -p "$VPS_PASSWORD" rsync -az --delete \
      -e "ssh ${SSH_OPTS[*]}" \
      "$@"
  else
    rsync -az --delete \
      -e "$RSYNC_SSH" \
      "$@"
  fi
}

echo "→ Подготовка сервера..."
run_ssh "apt-get update -qq && apt-get install -y -qq python3 python3-venv python3-pip rsync >/dev/null && mkdir -p '$REMOTE_DIR/data'"

echo "→ Загрузка кода (без .env и data/)..."
run_rsync \
  --exclude '.env' \
  --exclude '.deploy.local' \
  --exclude 'data/' \
  --exclude '.venv/' \
  --exclude '__pycache__/' \
  "$ROOT/" "$VPS_USER@$VPS_HOST:$REMOTE_DIR/"

echo "→ Загрузка .env (права 600)..."
if [[ -n "${VPS_PASSWORD:-}" ]] && command -v sshpass >/dev/null 2>&1; then
  sshpass -p "$VPS_PASSWORD" scp "${SSH_OPTS[@]}" "$ROOT/.env" "$VPS_USER@$VPS_HOST:$REMOTE_DIR/.env"
else
  scp "${SSH_OPTS[@]}" "$ROOT/.env" "$VPS_USER@$VPS_HOST:$REMOTE_DIR/.env"
fi
run_ssh "chmod 600 '$REMOTE_DIR/.env'"

echo "→ Установка зависимостей и systemd..."
run_ssh "bash -s" <<REMOTE
set -euo pipefail
cd '$REMOTE_DIR'
python3 -m venv .venv
.venv/bin/pip install -q -r requirements.txt
install -m 644 growcareer-bot.service /etc/systemd/system/growcareer-bot.service
systemctl daemon-reload
systemctl enable growcareer-bot
systemctl restart growcareer-bot
sleep 2
systemctl is-active --quiet growcareer-bot
REMOTE

echo "→ UFW: закрываем лишние порты (если ufw установлен)..."
run_ssh "command -v ufw >/dev/null && ufw allow OpenSSH && ufw --force enable || true"

echo "✅ Бот задеплоен на $VPS_HOST"
run_ssh "systemctl status growcareer-bot --no-pager -l | head -15"

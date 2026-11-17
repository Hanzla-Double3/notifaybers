#!/usr/bin/env bash
# Deploys the current master branch to your server and rebuilds the container.
# Usage: ./scripts/deploy.sh
#
# Settings come from the environment or from a git-ignored file named .deploy.env
# in the repo root (see .deploy.env.example):
#   NOTIFAYBERS_DEPLOY_HOST   ssh target, e.g. root@203.0.113.10
#   NOTIFAYBERS_DOMAIN        public URL, e.g. https://notify.example.com
#   NOTIFAYBERS_DEPLOY_KEY    (optional) ssh private key path
#   NOTIFAYBERS_REMOTE_DIR    (optional) checkout on the server, default /opt/notifaybers
set -euo pipefail

cd "$(dirname "$0")/.."
if [ -f .deploy.env ]; then
  # shellcheck disable=SC1091
  set -a; . ./.deploy.env; set +a
fi

: "${NOTIFAYBERS_DEPLOY_HOST:?Set NOTIFAYBERS_DEPLOY_HOST (see .deploy.env.example)}"
: "${NOTIFAYBERS_DOMAIN:?Set NOTIFAYBERS_DOMAIN (see .deploy.env.example)}"
HOST="$NOTIFAYBERS_DEPLOY_HOST"
DOMAIN="${NOTIFAYBERS_DOMAIN%/}"
REMOTE_DIR="${NOTIFAYBERS_REMOTE_DIR:-/opt/notifaybers}"
SSH_ARGS=()
if [ -n "${NOTIFAYBERS_DEPLOY_KEY:-}" ]; then
  SSH_ARGS=(-i "$NOTIFAYBERS_DEPLOY_KEY")
fi

echo "==> Deploying notifaybers to $HOST"

ssh "${SSH_ARGS[@]}" "$HOST" 'bash -s' -- "$REMOTE_DIR" << 'REMOTE'
set -euo pipefail
cd "$1"
git fetch origin -q
git reset --hard origin/master
echo "==> Deployed commit: $(git log --oneline -1)"
docker compose up -d --build
REMOTE

echo "==> Health check..."
sleep 10
status=$(curl -s -o /dev/null -w "%{http_code}" "$DOMAIN/login")
if [ "$status" = "200" ]; then
  echo "==> OK: $DOMAIN/login returned 200"
else
  echo "==> WARNING: $DOMAIN/login returned $status"
  exit 1
fi

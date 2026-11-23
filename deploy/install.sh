#!/usr/bin/env bash
# AI-orchestration single-host installer.
# Usage: sudo ./deploy/install.sh [target-dir]   (default /opt/ai-orchestration)
# Idempotent: safe to re-run after `git pull` to upgrade.
set -euo pipefail

SRC=$(cd "$(dirname "$0")/.." && pwd)
TARGET=${1:-/opt/ai-orchestration}
UNITS=(mcp-registry mcp-requirements-engineer mcp-implementation-engineer
       mcp-qa-engineer mcp-security-reviewer mcp-devops-release-engineer
       mcp-team-management mcp-it-lead mcp-web-ui-backend mcp-web-ui-frontend
       mcp-deployment-warden mcp-retro-observer)

log() { echo "[install] $*"; }

for c in python3 node npm psql git nginx; do
  command -v "$c" >/dev/null || { echo "MISSING: $c - install it first (see DEPLOY.md)"; exit 1; }
done

log "syncing $SRC -> $TARGET"
mkdir -p "$TARGET"
rsync -a --delete --exclude .git --exclude venv --exclude .venv \
      --exclude node_modules --exclude .env "$SRC/" "$TARGET/"

[ -f "$TARGET/.env" ] || { cp "$TARGET/.env.example" "$TARGET/.env"
  echo ">>> EDIT $TARGET/.env (POSTGRES_PASSWORD, LLM_PROVIDER_URL, LLM_MODEL, DEPLOYMENT_HOST...) then re-run"; exit 0; }
# shellcheck disable=SC1091
set -a; . "$TARGET/.env"; set +a

log "python venvs (global + per-server where present)"
python3 -m venv "$TARGET/.venv"
"$TARGET/.venv/bin/pip" -q install -U pip
for r in "$TARGET"/*/requirements.txt "$TARGET/it-lead-mcp-server/web-ui/backend/requirements.txt"; do
  [ -f "$r" ] && "$TARGET/.venv/bin/pip" -q install -r "$r"
done
"$TARGET/.venv/bin/pip" -q install fastapi uvicorn "psycopg2-binary" requests pydantic httpx
for d in "$TARGET"/*/; do
  [ -f "$d/requirements.txt" ] || continue
  [ -d "$d/venv" ] || python3 -m venv "$d/venv"
  "$d/venv/bin/pip" -q install -U pip
  "$d/venv/bin/pip" -q install -r "$d/requirements.txt"
done

log "web-ui frontend"
(cd "$TARGET/it-lead-mcp-server/web-ui/frontend" && npm ci --silent)

log "database"
PG() { if command -v sudo >/dev/null; then sudo -u postgres "$@"; else su postgres -c "$(printf '%q ' "$@")"; fi; }
PG psql -tAc "SELECT 1 FROM pg_roles WHERE rolname='${POSTGRES_USER:-postgres}'" | grep -q 1 || \
  PG psql -c "CREATE USER ${POSTGRES_USER:-postgres} PASSWORD '${POSTGRES_PASSWORD:-postgres}'"
PG psql -tAc "SELECT 1 FROM pg_database WHERE datname='${POSTGRES_DB:-mcp_registry}'" | grep -q 1 || \
  PG createdb "${POSTGRES_DB:-mcp_registry}"
# tables are created by the services themselves (CREATE TABLE IF NOT EXISTS)

log "runtime dirs + nginx edge"
mkdir -p "${SHOTS_DIR:-/var/www/shots}" /etc/nginx/mcp-deployments
cp "$TARGET/deploy/nginx-edge.conf" /etc/nginx/conf.d/mcp-deployments.conf
nginx -t && systemctl reload nginx

log "systemd units (paths rewritten to $TARGET)"
for u in "${UNITS[@]}"; do
  for ext in service timer; do
    [ -f "$TARGET/systemd/$u.$ext" ] || continue
    sed -e "s#/root/qwen/base#$TARGET#g" \
        -e "s#\bpython -m#$TARGET/.venv/bin/python -m#g" \
        -e "s#source venv/bin/activate#source $TARGET/.venv/bin/activate#" \
        "$TARGET/systemd/$u.$ext" > "/etc/systemd/system/$u.$ext"
  done
done
# opencode serve is optional (needed for the opencode coder path)
if [ -x "$HOME/.opencode/bin/opencode" ]; then
  sed "s#/root/qwen/base#$TARGET#g" "$TARGET/systemd/mcp-opencode-serve.service" \
    > /etc/systemd/system/mcp-opencode-serve.service
  UNITS+=(mcp-opencode-serve)
else
  log "NOTE: opencode CLI not found - coder will fall back to per-file generation"
fi
systemctl daemon-reload

log "starting services"
for u in "${UNITS[@]}"; do systemctl enable --now "$u" 2>/dev/null && log "up: $u"; done
systemctl enable --now mcp-retro-observer.timer 2>/dev/null || true

log "smoke"
sleep 8
curl -sf "http://127.0.0.1:${IT_LEAD_PORT:-3061}/mcp" -X POST -H 'Content-Type: application/json' \
  -d '{"jsonrpc":"2.0","id":1,"method":"tools/list"}' >/dev/null && log "IT Lead: OK"
curl -sf "http://127.0.0.1:${WEB_UI_BACKEND_PORT:-8000}/api/tasks" >/dev/null && log "web-ui: OK"
log "dashboard: http://${DEPLOYMENT_HOST}:$(( ${WEB_UI_FRONTEND_PORT:-5173} ))  (add TLS + /root/certs for system notifications)"

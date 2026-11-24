#!/usr/bin/env bash
# AI-orchestration single-host installer.
# Usage: sudo ./deploy/install.sh [target-dir]   (default /opt/ai-orchestration)
# Idempotent: safe to re-run after `git pull` to upgrade.
set -euo pipefail
export PATH="$PATH:/usr/sbin:/sbin"

SRC=$(cd "$(dirname "$0")/.." && pwd)
TARGET=${1:-/opt/ai-orchestration}
UNITS=(mcp-registry mcp-requirements-engineer mcp-implementation-engineer
       mcp-qa-engineer mcp-security-reviewer mcp-devops-release-engineer
       mcp-team-management mcp-it-lead mcp-web-ui-backend mcp-web-ui-frontend
       mcp-deployment-warden mcp-retro-observer
       mcp-documentation-engineer)

log() { echo "[install] $*"; }

log "syncing $SRC -> $TARGET"
mkdir -p "$TARGET"
# data/ and logs/ are runtime state - never let --delete touch them
rsync -a --delete --exclude .git --exclude venv --exclude .venv \
      --exclude node_modules --exclude .env --exclude data --exclude logs "$SRC/" "$TARGET/"

[ -f "$TARGET/.env" ] || { cp "$TARGET/.env.example" "$TARGET/.env"
  echo ">>> EDIT $TARGET/.env (POSTGRES_PASSWORD, LLM_PROVIDER_URL, LLM_MODEL, DEPLOYMENT_HOST...) then re-run"; exit 0; }
# shellcheck disable=SC1091
set -a; . "$TARGET/.env"; set +a

# psql is only required when the postgres backend is enabled (USE_POSTGRES=false
# falls back to sqlite, see db_compat)
USE_PG=${USE_POSTGRES:-true}
for c in python3 node npm git nginx; do
  command -v "$c" >/dev/null || { echo "MISSING: $c - install it first (see DEPLOY.md)"; exit 1; }
done
if [ "$USE_PG" != "false" ]; then
  command -v psql >/dev/null || { echo "MISSING: psql - install postgresql (or set USE_POSTGRES=false in $TARGET/.env to use sqlite)"; exit 1; }
fi

log "python venvs (global + per-server where present)"
python3 -m venv "$TARGET/.venv"
"$TARGET/.venv/bin/pip" -q install -U pip
while IFS= read -r r; do
  "$TARGET/.venv/bin/pip" -q install -r "$r"
done < <(find "$TARGET" -maxdepth 3 -name requirements.txt \
           -not -path "*/venv/*" -not -path "*/.venv/*" -not -path "*/node_modules/*")
"$TARGET/.venv/bin/pip" -q install fastapi uvicorn "psycopg2-binary" requests pydantic httpx
# per-server venvs: requirements.txt may sit one or two levels deep
# (requirements-engineer-mcp-server/requirement-engineer-mcp-server/...)
while IFS= read -r r; do
  d=$(dirname "$r")
  [ -d "$d/venv" ] || python3 -m venv "$d/venv"
  "$d/venv/bin/pip" -q install -U pip
  "$d/venv/bin/pip" -q install -r "$r"
done < <(find "$TARGET" -maxdepth 3 -name requirements.txt \
           -not -path "*/venv/*" -not -path "*/.venv/*" -not -path "*/node_modules/*")

log "web-ui frontend"
(cd "$TARGET/it-lead-mcp-server/web-ui/frontend" && npm ci --silent)

log "database"
if [ "$USE_PG" != "false" ]; then
PG() { if command -v sudo >/dev/null; then sudo -u postgres "$@"; else su postgres -c "$(printf '%q ' "$@")"; fi; }
PG psql -tAc "SELECT 1 FROM pg_roles WHERE rolname='${POSTGRES_USER:-postgres}'" | grep -q 1 || \
  PG psql -c "CREATE USER ${POSTGRES_USER:-postgres} PASSWORD '${POSTGRES_PASSWORD:-postgres}'"
PG psql -tAc "SELECT 1 FROM pg_database WHERE datname='${POSTGRES_DB:-mcp_registry}'" | grep -q 1 || \
  PG createdb "${POSTGRES_DB:-mcp_registry}"
PG psql -c "ALTER USER ${POSTGRES_USER:-postgres} PASSWORD '${POSTGRES_PASSWORD:-postgres}'" >/dev/null
# tables are created by the services themselves (CREATE TABLE IF NOT EXISTS)
else
log "USE_POSTGRES=false - sqlite fallback (db_compat), skipping postgres setup"
fi

log "runtime dirs + nginx edge"
mkdir -p "${SHOTS_DIR:-/var/www/shots}" /etc/nginx/mcp-deployments
cp "$TARGET/deploy/nginx-edge.conf" /etc/nginx/conf.d/mcp-deployments.conf
nginx -t && systemctl reload nginx

log "systemd units (paths rewritten to $TARGET)"
# postgres args are injected from the unit's own environment ($POSTGRES_*,
# already defaulted via Environment= lines). A bare ${VAR:-*} default would
# glob-expand if a .env value is empty or contains shell metacharacters.
sed -i -E 's/--postgres-host \$\{POSTGRES_HOST:-[^}]*\}/--postgres-host $POSTGRES_HOST/; s/--postgres-port \$\{POSTGRES_PORT:-[^}]*\}/--postgres-port $POSTGRES_PORT/; s/--postgres-db \$\{POSTGRES_DB:-[^}]*\}/--postgres-db $POSTGRES_DB/; s/--postgres-user \$\{POSTGRES_USER:-[^}]*\}/--postgres-user $POSTGRES_USER/; s/--postgres-password \$\{POSTGRES_PASSWORD:-[^}]*\}/--postgres-password "$POSTGRES_PASSWORD"/' \
  "$TARGET"/systemd/*.service 2>/dev/null || true
# some VPS guests forbid mount namespaces (unshare EPERM) - strip sandbox
# directives that force one, otherwise units die with status=226/NAMESPACE
for u in "${UNITS[@]}"; do
  for ext in service timer; do
    [ -f "$TARGET/systemd/$u.$ext" ] || continue
    sed -e "s#/root/qwen/base#$TARGET#g" \
        -e "s#\bpython -m#$TARGET/.venv/bin/python -m#g" \
        -e "s#\bpython -c#$TARGET/.venv/bin/python -c#g" \
        -e "s#source venv/bin/activate#source $TARGET/.venv/bin/activate#" \
        -e "/^\(ReadWritePaths\|ProtectSystem\|ProtectHome\|PrivateTmp\|PrivateDevices\|ProtectKernelTunables\|ProtectControlGroups\|ReadOnlyPaths\|InaccessiblePaths\)=/d" \
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
systemctl enable --now mcp-retro-observer.timer mcp-deployment-warden.timer 2>/dev/null || true

log "smoke"
sleep 8
curl -sf "http://127.0.0.1:${IT_LEAD_PORT:-3061}/mcp" -X POST -H 'Content-Type: application/json' \
  -d '{"jsonrpc":"2.0","id":1,"method":"tools/list"}' >/dev/null && log "IT Lead: OK"
curl -sf "http://127.0.0.1:${WEB_UI_BACKEND_PORT:-8000}/api/tasks" >/dev/null && log "web-ui: OK"
log "dashboard: http://${DEPLOYMENT_HOST}:$(( ${WEB_UI_FRONTEND_PORT:-5173} ))  (add TLS + /root/certs for system notifications)"

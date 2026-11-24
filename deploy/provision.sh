#!/usr/bin/env bash
# AI-orchestration one-command host bootstrap (Debian 12 / Ubuntu 24, as root).
# Installs OS deps -> opencode CLI + config -> ssh keys -> repo -> .env ->
# deploy/install.sh -> self-E2E task through the pipeline. Idempotent.
#
#   LLM_PROVIDER_URL=http://1.2.3.4:8081/v1/chat/completions \
#   LLM_MODEL=my-model \
#   MCP_GIT_REPO_URL=ssh://user@host/home/user/mcp-results.git \
#   bash deploy/provision.sh
#
# Env (defaults in parentheses):
#   REPO_URL/REPO_REF          repo to install (in40/ai-orchestration @ v0.5.11)
#   ORCH_DIR                   install target (/opt/ai-orchestration)
#   DEPLOYMENT_HOST            public IP/DNS (first host IP)
#   USE_POSTGRES               true|false (true; false = sqlite fallback)
#   POSTGRES_HOST/PORT/DB/USER connection to PostgreSQL (defaults 127.0.0.1:5432
#                              /mcp_registry/postgres). A non-local host means
#                              an EXTERNAL cluster: no local server is
#                              installed, role/db must already exist, and
#                              POSTGRES_PASSWORD is REQUIRED.
#   POSTGRES_PASSWORD          generated when local; required when external
#   SECURE_SEARCH_URL          search MCP for opencode agents (optional)
#   OPENCODE_VERSION           pin opencode CLI (latest)
#   MCP_GIT_REPO_URL           artifacts repo: ssh url, git+ssh, or any path git
#                              understands (default: local bare repo at
#                              $ORCH_DIR/data/mcp-results.git - created here)
#   RESULTS_SSH_KEY_B64        base64 private key for a REMOTE results repo
#                              (only needed when MCP_GIT_REPO_URL points at
#                              another host over ssh)
set -euo pipefail
export DEBIAN_FRONTEND=noninteractive PATH="$PATH:/usr/sbin:/sbin"
log() { echo "[provision] $*"; }
[ "$(id -u)" = 0 ] || { echo "run as root"; exit 1; }

log "0/7 bootstrap: package manager + fetch tools"
# a virgin minimal image may have neither git nor curl - the installer must
# provide its own prerequisites (network comes from the distro mirror anyway)
if ! command -v git >/dev/null || ! command -v curl >/dev/null; then
  if command -v apt-get >/dev/null; then
    export DEBIAN_FRONTEND=noninteractive
    apt-get update -qq && apt-get install -y -qq ca-certificates curl git rsync >/dev/null
  elif command -v dnf >/dev/null; then dnf -y -q install curl git rsync >/dev/null
  elif command -v yum >/dev/null;  then yum -y -q install curl git rsync >/dev/null
  elif command -v apk >/dev/null;  then apk add --no-cache curl git rsync bash >/dev/null
  else echo "no supported package manager (apt/dnf/yum/apk) - install git+curl first"; exit 1; fi
fi

REPO_URL=${REPO_URL:-https://github.com/in40/ai-orchestration}
REPO_REF=${REPO_REF:-v0.5.11}
ORCH_DIR=${ORCH_DIR:-/opt/ai-orchestration}
SRC=${SRC:-/root/ai-orchestration}
USE_POSTGRES=${USE_POSTGRES:-true}
# Postgres connection details (defaults = local cluster, provisioned by us).
# A non-local POSTGRES_HOST means an EXTERNAL pre-existing cluster: we do not
# install a server and cannot create role/db (needs admin on that host) -
# pre-create role $POSTGRES_USER and db $POSTGRES_DB and set POSTGRES_PASSWORD.
POSTGRES_HOST=${POSTGRES_HOST:-127.0.0.1}
POSTGRES_PORT=${POSTGRES_PORT:-5432}
POSTGRES_DB=${POSTGRES_DB:-mcp_registry}
POSTGRES_USER=${POSTGRES_USER:-postgres}
PG_LOCAL=0
case "$POSTGRES_HOST" in 127.0.0.1|localhost|::1|"") PG_LOCAL=1;; esac
[ -n "$POSTGRES_HOST" ] || POSTGRES_HOST=127.0.0.1
DEPLOYMENT_HOST=${DEPLOYMENT_HOST:-$(hostname -I | awk '{print $1}')}
LLM_PROVIDER_URL=${LLM_PROVIDER_URL:-}
LLM_MODEL=${LLM_MODEL:-}
SECURE_SEARCH_URL=${SECURE_SEARCH_URL:-}
OPENCODE_BASE_URL=${OPENCODE_BASE_URL:-${LLM_PROVIDER_URL%/chat/completions}}

[ -n "$LLM_PROVIDER_URL" ] || log "WARN: LLM_PROVIDER_URL unset - services will not plan/build until .env is fixed"

log "1/7 apt packages"
PKGS="ca-certificates curl git rsync sudo openssl python3 python3-venv python-is-python3 build-essential nginx nodejs npm postgresql-client"
if command -v apt-get >/dev/null; then
apt-get update -qq
apt-get install -y -qq $PKGS >/dev/null
apt-get install -y -qq chromium >/dev/null 2>&1 || apt-get install -y -qq chromium-browser >/dev/null 2>&1 || log "WARN: chromium not found (visual gate disabled)"
command -v docker >/dev/null || { apt-get install -y -qq docker.io >/dev/null && systemctl enable --now docker; }
if [ "$USE_POSTGRES" != "false" ] && [ "$PG_LOCAL" = 1 ] && ! command -v psql >/dev/null; then
  apt-get install -y -qq postgresql >/dev/null && systemctl enable --now postgresql
elif [ "$USE_POSTGRES" != "false" ] && [ "$PG_LOCAL" = 0 ]; then
  log "external postgres at $POSTGRES_HOST:$POSTGRES_PORT - no local server will be installed"
fi
else
  log "WARN: no apt-get - skipping distro packages (install python3/node/nginx/docker manually)"
fi

log "2/7 opencode CLI"
if [ ! -x /root/.opencode/bin/opencode ]; then
  curl -fsSL https://opencode.ai/install | bash -s -- ${OPENCODE_VERSION:-}
fi
ln -sf /root/.opencode/bin/opencode /usr/local/bin/opencode
log "opencode $(opencode --version 2>/dev/null)"

log "3/7 ssh"
[ -f /root/.ssh/id_ed25519 ] || ssh-keygen -q -t ed25519 -N '' -C "orch-$(hostname)" -f /root/.ssh/id_ed25519
if [ -n "${RESULTS_SSH_KEY_B64:-}" ]; then
  printf '%s' "$RESULTS_SSH_KEY_B64" | base64 -d > /root/.ssh/id_results
  chmod 600 /root/.ssh/id_results
  printf 'Host *\n  IdentityFile /root/.ssh/id_results\n  StrictHostKeyChecking accept-new\n' > /root/.ssh/config
fi
git config --global --add safe.directory '*' 2>/dev/null || true

log "4/7 repo $REPO_REF"
if [ -d "$SRC/.git" ]; then git -C "$SRC" fetch -q origin && git -C "$SRC" checkout -q "$REPO_REF" && git -C "$SRC" pull -q origin "$REPO_REF"
elif [ -f "$SRC/deploy/provision.sh" ]; then log "source pre-seeded at $SRC (no .git) - using as-is"
else git clone -q -b "$REPO_REF" "$REPO_URL" "$SRC"; fi
mkdir -p /root/.config/opencode/agents
cp "$SRC"/opencode-agents/*.md /root/.config/opencode/agents/

log "5/7 opencode + orchestration config"
if [ -n "$OPENCODE_BASE_URL" ] && { [ ! -f /root/.config/opencode/opencode.json ] || [ "${PROVISION_FORCE_OC:-0}" = 1 ]; }; then
  cat > /root/.config/opencode/opencode.json <<EOF
{
  "\$schema": "https://opencode.ai/config.json",
  "provider": {
    "orch": {
      "npm": "@ai-sdk/openai-compatible",
      "name": "Orchestration LLM",
      "options": { "baseURL": "$OPENCODE_BASE_URL" },
      "models": { "$LLM_MODEL": { "name": "$LLM_MODEL",
        "limit": { "context": ${OPENCODE_CTX:-524288}, "output": ${OPENCODE_OUT:-65536} } } }
    }
  },
  "model": "orch/$LLM_MODEL",
  "small_model": "orch/$LLM_MODEL",
  "mcp": { "servers": {
    "secure-search": { "type": "remote", "url": "${SECURE_SEARCH_URL:-http://127.0.0.1:8100/mcp/mcp}", "codemode": false },
    "image-tools": { "type": "local", "command": ["python3", "$ORCH_DIR/image-tools/image_tools_mcp.py"], "codemode": false }
  } },
  "permission": { "lsp": "allow" }
}
EOF
fi
mkdir -p "$ORCH_DIR"
ensure_local_results_repo() {
  # No external artifact repo configured: keep results in a local bare repo on
  # this host. git clones/pushes local paths natively - no ssh, no keys.
  # data/ is excluded from install.sh's rsync --delete, so it survives upgrades.
  LOCAL_RESULTS=$ORCH_DIR/data/mcp-results.git
  mkdir -p "$ORCH_DIR/data"
  if [ ! -d "$LOCAL_RESULTS" ]; then
    git init -q --bare "$LOCAL_RESULTS"
    git -C "$LOCAL_RESULTS" symbolic-ref HEAD refs/heads/main
    # seed main with an empty commit: services clone/push 'main' explicitly,
    # and a clone of a truly empty repo has no branch to build on
    SEED=$(mktemp -d)
    git -C "$SEED" init -q -b main 2>/dev/null || { git -C "$SEED" init -q && git -C "$SEED" checkout -q -b main; }
    git -C "$SEED" -c user.email=orch@local -c user.name=provision commit -q --allow-empty -m "results repo"
    git -C "$SEED" push -q "$LOCAL_RESULTS" main
    rm -rf "$SEED"
  fi
  MCP_GIT_REPO_URL=$LOCAL_RESULTS
  log "results repo: local bare $LOCAL_RESULTS (set MCP_GIT_REPO_URL to use a shared one)"
}
if [ ! -f "$ORCH_DIR/.env" ] || [ "${PROVISION_FORCE_ENV:-0}" = 1 ]; then
  [ -n "${MCP_GIT_REPO_URL:-}" ] || ensure_local_results_repo
  if [ "$USE_POSTGRES" = "false" ]; then
    PG_PW=${POSTGRES_PASSWORD:-postgres}
  elif [ -n "${POSTGRES_PASSWORD:-}" ]; then
    PG_PW=$POSTGRES_PASSWORD
  elif [ "$PG_LOCAL" = 1 ]; then
    PG_PW=$(openssl rand -hex 12)
  else
    echo "FATAL: external POSTGRES_HOST=$POSTGRES_HOST requires POSTGRES_PASSWORD in env (the cluster is not ours to provision)"; exit 1
  fi
  OC_PW=$(openssl rand -hex 12)
  cat > "$ORCH_DIR/.env" <<EOF
BASE_DIR=$ORCH_DIR
DATA_DIR=$ORCH_DIR/data
DEPLOYMENT_HOST=$DEPLOYMENT_HOST
LLM_PROVIDER_URL=$LLM_PROVIDER_URL
LLM_MODEL=$LLM_MODEL
USE_POSTGRES=$USE_POSTGRES
POSTGRES_HOST=$POSTGRES_HOST
POSTGRES_PORT=$POSTGRES_PORT
POSTGRES_DB=$POSTGRES_DB
POSTGRES_USER=$POSTGRES_USER
POSTGRES_PASSWORD=${PG_PW}
MCP_GIT_REPO_URL=${MCP_GIT_REPO_URL:-}
SECURE_SEARCH_URL=${SECURE_SEARCH_URL:-}
HEADLESS_SHELL=$(command -v chromium || command -v chromium-browser || echo /usr/bin/chromium)
SHOTS_DIR=/var/www/shots
OPENCODE_SERVE_URL=http://127.0.0.1:4097
OPENCODE_PASSWORD=${OC_PW}
EOF
  chmod 600 "$ORCH_DIR/.env"
  log "wrote $ORCH_DIR/.env (PROVISION_FORCE_ENV=1 to regenerate)"
elif [ -z "${MCP_GIT_REPO_URL:-}" ] && grep -q '^MCP_GIT_REPO_URL=$' "$ORCH_DIR/.env"; then
  # existing .env predates the local fallback and has an empty url - wire it up
  ensure_local_results_repo
  sed -i "s#^MCP_GIT_REPO_URL=\$#MCP_GIT_REPO_URL=$LOCAL_RESULTS#" "$ORCH_DIR/.env"
  log "patched empty MCP_GIT_REPO_URL in existing .env -> $LOCAL_RESULTS"
fi

log "6/7 install.sh"
bash "$SRC/deploy/install.sh" "$ORCH_DIR"

log "7/7 self-E2E"
TID="provision-e2e-$(date +%s)"
log "task $TID: python script that prints a greeting"
curl -sf -m 60 -X POST "http://127.0.0.1:${WEB_UI_BACKEND_PORT:-8000}/api/tasks/assign" \
  -H 'Content-Type: application/json' \
  -d "{\"task_id\":\"$TID\",\"title\":\"provision self-test\",\"description\":\"python script that prints a greeting\",\"assignee\":\"IT Lead\",\"priority\":\"low\",\"context\":{}}" >/dev/null
for i in $(seq 1 60); do
  S=$(curl -s -m 10 "http://127.0.0.1:${WEB_UI_BACKEND_PORT:-8000}/api/tasks" | \
      python3 -c "import json,sys; print(next((t['status'] for t in json.load(sys.stdin) if t['id']=='$TID'),'?'))")
  log "$((i*20))s: $S"
  case "$S" in done) log "E2E PASS - dashboard: http://$DEPLOYMENT_HOST:5173"; exit 0;;
               failed|needs_revision) log "E2E $S - inspect dashboard/API"; exit 1;; esac
  sleep 20
done
log "E2E TIMEOUT"; exit 1

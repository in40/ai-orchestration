#!/usr/bin/env bash
# Example workstation-side launcher for deploy/provision.sh — copy it,
# fill in your own addresses, keep the real version OUT of git (it holds
# host addresses and points at a private key).
#
#   cp provision.lan.example.sh ~/my-provision.sh && edit it && chmod +x
#   ~/my-provision.sh root@target-host
set -e
T=${1:?ssh target, e.g. root@192.0.2.10}

# base64 of the private key allowed to push to the results repo (optional:
# without it provision.sh generates a key and prints the public half for
# you to authorize on the results server)
KEY_B64=$(base64 -w0 "$HOME/.ssh/orch_results_key")

# provision.sh itself must come from this repo's checkout
REPO_CHECKOUT=${REPO_CHECKOUT:-/path/to/ai-orchestration}

scp -q -o StrictHostKeyChecking=accept-new \
    "$REPO_CHECKOUT/deploy/provision.sh" "$T":/tmp/provision.sh

ssh -o StrictHostKeyChecking=accept-new "$T" "bash -s" <<OUTER
export REPO_REF=v0.5.11
export LLM_PROVIDER_URL=http://llm.example.internal:8081/v1/chat/completions
export LLM_MODEL=your-model-name
export USE_POSTGRES=false
export DEPLOYMENT_HOST=target.example.internal
export SECURE_SEARCH_URL=http://search.example.internal:8100/mcp/mcp   # optional
export MCP_GIT_REPO_URL=ssh://git@results.example.internal/home/git/mcp-results.git
export RESULTS_SSH_KEY_B64=$KEY_B64
bash /tmp/provision.sh
OUTER

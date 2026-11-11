# Improvement Backlog — MCP Orchestration System

Derived from E2E testing 2026-11-10 (flappy-bird + MCP-template tasks).
Sequenced: each phase unblocks the next. P0 items are prerequisites for trusting any pipeline output.

## Status 2026-11-10: P0 ✅ P1 ✅ P2 ✅ P3.1 ✅ | P3.2 deferred (QA gate covers correctness; review adds LLM cost, revisit when false-passes appear) | P4 open

## P5 — Planner/manifest hardening (2026-11-10, from task-1794332820841) ✅
- P5.1 manifest derivation: JSONL protocol (one {path,spec} per line), line-level
  error tolerance, 1 retry, legacy whole-JSON fallback — malformed JSON no longer
  kills fan-out
- P5.2 planner prompts: file_manifest instruction appended to ALL planning prompts
  (was only in general prompt); plan flagged manifest_needed when keywords match
  but LLM omitted it
- P5.3 workflow order: first forward honors workflow_sequence[0] when it is
  requirements-engineer (analysis step no longer skipped by the coding->impl rule);
  "ALL coding tasks MUST go to implementation-engineer" scoped to execution, not ordering
- Open: pass requirements-engineer spec output as context into coder call (handoff wiring)
- E2E: tmpl8 18-file package, QA passed in ~7min (2026-11-10) ✅

## P6 — Fan-out interface drift (from tmpl7, 2026-11-10) ✅
tmpl7: 8/8 files generated in ~9 min (per-step budgets work), validate passed,
smoke caught real ImportError: server.py imports register_default_tools that
service_handlers.py never defines. Independent per-file generation drifts on
cross-file contracts.
- P6.1 contract-first: manifest spec must pin exact exports/imports per file;
  inject the full interface contract (not just one-line specs) into every
  generate_file call
- P6.2 repair loop: on smoke ImportError, feed error + both files back to coder
  to regenerate the offending file (1 pass), then re-QA
- P6.3 (cheap option): prompt rule "prefer lazy imports inside functions so
  module import never fails on sibling gaps"

## P6.4 — Run-contract architecture ✅ (2026-11-11)
QA plan_run_contract (LLM reads README+entries -> install/run/cwd/env/kind/healthcheck,
heuristic fallback); contract-driven smoke (venv install, kind-based healthcheck,
startup tracebacks); IT Lead passes contract to DevOps; DevOps Dockerfile from
contract; repair loop handles import AND runtime errors (stderr window 1500,
bash for source-commands). Found via E2E: tmplA repair blind spot (truncated
stderr), tmplB 'source' under dash. E2E tmplC running with deploy flag.

## P6.5 — found in tmplC E2E (2026-11-11) ✅ impl 69dd89e, E2E pending

## P7 — tmplD lessons + team buildout (2026-11-11) ✅
- S1 generate_file try/except + raw-response logging (opaque {} failures)
- S2 3x retry w/ backoff + sequential second pass for failed files
- S3 requirements.txt/.env.example generated deterministically (no LLM)
- T1 coder patch_file(task_id,path,error): surgical repair; IT Lead repair
  now patches first, regenerates only if patch fails
- T2 QA conformance probe: tools/list must answer on MCP services
- T3 Security Reviewer agent :3073 (scan_artifact: eval/exec/shell=True/pickle/
  unsafe yaml/AWS keys/hardcoded secrets; high findings block deploy);
  IT Lead security gate between QA and deploy
- T4 deployment warden (systemd timer, 5min): running deployments re-checked,
  flipped to unhealthy on death/restart-loop
- T5 get_deployment_status already covers healthcheck; rollback deferred
  (no artifact versioning); QA retest = smoke_run w/ cached contract
- tmplD E2E pending (S fixes untested live)

## task-1794401907867 postmortem fixes ✅ (62e9f4a, 065f209)
requirements.txt: deterministic import-derivation (no LLM), deferred after code
wave; per-extension token budgets; repetitive-loop guard in continuations.

## T6 — requirements-spec handoff ✅ (c674dae)
prev_result flows through _handle_workflow_sequence into coder prompt
(as authoritative TECHNICAL SPECIFICATION, 4K cap). Fan-out path unaffected
(manifest already carries per-file specs).
- Contract non-determinism: plan_run_contract is an LLM call; smoke-time and
  deploy-time contracts can differ -> verdicts unstable. Fix: plan contract ONCE
  per task, store (task metadata or results repo run_contract.json), reuse everywhere.
- Generated-code quality: tmplC capabilities.py calls official mcp SDK API
  (server.list_tools) against the template's own Server class -> runtime crash
  that passed QA. Fix options: manifest spec rule "implement against stdlib only,
  do not mimic third-party SDK APIs", or add mcp SDK to requirements and use it for real.
- Deploy-time healthcheck: container crash-loop after successful QA is invisible
  to the pipeline. Fix: devops post-run healthcheck + failure feeds repair.
- Fixed along the way: docker tags must be lowercase (67e8193).


## P0 — Stop silent garbage (do first, ~half day)

### P0.1 Truncation detection in vibe-coder
- Where: `mcp-std-coder/mcp-vibe-coding-agent/dependencies/vibe_coder.py` (~line 632 LLM call)
- Problem: `finish_reason=length` ignored; truncated envelope saved as success (task-1794307611315: 10.6KB cut mid-JSON)
- Do:
  - read `finish_reason` from response
  - if `length`: re-send with conversation continuation ("continue from cutoff") up to N=3 attempts
  - if still truncated: mark agent task `failed` with reason `truncated_output`
- Accept: task producing >max_tokens output ends `failed`, not `done`

### P0.2 Artifact validation gate before `done`
- Where: vibe-coder before `git_push_llm_response`; IT Lead status update
- Do:
  - envelope must parse as JSON (or be raw code)
  - extracted code must pass `ast.parse` (python) / basic HTML close-tag check
  - reject empty or <200-byte code
  - on fail: status `needs_revision` + reason, skip git push
- Accept: no truncated/empty artifact can reach `done`

### P0.3 Coder request timeout + engine health probe
- Where: `vibe_coder.py` requests.post — no timeout today
- Do: add `timeout=600`; on timeout mark `failed: llm_timeout`
- Accept: hung engine doesn't wedge the coder worker thread

## P1 — New team member: QA/Test Engineer (~1-2 days)

### P1.1 Scaffold QA agent
- Where: new `qa-engineer-mcp-server/` from `mcp-std-skeleton`
- Tools: `validate_artifact(task_id, git_url)`, `smoke_run(task_id, kind)`
  - python: `ast.parse` + import in venv sandbox
  - html: serve + HTTP 200 + `<html>`/`</html>` present
  - mcp-template: start server, `initialize` + `tools/list` handshake
- Registers with registry :3031, systemd unit `mcp-qa-engineer.service` port 3072
- Accept: appears in `/api/agents`, responds to `tools/list`

### P1.2 Wire QA into IT Lead flow
- Where: `it_lead_mcp_server/utils/task_routing_rules.py` + planner prompt
- Do: after coder `done`, IT Lead calls QA `validate_artifact`; fail → existing rework loop (`/api/tasks/{id}/request-rework`)
- Status flow: `done` → `validating` → `done`/`needs_revision`
- Accept: flappy-bird + template tasks both pass QA; a hand-broken artifact triggers rework

## P2 — Multi-file artifacts (~1 day)

### P2.1 File manifest support in coder
- Where: `vibe_coder.py` envelope schema + `git_push_llm_response`
- Do: envelope `files: [{path, content}]` → push directory `results/<task_id>/<paths>`; keep single-file fallback
- Accept: MCP-template task produces `server.py + README + requirements.txt` tree

### P2.2 Deployer multi-file awareness
- Where: devops `_deploy_web_application`
- Do: deploy whole result dir (not just result.py/html); Dockerfile COPY tree
- Accept: multi-file template deploys and serves

## P3 — Orchestration intelligence (~1 day)

### P3.1 Task-class routing to decomposition
- Where: IT Lead planner (`llm_task_planner.py`) + `sequence_sdlc_tasks`
- Do: classify task (app | library/template | multi-service); non-trivial → Requirements Engineer decomposition → ordered subtasks, each through coder+QA
- Accept: "MCP service template" produces a 3+ subtask plan, not one vibe shot

### P3.2 Wire review_code before done
- Where: IT Lead post-QA step
- Do: `review_code` on final artifact; findings stored in task metadata
- Accept: review notes visible in task history

## P4 — Infra (investigate)

### P4.1 Halogen engine long-generation behavior
- Symptom: >100s hang on 2000-line request; ~10KB output cap suspected despite `max_tokens=16384`
- Do: check engine config (max output, queue, slots); test dedicated slot for coder; consider bigger coding model
- Accept: deterministic known output ceiling documented; coder budget set below it

### P4.2 Push + tidy
- submodule `team-management-ui/mcp-skeleton-repo` dirty — commit or reset
- stale `.env` keys: `WEB_UI_*` now correct; audit remaining defaults (192.168.51.237 hardcodes in argparse defaults)

## Definition of done for backlog
E2E: submit "MCP service template" task → plan decomposed → files generated → QA handshake passes → deployed → URL live.

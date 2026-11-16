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

## Task activity log ✅ (803c154)
Fixed status_history persistence bug (was never written after INSERT). Added
activity jsonb timeline: agent_call/agent_done(+duration)/agent_error,
file_generated, qa_gate, security_gate, deploy. Rendered in Task History modal.
Guarded migration (lock_timeout) after DDL-on-startup caused a lock pileup.

## Phase B — opencode fixer in patch_file ✅ (3c557da)
patch_file: opencode run --agent fixer --session ses-fix-<task> (reproduce,
fix, re-verify) with single-shot fallback; live: 67s cold / 17s warm.
Bonus fix: latent settings-shadowing NameError that broke patch_file.

## Phase C — opencode tool-agents ✅
contract-planner (QA), sec-reviewer (advisory llm findings), code-reviewer
(advisory review) via shared opencode_run helper. Key fix: PWD env for
project resolution; fresh sessions per task (contaminated sessions keep
their first project binding).

## Phase A — coder with hands ✅
build_project: one opencode session implements + self-verifies the whole
manifest; fan-out = fallback. QA smoke uses free port. Live chain
build->contract->smoke->fixer(same session)->green verified on buildtest-a.

## Phases D1-D3 + first opencode E2E ✅
D1 serve runtime (HTTP transport, :4097 unit) / D2 live agent_step feed
+ token accounting (metadata.opencode_usage) / D3 permission asks ->
resolve_permission tool + auto-reject.
E2E e2e-d-1794473641: plan 5m -> build 19 files in 9m (self-tested) -> QA PASS
-> security PASS -> review stored -> deploy correctly failed (stdio template,
not deployable) -> needs_revision. Fixed: premature done, len(results) NameError,
planner HTTP-transport rule for deployable tasks.

## Requires client ✅
UI checkbox -> context.requires_client -> IT Lead injects client.py into the
manifest (deterministic); QA smoke runs client.py against the live service
(stage=client); IT Lead runs it against the public URL post-deploy
(client_acceptance activity; FAIL -> needs_revision). Pact-style "contract by
example", stdlib-only client, no new infra.

## Requires-client E2E ✅ (e2e-c5)
Route rule1 (nested flags) -> synthesized manifest + injected client.py ->
agent self-ran client at build -> QA -> security -> deploy behind nginx ->
client_acceptance PASS vs public URL. 11 min end-to-end. Permission ask on
workspace cleanup auto-rejected, agent recovered (allow-rule added for
/tmp/oc-builds). Independent re-run of artifact client.py: 6/6 PASS.

## Permission approve/deny in web UI ✅
Task History modal shows pending_permission block (command + 180s countdown +
Approve once / Always allow / Deny) -> POST /api/tasks/{id}/permission ->
IT Lead resolve_permission -> opencode serve -> session resumes. Verified
end-to-end with a live ask (succeeded outcome, metadata cleared).

## Generic deployment tester ✅
Deployments page: [Test] per row -> modal auto-detects artifact kind via backend
probe (all traffic proxied through web-ui -> no CORS): MCP (initialize+tools/list
-> schema-driven forms -> tools/call, session handled server-side) > OpenAPI
(GET /openapi.json -> operations -> execute) > raw HTTP mini-Postman.
SSRF guard: only task_deployments-registered URLs; relative paths only (404/400).
Convention added: deployable REST artifacts must serve GET /openapi.json
(planner prompt + coder AGENTS.md). Verified live: e2e-c5 -> openapi mode,
proxied POST /echo 200; MCP mode against a real streamable-HTTP server
(4 tools listed, tools/call 200); both SSRF guards fire.

## Legacy 1-file path retired ✅
task-1794818260746 postmortem: rule-1.0b (one "html" mention, threshold 0.5)
short-circuited to vibe_code_async: single-file client lib instead of web UI,
flask-only image crash-loop, done despite unhealthy. Fixes:
- planner is now MANDATORY for every task; rule matches are advisory hints
- simple route = synthesized single-file manifest through build_project
  (planner may name it via single_file_path); security gate skipped for simple
- vibe_code_async deprecated (kept for legacy tasks/redeploys only)
- workflow continuation (requirements->implementation) also uses build flow
- health gate: poll edge URL after deploy; 502/504/conn-refused for 60s
  -> deploy_health event + needs_revision instead of done
- legacy deploy deps: ast import derivation (alias map, fastapi->uvicorn)
  instead of hardcoded flask; empty deps no longer emit a pip RUN line

## Subpath-safe web UI E2E ✅ (e2e-u6)
Langflow web-UI contract (the task that exposed the legacy path) now runs
green end-to-end on the unified flow: planner -> 17-file gated build (UI +
same-origin proxy, stdlib) -> QA -> security -> deploy -> deploy_health 200
-> done, 33 min. Browser check: all HTML refs and ES-module imports are
relative and resolve under /<task>/ prefix; generic tester detects openapi.
Round fixed 3 false gates en route: QA primary-file (alphabetical -> largest,
c4697bf), JS validation (brace count -> node --check), secret regex
(config-key names/placeholders excluded); + subpath convention (AGENTS.md +
planner), + health-gate 404 grace.

## V1 visual evidence (screenshots) ✅
After deploy_health passes, IT Lead captures a headless-chromium screenshot
(playwright-bundled chrome-headless-shell CLI) of the public URL ->
/var/www/shots/<task>/deploy.png (outside git), served by web-ui at /shots/
(StaticFiles + vite proxy), stored in metadata.screenshots[], shown as a
"Render" preview in the Task History modal. Verified live: helper -> history
API -> static serving on :8000 and :5173. Next: V2 visual_gate (vision
rubric over this PNG), V3 eyes-for-coder.

## V2 visual_gate (advisory) ✅
qa-engineer tool visual_review: deploy screenshot + task text -> vision
rubric {page_kind, renders, styled, matches[{req,met,evidence}], issues,
verdict}; IT Lead runs it after the V1 screenshot, verdict -> metadata
.visual_review + visual_gate activity event, NEVER blocks (promotion to
blocking = separate measured decision). Acceptance 3/3: e2e-u5 bare UI
-> FAIL (concrete evidence: white bg, serif heading, no pastel), retro
webui -> PASS (evidence per requirement), raw-JSON endpoint -> PASS
(page_kind=raw_json). 5-12 s per review.

## V3 eyes for the coder ✅ (mechanics)
Verified opencode read-tool passes PNGs to the vision model (probe: coder
named the color of an unseen PNG). Build convention now instructs web-UI
coders to self-verify visually: chrome-headless-shell screenshot of their
running server -> read _shot.png -> fix -> repeat; delete shot before finish.
No API plumbing needed (shell allowed by default; external_directory deny
covers read/edit tools, not binary execution). E2E: e2e-v3 watching agent
steps for screenshot+read loop.

## V3 eyes-for-coder ✅ (live proof)
e2e-v3: build session ran chrome-headless-shell on its own server,
READ _shot.png (vision), cleaned up - all visible in agent_step feed.
Deploy screenshot + visual_gate PASS(advisory) in the same run: V1+V2+V3
closed loop, 9 min. flux2 probes green too (byte-identical seeds, edits,
seed+i batches); 256x256 unsupported -> default 512x512. V5 (image-tools
MCP facade) designed, awaiting go.

## V5 image-tools (generation inside builds) ✅
image_tools_mcp.py: stdio MCP facade for flux2-klein-4b (halogen :8081,
base via IMAGE_API_BASE). Tools generate_image/edit_image; PNGs written into
the session workspace; deterministic default seed=crc32(prompt+filename)
echoed back; path traversal blocked; agents never touch the network. Registered
in opencode mcp.servers (codemode:false -> direct tools). NOTE: MCP stdio =
newline-delimited JSON, NOT LSP Content-Length framing (first attempt timed
out). Live proof: coder session called generate_image, produced robot.png,
read it, answered "Robot". Build conventions: generated assets instead of
hotlinks + README provenance section. E2E e2e-v5 (favicon+hero robot) running.

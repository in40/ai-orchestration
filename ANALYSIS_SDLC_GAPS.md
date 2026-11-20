# SDLC Gap Analysis — what the pipeline still doesn't do
(2026-11-11, after P0–P7. Sources: agentic-SDLC articles — coderabbit agentic SDLC guide,
"10 Critical SDLC Gates AI Agents Silently Skip" (dev.to), Boris Tane "SDLC Is Dead"
(observability feeding the agent loop), MLflow/Langfuse regression-gating practices.)

## Coverage map: real SDLC vs our pipeline

| # | SDLC stage | Us | Gap severity |
|---|------------|----|--------------|
| 1 | Requirements / intent | requirements-engineer + T6 spec handoff | ok |
| 2 | Architecture / design | planner + file_manifest (implicit design) | medium — no design artifact, decisions untraceable |
| 3 | Decomposition | manifest fan-out | ok |
| 4 | Implementation | coder (generate_file / vibe_code_async) | ok |
| 5 | Unit self-check | ast/syntax gates, fence strip | ok |
| 6 | **Code review** | review_code tool exists, NOT wired | **open P3.2** |
| 7 | **Testing** | QA smoke + MCP conformance probe | **HIGH: coder generates tests/ dirs that nobody runs** |
| 8 | **Regression suite** | none | **HIGH: nothing re-runs checks on redeploy/change** |
| 9 | Security (static) | Security Reviewer regex scan | medium — homegrown; no bandit/semgrep |
| 10 | **Dependency audit** | none | **HIGH: requirements.txt installed blind (pip-audit/OSV missing)** |
| 11 | Performance / load | none | medium — "correct but O(n²)" class (dev.to article) |
| 12 | Build / release | docker build from contract | medium — no versioning, no changelog |
| 13 | **Env parity QA↔prod** | QA venv on host python3.13, container python:3.11-slim | **HIGH: latent "passes QA, dies in Docker" class** |
| 14 | Deploy | contract-driven + post-start healthcheck | ok |
| 15 | Config / secrets | .env.example generated | medium — no secret injection story for real services |
| 16 | Monitoring | warden liveness (5 min) | medium — liveness only, no logs/metrics |
| 17 | **Prod→dev feedback loop** | warden marks unhealthy → nothing happens | **HIGH: the loop the articles say wins — ours is open** |
| 18 | Rollback / canary | deferred (no artifact versions) | medium |
| 19 | Human escalation | escalate_to_human + /api/approvals exist, unwired | medium |
| 20 | Cost / usage accounting | none | low-medium — no token cost per task |
| 21 | Docs accuracy | QA reads README as contract input | ok-ish (bad docs now fail smoke — good pressure) |
| 22 | Data/migrations | n/a for templates | future |

## The three structural gaps (beyond individual tools)

1. **Tests are generated but never executed.** tmplC produced `tests/test_mcp_service.py`
   and QA ignored it. Every article converges: gate deploys on test/eval scores.
2. **QA environment ≠ runtime environment.** Smoke runs in host venv (py3.13), prod is
   python:3.11-slim. The pipeline's most common failure class (QA green → container
   crash-loop) is an artifact of this split.
3. **The loop doesn't close.** Warden detects death; no one re-enters the pipeline with
   the production evidence. "Observability that feeds directly back into the agent loop"
   is the whole point of the new SDLC.

## Recommended build order (value/effort)

| Pri | Item | Effort | Value |
|-----|------|--------|-------|
| 1 | **QA runs generated tests**: `pytest tests/` in contract smoke when tests/ exists | S | H |
| 2 | **Container-parity pipeline**: build image first → run contract smoke INSIDE the image → deploy same image (build-once, test-once, ship-that) | M | H — kills env-drift class |
| 3 | **pip-audit in Security Reviewer** (offline: OSV API or pip-audit --no-deps) | S | M-H |
| 4 | **Warden→rework loop**: unhealthy deployment auto-creates rework task with container logs as error context (reuses patch_file repair) | M | H — closes the loop |
| 5 | **Regression store**: persist run_contract + test results per task; `retest` re-runs both on any redeploy | M | M-H |
| 6 | review_code advisory gate (P3.2): findings in metadata, non-blocking | S | M |
| 7 | token/cost accounting: coder logs usage per task; task total in metadata | S | M |
| 8 | perf smoke: 10 concurrent requests / 5s budget in QA service check | S | M |
| 9 | artifact versioning + rollback tool (keep last N results dirs per task) | M | M |
| 10 | wire /api/approvals → human gate before deploy for flagged tasks | M | M |

Pri 2 is the architectural one: reordering build→test-in-image→deploy removes an entire
failure class we hit three times (tmpl9/10/C). Pri 1+4 together turn the pipeline from
"factory" into the "tight loop" the literature describes.

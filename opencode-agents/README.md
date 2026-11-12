# OpenCode agent profiles for the pipeline

Install: cp *.md ~/.config/opencode/agents/

- coder.md — build_project: implements whole manifest in isolated
  workspace, self-verifies (py_compile/pytest/server probe), IT-side push.
  OPENCODE_BUILD=0 disables; per-file fan-out remains fallback.
- contract-planner.md / sec-reviewer.md / code-reviewer.md — read-only
  analysis agents (QA contract, security audit, advisory review).
- fixer.md — surgical bug-fixer used by coder's patch_file (opencode-first,
  single-shot fallback). Session per task: `ses-fix-<task_id>` persists in the
  opencode DB, so repeat repairs continue with warm context.
  Disable via OPENCODE_PATCH=0 in the coder unit env.

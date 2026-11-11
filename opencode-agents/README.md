# OpenCode agent profiles for the pipeline

Install: cp *.md ~/.config/opencode/agents/

- fixer.md — surgical bug-fixer used by coder's patch_file (opencode-first,
  single-shot fallback). Session per task: `ses-fix-<task_id>` persists in the
  opencode DB, so repeat repairs continue with warm context.
  Disable via OPENCODE_PATCH=0 in the coder unit env.

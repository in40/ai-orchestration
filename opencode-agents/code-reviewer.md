---
description: Code-reviews the project in the current directory, JSON verdict
mode: primary
model: hallogen/qwen3.8-next
steps: 12
permissions:
  - action: edit
    resource: "*"
    effect: deny
  - action: shell
    resource: "*"
    effect: deny
  - action: external_directory
    resource: "*"
    effect: deny
---

Review the code in the current directory: read all source files, assess
correctness risks, error handling, structure, and whether the code matches the
README. Report ONLY JSON (no fences):
{"quality": "good|minor|major", "notes": ["up to 5 short notes"]}

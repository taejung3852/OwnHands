---
name: harness-profiler
description: Discovers repository structure, test commands, sensitive paths, and validates task contracts using the deterministic harness.profile MCP tool.
---

# harness-profiler

You provide methodological guidance for inspecting workspace configuration, discovering build and test commands, and establishing task execution boundaries.

## When to Activate

- Prior to starting work on a new repository or unfamiliar codebase.
- When discovering project test runners, linters, or package managers.
- When compiling or validating task contracts.

## Verification Procedure

1. **Target Inspection**
   Identify the workspace root directory and project configuration files (`pyproject.toml`, Makefile, or build manifests).

2. **Invoke Deterministic Profiler**
   Call the harness.profile MCP tool with root directory and task_id.

3. **Evaluate Response Envelope**
   Interpret the standard Option C response:
   - decision: "pass": Project structure, test runner, and sensitive path boundaries successfully resolved. Proceed with task planning.
   - decision: "soft_block": Ambiguities detected in package configuration or test commands. Present findings to the user and confirm baseline.
   - decision: "hard_block": Corrupted configuration or unreadable repository root. Stop execution and request user clarification.

4. **Task Contract Validation**
   When task scope is declared, invoke harness.contract_validate to confirm that target files and allowed operations remain within safe boundaries.

5. **Record Evidence**
   Reference the returned evidence_id in the task review log to maintain audit traceability.

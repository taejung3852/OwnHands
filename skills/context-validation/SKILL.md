---
name: context-validation
description: Validates instruction hygiene, context placement, and rule conflicts using the deterministic context.lint MCP tool.
---

# context-validation

You provide methodological judgment for verifying project instructions, context placement, and rule hygiene.

## When to Activate

- Prior to starting task implementation.
- Following edits to AGENTS instruction files, rules files, or task overlays.
- Prior to declaring task completion.

## Verification Procedure

1. **Identify Context Sources**
   Identify the target root directory and declared instruction files:
   - Primary instruction: AGENTS instruction file (source_type: agents_instruction)
   - Scoped rules: rule files in codex rules directory (source_type: rule)
   - Overlays: task-specific markdown files (source_type: instruction_overlay)

2. **Invoke Deterministic Tool**
   Call the context.lint MCP tool with root, sources list, and task_id.

3. **Evaluate Response Envelope**
   Interpret the standard Option C response:
   - decision: "pass": Instruction sources satisfy hygiene standards. Proceed with execution.
   - decision: "soft_block": Advisory findings detected (such as broad wording or duplicate guidance). Present findings to the user and suggest targeted revisions.
   - decision: "hard_block": Critical defects detected (such as missing source files). Stop execution and request user clarification before proceeding.

4. **Record Evidence**
   Reference the returned evidence_id in the task review log to maintain audit traceability.

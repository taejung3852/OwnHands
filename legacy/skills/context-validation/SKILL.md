---
name: context-validation
description: "[Legacy / Compat Only] Historical context linting harness. Do not invoke for new lifecycle workflows."
---

# context-validation

You provide methodological judgment for verifying project instructions, context placement, manifest completeness, benchmark plans, and context guarantee evaluation.

## Canonical MCP Tools

This sub-skill owns 6 canonical MCP tools:
1. context.lint: Deterministic static linting of instruction files for placement and hygiene defects.
2. context.inspect: Authoritative validation of context manifests, ensuring evidence and event reference completeness.
3. context.gate_evaluate: Evaluates task start and change context gates based on active sources and deterministic content hashes.
4. context.benchmark_plan: Plans combinatorial benchmark matrices across isolated contexts.
5. context.benchmark_evaluate: Evaluates benchmark outcomes and verifies instruction effectiveness.
6. context.guarantee_evaluate: Evaluates deterministic guarantees returning exact verdict keys.

## When to Activate

- Prior to starting task implementation or following edits to instructions.
- When validating context manifest integrity or evaluating task context gates.
- When benchmarking instruction stability across varied configurations.
- Prior to declaring task completion to verify context guarantees.

## Verification Procedure

1. **Instruction Hygiene and Placement**
   Call the context.lint MCP tool with root, sources list, and task_id.
   - decision: "pass": Instruction sources satisfy hygiene standards. Proceed with execution.
   - decision: "soft_block": Advisory findings detected. Present findings to the user and suggest targeted revisions.
   - decision: "hard_block": Critical defects detected. Stop execution and request user clarification before proceeding.

2. **Context Manifest Verification**
   Call context.inspect with manifest, evidence_ids, and event_ids to verify that all referenced entities exist and are authoritatively logged.

3. **Context Gate Evaluation**
   Call context.gate_evaluate with gate_input to produce compiled overlays.

4. **Context Guarantees**
   Call context.guarantee_evaluate with claim_id and evidence_ids to assess deterministic guarantees. Verify verdicts.

5. **Record Evidence**
   Reference the returned evidence_id in the task review log to maintain audit traceability.

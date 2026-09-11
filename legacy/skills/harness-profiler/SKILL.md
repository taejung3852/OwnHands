---
name: harness-profiler
description: "[Legacy / Compat Only] Historical workspace and contract profiler harness. Do not invoke for new lifecycle workflows."
---

# harness-profiler

You provide methodological guidance for inspecting workspace configuration, discovering build and test commands, validating execution contracts, and rendering safety previews.

## Canonical MCP Tools

This sub-skill owns 3 canonical MCP tools:
1. harness.profile: Scans repository structure, configuration layers, test commands, rules, and sensitive paths. Returns the profile document with null decision as compatibility anchor.
2. harness.contract_validate: Validates semantic integrity, permission boundaries, freshness triggers, and approval requirements of execution contracts or baseline profiles.
3. harness.compile_preview: Compiles contracts into concrete workspace artifacts and generates human-readable review previews.

## When to Activate

- Prior to starting work on a repository or establishing a task baseline.
- When compiling, checking freshness, or validating task execution contracts.
- When generating preview artifacts before candidate changes are applied.

## Verification Procedure

1. **Target Profiling**
   Call harness.profile with root directory, project_id, worktree_id, and environment_ref. Inspect detected commands, sensitive paths, and rule tiers.

2. **Task Contract Validation**
   Call harness.contract_validate with contract, baseline and overlay, or profile and interview_responses.
   - decision: "pass": Contract is valid and active permissions satisfy boundary constraints.
   - decision: "soft_block": Baseline freshness stale or interview ambiguity detected.
   - decision: "hard_block": Critical boundary violation, missing task block, or unapproved permission.

3. **Compile and Preview**
   Call harness.compile_preview with contract and existing file map to generate artifact diffs and review previews before applying modifications.

4. **Record Evidence**
   Reference returned evidence_id in the task review log for end-to-end traceability.

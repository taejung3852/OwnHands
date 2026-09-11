---
name: execution-control
description: "[Legacy / Compat Only] Historical execution and sandbox control harness. Do not invoke for new lifecycle workflows."
---

# execution-control

You provide methodological guidance for evaluating command safety, enforcing sandbox permissions, managing task lifecycles, and applying or rolling back candidate changes safely.

## Canonical MCP Tools

This sub-skill owns 9 canonical MCP tools:
1. sandbox.inspect: Inspects workspace cleanliness, untracked files, and checks command safety against policy.
2. git.restore_capture: Captures clean workspace restore points and verifies rollback readiness.
3. runtime.controls_check: Assesses command side-effects, process constraints, and approval requirements.
4. task.prepare: Prepares managed task execution environments with required SHA-256 patch fingerprints.
5. task.create: Atomically registers project, worktree, task, and canonical task.created sequence 1 event in Catalog.
6. task.record_run: Records managed execution run outcomes and evidence pointers into Catalog.
7. task.import: Imports external task fixtures adhering to schema v1.0 specifications.
8. harness.candidate_apply: Applies compiled candidate control artifacts with explicit product approval and creates an atomic rollback journal.
9. harness.candidate_rollback: Atomically reverses candidate artifacts using the generated rollback journal.

## When to Activate

- Prior to creating tasks or executing shell commands with mutating side-effects.
- Prior to running scripts or package managers that alter workspace files.
- When applying or rolling back candidate configuration files.
- When importing external task fixtures.

## Verification Procedure

1. **Task Creation and Preparation**
   - Call task.create to atomically initialize task identity and lifecycle.
   - For managed runs, call task.prepare with workspace root and patch hash.

2. **Pre-Execution Safety and Snapshots**
   - Invoke sandbox.inspect to verify clean workspace state and command compliance.
   - Invoke git.restore_capture to secure a restorable baseline snapshot.
   - Run runtime.controls_check to determine if human approval is triggered.

3. **Candidate Modification and Rollback**
   - Apply candidate artifacts via harness.candidate_apply with explicit approval.
   - If validation fails, restore state via harness.candidate_rollback using the recorded journal.

4. **Record Evidence**
   Invoke task.record_run to log execution outcomes, commands, and receipts to the authoritative Catalog.

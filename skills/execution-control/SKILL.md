---
name: execution-control
description: Enforces sandbox boundaries, checks command side-effects, and captures git restore snapshots before executing risky shell operations.
---

# execution-control

You provide methodological guidance for evaluating command safety, enforcing sandbox permissions, and capturing recovery snapshots.

## When to Activate

- Prior to executing shell commands with external network access or package installations.
- Prior to running scripts that perform filesystem modifications outside the active task scope.
- Prior to performing irreversible git operations.

## Verification Procedure

1. **Evaluate Command Scope**
   Inspect the command line string, environment variables, and target directories against declared worktree boundaries.

2. **Capture Restore Snapshot**
   Capture a git restore snapshot prior to running mutating commands to ensure recovery points exist.

3. **Check Sandbox Permissions**
   Verify that declared permissions allow the target operation (read-only, worktree-write, or network access).

4. **Approval Policy Check**
   When operations touch sensitive directories or root system paths, prompt for explicit human approval before execution.

5. **Record Execution Evidence**
   Log command outcome, exit code, and execution time to the audit trail with the associated task_id.

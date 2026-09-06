---
name: test-assurance
description: Guides test strategy design, baseline test capture, pre/post run comparisons, and authoritative regression gate evaluation using assurance MCP tools.
---

# test-assurance

You provide methodological guidance for test design, diff impact analysis, test run comparisons, and regression gate evaluation.

## When to Activate

- Prior to editing code: to design a test strategy and capture a baseline test run.
- After code modifications: to evaluate git diff impact and run comparative test analysis.
- Prior to declaring task completion: to evaluate the authoritative regression gate.

## Verification Procedure

1. **Test Strategy Formulation**
   Formulate a test design memo identifying affected functional areas, test levels, and risk factors aligned with project quality standards.

2. **Pre-Change Baseline Capture**
   Execute the test suite prior to code modifications using tests.compare_runs in baseline mode. Record the baseline run identifier.

3. **Diff Impact Analysis**
   After making code modifications, inspect git diff output to verify changes remain strictly within declared task boundaries.

4. **Post-Change Comparison**
   Execute the test suite again and invoke tests.compare_runs to compare pre-change and post-change test outcomes.

5. **Regression Gate Evaluation**
   Invoke the assurance.gate_evaluate MCP tool with baseline_run_id, current_run_id, and task_id.
   Interpret the standard Option C response:
   - decision: "pass": No regressions detected. Fixed failures or new passing tests verified. Proceed to completion.
   - decision: "soft_block": Coverage gaps or unobserved test outcomes detected. Present findings to the user for review.
   - decision: "hard_block": Regressions detected (previously passing tests now fail). Stop completion and resolve regressions.

6. **Record Evidence**
   Reference the returned evidence_id in the completion report to prove deterministic verification.

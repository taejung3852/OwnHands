---
name: test-assurance
description: "[Legacy / Compat Only] Historical test assurance and regression gate harness. Do not invoke for new lifecycle workflows."
---

# test-assurance

You provide methodological guidance for test design, diff impact analysis, test run comparisons, and authoritative regression gate evaluation.

## Canonical MCP Tools

This sub-skill owns 7 canonical MCP tools:
1. tests.baseline_record: Records observed test baseline receipts with strict validation of all 16 receipt fields. Failing baselines are fully valid for TDD Red state.
2. tests.compare_runs: Compares pre-change and post-change test receipts using authoritative 11-status mappings.
3. tests.gap_detect: Detects coverage gaps, unobserved criteria, and missing test executions.
4. tests.design_memo: Synthesizes structured test design memos and criterion bindings from contracts and impact analyses.
5. git.diff_impact: Analyzes modified file diff impact against relation catalogs with strict relation types.
6. assurance.gate_evaluate: Evaluates the authoritative regression gate using full contract, impact, design, comparison, and gap inputs.
7. guarantee.evaluate: Evaluates test domain guarantees returning exact verdict states.

## When to Activate

- Prior to editing code: to design a test strategy and capture a baseline test run.
- After code modifications: to evaluate git diff impact and run comparative test analysis.
- Prior to declaring task completion: to evaluate the authoritative regression gate.

## Verification Procedure

1. **Pre-Change Baseline Capture**
   Invoke tests.baseline_record with contract, selection, and observed test receipts. Even if tests currently fail in TDD Red state, baseline capture succeeds.

2. **Diff Impact Analysis**
   Call git.diff_impact with workspace root, restore point, and relation catalog to classify affected targets.

3. **Test Strategy and Design Memo**
   Invoke tests.design_memo and tests.gap_detect to verify comprehensive criterion coverage.

4. **Comparative Test Execution**
   Execute post-change tests and call tests.compare_runs.
   - pass: expected outcomes verified.
   - soft_block: non-critical advisory change.
   - hard_block: regression detected.

5. **Authoritative Gate Evaluation**
   Call assurance.gate_evaluate with contract, impact, design, comparison, and gaps.
   - decision: "pass": No regressions, criteria satisfied.
   - decision: "hard_block": Regressions or missing coverage detected. Completion is blocked.

6. **Authoritative Guarantees**
   Call guarantee.evaluate to verify that assurance guarantees remain supported.

7. **Record Evidence**
   Reference the returned evidence_id in the completion report to prove deterministic verification.

# Criteria Comparison Taxonomy Guide

Every criterion in an OwnHands Verification Specification must have one of three comparison types: `current`, `preserve`, or `improve`.

## 1. `current` (Post-Change Observation Only)
* **Definition**: Confirms that a new capability, endpoint, flag, or UI element functions correctly after implementation.
* **Requirements**:
  - Requires an observed After result of `pass`.
  - Does NOT require a Before baseline run.
* **Example**:
  - *"Adding a new `--format=json` flag returns valid JSON output."*

## 2. `preserve` (Regression Protection)
* **Definition**: Confirms that existing, previously working behavior has NOT broken as a consequence of the new changes.
* **Requirements**:
  - Requires an observed Before result of `pass`.
  - Requires an observed After result of `pass`.
  - Before and After MUST share the identical test meaning and execution environment.
* **Disallowed**:
  - If a test was already failing before the change, it CANNOT be marked as `preserve`.
* **Example**:
  - *"Existing refund endpoints continue returning HTTP 200 for valid first-time refund requests."*

## 3. `improve` (Defect Resolution / TDD Improvement)
* **Definition**: Confirms that an observed defect, bug, or missing feature was successfully resolved.
* **Requirements**:
  - Requires an observed Before result of `fail`.
  - Requires an observed After result of `pass`.
  - Before and After MUST share the identical test meaning and execution environment.
* **Disallowed**:
  - If a test was already passing before the change, it CANNOT be marked as `improve`.
* **Example**:
  - *"Submitting duplicate refund requests with identical idempotency keys previously returned HTTP 500, but now correctly returns HTTP 409 Conflict."*

## Summary Matrix

| Comparison Type | Before Observation | After Observation | Verdict Status |
|---|---|---|---|
| `current` | Not required | `pass` | `verified` |
| `preserve` | `pass` | `pass` | `verified` |
| `improve` | `fail` | `pass` | `verified` |
| Any | Inconclusive / Not run | `pass` | `inconclusive` |
| Any | Any | `fail` | `failed` |

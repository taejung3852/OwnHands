# TDD and SDD Integration with OwnHands Lifecycle

Spec-Driven Development (SDD) and Test-Driven Development (TDD) are core engineering methodologies supported natively by OwnHands. They are not separate lifecycle stages; rather, they map directly into the OwnHands stages.

## 1. Spec-Driven Development (SDD) Mapping

In SDD, you define the complete behavior contract before writing any implementation code:
1. **Goal / Problem Analysis** ➔ Managed by `work-map` when scope is broad.
2. **Contract Drafting** ➔ Managed by `verification-spec`. The acceptance criteria table formalizes the specification.
3. **Human Approval Gate** ➔ The spec must be reviewed and approved by a human (`spec_approval`). This turns human expectations into an immutable machine contract.

## 2. Test-Driven Development (TDD) Mapping

In TDD, the Red-Green-Refactor loop integrates seamlessly into OwnHands:

```
[Phase 1: Red]
Write failing unit test
      │
      ▼
verification-spec defines criterion as `improve`
      │
      ▼
baseline runs the test and records Before = `fail` (Valid Red State)

[Phase 2: Green]
Write implementation code (OwnHands DORMANT)
      │
      ▼
review runs the test and records After = `pass`
      │
      ▼
Claim evaluated as `verified` (Before fail ➔ After pass)

[Phase 3: Refactor]
Refactor implementation code
      │
      ▼
review re-runs full test suite to ensure existing criteria remain `preserve`
```

## Key Principle: A Failing Test Baseline is NOT an Error

Under OwnHands:
- A test run returning `fail` during the `baseline` stage is a **fully valid Before observation** for an `improve` criterion.
- It proves that the defect actually existed prior to code changes, providing concrete empirical proof that your subsequent code change fixed the problem.

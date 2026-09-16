# Dashboard WI-01 verification

Date: 2026-09-13. Scope: approved #89 SDD, WI-01 reader foundation only.
Base: `69f81517c5abcd81e84ec1aac873c006ab49f72d` (433 baseline tests).

## Executed evidence

| Check | Observed result |
|---|---|
| Initial TDD | 12 missing-feature assertion failures, 0 errors; then 12 passed |
| Independent review reproductions | WAL Catalog/Lifecycle sidecar creation and raw-directory corruption reproduced before fixes |
| Added failure fixtures | WAL factories: 2 assertion failures; raw directory and corrupt parent: filesystem exceptions before fixes |
| Final WI-01 tests | 16 passed; real Catalog/Lifecycle/Evidence fixtures |
| Full regression | 449 passed (433 baseline + 16 WI-01) |
| Existing #82 mutation runner | 9/9 mutations detected by assertions, 0 execution errors |
| Reader raw-validator bypass | Both corrupt and missing-object checks detected bypass: 2 assertion failures, 0 errors |
| Diff whitespace | `git diff --check` clean |

Commands from repository root:

```sh
PYTHONPATH=src ../ownhands-80/.venv/bin/python -m unittest tests.test_dashboard_readonly -q
PYTHONPATH=src ../ownhands-80/.venv/bin/python -m unittest discover -s tests -q
PYTHONPATH=src ../ownhands-80/.venv/bin/python tests/run_claim_mutations.py
git diff --check
```

The raw-validator bypass was an in-process `unittest.mock.patch.object` replacing
`EvidenceStore._validate_object` with a constant byte return, running the corrupt
and missing-object tests. It changed no production files.

## Acceptance coverage

- Existing source reads preserve file paths, contents and permission modes; orphan CAS objects remain untouched.
- Missing databases are not created, old schemas are not migrated, and reader writer APIs fail before file operations.
- Both explicit and implicit EvidenceStore construction inherit the catalog's read-only mode.
- SQL writes are rejected even after disabling `query_only`, because the source connection uses `mode=ro`.
- Closure diagnostics distinguish missing, purged, corrupt and permission-denied Evidence, retaining healthy sibling metadata.
- Journal, reference and cross-Task violations remain hard errors. Partial read health never changes stored Claim/Review judgments.
- Existing current/freshness/review-status reads work with deferred read transactions.

## Independent review and fixes

The independent reviewer found two P2 issues: SQLite WAL sidecar creation and
malformed raw filesystem objects aborting partial inspection. Both were addressed
with failing fixtures first. The reviewer rechecked the original fixes and also
identified the corrupt-parent `NotADirectoryError` case; that case now has its own
passing fixture and explicit diagnostic handling.
Final independent recheck reran all 16 targeted tests successfully and confirmed
both P2 findings resolved, with no outstanding confirmed P1/P2 findings.

## Boundaries and unverified scope

- Read-only sources support the existing rollback-journal storage format. WAL is
  rejected by reading the file header before opening SQLite, with no migration or
  automatic checkpoint. `immutable=1` is not used because it could omit committed
  WAL frames. Concurrent external journal-mode switching is outside this contract.
- File inventory checks cover paths, bytes and permission modes, not filesystem atime.
- No Dashboard HTTP, UI, cross-database snapshot atomicity, arbitrary raw-path serving,
  cache, provider integration or ELI5 semantic verification is claimed here.
  These remain later WIs; provider-neutral generation plus one adapter is approved
  but not implemented in WI-01.
- Full unittest reports `OK` while emitting the pre-existing M3 live fixture drift
  diagnostic for AGENTS.md. M3 live-environment success remains unverified.
- No source repair, verdict recalculation, HumanDecision write or issue close occurs.

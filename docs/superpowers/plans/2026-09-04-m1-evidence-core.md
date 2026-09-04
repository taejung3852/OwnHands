# M1 Evidence Core Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 비민감 작업의 실제 Event와 Evidence를 로컬에 저장하고, Projection을 재생성하며, Guarantee Matrix에 따른 Task Guarantee Report와 최소 검토 화면을 만든다.

**Architecture:** Python 3.12 표준 라이브러리만 사용하는 작은 Local Core를 만든다. 하나의 SQLite catalog가 identity, append-only Event, Evidence metadata, Projection을 관리하고, Raw Evidence는 SHA-256 content-addressed file object로 분리한다. Guarantee Evaluator는 catalog의 canonical record를 직접 조회해 Report를 만들며, 최소 HTML은 그 Report와 Projection의 직렬화 결과만 렌더링한다.

**Tech Stack:** Python 3.12, sqlite3 rollback journal, unittest, pathlib/hashlib/json/html 표준 라이브러리

**Spec:** `docs/product/향후계획.md`의 M1, `docs/adr/0002-control-validation-evidence-model.md`, `docs/adr/0003-guarantee-matrix-representation.md`, `docs/adr/0004-event-evidence-store.md`, `docs/adr/0006-assurance-dashboard-sequencing.md`

## Global Constraints

- Raw Evidence의 자동 삭제를 기본 동작으로 만들지 않는다.
- 보존 기간과 삭제는 사용자가 선택할 수 있게 하며 purge는 명시적 호출에서만 수행한다.
- 애플리케이션 자체 암호화를 제공한다고 주장하지 않는다.
- 민감정보 원문은 수집 단계에서 제거하거나 참조화한다.
- macOS Application Support 등 운영체제 표준 data root와 0700/0600 권한을 사용한다.
- SQLite는 rollback journal DELETE, synchronous FULL, single-writer transaction을 사용하며 WAL은 도입하지 않는다.
- Raw Evidence와 임시 검증 자료는 Git에 commit하지 않는다.
- Configured / Loaded / Enforced와 Observed / Inferred / Unobserved를 합치지 않는다.
- M5 Production UI를 만들지 않는다. M1 view는 실제 fixture 결과를 확인하는 최소 review artifact다.

---

### Task 1: Runtime 기준과 Project·Worktree·Task identity

**Files:**
- Create: `pyproject.toml`
- Create: `uv.lock`
- Create: `src/devharness/__init__.py`
- Create: `src/devharness/paths.py`
- Create: `src/devharness/catalog.py`
- Create: `src/devharness/identity.py`
- Create: `tests/__init__.py`
- Create: `tests/test_identity.py`
- Create: `docs/adr/0008-python-core-runtime.md`
- Modify: `docs/adr/README.md`
- Modify: `docs/product/Requirements_Traceability.md`

**Interfaces:**
- Produces: `DataPaths.resolve(override: Path | None) -> DataPaths`
- Produces: `Catalog.open(root: Path) -> Catalog`
- Produces: `IdentityRegistry.register_project(locator: str) -> ProjectIdentity`
- Produces: `IdentityRegistry.register_worktree(project_id: str, locator: str) -> WorktreeIdentity`
- Produces: `IdentityRegistry.create_task(worktree_id: str, mode: str, commit: str, branch: str, cwd: str, environment_ref: str) -> TaskIdentity`

- [ ] **Step 1: Write the failing identity tests**

```python
def test_same_locator_is_idempotent_and_worktree_is_project_scoped(self):
    project = self.registry.register_project("file:///repo")
    self.assertEqual(project, self.registry.register_project("file:///repo"))
    worktree = self.registry.register_worktree(project.project_id, "file:///repo/main")
    self.assertEqual(project.project_id, worktree.project_id)

def test_invalid_task_mode_and_cross_project_worktree_are_rejected(self):
    with self.assertRaises(ValueError):
        self.registry.create_task("missing", "managed", "abc", "main", "/repo", "local")
    with self.assertRaises(ValueError):
        self.registry.create_task(self.worktree.worktree_id, "other", "abc", "main", "/repo", "local")
```

- [ ] **Step 2: Run the test and observe RED**

Run: `PYTHONPATH=src uv run --python 3.12 python -m unittest tests.test_identity -v`

Expected: import failure because `devharness.identity` does not exist.

- [ ] **Step 3: Implement the minimum schema and identity registry**

Use UUID4 values stored behind unique locator constraints. `tasks.mode` has a database CHECK for `managed` or `imported`; task creation first resolves the referenced worktree and copies its project ID into the immutable task snapshot. `Catalog.open()` creates the data root with 0700, the database with 0600, `PRAGMA journal_mode=DELETE`, `PRAGMA synchronous=FULL`, `PRAGMA foreign_keys=ON`, and explicit transactions.

- [ ] **Step 4: Run Task 1 tests and syntax checks**

Run: `PYTHONPATH=src uv run --python 3.12 python -m unittest tests.test_identity -v`

Run: `uv run --python 3.12 python -m compileall -q src tests`

Expected: all identity tests pass and no syntax error is reported.

- [ ] **Step 5: Record the runtime decision and commit**

ADR-0008 records Python 3.12 stdlib selection, Node built-in SQLite release-candidate rejection for the core, zero runtime dependency, packaging deferral to M7, and the lack of app-level encryption. Commit message: `feat: add stable task identity model`.

---

### Task 2: Canonical append-only Event Log

**Files:**
- Create: `src/devharness/events.py`
- Create: `tests/test_events.py`
- Modify: `src/devharness/catalog.py`

**Interfaces:**
- Consumes: `Catalog`, `TaskIdentity`
- Produces: `EventDraft(event_id, task_id, event_type, event_version, occurred_at, payload, collection_method, redaction_status)`
- Produces: `EventLog.append(draft: EventDraft, redactor: Callable[[dict], dict]) -> EventRecord`
- Produces: `EventLog.list_for_task(task_id: str) -> list[EventRecord]`
- Produces: `EventLog.head_sequence(task_id: str) -> int`

- [ ] **Step 1: Write failing append, duplicate, rollback, redaction, and tamper tests**

```python
def test_duplicate_id_is_idempotent_only_for_identical_event(self):
    first = self.log.append(self.draft, redact_payload)
    self.assertEqual(first, self.log.append(self.draft, redact_payload))
    with self.assertRaises(EventConflict):
        self.log.append(replace(self.draft, payload={"different": True}), redact_payload)

def test_secret_is_redacted_before_storage(self):
    self.log.append(replace(self.draft, payload={"token": "secret"}), redact_payload)
    self.assertNotIn("secret", self.catalog.path.read_bytes().decode("utf-8", errors="ignore"))
```

- [ ] **Step 2: Run the tests and observe RED**

Run: `PYTHONPATH=src uv run --python 3.12 python -m unittest tests.test_events -v`

Expected: import failure because `devharness.events` does not exist.

- [ ] **Step 3: Implement Event transactions and append-only guards**

Allocate task sequence inside `BEGIN IMMEDIATE`; make `event_id` unique and `(task_id, sequence)` unique. Serialize payload with sorted keys and compact separators before fingerprinting. Identical redeliveries return the existing row; a different fingerprint raises `EventConflict`. SQLite triggers reject UPDATE and DELETE on `events`. The redactor runs before serialization and the unredacted payload is not retained.

- [ ] **Step 4: Run Event tests plus integrity checks**

Run: `PYTHONPATH=src uv run --python 3.12 python -m unittest tests.test_events -v`

Run: `PYTHONPATH=src uv run --python 3.12 python -m unittest discover -s tests -v`

Expected: sequence, idempotency, rollback, redaction, and tamper tests pass.

- [ ] **Step 5: Commit**

Commit message: `feat: add canonical event log`.

---

### Task 3: Local Evidence Store and retention boundary

**Files:**
- Create: `src/devharness/evidence.py`
- Create: `tests/test_evidence.py`
- Modify: `src/devharness/catalog.py`
- Modify: `.gitignore`

**Interfaces:**
- Consumes: `Catalog`, `EventLog`, Task identity
- Produces: `EvidenceDraft(evidence_id, task_id, requirement_id, evidence_type, subject_ref, exact_scope, result, basis, fields, content, collection_method, redaction_status)`
- Produces: `EvidenceStore.put(draft: EvidenceDraft, redactor: Callable[[bytes], bytes]) -> EvidenceRecord`
- Produces: `EvidenceStore.resolve(evidence_id: str) -> EvidenceRecord`
- Produces: `EvidenceStore.list_for_task(task_id: str) -> list[EvidenceRecord]`
- Produces: `EvidenceStore.set_retention(policy: RetentionPolicy) -> None`
- Produces: `EvidenceStore.purge(evidence_id: str, reason: str) -> None`

- [ ] **Step 1: Write failing permission, hash, dedupe, metadata, retention, and purge tests**

```python
def test_default_retention_never_deletes_automatically(self):
    self.assertEqual("keep_until_user_deletes", self.store.retention().mode)
    self.assertIsNone(self.store.retention().days)

def test_explicit_purge_removes_object_and_appends_tombstone(self):
    record = self.store.put(self.draft, redact_bytes)
    self.store.purge(record.evidence_id, "user request")
    self.assertFalse(record.object_path.exists())
    self.assertEqual("evidence.purged", self.events.list_for_task(self.task_id)[-1].event_type)
```

- [ ] **Step 2: Run the tests and observe RED**

Run: `PYTHONPATH=src uv run --python 3.12 python -m unittest tests.test_evidence -v`

Expected: import failure because `devharness.evidence` does not exist.

- [ ] **Step 3: Implement file-first content-addressed storage**

Redact bytes first, hash the redacted content, write a same-directory temporary file with 0600, flush and fsync, then atomically replace the final object. Store metadata only after the final object exists. Use `<root>/objects/<first-two-hash-chars>/<remaining-hash>` and verify the hash on read. Default retention is `keep_until_user_deletes`; no timer or startup cleanup exists. Purge requires a non-empty reason, deletes only the resolved object, marks metadata purged, and appends an `evidence.purged` Event.

- [ ] **Step 4: Run Evidence and Git-leak checks**

Run: `PYTHONPATH=src uv run --python 3.12 python -m unittest tests.test_evidence -v`

Run: `git check-ignore .dev-harness/probe.raw`

Run: `git status --short`

Expected: tests pass; `.dev-harness` is ignored; no Raw Evidence path is tracked.

- [ ] **Step 5: Commit**

Commit message: `feat: add local evidence store`.

---

### Task 4: Projection replay and freshness

**Files:**
- Create: `src/devharness/projections.py`
- Create: `tests/test_projections.py`
- Modify: `src/devharness/catalog.py`

**Interfaces:**
- Consumes: `EventLog.list_for_task()`, `EventLog.head_sequence()`
- Produces: `ProjectionEngine.project(task_id: str) -> ProjectionStatus`
- Produces: `ProjectionEngine.rebuild(task_id: str) -> ProjectionStatus`
- Produces: `ProjectionEngine.freshness(task_id: str) -> Freshness`

- [ ] **Step 1: Write failing replay, lag, handler failure, and unknown-version tests**

```python
def test_rebuild_recreates_the_same_projection(self):
    expected = self.engine.project(self.task_id)
    rebuilt = self.engine.rebuild(self.task_id)
    self.assertEqual(expected.state, rebuilt.state)
    self.assertEqual(expected.projected_sequence, rebuilt.projected_sequence)

def test_unknown_event_version_fails_freshness(self):
    self.append_event(event_type="task.created", event_version=99)
    status = self.engine.project(self.task_id)
    self.assertEqual("failed", status.state)
    self.assertFalse(self.engine.freshness(self.task_id).is_fresh)
```

- [ ] **Step 2: Run the tests and observe RED**

Run: `PYTHONPATH=src uv run --python 3.12 python -m unittest tests.test_projections -v`

Expected: import failure because `devharness.projections` does not exist.

- [ ] **Step 3: Implement deterministic replay**

Support version 1 handlers for `task.created`, `evidence.recorded`, `evidence.purged`, and `guarantee.evaluated`. Store projection JSON, projected sequence, state, and last error. Process Events in sequence order within one transaction. Unknown type/version or handler exception records failure without advancing past the failing Event. `freshness()` returns Event head, projected sequence, projection state, `is_fresh`, and separately keeps `collection_completeness="unobserved"`.

- [ ] **Step 4: Run Projection and full tests**

Run: `PYTHONPATH=src uv run --python 3.12 python -m unittest tests.test_projections -v`

Run: `PYTHONPATH=src uv run --python 3.12 python -m unittest discover -s tests -v`

Expected: deterministic rebuild and all failure-path tests pass.

- [ ] **Step 5: Commit**

Commit message: `feat: add replayable task projections`.

---

### Task 5: Matrix-backed Guarantee Evaluator

**Files:**
- Create: `src/devharness/guarantees.py`
- Create: `tests/test_guarantees.py`
- Create: `tests/fixtures/guarantee_attacks.json`
- Modify: `src/devharness/catalog.py`

**Interfaces:**
- Consumes: Guarantee Matrix JSON, `IdentityRegistry`, `EvidenceStore`, canonical Control Validation JSON records
- Produces: `GuaranteeEvaluator.evaluate(task_id: str, claim_ids: list[str] | None = None) -> dict`
- Produces: `GuaranteeEvaluator.record_control_validation(task_id: str, record: dict) -> None`

- [ ] **Step 1: Port adversarial tests before implementation**

```python
def test_imported_managed_only_claim_is_not_evaluated(self):
    report = self.evaluator.evaluate(self.imported_task_id, ["GM-002"])
    self.assertEqual("not_evaluated", report["claim_results"][0]["verdict"])

def test_observed_failure_overrides_pass_and_conflict_is_contradicted(self):
    self.add_required_evidence(result="pass", basis="observed")
    self.add_control(result="pass")
    self.add_control(record_id="control-fail", result="fail")
    report = self.evaluator.evaluate(self.managed_task_id, ["GM-001"])
    self.assertEqual("contradicted", report["claim_results"][0]["verdict"])
```

The fixture set also covers unknown Claim, Matrix version mismatch, missing/extra/duplicate requirement ID, duplicate Claim result rejection, Evidence ID/type/field/subject/scope mismatch, omitted canonical Control, different Control instance, empty Evidence material, and forbidden wording.

- [ ] **Step 2: Run the tests and observe RED**

Run: `PYTHONPATH=src uv run --python 3.12 python -m unittest tests.test_guarantees -v`

Expected: import failure because `devharness.guarantees` does not exist.

- [ ] **Step 3: Implement evaluator from authoritative Store queries**

Load exactly one Matrix version and reject duplicate Claim or requirement IDs. Query all non-purged Evidence for the Task; do not accept caller-supplied verdicts or Evidence objects. Resolve every required type and field, preserve exact subject/scope, and query every matching canonical Control record. Apply precedence: observed fail or pass/fail conflict → `contradicted`; inapplicable mode, missing material, not_run, unobserved, disallowed basis, mismatched selector, or unresolved reference → `not_evaluated`; only complete observed pass Evidence and complete Control closure → `supported`. Emit Matrix claim wording and residual risks only.

- [ ] **Step 4: Run Guarantee attacks and all tests**

Run: `PYTHONPATH=src uv run --python 3.12 python -m unittest tests.test_guarantees -v`

Run: `PYTHONPATH=src uv run --python 3.12 python -m unittest discover -s tests -v`

Expected: every attack is rejected or downgraded to the required verdict; no caller-provided wording enters the Report.

- [ ] **Step 5: Commit**

Commit message: `feat: evaluate task guarantees from stored evidence`.

---

### Task 6: HWPX fixture vertical POC and minimum review artifact

**Files:**
- Create: `src/devharness/review.py`
- Create: `src/devharness/__main__.py`
- Create: `tests/test_vertical_poc.py`
- Create: `tests/fixtures/hwpx_package_inspection.json`
- Create: `docs/reviews/m1/README.md`
- Create: `README.md`
- Modify: `docs/product/Requirements_Traceability.md`

**Interfaces:**
- Consumes: identity, Event, Evidence, Projection, Guarantee services
- Produces: `render_task_review(report: dict, freshness: Freshness, evidence_records: list[EvidenceRecord]) -> str`
- Produces CLI: `python -m devharness m1-demo --data-root PATH --output PATH`

- [ ] **Step 1: Write the failing end-to-end test**

```python
def test_fixture_flows_from_event_to_report_and_html_without_raw_evidence(self):
    result = run_m1_demo(self.data_root, self.output_path, self.fixture_path)
    html = self.output_path.read_text(encoding="utf-8")
    self.assertEqual("supported", result.report["claim_results"][0]["verdict"])
    self.assertIn("관련 테스트를 실행했다", html)
    self.assertIn(result.evidence_id, html)
    self.assertNotIn("raw package bytes", html)
    self.assertIn("수집 완전성: Unobserved", html)
```

- [ ] **Step 2: Run the test and observe RED**

Run: `PYTHONPATH=src uv run --python 3.12 python -m unittest tests.test_vertical_poc -v`

Expected: import failure because `devharness.review` and the CLI do not exist.

- [ ] **Step 3: Implement the fixture pipeline and escaped HTML**

The fixture describes a synthetic HWPX ZIP-part inspection command, environment, target commit, selection scope, and observed result. The demo registers identities, appends Task/Event records, stores redacted Evidence, projects Events, evaluates GM-013, appends `guarantee.evaluated`, refreshes the Projection, and renders escaped summary HTML. The HTML includes verdict, Evidence ID, hash, scope, freshness, residual risk, and Unobserved collection completeness, but not Raw Evidence bytes or a Production UI layout.

- [ ] **Step 4: Run the exact M1 Gate**

Run: `PYTHONPATH=src uv run --python 3.12 python -m unittest discover -s tests -v`

Run: `PYTHONPATH=src uv run --python 3.12 python -m devharness m1-demo --data-root /tmp/devharness-m1-evidence --output /tmp/devharness-m1-review.html`

Run: `uv run --python 3.12 python -m compileall -q src tests`

Run: `git diff --check origin/main...HEAD`

Run: `git ls-files | rg '(^|/)(raw|objects|catalog\.sqlite3)'` and expect no output.

- [ ] **Step 5: Self-review the plan and implementation**

Confirm every M1 issue has a test, Evidence, Non-goal, and an explicit Unobserved boundary. Confirm no placeholder terms remain and all function names match the interfaces above.

- [ ] **Step 6: Commit, push, independent review, and PR**

Commit message: `feat: add M1 evidence vertical slice`. Push `m1/evidence-core`, open one M1 PR linking #10–#15 without automatic close keywords, run an independent fail-open/data-integrity review, fix findings, rerun the full Gate, then merge only with zero blocking findings. Close #10–#15 after the merged-main verification and keep #7 open.

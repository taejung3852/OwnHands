# M5 Dashboard Vertical Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 기존 M1~M4 truth source를 재해석하지 않고, 한 Task를 쉬운 말 Summary → Trace → Evidence → Decision 순서로 검토하는 5-route local Dashboard를 구현하고 M5-01~M5-09를 검증한다.

**Architecture:** Python 3.12 표준 라이브러리 loopback SSR이다. 저장되는 새 사실은 versioned Assurance reference와 Decision Event뿐이다. `TaskReviewView`는 요청마다 canonical source를 검증하는 비영속 read model이고, resolver는 M1 Store reference와 M4 logical reference를 구분한다.

**Tech Stack:** Python 3.12 stdlib, SQLite, `unittest`, 기존 Node/Chrome DevTools Protocol browser probe 방식

**Spec:** `docs/superpowers/specs/2026-09-06-m5-dashboard-vertical-design.md`

## Global constraints

- `pyproject.toml`의 `dependencies = []`와 `runtime = "stdlib-only"`를 유지한다. SPA, framework, component library, remote asset, telemetry를 추가하지 않는다.
- 실제 M3/M4 packet은 저장소에 복사하지 않는다. `/tmp/ownhands-m3-runtime-path-closure-20260906.json`과 `/tmp/ownhands-m4-actual-packet-568c46e.json`이 없으면 actual Gate를 실패시킨다.
- M3 actual packet은 project-level, M4 actual packet은 그 packet의 task-level observation이다. 둘을 같은 Task 성공으로 합치지 않는다. M5에서 새로 생성하는 same-task vertical만 end-to-end closure를 증명한다.
- TGR 부재/identity mismatch는 `Not Evaluated`, HWPX adapter 또는 사람 관찰 부재는 `Unobserved`다.
- 모든 data directory는 0700, packet/review/export/cache는 atomic 0600이다. Raw path, private command prefix, object path, secret-like field를 화면과 export에서 제거한다.
- Hard Block의 `accept`/`risk_acceptance`와 stale/failed Projection의 모든 Decision을 UI와 서버에서 거부한다.
- ADR-0007에는 “사용자 사전 위임에 따른 에이전트 결정”과 “사용자가 세부 UI/UX를 직접 검토하지 않았다”를 함께 기록한다.
- 각 Task는 RED test → 실패 확인 → 최소 구현 → GREEN 확인 → 독립 커밋 순서로 실행한다.

## File map

| Boundary | Production/review files | Split tests |
|---|---|---|
| Event + security | `src/devharness/dashboard_events.py`, `src/devharness/projections.py`, `src/devharness/dashboard_security.py`, `src/devharness/m4_review.py` | `tests/test_dashboard_events.py`, `tests/test_dashboard_security.py`, `tests/test_m4_review.py` |
| Sources + view | `src/devharness/dashboard_sources.py`, `src/devharness/dashboard_view.py` | `tests/test_dashboard_identity.py`, `tests/test_dashboard_evidence.py`, `tests/test_dashboard_view.py`, `tests/test_dashboard_freshness.py` |
| Actions + server | `src/devharness/dashboard_actions.py`, `src/devharness/dashboard_server.py`, `src/devharness/__main__.py` | `tests/test_dashboard_actions.py`, `tests/test_dashboard_server.py`, `tests/test_dashboard_http_security.py` |
| SSR + export | `src/devharness/dashboard_assets.py`, `src/devharness/dashboard_render.py`, `src/devharness/dashboard_export.py` | `tests/test_dashboard_render.py`, `tests/test_dashboard_accessibility.py`, `tests/test_dashboard_export.py` |
| Vertical + trace | `tests/fixtures/m5/same-task-input.json`, `docs/reviews/m5/*`, ADR/product docs | `tests/test_dashboard_actual_packets.py`, `tests/test_dashboard_vertical.py`, `tests/test_m5_scope_trace.py` |

---

### Task 1: Canonical Decision/Assurance references and security primitives

**M5 coverage:** M5-07, M5-08; all routes’ privacy prerequisite

**Files:**
- Create: `src/devharness/dashboard_events.py`
- Create: `src/devharness/dashboard_security.py`
- Modify: `src/devharness/projections.py`
- Modify: `src/devharness/m4_review.py`
- Create: `tests/test_dashboard_events.py`
- Create: `tests/test_dashboard_security.py`
- Modify: `tests/test_m4_review.py`

**Exact public signatures:**

```text
record_assurance_reference(events: EventLog, *, event_id: str, task_id: str, packet_fingerprint: str, gate_fingerprint: str, gate_decision: str, evidence_refs: Sequence[str], occurred_at: str) -> EventRecord
record_task_decision(events: EventLog, *, event_id: str, task_id: str, assurance_packet_fingerprint: str, gate_fingerprint: str, gate_decision: str, decision: str, decision_source: str, actor_ref: str, reason: str, residual_risks: Sequence[str], follow_up: str, evidence_refs: Sequence[str], occurred_at: str) -> EventRecord
private_atomic_write(path: Path, content: bytes | str) -> None
mask_dashboard_text(value: str, *, private_roots: Sequence[Path]) -> str
mask_dashboard_value(value: object, *, private_roots: Sequence[Path]) -> object
require_opaque_identifier(value: str, name: str) -> str
issue_session_token() -> str
issue_csrf_token(session_token: str) -> str
validate_request_security(*, host: str, token: str, expected_token: str, method: str, origin: str | None, expected_origin: str, csrf_token: str | None, expected_csrf_token: str) -> None
```

- [ ] **Step 1: Write RED Event/Projection and Hard Block tests in `tests/test_dashboard_events.py`.**

```python
assurance = record_assurance_reference(
    events,
    event_id="event:assurance:1",
    task_id=task.task_id,
    packet_fingerprint="sha256:" + "a" * 64,
    gate_fingerprint="sha256:" + "b" * 64,
    gate_decision="soft_block",
    evidence_refs=("evidence:gate",),
    occurred_at=NOW,
)
decision = record_task_decision(
    events,
    event_id="event:decision:1",
    task_id=task.task_id,
    assurance_packet_fingerprint=assurance.payload["packet_fingerprint"],
    gate_fingerprint=assurance.payload["gate_fingerprint"],
    gate_decision="soft_block",
    decision="revise",
    decision_source="product_authority",
    actor_ref="actor:local-user",
    reason="Human observation is missing",
    residual_risks=("HWPX observation remains unobserved",),
    follow_up="Run the registered HWPX adapter",
    evidence_refs=("evidence:gate",),
    occurred_at=NOW,
)
status = projections.project(task.task_id)
self.assertEqual("event:decision:1", status.projection["decision"]["event_id"])
with self.assertRaisesRegex(ValueError, "Hard Block"):
    record_task_decision(events, **hard_block_accept_values)
```

Also assert same Event ID+same content is idempotent, changed content raises `EventConflict`, unsupported version fails Projection, and Decision must reference the latest projected packet/Gate.

- [ ] **Step 2: Write RED permission/masking/request tests in `tests/test_dashboard_security.py` and `tests/test_m4_review.py`.**

```python
target = root / "review.html"
target.write_text("old", encoding="utf-8")
target.chmod(0o644)
private_atomic_write(target, "new")
self.assertEqual(0o600, stat.S_IMODE(target.stat().st_mode))
self.assertEqual(
    {"command": "[private-root]/.venv/bin/python -m unittest tests", "api_token": "[redacted]"},
    mask_dashboard_value(
        {"command": "/Users/example/worktree/.venv/bin/python -m unittest tests", "api_token": "secret"},
        private_roots=(Path("/Users/example/worktree"),),
    ),
)
with self.assertRaises(RequestSecurityError):
    validate_request_security(
        host="0.0.0.0", token="session", expected_token="session", method="POST",
        origin="http://127.0.0.1:8765", expected_origin="http://127.0.0.1:8765",
        csrf_token="csrf", expected_csrf_token="csrf",
    )
```

Assert opaque IDs reject slash, backslash, `%2f`, `..`, NUL, URL scheme, and whitespace. Assert all M4 fixture packet/review/raw outputs are 0600 and parent directories 0700.

- [ ] **Step 3: Run RED.**

Run: `PYTHONPATH=src uv run --python 3.12 python -m unittest -v tests.test_dashboard_events tests.test_dashboard_security tests.test_m4_review`

Expected: FAIL because dashboard modules/Projection handlers are absent and existing M4 writes can preserve 0644.

- [ ] **Step 4: Implement the minimum Event and Projection contract.**

```python
def record_task_decision(events: EventLog, **values: object) -> EventRecord:
    decision = _member(values["decision"], DECISIONS, "decision")
    gate = _member(values["gate_decision"], GATE_DECISIONS, "gate_decision")
    if gate == "hard_block" and decision in {"accept", "risk_acceptance"}:
        raise ValueError("Hard Block cannot be accepted or risk accepted")
    return events.append(
        EventDraft(
            event_id=_text(values["event_id"], "event_id"),
            task_id=_text(values["task_id"], "task_id"),
            event_type="task.decision.recorded",
            event_version=1,
            occurred_at=_text(values["occurred_at"], "occurred_at"),
            payload=_decision_payload(values, decision, gate),
            collection_method="dashboard-decision-form",
            redaction_status="redacted",
        ),
        lambda payload: payload,
    )
```

Add `assurance.references` and `decision` to `_initial_projection()`. Register `("assurance.evaluated", 1)` and `("task.decision.recorded", 1)`. Store exact packet/Gate fingerprints, Event ID/sequence, actor/source, reason, residual risks, follow-up, Evidence refs, and occurred time. Reject a Decision whose packet/Gate is not the latest Assurance reference.

- [ ] **Step 5: Implement private writes and request primitives; reuse them in M4.**

```python
def private_atomic_write(path: Path, content: bytes | str) -> None:
    payload = content.encode("utf-8") if isinstance(content, str) else content
    path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    os.chmod(path.parent, 0o700)
    descriptor, name = tempfile.mkstemp(dir=path.parent, prefix=f".{path.name}.")
    temporary = Path(name)
    try:
        os.fchmod(descriptor, 0o600)
        with os.fdopen(descriptor, "wb") as stream:
            stream.write(payload)
            stream.flush()
            os.fsync(stream.fileno())
        temporary.replace(path)
        os.chmod(path, 0o600)
    except BaseException:
        temporary.unlink(missing_ok=True)
        raise
```

Use `secrets.token_urlsafe(32)` and `hmac.compare_digest`. GET requires loopback+session token; POST additionally requires exact Origin+CSRF. Mask secret-key fragments recursively and replace configured private root prefixes; never return raw object paths. Replace `m4_review._write` with `private_atomic_write`.

- [ ] **Step 6: Run GREEN and commit.**

Run: `PYTHONPATH=src uv run --python 3.12 python -m unittest -v tests.test_dashboard_events tests.test_dashboard_security tests.test_events tests.test_projections tests.test_m4_review`

Expected: PASS; Decision references are canonical/idempotent, Hard Block is not overridable, and artifacts are private.

```bash
git add src/devharness/dashboard_events.py src/devharness/dashboard_security.py src/devharness/projections.py src/devharness/m4_review.py tests/test_dashboard_events.py tests/test_dashboard_security.py tests/test_m4_review.py
git commit -m "feat: add secure dashboard event contracts"
```

---

### Task 2: Evidence resolver, identity/freshness, and TaskReviewView

**M5 coverage:** M5-01, M5-02, M5-03, M5-04, M5-05; M5-07 eligibility input

**Files:**
- Create: `src/devharness/dashboard_sources.py`
- Create: `src/devharness/dashboard_view.py`
- Create: `tests/test_dashboard_identity.py`
- Create: `tests/test_dashboard_evidence.py`
- Create: `tests/test_dashboard_view.py`
- Create: `tests/test_dashboard_freshness.py`

**Exact public signatures:**

```text
validate_m3_source(*, task: TaskIdentity, packet: object) -> SourceClosure
validate_m3_packet(packet: object) -> dict
m3_task_ref(task_id: str) -> str
validate_m4_source(*, task: TaskIdentity, packet: object) -> SourceClosure
resolve_evidence(store: EvidenceStore, *, task_id: str, evidence_id: str, assurance_packet: dict | None, disclose_raw: bool = False) -> tuple[EvidenceView, bytes | None]
assemble_task_review(*, task: TaskIdentity, events: EventLog, projection: ProjectionStatus, freshness: Freshness, evidence_store: EvidenceStore, baseline: dict | None, context_status: dict | None, execution_contract: dict | None, m3_packet: dict | None, assurance_packet: dict | None, guarantee_report: dict | None, assembled_at: str) -> TaskReviewView
```

`SourceClosure` fields: `source`, `scope` (`project|task`), `status` (`closed|mismatch|unavailable|invalid|unobserved`), `task_applicable`, `observed_at`, `fingerprint`, `reasons`. `EvidenceView` fields: `evidence_id`, `reference_kind` (`store|reference_only|unavailable`), `task_id`, `result`, `basis`, `content_hash`, `content_size`, `redaction_status`, `raw_available`, allowlisted `metadata`. `TaskReviewView` has `task`, `summary`, `freshness`, `completeness`, `diagram`, `relations`, `verification`, `guarantees`, `harness`, `assurance`, `decision`, `history`, `evidence`, `assembled_at`.

- [ ] **Step 1: Write RED identity/resolver tests in their separate files.**

```python
closure = validate_m3_source(task=task, packet=m3_packet_for_other_task)
self.assertEqual("project", closure.scope)
self.assertFalse(closure.task_applicable)
self.assertIn("task_ref mismatch", closure.reasons)

view, content = resolve_evidence(
    store,
    task_id=task.task_id,
    evidence_id="evidence:m4:logical",
    assurance_packet=m4_with_unregistered_logical_ref,
)
self.assertEqual("reference_only", view.reference_kind)
self.assertFalse(view.raw_available)
self.assertIsNone(content)
```

Assert M4 canonical `project_id/worktree_id/task_id/environment_ref/mode`, Contract fingerprint, packet/patch/Gate identity all close. Assert registered M4 Evidence requires same Task and `fields.packet_fingerprint == packet["fingerprint"]`. Assert purge, hash/size mismatch, cross-task row, symlink, and traversal-like ID fail closed.

- [ ] **Step 2: Write RED view/freshness tests.**

```python
view = assemble_task_review(**same_task_sources, guarantee_report=None)
self.assertEqual(("summary", "trace", "evidence", "decision"), view.summary["disclosure_order"])
self.assertEqual("not_evaluated", view.guarantees[0]["status"])
self.assertEqual("unobserved", direct_validation_row(view)["basis"])
self.assertEqual("fresh", view.freshness["state"])
self.assertEqual("unobserved", view.completeness["state"])

stale = assemble_task_review(**complete_sources_with_lag)
self.assertEqual("stale", stale.freshness["state"])
self.assertEqual("complete", stale.completeness["state"])
self.assertFalse(stale.decision["submission_allowed"])
```

Assert six visible results are `passed`, `failed`, `not_run`, `no_adequate_test`, `inconclusive`, `unknown`; relation priority is source-derived; a relationless Diagram is `unobserved`; repeated assembly writes no Catalog row/file.

- [ ] **Step 3: Run RED.**

Run: `PYTHONPATH=src uv run --python 3.12 python -m unittest -v tests.test_dashboard_identity tests.test_dashboard_evidence tests.test_dashboard_view tests.test_dashboard_freshness`

Expected: FAIL with missing source/view modules.

- [ ] **Step 4: Implement exact source closure and resolver.**

```python
def resolve_evidence(store: EvidenceStore, *, task_id: str, evidence_id: str,
                     assurance_packet: dict | None, disclose_raw: bool = False) -> tuple[EvidenceView, bytes | None]:
    require_opaque_identifier(evidence_id, "evidence_id")
    logical_refs = frozenset(assurance_packet["evidence_refs"]) if assurance_packet else frozenset()
    try:
        record = store.resolve(evidence_id)
    except ValueError as error:
        if evidence_id in logical_refs and "unknown evidence" in str(error):
            return _logical_reference_view(task_id, evidence_id), None
        raise
    if record.task_id != task_id:
        raise ValueError("Evidence Task binding mismatch")
    if assurance_packet and evidence_id in logical_refs:
        if record.fields.get("packet_fingerprint") != assurance_packet["fingerprint"]:
            raise ValueError("Evidence packet fingerprint mismatch")
    content = store.read_content(evidence_id) if disclose_raw else None
    return _store_view(record), content
```

`validate_m4_source` calls `validate_packet_document` first. `validate_m3_packet` validates the allowlisted shape, packet fingerprint, six control×three stage states, Event/Evidence closure, runtime Gate, and human-friction state. `m3_task_ref` reproduces M3's canonical `sha256:` reference from `{"task_id": task_id}`; it never compares raw paths. `validate_m3_source` may return project runtime provenance when task ref differs, but never current-task Loaded/Enforced. Ref strings are never filesystem paths; `object_path` never enters view metadata.

- [ ] **Step 5: Implement non-persistent deterministic assembly.**

```python
def assemble_task_review(*, task: TaskIdentity, events: EventLog, projection: ProjectionStatus,
                         freshness: Freshness, evidence_store: EvidenceStore, baseline: dict | None,
                         context_status: dict | None, execution_contract: dict | None,
                         m3_packet: dict | None, assurance_packet: dict | None,
                         guarantee_report: dict | None, assembled_at: str) -> TaskReviewView:
    m3 = validate_m3_source(task=task, packet=m3_packet) if m3_packet else _unavailable("m3")
    m4 = validate_m4_source(task=task, packet=assurance_packet) if assurance_packet else _unavailable("m4")
    return TaskReviewView(
        task=_task_identity(task),
        summary=_source_backed_summary(execution_contract, assurance_packet, m4),
        freshness=_freshness_view(freshness),
        completeness=_completeness(m3, m4, guarantee_report),
        diagram=_bounded_diagram(execution_contract, assurance_packet, m4),
        relations=_relations(execution_contract, assurance_packet, m4),
        verification=_verification(assurance_packet, m4),
        guarantees=_guarantees(task, guarantee_report),
        harness=_harness(baseline, context_status, m3),
        assurance=_assurance(assurance_packet, m4),
        decision=_decision(projection, freshness, m4),
        history=_history(events.list_for_task(task.task_id)),
        evidence=_evidence_views(evidence_store, task.task_id, assurance_packet),
        assembled_at=_iso_time(assembled_at),
    )
```

Summary uses only Task goal, Contract mapping, changed paths, declared relations. Diagram emits only source-ref nodes/edges. `required` derives from Hard Block/required impacted tests, `recommended` from Soft Block/bounded Unobserved, otherwise `reference`. Missing/mismatched TGR yields `Not Evaluated`; missing HWPX observation yields `Unobserved`. Freshness compares Event head/projected sequence; completeness independently evaluates required source collection.

- [ ] **Step 6: Run GREEN and commit.**

Run: `PYTHONPATH=src uv run --python 3.12 python -m unittest -v tests.test_dashboard_identity tests.test_dashboard_evidence tests.test_dashboard_view tests.test_dashboard_freshness tests.test_evidence tests.test_assurance tests.test_projections`

Expected: PASS; no cross-task aggregation, logical refs stay Reference Only, and assembly is non-persistent.

```bash
git add src/devharness/dashboard_sources.py src/devharness/dashboard_view.py tests/test_dashboard_identity.py tests/test_dashboard_evidence.py tests/test_dashboard_view.py tests/test_dashboard_freshness.py
git commit -m "feat: assemble trusted task review views"
```

---

### Task 3: Feature/Decision actions and five-route loopback server

**M5 coverage:** M5-01, M5-05, M5-06, M5-07, M5-08 route/action boundary

**Files:**
- Create: `src/devharness/dashboard_actions.py`
- Create: `src/devharness/dashboard_server.py`
- Modify: `src/devharness/__main__.py`
- Create: `tests/test_dashboard_actions.py`
- Create: `tests/test_dashboard_server.py`
- Create: `tests/test_dashboard_http_security.py`

**Exact public signatures:**

```text
ValidationAdapter.validate(request: ValidationRequest) -> ValidationObservation
run_feature_validation(*, adapter: ValidationAdapter | None, request: ValidationRequest, evidence_store: EvidenceStore, evidence_id: str, occurred_at: str) -> EvidenceRecord
submit_task_decision(*, view: TaskReviewView, events: EventLog, form: Mapping[str, str], event_id: str, occurred_at: str) -> EventRecord
route_request(*, method: str, path: str, query: Mapping[str, Sequence[str]], headers: Mapping[str, str], body: bytes, config: DashboardConfig, services: DashboardServices) -> DashboardResponse
create_dashboard_server(config: DashboardConfig, services: DashboardServices) -> ThreadingHTTPServer
serve_dashboard(config: DashboardConfig, services: DashboardServices) -> None
```

`DashboardConfig`: loopback host, port, session token, data root. `DashboardServices`: `load_view`, `resolve_evidence`, `validate_feature`, `decide`, `export_history`. Exactly five GET patterns:

```text
/tasks/{task_id}
/tasks/{task_id}/harness
/tasks/{task_id}/validate/{subject_ref}
/tasks/{task_id}/history
/tasks/{task_id}/evidence/{evidence_id}
```

- [ ] **Step 1: Write RED action tests.**

```python
record = run_feature_validation(
    adapter=None,
    request=ValidationRequest(task.task_id, "subject:hwpx:bold", "Bold is preserved", "sample.hwpx"),
    evidence_store=store,
    evidence_id="evidence:direct:1",
    occurred_at=NOW,
)
self.assertEqual(("direct_feature_probe", "not_run", "unobserved"),
                 (record.evidence_type, record.result, record.basis))

for view, decision in ((stale_view, "revise"), (hard_block_view, "accept")):
    with self.subTest(decision=decision), self.assertRaisesRegex(ValueError, "stale|Hard Block"):
        submit_task_decision(view=view, events=events, form=decision_form(decision), event_id="event:x", occurred_at=NOW)
```

Assert registered adapter records input/environment/expected/actual/generated files/tool error/human observation as M1 `direct_feature_probe`. Soft Block risk acceptance requires exact Gate, reason, residual risk, and `product_authority`.

- [ ] **Step 2: Write RED route/security tests.**

```python
for path in five_route_paths:
    with self.subTest(path=path):
        self.assertEqual(200, self.get(path).status)
self.assertEqual(404, self.get("/").status)
self.assertEqual(404, self.get(f"/tasks/{TASK}/analytics").status)

for headers in (valid_headers | {"Origin": "http://evil.invalid"}, valid_headers | {"X-CSRF-Token": "wrong"}):
    with self.subTest(headers=headers):
        self.assertEqual(403, self.post(f"/tasks/{TASK}", headers=headers).status)
self.assertEqual(409, self.post_hard_block_accept().status)
```

Assert token is required on every request; decoded path/traversal IDs fail before lookup; metadata is Evidence GET default; `raw=1` is explicit; Raw active markup is escaped; task POST reloads current view before Decision; validation POST uses the same validation route.

- [ ] **Step 3: Run RED.**

Run: `PYTHONPATH=src uv run --python 3.12 python -m unittest -v tests.test_dashboard_actions tests.test_dashboard_server tests.test_dashboard_http_security`

Expected: FAIL with missing action/server modules.

- [ ] **Step 4: Implement bounded actions.**

```python
def run_feature_validation(*, adapter: ValidationAdapter | None, request: ValidationRequest,
                           evidence_store: EvidenceStore, evidence_id: str, occurred_at: str) -> EvidenceRecord:
    observation = adapter.validate(request) if adapter else ValidationObservation(
        result="not_run", basis="unobserved", actual="No registered adapter or human observation",
        generated_files=(), tool_error=None, human_observation=None,
    )
    return evidence_store.put(EvidenceDraft(
        evidence_id=evidence_id, task_id=request.task_id, requirement_id="M5-06",
        evidence_type="direct_feature_probe", subject_ref=request.subject_ref,
        exact_scope=request.input_summary, result=observation.result, basis=observation.basis,
        fields=_allowlisted_observation(request, observation, occurred_at),
        content=_observation_bytes(observation), collection_method=_collection_method(adapter),
        redaction_status="redacted",
    ), lambda content: content)
```

`submit_task_decision` rechecks current Task, packet/Gate fingerprints, Projection freshness, Gate policy, non-empty reason/actor/follow-up, and authority before calling Task 1. It never approves tool execution, merge, deploy, or cleanup.

- [ ] **Step 5: Implement exact router/server and CLI.**

```python
GET_ROUTES = (
    re.compile(r"^/tasks/(?P<task_id>[^/]+)$"),
    re.compile(r"^/tasks/(?P<task_id>[^/]+)/harness$"),
    re.compile(r"^/tasks/(?P<task_id>[^/]+)/validate/(?P<subject_ref>[^/]+)$"),
    re.compile(r"^/tasks/(?P<task_id>[^/]+)/history$"),
    re.compile(r"^/tasks/(?P<task_id>[^/]+)/evidence/(?P<evidence_id>[^/]+)$"),
)

def create_dashboard_server(config: DashboardConfig, services: DashboardServices) -> ThreadingHTTPServer:
    if config.host not in {"127.0.0.1", "::1"}:
        raise ValueError("Dashboard must bind to loopback")
    return ThreadingHTTPServer((config.host, config.port), _handler(config, services))
```

Decode once, validate opaque IDs, enforce Task 1 security, and return no-store headers. Set CSP `default-src 'none'; style-src 'nonce-{nonce}'; script-src 'nonce-{nonce}'; img-src 'self' data:; form-action 'self'; frame-ancestors 'none'`, `X-Content-Type-Options: nosniff`, and `Referrer-Policy: no-referrer`. Disable `BaseHTTPRequestHandler` request logging. The CLI issues a one-use `?session_token=` bootstrap URL; the server validates it once, sets an HttpOnly/SameSite=Strict cookie, invalidates the bootstrap value, and redirects to a clean URL under `Referrer-Policy: no-referrer`. Later links never contain a token. Add `PYTHONPATH=src uv run --python 3.12 python -m devharness dashboard --data-root PATH --host 127.0.0.1 --port 0`; reject non-loopback and never print private packet paths.

- [ ] **Step 6: Run GREEN and commit.**

Run: `PYTHONPATH=src uv run --python 3.12 python -m unittest -v tests.test_dashboard_actions tests.test_dashboard_server tests.test_dashboard_http_security tests.test_dashboard_events tests.test_dashboard_security`

Expected: PASS against an ephemeral `127.0.0.1:0` server; five GET shapes only, CSRF/Origin/token enforced, stale/Hard Block rejected server-side.

```bash
git add src/devharness/dashboard_actions.py src/devharness/dashboard_server.py src/devharness/__main__.py tests/test_dashboard_actions.py tests/test_dashboard_server.py tests/test_dashboard_http_security.py
git commit -m "feat: serve secure dashboard review actions"
```

---

### Task 4: SSR components, Ledger themes, accessible SVG, and masked export

**M5 coverage:** visible product for M5-01~M5-08

**Files:**
- Create: `src/devharness/dashboard_assets.py`
- Create: `src/devharness/dashboard_render.py`
- Create: `src/devharness/dashboard_export.py`
- Create: `tests/test_dashboard_render.py`
- Create: `tests/test_dashboard_accessibility.py`
- Create: `tests/test_dashboard_export.py`

**Exact public signatures:**

```text
dashboard_css() -> str
dashboard_script() -> str
render_task_review(view: TaskReviewView, *, csrf_token: str) -> str
render_harness_status(view: TaskReviewView) -> str
render_feature_validation(view: TaskReviewView, *, subject_ref: str, csrf_token: str) -> str
render_history(view: TaskReviewView) -> str
render_evidence_detail(view: TaskReviewView, *, evidence: EvidenceView, raw: bytes | None) -> str
render_document(*, title: str, task_id: str, main: str, status: str, nonce: str) -> bytes
export_masked_history(*, view: TaskReviewView, sections: Sequence[str], private_roots: Sequence[Path], exported_at: str) -> bytes
```

- [ ] **Step 1: Write RED renderer/accessibility tests.**

```python
page = render_task_review(view, csrf_token="csrf")
positions = [page.index(f'id="{section}"') for section in ("summary", "trace", "evidence", "decision")]
self.assertEqual(sorted(positions), positions)
self.assertIn("<details", page)
self.assertNotIn("<script>alert(1)</script>", page)
self.assertRegex(page, r'<svg[^>]+aria-labelledby="task-[^"]+-diagram-title task-[^"]+-diagram-desc"')
self.assertRegex(page, r'<svg[^>]*>\s*<title id="task-[^"]+-diagram-title">')
self.assertIn('class="diagram-fallback"', page)
for evidence_id in view.diagram["evidence_refs"]:
    self.assertGreaterEqual(page.count(f"/evidence/{evidence_id}"), 2)
```

Assert Korean `lang`, skip link, landmarks, one H1, ordered headings, native labels, named overflow regions, no positive tabindex, status text+symbol, hard-block controls absent, SVG unique prefixed IDs/title/desc, and HTML fallback. Assert CSS contains B Warm Paper/Ledger Indigo Light/Dark tokens, focus/status separation, reduced motion, 320/390/1440 rules, no `@import` or remote URL.

- [ ] **Step 2: Write RED export tests.**

```python
payload = json.loads(export_masked_history(
    view=view,
    sections=("summary", "history"),
    private_roots=(private_root,),
    exported_at=NOW,
))
self.assertEqual({"task", "summary", "history", "exported_at"}, set(payload))
serialized = json.dumps(payload)
self.assertNotIn(str(private_root), serialized)
self.assertNotIn("raw_payload", serialized)
self.assertNotIn("object_path", serialized)
```

Assert only `summary`, `verification`, `guarantees`, `history`, `decision` are accepted; prompts, transcripts, command output, secret-like fields, absolute paths, and unknown sections fail or are absent.

- [ ] **Step 3: Run RED.**

Run: `PYTHONPATH=src uv run --python 3.12 python -m unittest -v tests.test_dashboard_render tests.test_dashboard_accessibility tests.test_dashboard_export`

Expected: FAIL with missing SSR/assets/export modules.

- [ ] **Step 4: Implement server-rendered progressive disclosure and themes.**

```python
def render_task_review(view: TaskReviewView, *, csrf_token: str) -> str:
    choices = () if view.assurance["gate"] == "hard_block" else _allowed_decisions(view)
    return "".join((
        _freshness_banner(view.freshness, view.completeness),
        _section("summary", "한눈에 보기", _summary_cards(view.summary)),
        _details("trace", "변경과 연관 기능", _bounded_diagram(view) + _related_checklist(view)),
        _details("evidence", "검증과 근거", _verification_table(view) + _guarantee_claims(view)),
        _section("decision", "판단", _decision_form(view, csrf_token, choices)),
    ))
```

Escape every text/attribute using `html.escape(value, quote=True)`. Native `<details>/<summary>` provides the ELI5 disclosure order without JavaScript. Raw bytes render only as escaped `<pre>` or attachment. JavaScript is limited to theme preference and optional SVG focus mirroring; core navigation/forms work without it. `FreshnessBanner` names freshness and completeness separately. Implement `StatusWithBasis`, `SummaryCards`, `BoundedDiagram`, `RelatedFunctionChecklist`, `VerificationTable`, `GuaranteeClaims`, `EvidenceLink`, and `DecisionForm` as private renderer functions.

- [ ] **Step 5: Implement allowlisted export with private 0600 delivery.**

```python
def export_masked_history(*, view: TaskReviewView, sections: Sequence[str],
                          private_roots: Sequence[Path], exported_at: str) -> bytes:
    allowed = {"summary", "verification", "guarantees", "history", "decision"}
    requested = tuple(dict.fromkeys(sections))
    unknown = set(requested) - allowed
    if unknown:
        raise ValueError(f"unknown export sections: {sorted(unknown)}")
    payload = {"task": _export_task(view.task)}
    payload.update({name: getattr(view, name) for name in requested})
    payload["exported_at"] = exported_at
    return json.dumps(mask_dashboard_value(payload, private_roots=private_roots),
                      ensure_ascii=False, sort_keys=True).encode("utf-8")
```

History route writes an optional saved export through `private_atomic_write`; HTTP attachment remains `no-store` and does not expose its local path.

- [ ] **Step 6: Run GREEN and commit.**

Run: `PYTHONPATH=src uv run --python 3.12 python -m unittest -v tests.test_dashboard_render tests.test_dashboard_accessibility tests.test_dashboard_export tests.test_dashboard_view tests.test_dashboard_server`

Expected: PASS; no remote/client framework, Raw execution, path leak, color-only status, inaccessible SVG, or hard-block acceptance control.

```bash
git add src/devharness/dashboard_assets.py src/devharness/dashboard_render.py src/devharness/dashboard_export.py tests/test_dashboard_render.py tests/test_dashboard_accessibility.py tests/test_dashboard_export.py
git commit -m "feat: render accessible evidence-first dashboard pages"
```

---

### Task 5: Actual/same-task vertical Gate, browser checks, scope trace, and M6 handoff

**M5 coverage:** M5-01~M5-09 final evidence and governance

**Files:**
- Create: `tests/fixtures/m5/same-task-input.json`
- Create: `tests/test_dashboard_actual_packets.py`
- Create: `tests/test_dashboard_vertical.py`
- Create: `tests/test_m5_scope_trace.py`
- Create: `docs/reviews/m5/run_vertical_fixture.py`
- Create: `docs/reviews/m5/run_actual_review.py`
- Create: `docs/reviews/m5/run_browser_probe.mjs`
- Create: `docs/reviews/m5/sync_github_scope.py`
- Create: `docs/reviews/m5/README.md`
- Create: `docs/reviews/m5/automated-gate-summary.json`
- Create: `docs/reviews/m5/scope-trace.json`
- Modify: `docs/adr/0007-brand-dashboard-design-foundation.md`
- Modify: `docs/adr/README.md`
- Modify: `docs/product/Requirements_Traceability.md`
- Modify: `docs/product/향후계획.md`

**Exact review signatures:**

```text
run_vertical_fixture(*, data_root: Path, output_root: Path, observed_at: str) -> dict[str, object]
review_actual_packets(*, m3_packet: Path, m4_packet: Path, output: Path, observed_at: str) -> dict[str, object]
required_issue_specs() -> Sequence[IssueSpec]
synchronize_scope(*, repository: str, apply: bool, output: Path | None = None) -> dict[str, object]
```

The issue synchronizer owns exactly these unique titles: `M5-01 Task Review Page`, `M5-02 Before / After Diagram`, `M5-03 연관된 기능 Checklist`, `M5-04 Verification Status 및 Task Guarantee Report`, `M5-05 Harness Status Page`, `M5-06 Feature Validation Page`, `M5-07 Decision Panel`, `M5-08 Audit & History 최소 버전`, `M5-09 Dashboard 전체 범위 추적 검증`, and `M6-00 HWPX Dashboard 사람 검토와 접근성·이해 시간 관찰`.

- [ ] **Step 1: Write RED actual and same-task tests.**

```python
actual = review_actual_packets(
    m3_packet=write_valid_m3_packet(root / "m3.json", task_id="task:m3-probe"),
    m4_packet=write_valid_m4_packet(root / "m4.json", task_id="task:m4-review"),
    output=root / "summary.json", observed_at=NOW,
)
self.assertEqual(("observed", "observed", False, "unobserved"), (
    actual["m3"]["validation_basis"], actual["m4"]["validation_basis"],
    actual["same_task"], actual["combined_task_assurance"],
))

vertical = run_vertical_fixture(data_root=root / "data", output_root=root / "output", observed_at=NOW)
self.assertTrue(vertical["identity_closed"])
self.assertTrue(vertical["projection_fresh"])
self.assertEqual(("reference_only", "store"),
                 (vertical["unregistered_m4_ref"], vertical["registered_m4_ref"]))
self.assertEqual(("not_evaluated", "unobserved", "revise"),
                 (vertical["missing_tgr"], vertical["missing_hwpx_human_observation"], vertical["decision"]))
```

The unit test helpers write validated packet shapes under their temporary directory so the regular suite is hermetic; they are not M5 Production acceptance Evidence. Separately assert missing explicit paths raise `FileNotFoundError("actual M3 packet unavailable")` or `FileNotFoundError("actual M4 packet unavailable")`; never load committed examples. The later `run_actual_review.py` command is the mandatory Gate using the two `/tmp/ownhands-*` actual inputs. The same-task fixture must call existing M3/M4 builders and create a canonical HWPX feature/data-flow Task, Contract, M3 task ref, M4 packet, registered/unregistered Evidence, Assurance Event, fresh Projection, and Decision. Its declared Diagram nodes/edges describe fixture-provided HWPX package→body paragraph→character property relations only; they do not claim a human-rendered result. `same-task-input.json` contains safe input/expected observation only—no result/Gate.

- [ ] **Step 2: Write RED scope tests.**

```python
trace = json.loads(TRACE.read_text(encoding="utf-8"))
self.assertEqual([f"M5-{number:02d}" for number in range(1, 10)],
                 [row["id"] for row in trace["requirements"]])
self.assertEqual(9, len({row["leaf_issue_url"] for row in trace["requirements"]}))
self.assertTrue(all(row["parent_issue_url"].endswith("/issues/7") for row in trace["requirements"]))
self.assertEqual({"missing": 0, "duplicate": 0, "orphan": 0}, trace["coverage"])

adr = ADR.read_text(encoding="utf-8")
self.assertIn("사용자 사전 위임에 따른 에이전트 결정", adr)
self.assertIn("사용자가 세부 UI/UX를 직접 검토하지 않았다", adr)
self.assertEqual([], tomllib.loads(PYPROJECT.read_text(encoding="utf-8"))["project"]["dependencies"])
```

Assert #7↔nine leaves↔test/evidence mapping is bidirectional, one M6 human issue is linked from M5-06/M5-09/#7, and no `package.json`, Vite, Webpack, SPA, new dependency, M6 success claim, M7/M8 implementation, or Raw local path exists.

- [ ] **Step 3: Run RED.**

Run: `PYTHONPATH=src uv run --python 3.12 python -m unittest -v tests.test_dashboard_actual_packets tests.test_dashboard_vertical tests.test_m5_scope_trace`

Expected: FAIL because M5 review runners/fixtures/trace are absent. Missing actual packet is a Gate failure, not a fixture fallback.

- [ ] **Step 4: Implement vertical and actual runners.**

```python
def review_actual_packets(*, m3_packet: Path, m4_packet: Path,
                          output: Path, observed_at: str) -> dict[str, object]:
    if not m3_packet.is_file():
        raise FileNotFoundError("actual M3 packet unavailable")
    if not m4_packet.is_file():
        raise FileNotFoundError("actual M4 packet unavailable")
    m3 = validate_m3_packet(json.loads(m3_packet.read_text(encoding="utf-8")))
    m4 = validate_packet_document(json.loads(m4_packet.read_text(encoding="utf-8")))
    result = _allowlisted_actual_summary(m3, m4, observed_at)
    private_atomic_write(output, json.dumps(result, ensure_ascii=False, indent=2) + "\n")
    return result
```

`automated-gate-summary.json` permits enum states, timestamps, fingerprints, counts, relative test names only. It excludes packet bodies, raw output, command prefix, token, absolute path, and object path.

- [ ] **Step 5: Implement dependency-free browser probe and run automated Gates.**

Base `run_browser_probe.mjs` on `docs/design/m0-07/probes/m0-07-browser-probe.mjs` using Node built-ins and installed Chrome. In Light/Dark at 320, 390, 1440 assert document overflow 0, skip focus, logical tab order, disclosures/forms, text+symbol status, text contrast ≥4.5:1, focus ≥3:1, reduced motion, SVG IDs/title/desc+HTML links, five-route navigation, escaped Raw, and Hard Block control absence. VoiceOver is manual and cannot be browser-Pass.

Run:

```bash
PYTHONPATH=src uv run --python 3.12 python -m unittest -v tests.test_dashboard_actual_packets tests.test_dashboard_vertical tests.test_dashboard_server tests.test_dashboard_http_security tests.test_dashboard_render tests.test_dashboard_accessibility tests.test_dashboard_export
PYTHONPATH=src uv run --python 3.12 python docs/reviews/m5/run_vertical_fixture.py --data-root /tmp/ownhands-m5-data --output-root /tmp/ownhands-m5-review --observed-at 2026-09-06T12:00:00+00:00
PYTHONPATH=src uv run --python 3.12 python docs/reviews/m5/run_actual_review.py --m3-packet /tmp/ownhands-m3-runtime-path-closure-20260906.json --m4-packet /tmp/ownhands-m4-actual-packet-568c46e.json --output docs/reviews/m5/automated-gate-summary.json --observed-at 2026-09-06T12:00:00+00:00
node docs/reviews/m5/run_browser_probe.mjs --url http://127.0.0.1:8765 --session-token-env DEVHARNESS_M5_SESSION_TOKEN
```

Expected: machine checks PASS; actual M3/M4 individually validate but `same_task=false`; generated slice closes; absent TGR/HWPX human input remains `not_evaluated`/`unobserved`.

- [ ] **Step 6: Implement idempotent GitHub scope sync, dry-run, then apply only with execution-session approval.**

`sync_github_scope.py` uses `subprocess.run(["gh", "api", *arguments])` and `json`. It lists open/closed issues by exact title; dry-run makes no mutation; apply creates only absent titles and rejects duplicates. Each M5 leaf body links parent [Issue #7](https://github.com/taejung3852/own-hands/issues/7), requirement, tests, and evidence. #7 links all nine leaves by replacing only a bounded `<!-- m5-scope:start -->`…`<!-- m5-scope:end -->` section while preserving the rest of the body. The open M6 issue links from M5-06, M5-09, and #7. The script does not close any issue.

```bash
PYTHONPATH=src uv run --python 3.12 python docs/reviews/m5/sync_github_scope.py --repository taejung3852/own-hands
PYTHONPATH=src uv run --python 3.12 python docs/reviews/m5/sync_github_scope.py --repository taejung3852/own-hands --apply --output docs/reviews/m5/scope-trace.json
```

Before the second command, verify authenticated repo and obtain explicit approval for GitHub mutation. Update ADR-0007 and its index with the adopted spec, prior-delegation mechanism, and direct-review absence. Update `Requirements_Traceability.md`/`향후계획.md` with actual leaf URLs, actual-vs-same-task results, and open M6 human issue.

- [ ] **Step 7: Run scope/full GREEN and manual observation Gate.**

```bash
PYTHONPATH=src uv run --python 3.12 python -m unittest -v tests.test_m5_scope_trace
PYTHONPATH=src uv run --python 3.12 python -m unittest discover -s tests -v
PYTHONPATH=src uv run --python 3.12 python -m compileall -q src docs/reviews/m5 tests
git diff --check
rg -n "0\.0\.0\.0|/Users/|object_path|raw_output" docs/reviews/m5 src/devharness/dashboard_*.py tests/test_dashboard_*.py
```

Expected: all automated checks pass; inspect search hits and permit only attack fixtures/prohibition assertions. `scope-trace.json` has `missing=0`, `duplicate=0`, `orphan=0`.

Manually check both themes: keyboard-only five-route flow, disclosures, Evidence metadata/Raw, validation, Decision, export; VoiceOver landmarks/status/Diagram/forms; 320/390/1440 overflow; one Summary→Evidence→Decision explanation; 0700/0600 modes. Record only `Observed Pass`, `Observed Fail`, or `Unobserved`. If no person participates, keep VoiceOver, explanation time, repeated HWPX use, and Dashboard overhead `Unobserved` in the open M6 issue.

- [ ] **Step 8: Commit final M5 evidence and trace docs.**

```bash
git add tests/fixtures/m5/same-task-input.json tests/test_dashboard_actual_packets.py tests/test_dashboard_vertical.py tests/test_m5_scope_trace.py docs/reviews/m5 docs/adr/0007-brand-dashboard-design-foundation.md docs/adr/README.md docs/product/Requirements_Traceability.md docs/product/향후계획.md
git commit -m "test: verify and trace the M5 dashboard vertical"
```

---

## M5-01~M5-09 mapping

| Requirement | Plan Tasks | Required evidence |
|---|---|---|
| M5-01 Task Review | 2, 3, 4, 5 | identity-closed Summary/Gate/conflict/unverified states and actual/same-task Gate |
| M5-02 Before/After Diagram | 2, 4, 5 | source-ref-only graph, accessible SVG+HTML fallback, viewport probe |
| M5-03 Related Function Checklist | 2, 4, 5 | deterministic priority/basis/validation links |
| M5-04 Verification/TGR | 2, 4, 5 | six states, original comparison details, Claim→Evidence, absent TGR `Not Evaluated` |
| M5-05 Harness Status | 2, 3, 4, 5 | M3 project/task split and Configured/Loaded/Enforced basis |
| M5-06 Feature Validation | 1, 3, 4, 5 | existing adapter boundary, M1 direct probe, human absence `Unobserved` |
| M5-07 Decision Panel | 1, 2, 3, 4, 5 | canonical Event, current fingerprint/freshness, authority, Hard Block rejection |
| M5-08 Audit & History | 1, 3, 4, 5 | canonical sequence and allowlisted masked 0600 export |
| M5-09 Scope trace | 5 | #7↔nine leaves↔tests/evidence, M6 issue, zero missing/duplicate/orphan |

## Completion and non-goals

M5 completion requires Tasks 1–5 committed, full suite plus actual/same-task/browser/security/accessibility automated Gates, and zero scope-trace gaps. Missing actual packet files block the actual Gate. Missing TGR, HWPX human observation, VoiceOver, or reviewer timing remains `Not Evaluated`/`Unobserved` rather than synthesized.

Out of scope: repeated HWPX dogfooding and generalized human bottleneck claims (M6), packaging/release/deployment (M7), usage/cost analytics and non-Codex adapters (M8), generic test runner, automatic dependency discovery, cloud/team Raw Evidence sharing, merge/deploy actions, and final brand assets.

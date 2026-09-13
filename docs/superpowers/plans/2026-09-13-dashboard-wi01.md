# Dashboard WI-01 Implementation Plan

> For agentic workers: execute this bounded plan with executing-plans; request a read-only code review before PR. Do not start WI-02 in this PR.

**Goal:** 원본을 변경하지 않고 Catalog/Lifecycle/Evidence를 읽으며, 무결성이 확인된 레코드와 읽을 수 없는 Evidence를 구별한다.

**Architecture:** 기존 validator와 writer를 보존하며 명시적 read-only factories를 추가한다. SQLite mode=ro와 query_only를 모두 사용하고 파일을 만지는 writer 메서드는 선행 차단한다. partial closure는 typed result로 제공하되 journal/참조/scope 오류는 성공으로 변환하지 않는다.

**Tech Stack:** Python >=3.12, sqlite3/dataclasses/unittest, 새 의존성 없음.

**Spec:** `docs/m5-r/dashboard-sdd.md` — 사용자 승인 v0.1 및 backend 경계 추가. 문서 초안의 구현 미착수 문구는 승인 이전 기록이며 이번 사용자 구현 요청이 우선한다.

## Global Constraints

- WI-01은 R01/R07/R15의 reader 기반만 구현한다. HTTP/브라우저/캐시/LLM/VM은 후속 WI다.
- 기본10/legacy25 MCP 계약과 모든 기존 writer 동작을 보존한다.
- 원본 없는 조회는 파일/디렉터리/DB를 생성하지 않는다. 지원하지 않는 Catalog 버전은 migration하지 않고 거부한다.
- 순수 조회는 chmod/reconcile/purge/Event append/Claim 평가를 수행하지 않는다.
- 같은 정상 metadata와 다른 손상 raw를 가진 fixture에서 partial과 정상 sibling을 함께 반환한다. raw 손상 상태를 Claim 재판정으로 승격하지 않는다.
- ELI5는 승인된 provider 중립 경계+v1 adapter 하나. WI-03에서 구현하며 WI-01에 추상 provider 코드를 미리 추가하지 않는다.
- 기존 rollback-journal DB만 지원한다. WAL은 SQLite 연결 전에 거부하여 원본 sidecar 생성을 방지한다.

## Execution status (2026-09-13)

Task 1–3 completed. Task 4 verification completed: targeted16/full449 pass,
#82 mutations9/9 detected, raw-validator bypass2/2 detected. Independent review's
WAL and malformed raw-path findings have regression fixtures and fixes.
Below checklists retain the original pre-implementation plan; authoritative
execution results are in `docs/m5-r/dashboard-wi01-verification.md`.
PR publication follows the final verification commit. No merge is authorized.

## 완료 조건 / 실패 fixture 먼저 고정

| Fixture | WI-01 성공 | 잡아야 할 실패 |
|---|---|---|
| 정상 Snapshot+Evidence, 오래된 orphan CAS | 기존 get/read_content 동일 결과, 원본 hash/mode/path 불변, orphan 보존 | 조회 생성자의 reconcile/chmod |
| 미존재 root/DB | 명시적 열기 실패, 파일 생성0 | SQLite 기본 연결의 자동 생성 |
| 오래된/위조 schema, journal 변조 | 거부, migration/수리0 | 읽기 factory가 검증 건너뜀 |
| reader에 writer API 및 직접 SQL 호출 | 원본 쓰기/파일 부작용 전에 거부 | read_only flag만 표시하고 실제 쓰기 허용 |
| raw 손상/삭제/purge/권한 거부 | typed diagnostic, 정상 sibling 유지, get은 기존처럼 실패 | 예외 삼키거나 전체 결과를 verified로 표시 |
| foreign Task Evidence | partial로 허용하지 않고 scope 오류 | 오류를 모두 단순 missing으로 변환 |
| read-only review_status/current/freshness | 정상 읽기, writer transaction 없음 | BEGIN IMMEDIATE 및 내부 EvidenceStore 초기화 |

## Task 1 — tests first

Files: create `tests/test_dashboard_readonly.py`. Reuse real `tests.test_claim_evaluation.ClaimEvaluationTests` fixture through composition (do not inherit its test suite).

- [ ] RED: factory/partial API 존재를 assertion으로 확인하고, fixture 기반 동작 테스트 작성.

```python
self.assertTrue(callable(getattr(Catalog, 'open_readonly', None)))
with Catalog.open_readonly(paths) as catalog:
    with LifecycleStore.open_readonly(catalog) as reader:
        self.assertEqual(reader.get(snapshot)['data']['review'], review)
        with self.assertRaises(PermissionError):
            reader.append('work_issue', 'new', project_scope, {'title': 'write'})
```

- [ ] Run: `PYTHONPATH=src ../ownhands-80/.venv/bin/python -m unittest tests.test_dashboard_readonly -v`. Expected feature-missing assertion failures, not import errors.

## Task 2 — read-only connection and file boundaries

Files: modify `src/devharness/catalog.py`, `src/devharness/evidence.py`, `src/devharness/lifecycle/store.py`.

Interfaces: `Catalog.open_readonly(paths)`, `EvidenceStore.open_readonly(catalog)`, `LifecycleStore.open_readonly(catalog, path=None)`. Reader catalog is required for the latter two. Constructors receiving a reader catalog must not silently restore writable mode.

- [ ] Implement `mode=ro` URI connection, query_only and existing schema/integrity validation without initialization.
- [ ] Make EvidenceStore infer readonly from catalog; skip directory permission/reconciliation work and reject put/set_retention/purge/reconcile before filesystem work.
- [ ] Make LifecycleStore skip init writes in readonly mode; reject mutations before validation can cause side effects; use a deferred transaction for read-only review_status.
- [ ] Run targeted tests, then old suites. Writer flags default false.

## Task 3 — typed partial closure

Files: create `src/devharness/lifecycle/reading.py`; modify lifecycle store only for public entry and reuse hooks.

Interfaces: `reader.inspect_closure(ref) -> ClosureRead`; `ClosureRead(record, records, diagnostics)` with `read_health` complete/partial; `ReadDiagnostic(reference, evidence_id, availability, reason)`. No raw byte field is added to the partial result.

- [ ] Share traversal/reference/scope verification with strict get. Journal/reference/scope errors remain exceptions.
- [ ] Catch only inaccessible raw cases (missing/corrupt/purged/denied) as diagnostics; retain successful siblings, identify affected binding.
- [ ] Keep strict `get` behavior and source verdict immutable.
- [ ] Run fixture regression for each availability and source corruption.

## Task 4 — verify and PR

- [ ] Run full suite, Control-boundary regression and #82 mutations9. Record baseline433 separately from new total.
- [ ] Independently review diff against `69f8151`; resolve material findings with regression tests.
- [ ] Write `docs/m5-r/dashboard-wi01-verification.md` with executed cases, limits, commands and review findings.
- [ ] Commit only this WI, push `feat/dashboard-wi01-readonly`, create small PR against main. Keep #89 parent open; no automatic merge/close.

Follow-up order: WI-02 View Model → WI-03 provider-neutral presentation/cache + one actual adapter → WI-04 HTTP → WI-05 screens → WI-06 acceptance. Each begins by freezing its own failures/acceptance criteria, and gets a separate PR. A later WI must not silently add changes to this PR.

# Dashboard WI-02 Implementation Plan

> **For agentic workers:** Use executing-plans to implement this plan task-by-task after user review. Do not start implementation in the plan-writing turn.

**Goal:** #91에서 Snapshot 원본을 재판정하지 않고 Dashboard View Model로 읽는다.

**Architecture:** WI-01 reader로 검증한 closure를 얇은 mapper가 JSON 계약으로 변환한다. 현재 맥락은 별도로 읽고, request 전체의 시작/끝 token으로 변화 여부를 검사한다. 기존 lifecycle validation/semantic 비교를 재사용하며 별도 평가 엔진·범용 repository 계층은 만들지 않는다.

**Tech Stack:** Python >=3.12, stdlib sqlite3/dataclasses/hashlib/json/unicodedata/unittest; 새 의존성 없음.

**Spec:** `docs/m5-r/dashboard-sdd.md` §4–6/9/10. GitHub #89 상위 계약, #91 구현 이슈. main `07809a0675a00d73f16da77c98cfd47d65fd1c8e`; PR #90 merged.

## Global Constraints

- 상태: 계획 검토 대기. 제품 코드/테스트를 이 작성 작업에서 만들거나 실행하지 않는다.
- Understand → Prove. HumanDecision/Claim/Review/원본 DB/raw 변경 없음.
- Snapshot Ref(kind/id/revision/hash), 원본 WorkIssue revision과 source pointer 고정.
- 총계는 Claim 단위. 제외된 선택도 분모에 포함. 필수 0은 제품 완료가 아님.
- freshness는 등록된 현재 입력 기준이며 실제 디스크/환경 실시간 검사 아님.
- 원본 쓰기·migration·reconcile·BEGIN IMMEDIATE·LLM·Skill·evaluate_review 호출 0.
- 기본 limit20/최대50, q최대200자, 상단 problem3개. cursor 변경 오류는 기존 SDD 코드 유지.
- HTTP/인증/raw content chunk는 WI-04, cache/provider/생성 fallback은 WI-03.
- WI-01의 rollback-only reader 지원 범위를 승계. WAL을 자동 전환하지 않는다.
- 한 구현 이슈당 PR 하나. #89는 이슈1–6 및 통합검증 완료 후에만 종료.

## 파일과 인터페이스

Create:
- `src/devharness/dashboard/__init__.py`: 패키지 표시만.
- `src/devharness/dashboard/read_model.py`: reader orchestration, scope/key, mapping, listing/context.
- `tests/test_dashboard_read_model.py`: 실 store fixture 조합 + 실패별 검사.
- `tests/fixtures/dashboard/view-model-golden.json`: 수작업 input/expected projection. 생성 결과 복사 금지.
- `docs/m5-r/dashboard-wi02-verification.md`: F01–F09/E01/E02/E04/E09 결과.

Modify only if shared read helpers are needed:
- `src/devharness/lifecycle/store.py`: public read-only head/enumeration helper 및 기존 semantic 비교의 공통 helper 추출. 평가/검증 약화 금지.
- `src/devharness/lifecycle/evaluation_store.py`: 기존 _collect 선택 의미를 재사용하는 읽기 helper만. 판정 알고리즘 변경 없음.

계획 내부 interface (wire JSON은 SDD §6.2 유지):
```python
class DashboardReadModel:
    def __init__(self, catalog, lifecycle, project_id: str): ...
    def read_list(self, *, filter: str = "all", q: str = "",
                  cursor: str | None = None, limit: int = 20,
                  presentations: tuple[dict, ...] = (),
                  ready_sequence: int = 0) -> dict: ...
    def read_detail(self, snapshot_key: str) -> dict: ...
    def read_claim(self, snapshot_key: str, claim_id: str) -> dict: ...
    def read_evidence(self, snapshot_key: str, evidence_key: str) -> dict: ...
    def read_context(self, snapshot_key: str) -> dict: ...

class ReadModelError(Exception):
    # code: NOT_FOUND / INVALID_QUERY / LIST_CHANGED / SOURCE_CHANGED /
    # SOURCE_UNAVAILABLE / SOURCE_INTEGRITY_ERROR / UNSUPPORTED_SCHEMA
    code: str
```

`presentations`는 같은 project/snapshot의 검증된 ready 표현물 dict에 ready_sequence와 snapshot_key를 더한 입력이다. WI-03이 이를 공급한다. 상한 이하·같은 Ref에 속한 ready 항목만 검색에 사용하며 제공자 호출이나 저장 기능은 없다. 미제공이면 상태 unavailable/absent와 원본 제목을 사용하는 결정적 임시 Presentation을 반환한다. 이것을 생성 backend 완료로 주장하지 않는다.
`read_evidence`는 FieldVM의 availability/출처와 기록된 구조화 field만 제공한다. raw byte를 열어 HTTP content로 내보내지 않는다. 누락 field는 not_collected/null, stdout/stderr를 통합 raw에서 발명하지 않는다.

## Task 1 — Snapshot 고정 mapping과 원본 집계 (F01–F04)

- [ ] 새 실행 브랜치를 당시 origin/main에서 만들고 clean 상태/선행 #90 반영을 확인한다. 이 계획 파일만 이관한다.
- [ ] ClaimEvaluationTests를 상속하지 않고 composition으로 fixture를 사용한다. Snapshot 생성 이후 WorkIssue/Spec revision을 추가해 옛 Snapshot의 제목/숫자가 바뀌지 않는 테스트를 먼저 작성한다.
- [ ] golden에 required5={verified2,failed1,inconclusive1,unobserved1}, optional2={verified1,unobserved1}, excluded1을 수작업 기록한다. all7={verified3,failed1,inconclusive1,unobserved2}를 기대한다.
```python
self.assertEqual(vm["counts"]["all"],
    dict(total=7, verified=3, failed=1, inconclusive=1, unobserved=2))
self.assertEqual(vm["counts"]["excluded_optional_count"], 1)
self.assertEqual(vm["issue"]["ref"], original_issue_ref)
self.assertEqual(vm["review_state"], stored_review["data"]["verdict"])
```
- [ ] `python -m unittest tests.test_dashboard_read_model -v`로 미구현 동작의 RED를 확인한다. fixture 구성 자체의 예외와 기능 assertion 실패를 구분한다.
- [ ] WI-01 inspect_closure 결과에서 exact ref index를 만든다. Spec과 Review의 저장된 Claim/check를 연결하고 상태를 복사한다. 합계는 상태별 Claim 수만 센다. v1에는 없는 check를 추가하지 않는다.
- [ ] problem source(pointer+kind)만 dedup한다. required blocker→failure→integrity/conflict→gap→excluded 순서로 top3와 remaining을 구하고, 전체 problems/Observation 배열을 보존한다.
- [ ] Before 없는 비교, 반복 pass+fail, blocked+failed, verified+finding, legacy/required0 테스트를 GREEN으로 확인하고 task commit한다.

## Task 2 — scoped Evidence와 partial 안전성 (F06/F09)

- [ ] 동일 Task의 서로 다른 Snapshot에 속한 Evidence key, 타 project key, 손상/삭제/purge fixture를 만든다.
```python
with self.assertRaises(ReadModelError) as caught:
    reader.read_evidence(left_key, right_only_evidence_key)
self.assertEqual(caught.exception.code, "NOT_FOUND")
self.assertEqual(partial["context"]["read_health"], "partial")
self.assertTrue(partial["presentation"]["fallback"])
```
- [ ] RED 관찰 후 key를 namespace/scope/full Snapshot Ref 및 binding identity의 canonical hash로 결합한다. 허용된 project와 선택 closure 안에서만 key를 해석한다.
- [ ] unavailable metadata를 available로 만들지 않는다. partial은 저장 당시 verdict와 조회 상태를 분리하고 ready 생성문을 억제한다. journal/hash/scope 오류는 partial 성공으로 삼키지 않는다.
- [ ] Evidence command/stdout/stderr/diff의 명시적 원본 field만 연결하고, SourcePointer가 data payload를 가리키는지 검사한다.
- [ ] 다른 key 응답의 오류 code/message가 동일한지, 원본 inventory가 변하지 않는지 GREEN 확인 후 commit한다.

## Task 3 — context overlay와 일관된 read token (F05/F08)

- [ ] recapture(같은 fingerprint 다른 ID), active 없음, test meaning 충돌, 새 attempt, 새 Evidence와 Snapshot fixture를 고정한다.
```python
self.assertEqual(recapture["freshness"], "current")
self.assertEqual(no_active["freshness"], "unknown")
self.assertEqual(new_attempt["reasons"], ["attempt_changed"])
self.assertTrue(new_attempt["superseded_attempt"])
self.assertEqual(after_vm["counts"], before_vm["counts"])
```
- [ ] RED 후 current_activation을 통해 approved Spec/동일 attempt CodeState/Environment를 선택한다. 현재 meaning은 이에 정확히 맞는 after Observation만 수집한다.
- [ ] 기존 freshness 비교를 재사용한다. 누락 입력 때문에 전체 비교 호출이 불가능하면 공통 semantic 비교 helper를 추출해 확인된 차이는 stale, 차이 없이 부족하면 unknown을 유지한다. old Review meaning을 현재 값으로 복사하지 않는다.
- [ ] 새 Evidence는 _collect의 기존 범위 선택 규칙으로만 감지한다. raw 읽기 실패는 unknown/null 등 읽기 진단으로 보존하고 결과 재평가를 호출하지 않는다.
- [ ] lifecycle record/activation head, Catalog event head와 참조 metadata fingerprint로 시작/끝 token을 비교한다. 겹친/nested BEGIN을 만들지 않도록 WI-01 메서드의 transaction 소유를 존중한다. 값이 바뀌면 전체 읽기 1회 재시도, 또 바뀌면 SOURCE_CHANGED.
- [ ] 동기화 barrier fixture로 1회 변경 성공/계속 변경 실패를 각각 확인한다. DB 둘과 파일의 전역 atomic snapshot을 보장한다고 쓰지 않는다. GREEN 후 commit한다.

## Task 4 — 목록 선택·검색·페이지 안정성 (F01/F07)

- [ ] 2 issue×2 attempt×여러 Snapshot, stale 중첩 및 ready+unknown fixture를 추가한다. 저장 sequence 최댓값과 활성 Snapshot이 다른 경우도 포함한다.
```python
self.assertEqual([x["snapshot_key"] for x in page["items"]], expected_order)
self.assertEqual(page["summary_search"], "cached_only")
with self.assertRaises(ReadModelError) as caught:
    reader.read_list(cursor=old_cursor)
self.assertEqual(caught.exception.code, "LIST_CHANGED")
```
- [ ] RED 후 issue/attempt별 latest stored를 선택한다. rank needs-review/unreadable0, blocked1, 기타 stale2, ready3; ready unknown이 current보다 먼저. sequence내림/key오름을 마지막 tie-break로 쓴다.
- [ ] 필터는 독립 predicate, 검색은 Unicode 정규화+casefold 부분 일치로 원본 제목과 supplied ready 요약만 대상으로 한다.
- [ ] cursor에 head/질의 fingerprint/마지막 정렬키/cache 상한을 결합한다. 잘못된 cursor는 INVALID_QUERY, head 변화는 LIST_CHANGED. 중간 cache 추가는 기존 페이지에 섞지 않는다.
- [ ] page 순회 중 중복/누락 및 숨은 생성 호출이 없는지 GREEN 확인 후 commit한다.

## Task 5 — 검증 기록과 작은 PR (F01–F09)

- [ ] 금지 호출 spy로 모든 read_* 경로에 evaluate_review/append/activate/Evidence put 등이 호출되지 않음을 검사한다.
- [ ] 아래 명령을 실행하고 Python 버전/commit과 결과를 기록한다. 테스트 수는 실행 결과만 사용한다.
```sh
PYTHONPATH=src ../ownhands-80/.venv/bin/python -m unittest tests.test_dashboard_read_model tests.test_dashboard_readonly -v
PYTHONPATH=src ../ownhands-80/.venv/bin/python -m unittest discover -s tests -q
PYTHONPATH=src ../ownhands-80/.venv/bin/python tests/run_claim_mutations.py
git diff --check
```
- [ ] F01–F09 input/golden/실패·성공/미실행→E02, 원본·scope→E01/E04, 회귀→E09를 검증 문서에 연결한다.
- [ ] 독립 검수에서 pointer 도달성, snapshot 혼합, partial→ready 승격, freshness 자기복사, cursor head 오류를 확인한다. 확정된 중요 문제 해결 후 작은 PR 하나로 제출한다.
- [ ] PR은 Refs #89와 Closes #91을 사용한다. #89 종료 문구를 넣지 않는다. 병합은 별도 승인에 따른다.

## 계획 자체 검토

범위 대응: T02→Task1/4, T04/T05/T06→Task1, T08→Task3, T07의 VM부분→Task2, T01/T15→Task5.
HTTP status 전송·raw content 보안·브라우저·실제 provider/ELI5 의미·pilot는 이슈4–6에서 확인한다.
이 계획의 검사 코드 예시는 구현할 테스트 단언이며 실행 증거가 아니다. M3 live 미확인은 유지한다.

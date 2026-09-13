# Dashboard WI-02 Verification

## 범위와 기준

- 대상: Dashboard Snapshot View Model, Claim 집계, 문제 인덱스, scoped Evidence, 현재 맥락 overlay, 목록 선택·검색·페이지 처리.
- 기준 main: `07809a0675a00d73f16da77c98cfd47d65fd1c8e` (PR #90 병합 커밋).
- 검증한 구현 커밋: `300349ebaa3b7869afe3c8208cfed84e543c82b5`.
- 실행 브랜치: `feat/dashboard-wi02-view-model`.
- 환경: Python `3.12.14`, macOS 로컬 fixture.
- 원칙: 저장된 Claim/Review 판정은 복사하며 `evaluate_review`를 조회 경로에서 호출하지 않는다.

## TDD 관찰

최초 `tests/test_dashboard_read_model.py` 실행은 10/10 테스트가 `Dashboard read model is not implemented` 단언으로 실패했다. fixture 구성 오류나 저장소 예외가 아니라 WI-02 모듈 부재 때문에 실패함을 확인한 뒤 최소 구현을 추가했다. 이후 required-zero/legacy, foreign project, missing/purged 경계를 보강했다. 독립 재검수에서 재현된 known-change+missing, legacy/additional Observation Evidence, 고유 Evidence ID, raw 상태 cursor, malformed cursor 반례도 각각 실패를 확인한 뒤 수정했다. 최종 신규 테스트는 17개다.

## F01–F09 결과

| ID | 고정 입력/공격 | 관찰 결과 | Evidence |
|---|---|---|---|
| F01 | 같은 issue/attempt의 여러 Snapshot, Snapshot 뒤 WorkIssue 제목 revision 추가 | 목록은 journal sequence가 가장 큰 저장 Snapshot만 선택하고, 상세는 선택 Snapshot closure의 옛 제목·Spec·Review만 사용 | E02 |
| F02 | required 5, optional 2, excluded 1, 네 Claim 상태, required 0, legacy v1 | `all=7/verified=3/failed=1/inconclusive=1/unobserved=2`; 제외 선택도 분모 유지; required 0과 v1 `checks=[]` 및 원본 Observation/Evidence 경로 보존 | E02 |
| F03 | blocker, failure, finding, inconclusive, unobserved, exclusion | 저장 verdict를 유지하며 source pointer+kind 단위로만 중복 제거; blocker 우선, 전체 문제와 `remaining_problem_count` 보존 | E02 |
| F04 | Before conflict, 반복 실행, preserve check의 Before 부재, Claim 밖 additional Observation | 저장 Claim/check 상태와 모든 Before/After 실행을 유지; 비교 불가를 PASS로 승격하지 않으며 additional Observation의 scoped Evidence도 조회 가능 | E02, E04 |
| F05 | active 입력 부재, semantic recapture, meaning 충돌, 새 Evidence/Snapshot/attempt | 부재·meaning 충돌은 unknown, 동일 fingerprint 재수집은 current; 다른 입력이 없어도 확인된 code 차이는 stale; 새 Evidence와 attempt는 별도 축이며 Snapshot counts 불변 | E02 |
| F06 | 다른 project, 다른 Snapshot key, raw corrupt/missing/purged, 동일 Evidence의 복수 binding | 범위 밖 key는 동일 `NOT_FOUND`; partial에서 저장 verdict와 조회 상태를 분리하고 fallback 강제; 정상 metadata/형제 근거 유지; 수량은 고유 Evidence ID 기준 | E01, E04 |
| F07 | 중복 Snapshot, 상태 rank, NFKC/casefold 검색, cursor 중 source/cache 변화와 malformed payload | issue/attempt별 최신 저장 1개, 합의 rank, cached-only 검색; source head 변화는 `LIST_CHANGED`, cache 상한 뒤 ready 항목은 미혼합, 잘못된 cursor 구조는 `INVALID_QUERY` | E02 |
| F08 | 읽기 중 source 1회/계속 변경, 페이지 사이 raw 손상, 빈 목록, journal 변조 | 1회 변화는 전체 read 재시도 후 성공, 연속 변화는 `SOURCE_CHANGED`; raw 읽기 상태로 목록 순서가 바뀌면 `LIST_CHANGED`; 빈 목록/직접 `NOT_FOUND`/journal 손상 구분 | E01, E04 |
| F09 | 모든 read 경로에서 writer/evaluator spy, 원본 inventory 전후 비교 | append/activate/put/purge/reconcile/evaluate 호출 0, 원본 file/mode/hash inventory 불변 | E01, E09 |

## 실행 결과

```text
PYTHONPATH=src ../ownhands-80/.venv/bin/python -m unittest tests.test_dashboard_read_model tests.test_dashboard_readonly -v
Ran 33 tests in 3.122s
OK

PYTHONPATH=src ../ownhands-80/.venv/bin/python -m unittest discover -s tests -q
Ran 466 tests in 16.668s
OK

PYTHONPATH=src ../ownhands-80/.venv/bin/python tests/run_claim_mutations.py
9/9 mutations killed; 각 mutation assertion failure 1개 이상, error 0

git diff --check
exit 0
```

전체 회귀 출력의 `M3 live probe refused or failed: live fixture content drift: AGENTS.md`는 기존 테스트가 예상하는 진단이며 suite exit는 0이었다. 이것은 M3 실환경 성공 증거가 아니다.

## Evidence 경계

- E01: F09가 원본 data root의 file mode/hash inventory를 read 전후 비교하고 금지 writer/evaluator 호출을 spy로 차단한다. atime은 비교하지 않는다.
- E02: `tests/fixtures/dashboard/view-model-golden.json`은 mapper 출력에서 생성하지 않은 수작업 기대값이다.
- E04: F04/F06/F08이 pointer 도달성, Snapshot scope, 비교 불가, 부분 손상과 journal 손상을 구분한다. WI-02는 raw content를 응답으로 반환하거나 전송하지 않으며, 무결성 검증을 위해 내부에서 읽는다.
- E09: 기준 SHA, Python 버전, 대상/전체/Claim mutation 명령과 결과를 위에 기록했다.

## 독립 재검수

1차 독립 재검수는 Critical 0건, Important 5건이었다. 확인된 차이와 입력 누락의 동시 처리, legacy/additional Observation Evidence 경로, raw 상태의 cursor 결합, 고유 Evidence ID 집계, malformed cursor 경계를 모두 재현 테스트로 고정하고 `300349e`에서 수정했다.

수정본 독립 재검수는 제품 코드와 테스트 `300349e` 및 후속 문서 정합성을 확인했다. 독립 실행에서 대상 33개, 전체 466개, `git diff --check`가 통과했고 남은 Critical/Important 이슈가 없어 **WI-02 병합 가능** 판정을 받았다. 이 판정은 아래 미실행 범위를 포함하지 않는다.

## 미실행 및 후속 범위

- M3 live 환경은 확인하지 않았다. 기존 `AGENTS.md` fixture drift 상태를 유지한다.
- HTTP/인증/status mapping, raw content 64KiB cursor/전송, 브라우저·UI·접근성은 WI-04/WI-05 범위라 실행하지 않았다.
- Presentation Cache 저장, provider adapter, LLM 호출·실제 모델 의미 품질·fallback retry는 WI-03/WI-06 범위라 실행하지 않았다.
- 사용자 60초 이해도 pilot와 통합 R01–R16 수용은 실행하지 않았다.
- 따라서 이 문서는 WI-02 View Model 구현 근거이며 Dashboard v1 전체 완료나 #89 종료 근거가 아니다.

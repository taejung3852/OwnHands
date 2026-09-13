# Dashboard WI-03 Verification — ELI5 Presentation 생성·캐시 (#93)

## 범위와 기준

- 대상: provider 중립 `PresentationGenerator` 경계, OpenAI-compatible adapter 1개, Snapshot+recipe
  Presentation Cache, grounding/출력 validation, single-flight lease/retry/cooldown, deterministic
  fallback, dashboard/using-ownhands Skill 및 routing 계약 정합화.
- 기준 main: `4e3d3d0f8be87fab3f0ecd01256234e5d155c7af` (PR #92 병합 커밋).
- 실행 브랜치: `feat/dashboard-wi03-presentation-cache`.
- 환경: Python `3.12.14`, macOS 로컬 fixture, stdlib 전용(신규 의존성 0).
- 원칙: 저장된 Review verdict, Claim status/count, freshness, HumanDecision을 cache가 소유하거나
  다시 판정하지 않는다. 원본 Lifecycle/Evidence는 read-only이며 쓰기 대상은 Presentation Cache뿐이다.

## Baseline 재측정

새 worktree를 최신 `origin/main`에서 만든 뒤, 구현 전에 baseline을 다시 실행했다. 이전 WI-02 세션의
수치를 증거로 재사용하지 않았다.

```text
PYTHONPATH=src uv run --python 3.12 python -m unittest discover -s tests
Ran 469 tests — OK

PYTHONPATH=src uv run --python 3.12 python tests/run_claim_mutations.py
9/9 mutations killed, errors 0
```

## TDD 관찰

1. `tests/test_dashboard_presentation.py`의 32개 fixture를 구현 전에 작성했다. 최초 실행은 32/32가
   `Dashboard presentation service is not implemented` / `Dashboard generator is not implemented`
   **단언 실패**로 RED였다. WI-02와 같은 `try/except ImportError` 가드를 써서 fixture import 오류가
   아니라 기능 부재로 실패함을 확인했다.
2. routing/Skill fixture는 `tests/test_skill_routing_fixtures.py`(6개), `tests/test_skills.py`(2개)에
   추가했고 각각 `routing contract does not model a Dashboard view intent yet`,
   `'(Spec, Review, CodeState)' unexpectedly found` 단언 실패로 RED를 확인했다.
3. 최소 구현 후 GREEN. 독립 재검수에서 발견한 4건은 각각 실패 fixture를 먼저 추가해 RED를 확인한 뒤
   수정했다(아래 «독립 재검수»). 최종 신규 테스트는 46개(presentation 38, routing 6, skills 2)다.

## F01–F11 결과

| ID | 고정 입력/공격 | 관찰 결과 |
|---|---|---|
| F01 | Review/Snapshot 저장 후 Dashboard 미조회, 서비스 생성, 목록 GET | provider 호출 0, cache row 0, **cache 파일 자체가 생성되지 않음** |
| F02 | 최초 detail ensure 후 read/detail/list ensure 반복 3회 | 최초 miss에서만 생성(호출 1), 이후 모두 hit에서 호출 0, `attempt_count=1`, row 1 |
| F03 | 동일 key에 20 thread 동시 ensure(각자 별도 connection) | provider 호출 1, ready row 1, `ready_sequence=1`, `attempt_count=1`, 나머지는 pending/ready |
| F04 | 서로 다른 Snapshot 2개, 그리고 model만 바꾼 recipe | cache key 3개·recipe 2종, 과거 결과 혼합 0. client가 보낸 잘못된 `recipe_hash`는 `RECIPE_CHANGED` |
| F05 | 같은 Snapshot에 새 code_state activate(stale overlay만 변경) | `freshness=stale`·`context_notices` 변경, presentation은 동일 headline으로 ready 유지, 추가 호출 0, row 1 |
| F06 | timeout / 5xx / cooldown / 재시도 상한 / 시계 역행 | ready 저장 0, 60초 cooldown 준수, 자동 시도 최대 2, 이후 `failed` 고정. 시계를 100000초 되돌려도 추가 시도 0. fallback은 원본 제목+원본 집계로 제공 |
| F07 | provider 미설정 / lease 만료 / 지연 응답 / 최종 시도 중 crash | 미설정은 `unavailable`·호출 0·row 0·cache 파일 없음. 유효 lease는 탈취 불가, 만료 후 잔여 1회만 재개(`attempt_count=2`). lease를 잃은 지연 응답은 폐기되고 ready 저장 0. 최종 시도 중 crash는 `failed`로 정착(무한 pending 없음) |
| F08 | 다른 Snapshot pointer / 없는 pointer / 허위 count / verdict field / 미검증 Claim을 observed / Problem pointer를 observed / **verified Claim만 근거로 삼은 gap** / 범위 초과 단정 4종 / raw prompt injection | 전부 `invalid_output`으로 reject, ready 저장 0, 안전 fallback. 정당한 근거(`gap`의 Problem·비-verified Claim 인용, `intent`의 Spec·변경 pointer 인용)는 계속 허용. injection 문자열은 인용 데이터로만 전송되고 credential·raw·stdout·stderr·diff·evidence/code/environment ref·file mode/origin/commit은 전송 payload에 없음 |
| F09 | ready 생성 뒤 Evidence raw 손상(partial) | 신규 생성 금지(호출 0), 기존 생성문 표시 억제 후 deterministic fallback, `reason_code=source_partial`, 저장된 ready row는 삭제·변경 없이 보존 |
| F10 | view_intent 계약 / 목록 카드 상태 / routing 계약 | `list_visible`·`detail`만 생성 가능, `drawer`/`refresh`/`content`/빈 값/대소문자 불일치는 `INVALID_QUERY`. 목록 카드가 상세와 동일한 `recipe_hash`·`failed`·`retry_after`를 반환. Skill routing은 cache hit·Drawer·refresh·Review 완료에서 dormant |
| F11 | 원본 writer/evaluator spy + data root inventory 전후 비교 | `append`/`activate`/`bind_evidence`/`evaluate_review`/`put`/`purge` 호출 0. 변경된 경로는 `dashboard-presentation.sqlite3` 하나뿐, 권한 `0600`. 원본 DB 파일과 경로가 겹치면 생성 거부, schema version 불일치는 열기 거부 |

## 구현이 고정한 계약

- **recipe/cache key**: `recipe_hash = sha256(prompt_version, output schema_version,
  grounding_policy_version, locale, provider_id, model_id, generation_parameters)`,
  `cache_key = sha256(namespace, scope, full Snapshot Ref, recipe_hash)`.
- **provider 미설정**: `recipe_hash`는 `provider_id=null, model_id=null, generation_parameters={}`로
  결정적으로 계산되지만 cache row는 만들지 않고 호출 0으로 `unavailable`을 반환한다.
- **환경변수**: `OWNHANDS_PRESENTATION_BASE_URL`, `_MODEL`, `_API_KEY`(선택), `_PROVIDER_ID`(선택).
  `POST {base_url}/chat/completions`, `temperature=0`, `max_tokens=1200`,
  `response_format=json_object`, `stream=false`, `Idempotency-Key: {cache_key}:{attempt}`,
  timeout 30초, 응답 읽기 상한 256KiB, 구조화 입력 상한 48KiB.
- **오류 분류**: `timeout / http_status / transport / invalid_response` + Core의
  `invalid_output / input_too_large / input_changed / lease_expired`. 저장·반환되는 오류에는 응답
  본문, 헤더, URL, credential이 들어가지 않는다(F06 redaction 검사).
- **lease**: 획득 시 `attempt_count += 1`, lease 45초, provider 호출은 write transaction 밖에서만
  수행, 저장 직전 snapshot_ref와 structured input hash 재확인, `lease_owner`가 같을 때만 저장.
- **생성 입력(SDD §7.3)**: WorkIssue, 승인 Spec 문서(path/text), 전체 Claim·check와 저장 status,
  Before/After Observation 결과와 비교, Baseline↔Review code state의 경로 단위 변경 목록
  (`added|modified|removed`), problem/제외, 저장 Review verdict. 변경 목록은 40개 상한을 넘으면
  `more_changed_files`로 남은 개수를 명시하며 조용히 잘라내지 않는다. Baseline code state가 없거나
  coverage가 complete가 아니면 `comparable=false`다. raw/diff 본문, file mode/origin, commit,
  Evidence·code·environment ref는 보내지 않는다.
- **grounding 양방향 규칙**: `observed`는 verified Claim source pointer만, `gap`은 기록된 gap
  (비-verified Claim source 또는 Problem source)을 최소 1개 인용해야 한다. Spec 문서와 변경 목록
  pointer는 `intent`/`inference` 근거로만 쓸 수 있다.
- **cache 분리**: `<data root>/dashboard-presentation.sqlite3`, 권한 `0600`,
  `namespace=ownhands.dashboard.presentation`, `schema_version=1`. Review verdict/Claim
  count/freshness/HumanDecision 열은 존재하지 않는다.

## 실행 결과

```text
PYTHONPATH=src uv run --python 3.12 python -m unittest tests.test_dashboard_presentation \
  tests.test_dashboard_read_model tests.test_dashboard_readonly \
  tests.test_skill_routing_fixtures tests.test_skills tests.test_skill_discovery_contract
Ran 131 tests — OK

PYTHONPATH=src uv run --python 3.12 python -m unittest discover -s tests
Ran 520 tests — OK

PYTHONPATH=src uv run --python 3.12 python tests/run_claim_mutations.py
9/9 mutations killed, errors 0

git diff --check
exit 0
```

전체 회귀 출력의 `M3 live probe refused or failed: live fixture content drift: AGENTS.md`는 기존
테스트가 예상하는 진단이며 suite exit는 0이었다. **이번 구현은 M3 live 미확인 상태를 해소하지 않는다.**

## Evidence 경계

- **E05 (mock provider ledger, fake clock, lease/restart, cache 전이)**: `RecordingGenerator`가 key별
  호출 수, `request_id`, `idempotency_key`, timeout, 전송 payload 전체를 기록한다. `Clock`은 주입형
  fake clock이며 cooldown·lease 만료·시계 역행을 초 단위로 조작한다. cache row 전이(absent →
  pending → ready/failed)와 `ready_sequence`·`attempt_count`는 cache 파일을 직접 sqlite로 열어
  확인한다. 실제 과금 없이 제어를 검증했다.
- **E06 (부적합/악의적 출력)**: F08의 8종 reject fixture와 전송 payload 가림 검사. fixture에 실제
  비밀은 쓰지 않았고, credential 문자열은 테스트용 상수다.
- **E08 (Skill/Router old→new 대응)**: `tests/test_skills.py`가 `(Spec, Review, CodeState)` key,
  explicit-request-only, stale 재생성 문구의 **부재**와 Snapshot Ref/recipe_hash/`list_visible`/
  `detail`/legacy 문구의 **존재**를 양방향으로 고정한다. `tests/test_skill_routing_fixtures.py`의
  `LifecycleRoutingContext`는 `dashboard_presentation`을 `missing|ready`로 좁히고(`stale` 제거)
  `view_intent`를 추가했다.
- **E09 (실행 기록)**: 기준 SHA, Python 버전, 명령과 결과를 위에 기록했다.
- **E01은 부분 재사용**: F11이 data root inventory와 writer/evaluator spy를 재확인한다. WI-01의 전체
  원본 dump 비교는 이번 WI에서 다시 실행하지 않았다.

## 독립 재검수

구현 직후 독립 재검수를 수행해 6건을 보고받았고, Critical/Important 4건은 실패 fixture를 먼저
추가(RED 확인)한 뒤 수정했다.

| # | 발견 | 처리 |
|---|---|---|
| 1 | `observed` TextFact가 Problem pointer(failure/blocker/unobserved)를 인용해도 통과. `status_by_pointer`의 기본값이 `verified`였다 | 기본값을 제거해 **verified Claim source pointer만** `observed` 근거가 되도록 수정. `test_f08_a_problem_pointer_may_not_be_reported_as_a_success_observation`과, 정당한 `gap` 인용이 계속 허용되는 반대 방향 fixture를 함께 추가 |
| 2 | 목록 카드에 cache 상태 overlay가 없어 `recipe_hash=""`, 항상 `absent`. viewport ensure가 `recipe_hash`를 되돌려 보낼 수 없고 `next_retry_at`도 읽을 수 없었다 | `read_list`가 상세와 같은 overlay를 적용. `test_f10_list_cards_carry_the_cache_state_the_browser_needs_to_ensure` 추가 |
| 3 | 마지막 시도 중 프로세스가 죽으면 row가 영구 `pending`으로 남아 `failed`로 정착하지 못했다 | lease 만료 + 잔여 시도 0이면 같은 transaction에서 `failed`(`lease_expired`)로 정착. `test_f07_a_crash_on_the_final_attempt_settles_as_failed_not_pending` 추가 |
| 4 | `http.client.IncompleteRead`는 `OSError`도 `URLError`도 아니어서 분류되지 않고 adapter 밖으로 탈출했다 | `HTTPException`을 transport 분류에 포함. `test_a_truncated_response_body_is_classified_as_transport` 추가 |
| 5 | 구조화 입력에 Before/After Observation 결과와 비교가 빠져 #93·SDD §7.3의 입력 목록을 충족하지 못했다 | check별 `before`/`after`/`comparisons`를 추가하되 ref·evidence link·execution·raw는 제외. `test_f08_the_structured_input_carries_before_after_results_and_comparisons` 추가 |
| 6 | `COMMIT` 뒤의 후속 조회가 실패하면 `ROLLBACK`이 원 예외를 가릴 수 있었다 | 두 write transaction의 조기 반환을 제거해 transaction 밖에서만 후속 조회하도록 정리 |

재검수 후 Critical/Important 미해결 **0**.

## PR #94 검토 반영

merge 전 검토에서 3건을 추가로 요청받았다. 모두 실패 fixture를 먼저 확인(RED)한 뒤 수정했다.

| # | 요청 | 처리 |
|---|---|---|
| 1 | `skills/dashboard/SKILL.md`의 "page navigation/inspection은 LLM을 절대 호출하지 않는다"가 최초 cache-miss view 예외와 모순 | 절대 금지 문구를 제거하고, 일반 GET·refresh·Drawer/Evidence 탐색·cache hit은 **호출 0**, **최초 real view intent**의 `ensure`만 server worker에게 해당 cache key를 넘긴다고 명시. 같은 cache key에는 한 번에 하나의 생성만 진행하고(single-flight), 성공 후에는 다시 호출하지 않으며, 실패한 경우에만 정해진 retry policy에 따라 총 2회까지 시도한다. 수동 생성/재생성 조작은 없다는 문장도 함께 고정. `test_dashboard_skill_allows_the_first_view_ensure_without_contradiction`이 옛 문구의 부재와 새 예외 문구의 존재를 양방향으로 검사 |
| 2 | SDD §7.3대로 allowlisted Spec 정보와 실제 변경 정보를 생성 입력에 포함 | `DashboardReadModel.read_generation_facts`를 추가해 승인 Spec 문서(path/text)와 Baseline↔Review code state의 **경로 단위 변경 목록**을 제공한다. §6.2 View Model은 바꾸지 않았고(브라우저는 이 값을 받지 않는다), raw·diff 본문·file mode/origin·commit은 제외했다. 40개 상한 초과는 `more_changed_files`로 명시하며 조용히 자르지 않는다. `test_f08_the_structured_input_carries_allowlisted_spec_and_change_facts`와 `test_f08_spec_and_change_pointers_may_ground_an_intent_sentence` 추가 |
| 3 | `gap`이 verified Claim만 근거로 미확인처럼 표현하지 못하게 | grounding validation을 양방향으로 바꿔 `gap`은 비-verified Claim source 또는 Problem source를 최소 1개 인용하도록 요구한다. `test_f08_a_gap_may_not_rest_only_on_verified_claims`(반례)와 `test_f08_a_gap_may_not_hide_a_verified_claim_behind_a_real_problem`(정당한 gap은 계속 통과) 추가 |

세 항목 반영 후 대상 131 / 전체 520 / mutation 9-9가 모두 통과했다.

## 미실행 및 후속 범위

- `semantic_quality=unverified`. 실제 model 호출은 한 번도 수행하지 않았다. 이 문서의 모든 결과는
  mock provider 기반 **제어 검증**이며, SDD §9의 6유형×3생성=18출력 의미 검사(T13/E07)는 이슈 6에서
  수행한다. fallback 동작만으로 ELI5 완료라고 주장하지 않는다.
- 사용자 3시나리오 60초 이해도 pilot(R16) 미실행.
- HTTP endpoint / 세션 인증 / CSRF / Origin / raw 64KiB delivery — 이슈 4.
- 브라우저 UI, 접근성·viewport 관찰(T03/E03) — 이슈 5.
- 선택 raw 발췌 extractor는 SDD §7.3의 "raw 추가는 기본 0" 기본값을 채택해 구현하지 않았다. v1
  생성 입력은 구조화 전용이다.
- 두 번째 provider adapter, provider 멱등키의 실제 서버 동작 확인, 실제 네트워크 smoke는 미실행이다.
  wire contract는 공식 OpenAI chat-completions 형식에 맞춰 작성하고 fake `urlopen`으로만 검증했다.
- single-flight는 정상 경로의 중복 호출을 막지만 충돌/종료 경계의 외부 과금까지 strict
  exactly-once를 보장하지 않는다.
- M3 live는 기존 `AGENTS.md` fixture drift로 여전히 미확인이며, 이번 구현 성공을 해소 근거로
  사용하지 않는다.
- 이 WI의 완료는 **Presentation 생성·캐시 계층 완료**만 의미한다. #89는 이슈 1–6과 통합 수용 검증이
  끝날 때까지 OPEN으로 유지한다.

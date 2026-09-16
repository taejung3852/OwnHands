# Dashboard WI-03 실행 계획 — ELI5 Presentation 생성·캐시 (#93)

기준 main: `4e3d3d0f8be87fab3f0ecd01256234e5d155c7af` (PR #92 병합).
브랜치: `feat/dashboard-wi03-presentation-cache`.
Baseline 재실행 결과: 전체 469 tests OK, Claim mutation 9/9 killed.

제품 방향은 #89 / `docs/m5-r/dashboard-sdd.md` §7·§9–10에서 승인됐다. 이 계획은 재설계가 아니라
현재 main 정합성과 구현 세부 계약만 고정한다.

## 1. 산출물

| 파일 | 역할 |
|---|---|
| `src/devharness/dashboard/generator.py` | provider 중립 `PresentationGenerator` 경계 + OpenAI-compatible adapter 1개 + 오류 분류 |
| `src/devharness/dashboard/presentation.py` | Presentation Cache(SQLite), recipe/cache key, grounding 입력, 출력 validator, lease/retry/cooldown, deterministic fallback |
| `src/devharness/dashboard/read_model.py` | `read_detail`에 `presentations`/`ready_sequence` 전달 경로만 추가 (기존 `_presentation` 재사용) |
| `tests/test_dashboard_presentation.py` | F01–F09, F11 |
| `tests/test_skill_routing_fixtures.py` | F10 routing 계약 갱신 |
| `tests/test_skills.py` | Skill 본문 회귀 fixture |
| `skills/dashboard/SKILL.md`, `skills/using-ownhands/SKILL.md` | 계약 정합화 |
| `docs/m5-r/dashboard-issue03-verification.md` | 검증 Evidence |

새 의존성 없음. stdlib(`sqlite3`, `urllib.request`, `hashlib`, `json`, `uuid`, `time`)만 사용한다.

## 2. 고정하는 구현 계약

### 2.1 provider 미설정

`PresentationConfig.from_environment()`가 base_url 또는 model을 얻지 못하면 `provider_id=None`,
`model_id=None`이다.

- `recipe_hash`는 그래도 결정적으로 계산한다: `provider_id=null, model_id=null, generation_parameters={}`.
  cache_key도 계산된다. 값이 정의되지 않는 상태를 만들지 않는다.
- `ensure_presentation`은 **cache row를 만들지 않는다.** attempt_count 증가 0, provider 호출 0.
- 반환은 `status="unavailable"`, `reason_code="provider_not_configured"`, `fallback=True`,
  `retry_after=None`. `read_presentation`도 동일하게 row 없이 unavailable을 반환한다.
- 이미 다른 recipe로 만들어진 과거 ready row는 key가 다르므로 조회되지 않는다.

### 2.2 OpenAI-compatible adapter wire contract

- 환경변수: `OWNHANDS_PRESENTATION_BASE_URL`, `OWNHANDS_PRESENTATION_MODEL`,
  `OWNHANDS_PRESENTATION_API_KEY`(선택, Ollama 등 미인증 endpoint 허용),
  `OWNHANDS_PRESENTATION_PROVIDER_ID`(선택, 기본값은 base_url의 `scheme://host[:port]`).
- 요청: `POST {base_url}/chat/completions`, `Content-Type: application/json`.
  body `{"model", "messages":[system, user], "temperature":0, "max_tokens":1200,
  "response_format":{"type":"json_object"}, "stream":false}`.
- 헤더: API key가 있을 때만 `Authorization: Bearer …`. 멱등키는 `Idempotency-Key: {cache_key}:{attempt}`.
- 크기 상한: 요청 body 64KiB(구조화 입력 48KiB 상한 + envelope), 응답 본문 읽기 상한 256KiB.
  상한 초과 응답은 더 읽지 않고 `invalid_response`.
- timeout: 30초를 `urlopen(timeout=)`에 전달한다. 프로세스 내부 경과 판정은 `time.monotonic`.
- 오류 분류: `timeout / http_status / transport / invalid_response`. 모두 Core에서 `failed`로 이어진다.
- 가림: 저장·반환하는 오류에는 응답 본문, 헤더, URL, credential을 넣지 않는다. `error_code`와
  HTTP status code만 남긴다. base_url/credential은 예외 메시지에도 넣지 않는다.
- scheme은 `http`/`https`만 허용한다.

### 2.3 cache 파일

- 경로: `catalog.paths.root / "dashboard-presentation.sqlite3"`. 코드 저장소 안에 만들지 않는다.
- 생성 시 파일 권한 `0o600`.
- 원본 `catalog.sqlite3` / `lifecycle-v1.sqlite3` 경로와 같으면 생성을 거부한다. 원본 연결은 계속
  `mode=ro` / `query_only=ON`이며 cache는 완전히 분리된 별도 connection이다.
- `presentation_meta(key, value)`에 `namespace='ownhands.dashboard.presentation'`,
  `schema_version='1'`을 기록하고 불일치 시 열기를 거부한다.
- 테이블 `presentations(cache_key UNIQUE, …)`는 SDD §7.1의 열을 그대로 쓴다.
  Review verdict / Claim status / count / freshness / HumanDecision 열은 두지 않는다.

### 2.4 lease 전이와 attempt_count

`ensure`는 짧은 write transaction 두 번으로 나뉘고, provider 호출은 그 사이 바깥에서 일어난다.

1. **claim transaction**: `BEGIN IMMEDIATE` → row 조회
   - `ready` → 그대로 반환(호출 0)
   - `attempt_count >= 2` 이고 `failed` → `failed` 유지, 호출 0
   - `next_retry_at`이 미래 → `failed` + `retry_after`, 호출 0
   - `pending` 이고 lease 미만료 → `pending` 반환, 호출 0
   - 그 외(absent / lease 만료 / cooldown 경과) → `status=pending`, `lease_owner=uuid4`,
     `lease_expires_at=now+45s`, **`attempt_count += 1`** 후 COMMIT.
   → attempt_count는 **lease 획득 시점에만** 증가한다. row 생성과 lease 획득은 같은 순간이므로
     "worker가 가져가기 전 pending"은 존재하지 않는다.
2. **provider 호출**: transaction 밖. 30초 timeout.
3. **commit transaction**: `BEGIN IMMEDIATE` → `lease_owner`가 동일할 때만 갱신한다.
   - 저장 직전 `snapshot_ref`와 `structured_input_hash`를 다시 계산해 일치할 때만 ready 저장.
     불일치면 지연 응답으로 보고 폐기한다.
   - 성공: `status=ready`, `ready_sequence = max(ready_sequence)+1`, 본문 저장. 같은 key의 ready
     본문은 이후 덮어쓰지 않는다.
   - 실패: `status=failed`, `error_code`, `next_retry_at = now+60s`, lease 해제.

시계 역행은 조기 재시도를 허용하지 않는다(`attempt_count` 상한 2가 독립적으로 막는다).

### 2.5 출력 validator 경계 — 생성 TextFact는 판정을 만들 수 없다

reject 규칙(위반 시 ready 저장 0, 생성 실패로 계산해 재시도 상한에 포함):

- schema 위반: 미정의 key, 잘못된 타입, icon 허용 목록 밖, 길이 초과(headline 60자, summary 문장
  각 120자, summary 2–3, key_changes 0–4, attention_items 0–3, next_checks 0–3).
- `kind`가 `intent|observed|gap|inference` 밖.
- SourcePointer 0개, 또는 입력에서 제공한 pointer allowlist 밖(다른 Snapshot·미도달 pointer 포함).
- **수치 집계 금지**: 어떤 TextFact `text`에도 `\d+\s*(개|건|%|/)` 형태의 집계 표현을 허용하지 않는다.
  Claim count·verdict는 API/fallback이 원본에서 직접 계산하며 모델 출력은 절대 소유하지 않는다.
- **verdict/count field 금지**: 출력 object의 어느 깊이에도 `counts/verdict/total/verified/failed/
  inconclusive/unobserved/required_complete/freshness/human_decision` key가 있으면 reject.
- 상태 정합성(양방향):
  - `kind="observed"`는 **저장 status가 `verified`인 Claim source pointer만** 인용할 수 있다.
    Problem pointer, WorkIssue 제목, Spec 문서, 변경 목록 pointer는 `observed` 근거가 될 수 없다.
  - `kind="gap"`은 **실제 기록된 gap**(비-verified Claim source 또는 Problem source)을 최소 1개
    인용해야 한다. verified Claim만 근거로 삼아 미확인처럼 말하는 문장은 reject한다.
  - Spec 문서/변경 목록 pointer는 `intent`·`inference` 근거로만 쓸 수 있다.
  (Problem pointer가 기본값 `verified`로 통과하던 구멍과 근거 없는 `gap` 구멍을 각각 재검수에서
  확인해 수정했다.)
- 금지 표현: `완전히 안전`, `모두 해결`, `merge 가능`, `현재도 최신`, `지금도 최신`, `이후 새 근거 없음`.

### 2.6 `skills/dashboard/SKILL.md` 회귀 fixture

옛 문구를 새 계약으로 교체하고, 테스트가 **양방향**으로 고정한다.

- 사라져야 할 것: `(Spec, Review, CodeState)` cache key, `only upon explicit user request`,
  `stale … making existing presentation artifacts stale` 재생성 사유.
- 있어야 할 것: `Snapshot Ref + recipe_hash` cache key, `first real Dashboard view intent`
  (`list_visible` / `detail`), stale은 재생성 사유가 아니라는 명시, 옛 key는 legacy로만 식별하고
  새 Snapshot cache로 암묵 이전하지 않는다는 명시.

### 2.7 `skills/using-ownhands/SKILL.md` routing fixture

routing 계약을 `view_intent`와 cache 상태 기준으로 바꾼다.

- `LifecycleRoutingContext`에 `view_intent: none|list_visible|detail|drawer|refresh` 추가,
  `dashboard_presentation`을 `missing|ready`로 바꾼다(`stale` 제거 — stale Snapshot은 재생성 사유가 아님).
- `dashboard` 선택 조건: 사용자의 명시 요청 **또는** 실제 최초 view intent(`list_visible`/`detail`)
  이면서 cache가 `missing`일 때만.
- Dormant: cache `ready`(hit), `drawer`, `refresh`, 일반 GET, Review 완료만 있는 상태.

## 3. 진행 순서 (RED → GREEN)

1. `tests/test_dashboard_presentation.py`에 F01–F09, F11을 먼저 작성한다. 모듈 부재로 인한
   import 오류가 아니라 **단언 실패**로 RED가 되도록 WI-02와 같은 `try/except ImportError` 패턴을 쓴다.
2. `tests/test_skill_routing_fixtures.py`, `tests/test_skills.py`에 F10과 Skill 본문 fixture를 추가해 RED 확인.
3. `generator.py` → `presentation.py` → `read_model.py` 전달 인자 → Skill 문서 순으로 최소 구현.
   목록 카드와 상세는 같은 cache 상태 overlay(`recipe_hash`, `pending/failed`, `next_retry_at`)를
   반환한다. viewport ensure가 카드의 `recipe_hash`를 그대로 되돌려 보낼 수 있어야 한다.
4. 대상 테스트 → 전체 회귀 → `tests/run_claim_mutations.py`.
5. `docs/m5-r/dashboard-issue03-verification.md` 작성. 실제 model 미실행이면 `semantic_quality=unverified`.
6. 독립 재검수 → Critical/Important 미해결 0.
7. 작은 PR 1개 (`Refs #89`, `Closes #93`), merge하지 않는다. #89는 OPEN 유지.

## 4. 이번 WI에서 하지 않는 것

- HTTP endpoint / 세션 인증 / CSRF (이슈 4)
- 브라우저 UI, raw 64KiB delivery (이슈 4·5)
- 실제 model 의미 품질 18출력 검사와 사용자 이해 pilot (이슈 6)
- **선택 raw 발췌 extractor**: SDD §7.3의 "raw 추가는 기본 0" 기본값을 채택해 v1 입력은 구조화
  전용이다. 입력에 포함되는 Spec/WorkIssue/problem 텍스트는 모두 untrusted quoted data로 감싼다.
  구조화 입력에는 WorkIssue, 승인 Spec 문서(path/text), 전체 Claim·check, Before·After
  Observation 결과와 비교, Baseline↔Review code state의 **경로 단위 변경 목록**, problem/제외,
  저장 Review verdict가 들어간다. Evidence ref, code/environment ref, execution, file mode/origin,
  commit, raw/stdout/stderr/diff는 보내지 않는다.
  변경 목록은 경로와 `added|modified|removed`만 담고 40개를 넘으면 `more_changed_files`로 남은
  개수를 명시한다. 조용히 잘라내지 않는다. Baseline code state가 없거나 coverage가 complete가
  아니면 `comparable=false`로 표시해 전체 변경이라고 말할 수 없게 한다.
- 두 번째 provider adapter
- Claim/Review 재평가, 원본 Lifecycle/Evidence 쓰기

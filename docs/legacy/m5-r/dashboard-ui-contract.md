# Dashboard UI 계약 — 화면 · 상태 · API 대응

SDD §4~9의 좁은 보완이다. 같은 계약을 두 곳에서 다르게 유지하지 않는다.

## 1. route

hash routing을 쓴다(이슈 §6.1이 허용). **SPA fallback을 두지 않으므로** API의 404/401이
HTML 200으로 바뀌는 경로가 구조적으로 없다.

```text
#/                                  Review List (랜딩)
#/?filter=<enum>                    필터 적용 목록
#/snapshots/<key>                   Review Detail
#/snapshots/<key>/claims/<id>       Detail + Evidence Drawer 열림
#/snapshots/<key>/evidence/<key>    Detailed Evidence
```

## 2. 정적 제공

| 요청 | 자산 | Content-Type | CSP |
|---|---|---|---|
| `/` | `web/index.html` | `text/html; charset=utf-8` | 문서 정책(아래) |
| `/app.js` | `web/app.js` | `text/javascript; charset=utf-8` | `default-src 'none'` |
| `/styles.css` | `web/styles.css` | `text/css; charset=utf-8` | `default-src 'none'` |

그 밖의 비-API 경로는 404 JSON이다. 경로를 조합하지 않는 literal allowlist라 traversal이
도달할 대상이 없다. 자산은 `importlib.resources`로 읽어 설치된 wheel에서도 동작한다.

문서 CSP: `default-src 'none'; script-src 'self'; style-src 'self'; connect-src 'self';
img-src 'self' data:; font-src 'self'; base-uri 'none'; form-action 'none'; frame-ancestors 'none'`

정적 경로는 **인증 전에 접근 가능**하다(토큰 화면을 그려야 하므로). Host/Origin 검사는 적용된다.
API는 그대로 세션 뒤에 있다.

## 3. 화면 ↔ API 필드

| 화면 요소 | 출처 |
|---|---|
| 목록 순서·페이지 | `GET /reviews` 응답 순서 그대로. 클라이언트 정렬 없음 |
| 작업 번호 | `issue.ref.id` |
| 작업 제목 | `issue.title` (선택 Snapshot의 revision) |
| 판정 · 이유 | `review_state`, `state_reason` |
| 숫자 | `counts.all/required/optional`, `excluded_optional_count` |
| 최신성 | `context.freshness`, `context.new_evidence_available`, `context.newer_snapshot_key` |
| 읽기 상태 | `context.read_health` |
| 설명 | `presentation.status/headline/summary/key_changes/next_checks/fallback/reason_code/retry_after` |
| 주의 | `problems[]` (Claim뿐 아니라 finding·diagnostic·blocker·conflict 포함), `remaining_problem_count` |
| 조건·검사·Before/After | `claims[].checks[].before/after/comparisons` |
| 원문 | `GET .../content?field=&cursor=` 의 `FieldVM` |

### 요약 라벨 ↔ TextFact kind

| 라벨 | kind |
|---|---|
| 왜 바꿨나 | `intent` |
| 한 일 | `key_changes[]` |
| 근거 있는 것 | `observed` |
| 아직 근거 없는 것 | `gap` |
| 추정 | `inference` |

`presentation.fallback`이 true면 라벨을 붙이지 않는다. 그 문장은 생성문이 아니라 서버의
결정적 문장이기 때문이다.

## 4. 상태 축 (뭉개지 않음)

```text
Review 판정   ready / needs-review / blocked        → 판정 카드
최신성        current / stale / unknown             → 배너 + 최신성 칩
읽기 상태     complete / partial / unavailable      → 배너 + 근거 목록 표시
설명 상태     absent / pending / ready / failed / unavailable → 요약 카드 주석
```

`ready + stale`만 판정 문자열에 `(이전 결과)`를 붙인다(이슈 §4 표). 나머지는 판정과 최신성을
같은 문자열에 합치지 않는다.

## 5. 생성 계약

- 최초 GET으로 원본과 fallback을 먼저 그린다. 생성 대기가 화면을 막지 않는다.
- 목록은 `IntersectionObserver`로 실제 viewport에 들어온 카드만 `list_visible`,
  Detail은 해당 Snapshot만 `detail`로 ensure한다.
- `presentation.status`가 `absent`가 아니면 POST하지 않는다. `recipe_hash`는 서버 값을 되돌린다.
- 같은 key의 진행 중 요청은 in-flight Set으로 막고, 같은 화면에서 두 번 ensure하지 않는다.
- `202` → polling 1s → 2s → 5s → 이후 5s, 누적 60s에 중단. `document.hidden`이면 중단하고
  다시 보이면 GET부터 재개한다. polling GET은 재생성이 아니다.
- `failed`의 `retry_after` 이전에는 재요청하지 않는다. 수동 생성·재생성 버튼은 없다.
- route가 바뀌면 이전 요청의 늦은 응답을 버린다(route token 비교).

## 6. 세션

- boot token → `POST /session` → cookie는 브라우저, CSRF는 **메모리 변수**.
- 토큰은 제출 즉시 입력칸을 비우고 URL·`localStorage`·`sessionStorage`·console에 남기지 않는다.
- **새로고침 후 cookie는 남고 CSRF는 사라진다.** 이때 조회는 그대로 되고(GET에 CSRF 불필요)
  생성만 멈춘다. 화면은 그 상태를 안내하고 토큰 재입력 경로를 제공한다. 현재 API에 CSRF 재발급
  경로가 없다는 계약 차이는 그대로 기록해 둔다.
- 401/403에서 자동 재요청 루프를 만들지 않는다.

## 7. 오류 매핑

| 응답 | 화면 |
|---|---|
| 200 빈 목록 | 빈 상태 문구 (검색·필터 결과 없음과 구분) |
| 400 `INVALID_QUERY` | 안내 + 목록 재조회 |
| 401 | 토큰 화면, 원래 route 복원 |
| 403 `ORIGIN_DENIED`/`CSRF_FAILED` | 안내만. 재시도 버튼 없음 |
| 404 `NOT_FOUND` | 없음 안내 + 목록 복귀 |
| 409 `LIST_CHANGED`/`SOURCE_CHANGED` | 페이지를 이어붙이지 않고 처음부터 재조회 |
| 409 `RECIPE_CHANGED` | 실패 요청을 replay하지 않음 |
| 503 | 읽을 수 없음 안내 + 마지막 확인 시각 |

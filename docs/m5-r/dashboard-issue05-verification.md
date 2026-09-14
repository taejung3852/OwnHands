# Dashboard 이슈 5 Verification — 3페이지 + Evidence Drawer UI (#97)

## 범위와 기준

- 대상: 디자인 정합화, 같은 origin 정적 제공, 3페이지 + Drawer 화면, 기존 API 결합, 세션 연결.
- 기준 main: `914885c611e65a305b3186685b21918abfdd9ed9` (PR #96 병합).
- 실행 브랜치: `feat/dashboard-issue05-ui`.
- 환경: Python `3.12.14`, macOS. stdlib 전용, 신규 런타임 의존성 0.
- 디자인 원문 SHA-256: `be43b27308068a4b588131982c0998c8466b3ecdcc6e5ffa8846cdd1953a8204`
  (`docs/m5-r/dashboard-design-source.md`). 이슈 §0에 기록된 해시와 **일치**한다.

## Baseline 재측정

```text
PYTHONPATH=src uv run --python 3.12 python -m unittest discover -s tests
Ran 550 tests — OK

PYTHONPATH=src uv run --python 3.12 python tests/run_claim_mutations.py
9/9 mutations killed, errors 0
```

## 실행 결과

```text
PYTHONPATH=src uv run --python 3.12 python -m unittest tests.test_dashboard_web \
  tests.test_dashboard_api tests.test_dashboard_presentation tests.test_dashboard_read_model \
  tests.test_dashboard_readonly tests.test_skills tests.test_skill_routing_fixtures
Ran 177 tests — OK

PYTHONPATH=src uv run --python 3.12 python -m unittest discover -s tests
Ran 569 tests — OK   (baseline 550 → 신규 19)

PYTHONPATH=src uv run --python 3.12 python tests/run_claim_mutations.py
9/9 mutations killed, errors 0

git diff --check
exit 0
```

전체 회귀의 `M3 live probe refused or failed: live fixture content drift: AGENTS.md`는 기존
테스트가 예상하는 진단이며 suite exit는 0이었다. 이번 구현은 M3 live 미확인을 해소하지 않는다.

## 설치 패키지 확인

저장소 개발 경로가 아니라 **설치된 wheel**에서 확인했다.

```text
uv build --wheel
  → devharness/dashboard/web/{index.html,app.js,styles.css} 포함 확인

uv pip install <wheel>  (별도 venv)
  → importlib.resources 로 site-packages 경로에서 3개 자산 해석 확인

python -m devharness dashboard --data-root <fixture> --project-id <id> --port 8791
  → dashboard=http://127.0.0.1:8791/
     token=...
```

이후의 브라우저 관찰은 모두 이 **설치 패키지 서버**를 대상으로 했다.

## 브라우저 관찰 (Chromium, 사용자 주환경)

고정 fixture 데이터(합성)로 실제 조작했다. 실제 LLM은 쓰지 않았고 Presentation은 provider
미설정 상태의 결정적 fallback이다.

| 확인 | 관찰 결과 |
|---|---|
| 접속 → 목록 | 토큰 입력 화면이 먼저 뜨고, 접속 후 `먼저 볼 것` + `다른 작업의 검토 N건`이 렌더 |
| 목록 정보 | 작업 번호·제목·요약·숫자·최신성·Snapshot 시각. 순서는 서버 rank 그대로 |
| Detail | 60:40 좌우. 좌: 작업 요약 → 검증 요약 → 근거 탐색 / 우 rail: 판정 → 주의 → 다음 확인 |
| 분모 보존 | `전체 7 · 필수 5 · 선택 2 (선택 제외 1)`, 확인됨 3 / 실패 1 / 판단불가 1 / 미확인 2 |
| 주의 ≠ Claim | 모든 Claim이 verified가 아닌 Snapshot에서 `주의 필요 8건`이 problems 기준으로 표시 |
| Drawer | 우측에서 열리고 Detail이 뒤에 남음. `role=dialog`, `aria-modal=true`, 접근 가능한 이름 |
| Drawer focus trap | Tab 3회 후에도 focus가 Drawer 안에 유지 |
| ESC 닫기 + 복귀 | ESC로 닫히고 focus가 **열었던 조건 행으로 복원**(`restoredToTrigger: true`) |
| 근거 상세 | metadata 표시, 미수집 field는 `not_collected`로 정직하게 표기(명령 추측 0) |
| 64KiB 페이징 | 216KB raw가 17,039자 → 51,023 → 85,003 → 112,103자로 이어지고 마지막에 버튼 사라짐 |
| 안전한 렌더링 | 원문의 `<script>`가 텍스트로만 표시. DOM의 `<script>`는 `app.js` 1개뿐 |
| ANSI 무력화 | 원문 ESC가 실제 제어 바이트 없이 `\x1b` 문자열로만 전달(`escBytes: false`) |
| deep link 새로고침 | 근거 상세 URL에서 새로고침 → 같은 화면 복원, 로그인 요구 없음 |
| CSRF 소실 상태 | 새로고침 후 조회는 유지되고 생성만 중단. 별도 안내와 토큰 재입력 경로 제공 |
| 375×812 | 좌우 분할이 1열(`grid-template-columns: 293px`), 페이지 가로 스크롤 없음, `word-break: keep-all` |
| CSP | 문서 정책 위반 0. (초기 구현의 인라인 style 위반 64건은 전량 클래스로 이전해 해소) |

### 구현 중 브라우저로 잡은 결함

1. **인라인 style 64건이 CSP에 막힘** — `style-src 'self'`는 style 속성도 차단한다.
   정책을 완화하지 않고 전부 클래스로 옮겼고, 재발 방지 테스트를 추가했다.
2. **`lastCards is not defined`로 목록이 백지** — strict mode에서 미선언 할당이 throw.
   죽은 변수라 제거하고, 미선언 최상위 할당을 잡는 정적 검사를 테스트로 고정했다.
3. **로그인 실패 문구가 화면에 안 붙음** — 오류 문단을 조건부로만 DOM에 넣고 있었다.
   항상 넣고 `role="alert"`를 달았다.
4. **Drawer를 닫아도 focus가 body로** — hashchange 재렌더가 trigger를 없앤다.
   닫을 때 조건 id를 기억해 재렌더 후 그 행으로 복원한다.
5. **fallback 문장에 생성문 라벨이 붙음** — 서버의 결정적 문장에 `근거 있는 것`이 붙어 오해를 준다.
   `presentation.fallback`이면 라벨 없이 문장만 보인다.
6. **시작 실패가 traceback** — 포트 충돌 시 argparse 오류로 바꿨다.

## 독립 재검수

구현 후 독립 재검수에서 7건을 보고받았고 전부 수정했다. 동작을 바꾸는 3건은 실패 fixture를
먼저 확인(RED)한 뒤 고쳤다.

| # | 발견 | 처리 |
|---|---|---|
| 1 | `failed`로 정착한 설명이 다시 시도되지 않음 — 모든 ensure 트리거가 `status === "absent"`만 봤다 | `ensurable()` 술어를 도입해 `absent` 또는 cooldown이 지난 `failed`를 재시도 대상으로 삼는다. 서버가 허용한 2회차가 실제로 도달 가능해졌다 |
| 2 | 탭 복귀 때마다 화면 전체를 다시 그려 스크롤이 초기화됨 | 복귀는 중단된 polling만 재개한다. 실측으로 같은 DOM 노드 유지·scrollY 900 보존 확인 |
| 3 | polling timer가 전역 하나라 동시 polling을 취소할 수 없었다 | key별 Map으로 추적하고 `stopPolls()`로 모두 해제. F07의 "누적 timer 없음"을 실제로 만족 |
| 4 | 근거 상세가 5개 field를 순차로 기다린 뒤에야 화면을 그림 | 머리말·metadata를 먼저 칠하고 각 패널을 도착하는 대로 채운다 |
| 5 | 거부된 ensure가 "이미 요청함"으로 기억됨 | 200/202가 아니면 `asked`에서 제거해 세션을 고친 뒤 다시 시도할 수 있게 했다 |
| 6 | 시작 시 목록을 두 번 읽음 | probe를 없애고 `listScreen`의 401 분기가 토큰 화면을 담당한다 |
| 7 | 자산을 요청마다 디스크에서 다시 읽음 | 프로세스 수명 동안 1회만 읽어 캐시한다 |

재검수 후 Critical/Important 미해결 **0**.

## PR #98 리뷰 반영 (4건)

리뷰에서 받은 4건은 각각 실패 fixture를 먼저 넣어 RED를 확인한 뒤 고쳤다. 직전 클라이언트로
되돌려 실행했을 때 새 fixture 5건이 모두 실패하는 것을 확인했다(`failures=4, errors=1`).

| # | 요청 | 구현 | 브라우저 관찰 |
|---|---|---|---|
| 1 | `/reviews?q=&cursor=` 실제 연결 + `active_snapshot_key` 불일치 표시 | 검색 form이 `#/?q=`를 만들고 `listQuery()`가 `filter`/`q`/`cursor`를 그대로 전달한다. `next_cursor`가 있을 때만 `더 보기`가 붙고 다음 장을 **덧붙인다**. `list_token`이 1장과 다르면 이어 붙이지 않고 `LIST_CHANGED` 안내와 함께 처음부터 다시 읽는다. 검색은 `canEnsure()`의 `searching()` 분기로 생성을 막는다 | 24건 fixture에서 20건 + `더 보기` → 24건, 버튼·안내문 동시 제거, 머리말 수가 함께 갱신. `결제` 검색은 3건으로 좁혀지고 `presentation/ensure` 요청 0. 활성본이 다른 Snapshot에 `현재 적용 중인 보고서는 따로 있습니다` 링크 표시 |
| 2 | hidden 전환 시 polling key/onDone 보존, 복귀는 GET부터 | `polls`가 `{timer, onDone, step, spent}`를 들고, `stopPolls(true)`가 `suspended`로 옮긴다. `resumePolls()`는 먼저 `refresh(key)`로 GET한 뒤 저장된 `step`/`spent`에서 사다리를 잇는다. 화면 이동(`render()`)은 `stopPolls(false)`로 폐기한다 | **미관찰** — 아래 참조 |
| 3 | legacy `checks=[]` + `observations[]`의 Evidence 수·링크·Drawer 탐색 | `claimObservations()`가 `checks`가 비면 `claim.observations`를 쓰고, `evidenceKeysOf()`가 거기서 Evidence key를 중복 없이 센다. legacy Drawer는 `상세 검사 항목은 이전 형식에서 기록되지 않았습니다`를 밝히고 저장된 Before/After만 보여준다. 새 check는 만들지 않는다 | v1·`checks=0`·`observations=1` fixture에서 `필수 · 근거 1` 표시, Drawer에 안내문과 Before/After, `상세 근거 열기` → 근거 상세 화면까지 이동 |
| 4 | `problems` 4번째 이후 확장 UI | 전부 렌더하고 3건 뒤는 `hidden`으로 두며, `aria-expanded`가 붙은 토글이 펼치고 접는다. 상태 변화는 live region이 읽는다 | 7건 fixture에서 3건 표시 + `추가 4건 보기` → 7건, `aria-expanded` false↔true, `주의 7건을 모두 표시했습니다.`/`주의 3건만 표시합니다.` 안내 |

### 이번 라운드에 브라우저로 잡은 결함

1. **`hidden`이 먹지 않아 4건이 그대로 보임** — 항목이 `display:flex`라 UA의 `[hidden]` 규칙을
   덮어썼다. `[hidden] { display: none !important; }`를 시트에 넣고 재발 방지 검사를 추가했다.
2. **`더 보기`가 사라져도 옆의 설명 문구가 남음** — 버튼만 지우고 있었다. 행 전체를 지운다.
3. **머리말의 총 건수가 1장 기준으로 굳음** — 페이지를 이을 때 머리말과 부제를 함께 갱신한다.

## 2차 외부 재검수 (2건)

외부 재검수에서 Important 2건을 받았고 둘 다 타당해 수정했다. 각각 실패 fixture를 먼저 확인했다.

| # | 발견 | 확인한 사실 | 처리 |
|---|---|---|---|
| 1 | 생성이 끝나면 목록 pagination이 날아감 | 목록 카드의 ensure 완료 callback이 `render()`였다. 브라우저에서 `더 보기`로 24건을 본 뒤 `render()`를 호출하니 **19건으로 되돌아갔다**. 지적되지 않은 부작용이 하나 더 있었다 — `render()`는 `stopPolls(false)`로 `suspended`까지 비우므로 다른 카드의 일시정지된 polling도 함께 버려진다. 한편 스크롤 초기화는 실제로 일어나지 않았다(`paint()`가 `scrollY`를 건드리지 않는다) | `watchCard()`가 카드마다 repaint 함수를 등록하고, 생성이 끝나면 그 노드만 `replaceChild`로 교체한다. IntersectionObserver가 없는 경로도 같은 함수를 쓴다. 관찰: 24건 유지, 새 요약 문장 표시, `다른 작업의 검토 24건` 그대로 |
| 2 | Claim과 무관한 Problem을 `선택`으로 오표시 | SDD §Problem은 `required: bool\|null`이고, `read_model.py:461`의 `required.get(claim_id)`는 `criterion_id` 없는 finding/diagnostic에 `None`을 준다. 실제로 읽어 `finding \| required = null \| claim_id = null`을 확인했다. 저장소의 기존 fixture 두 곳이 이미 이런 finding을 만든다 | `problemBadge()`가 `true`→`필수 · kind`, `false`→`선택 · kind`, `null`→**kind만** 표시한다. `조건 미지정` 같은 라벨은 '값이 빠졌다'는 뉘앙스를 주는데, finding/diagnostic은 Claim에 속하지 않는 문제라 애초에 진술할 필수/선택이 없다. 확인 결과 `required=null`은 `claim_id=null`일 때만 나오며, 제외된 선택 조건은 `required=false`로 정상 해석된다. 관찰: 같은 화면에 `필수 · failure`와 `finding`이 나란히 표시됨. 서버 계약도 API 테스트로 고정했다 |

## F01–F14 대응

| ID | 이번 이슈에서 확보한 근거 | 상태 |
|---|---|---|
| F01 디자인 우선순위 | 정합화표 12건(`dashboard-design.md`), 실제 화면에서 요약·상태·이유가 먼저 보임 | 확보 |
| F02 목록/탐색 | 서버 순서 그대로 렌더, 클라이언트 정렬 없음. 필터 chip + 검색 + `next_cursor` 이어 읽기. 검색 생성 0(cached-only) | 확보 — 24건 fixture로 2장 이어 읽기 관찰. `LIST_CHANGED` 재시작만 자동 테스트 |
| F03 판정/분모 | 전체 7·필수 5·선택 2·제외 1 보존, 모든 Claim verified 아님 + problems 8건 동시 표시 | 확보 |
| F04 최신성/읽기 | 네 축 분리 렌더. `ready+stale`만 판정에 `(이전 결과)` | 부분 — partial 원본은 자동 테스트로만 |
| F05 최초 생성 | `IntersectionObserver` 기반 viewport ensure, in-flight 억제, cache ready면 POST 0 | 부분 — provider 미설정 fixture라 실제 생성 왕복은 미관찰 |
| F06 대기/실패 | polling 1→2→5s·60s 상한·hidden 중단 구현. `retry_after` 준수 | 미관찰 — 실제 pending을 만들 provider가 없음 |
| F07 응답 경쟁 | route token으로 늦은 응답 폐기, hashchange마다 timer 해제 | 부분 — 코드 경로만, 지연 주입 미실행 |
| F08 Drawer/Evidence | Drawer→상세→복귀, ESC/focus 복원, Before 없음 표기, 미관측 PASS화 0 | 확보 |
| F09 raw 보안/페이징 | 216KB·HTML·ANSI·제어문자로 4회 페이징, script 주입 0, ESC 바이트 0 | 확보 |
| F10 브라우저 세션 | 최초 로그인·새로고침·deep link·CSRF 소실·401. token 저장·URL 노출 0 | 부분 — 새 탭·서버 재시작은 미관찰 |
| F11 정적 제공 | 설치 후 시작, MIME/CSP, allowlist 밖 404, traversal 0, API 오류 HTML화 0 | 확보 |
| F12 오류 상태 | 401/404/409/503 매핑 구현 + 자동 테스트 | 부분 — 409 실제 경쟁은 자동 테스트로만 |
| F13 시각/접근성 | 375·1440 관찰, 900px 전환, keep-all, focus trap, 44px 조작 | 부분 — 768·200% zoom 미관찰 |
| F14 읽기전용 회귀 | writer/evaluator spy 0, inventory 불변, 전체 579 + mutation 9/9 | 확보 |

## 미실행 및 후속 범위

- **`semantic_quality=unverified`**. 실제 LLM 호출 0. 화면 검증은 provider 미설정 상태의
  결정적 fallback 기준이며, 18출력 의미 검사와 사용자 60초 이해도 pilot은 이슈 6 범위다.
- 768×1024와 200% zoom은 실제 브라우저로 관찰하지 않았다. CSS 규칙은 있으나 미확인이다.
- Safari 등 Chromium 외 브라우저는 실행하지 않았다. 지원 검증 완료라고 하지 않는다.
- 실제 생성 왕복(202 pending → polling → ready), 서버 재시작 후 재접속, 새 탭은 자동 테스트
  또는 코드 경로로만 확인했고 브라우저 관찰은 없다. 다중 페이지 cursor는 이번에 관찰했다.
- **hidden 탭 polling 보존·재개는 브라우저로 관찰하지 못했다.** 두 가지가 겹친다. (1) 이 환경의
  미리보기 탭은 `document.visibilityState`가 계속 `hidden`이라 실제 전환을 만들 수 없다.
  (2) 느린 stub provider를 붙여도 서버가 lease를 기다렸다가 종결 상태로 답하므로 클라이언트가
  `pending`에 머무르지 않는다. 구현과 fixture로만 확인했다.
- CSRF 재발급 endpoint는 API에 없다. 현재는 토큰 재입력이 유일한 복구 경로이며, 최소 계약
  변경 제안은 별도로 남긴다.
- 팔레트 채도 조정은 사용자 선택 대기 중이라 원문 값을 유지했다.
- M3 live는 기존 `AGENTS.md` fixture drift로 여전히 미확인이다.
- 이 이슈의 완료는 화면 계층 완료만 의미하며 #89 종료는 이슈 6 이후다.

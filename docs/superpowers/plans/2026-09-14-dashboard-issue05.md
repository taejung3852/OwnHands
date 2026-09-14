# Dashboard 이슈 5 실행 계획 — 3페이지 + Evidence Drawer UI (#97)

기준 main: `914885c611e65a305b3186685b21918abfdd9ed9` (PR #96 병합).
브랜치: `feat/dashboard-issue05-ui`.
Baseline 재실행: 전체 550 tests OK, Claim mutation 9/9 killed.

## 0. 디자인 기준

사용자 확정 지시:

> 시안의 정보 계층·톤·전체 UX는 구현 기준으로 따른다. 픽셀 단위 너비·간격·줄바꿈·breakpoint는
> 실제 브라우저에서 더 자연스러운 결과를 위해 조정할 수 있다. 데이터·상태·보안 계약은 변경하지
> 않는다. 시안을 픽셀 퍼펙트하게 복제하는 것보다 실제 데이터에서 깨지지 않는 UI를 우선한다.

시안(artifact v15)에서 확정된 정보 계층을 그대로 구현한다.

- 랜딩 = `먼저 볼 것`(서버 우선순위 1번) + `다른 작업의 검토 N건`. 각 행은 서로 다른 작업이며
  작업 번호를 단다.
- 요약은 kind 라벨 행으로 나눈다: `왜 바꿨나 / 한 일 / 근거 있는 것 / 아직 근거 없는 것`.
- Detail은 좌측 읽기 흐름(작업 요약 → 검증 요약 → 근거 탐색) + 우측 rail(상태 → 주의 → 다음 확인).
- 상태는 inline SVG 아이콘 + 텍스트. 색만으로 구분하지 않는다.
- 대비 미달 토큰은 시안의 정합화를 따른다: 본문은 `ink-muted #4f5662`,
  `warn-ink #7a5412` / `ok-ink #27693f` / `stale-ink #5a5478`. 원본 hue는 아이콘·경계선에만.
- Warm Paper Neutral 유지. 팔레트 채도 변경은 사용자 선택 대기 중이므로 원본 §6 값을 쓴다.

## 1. 라우팅 — hash routing

이슈 §6.1이 허용하는 단순한 방식을 택한다.

```text
#/                                    Review List (랜딩)
#/snapshots/<key>                     Review Detail
#/snapshots/<key>/claims/<id>         Detail + Evidence Drawer 열림
#/snapshots/<key>/evidence/<key>      Detailed Evidence
```

**SPA fallback을 두지 않는다.** 정적 경로는 아래 세 개의 allowlist뿐이고 나머지 비-API 경로는
404다. 그래서 API의 404/401이 HTML 200으로 바뀌는 경로가 구조적으로 존재하지 않는다.
새로고침·뒤로·앞으로는 `hashchange`로 처리하고 기존 API 경로는 바꾸지 않는다.

## 2. 정적 제공

`src/devharness/dashboard/web/` 아래 3개 파일만 제공한다.

| 요청 | 파일 | Content-Type |
|---|---|---|
| `/` | `index.html` | `text/html; charset=utf-8` |
| `/app.js` | `app.js` | `text/javascript; charset=utf-8` |
| `/styles.css` | `styles.css` | `text/css; charset=utf-8` |

- 경로는 **literal dict allowlist**다. 경로 조합·traversal·data root 노출 경로가 없다.
- 자산은 `importlib.resources`로 읽어 설치된 패키지에서도 동작한다. wheel 포함은
  `[tool.setuptools.package-data]`로 고정한다.
- 인증 **전**에 접근 가능해야 한다(토큰 입력 화면을 그려야 하므로). API는 그대로 인증 뒤에 있다.
- Host/Origin 검사는 정적 경로에도 적용한다.
- HTML 문서에만 별도 CSP를 준다:
  `default-src 'none'; script-src 'self'; style-src 'self'; connect-src 'self'; img-src 'self' data:; base-uri 'none'; form-action 'none'; frame-ancestors 'none'`.
  인라인 script/style을 쓰지 않는다. `/api/` 응답의 기존 `default-src 'none'`은 건드리지 않는다.

## 3. 생성 계약 (이슈 §5)

- 최초 GET으로 원본과 fallback을 먼저 그린다. 생성 대기가 화면을 막지 않는다.
- 목록은 `IntersectionObserver`로 **실제 viewport에 들어온 카드만** `list_visible` ensure.
  Detail은 해당 Snapshot만 `detail`.
- cache ready이면 ensure POST를 보내지 않는다. `recipe_hash`는 서버가 준 값을 그대로 되돌린다.
- 같은 key의 진행 중 요청은 프론트에서도 중복 등록하지 않는다(in-flight Set).
- `202 pending`이면 polling 1초 → 2초 → 5초 → 이후 5초, 누적 60초에 중단.
  `document.hidden`이면 중단하고 다시 보이면 GET부터 재개한다.
- `failed`는 `retry_after` 이전에 재요청하지 않는다. 수동 생성/재생성 버튼 없음.
- route가 바뀌면 이전 요청의 늦은 응답을 버린다(요청마다 route token 비교).

## 4. 세션

- 토큰 입력 → `POST /api/dashboard/v1/session` → cookie는 브라우저가, CSRF는 **메모리 변수**에만.
- 토큰은 제출 즉시 입력칸을 비우고 URL·`localStorage`·`sessionStorage`·console에 남기지 않는다.
- 새로고침 시 CSRF가 없으면 토큰 재입력 화면을 보이고, 입력 후 **원래 hash route로 복원**한다.
- 401/403에서 자동 재요청 루프를 만들지 않는다.

## 5. 안전한 렌더링

- 모든 텍스트는 `textContent`로 넣는다. `innerHTML`은 이 코드베이스에서 쓰지 않는다.
- 아이콘 SVG만 고정 문자열로 생성하며 사용자 데이터가 들어가지 않는다.
- 서버가 준 visible escape(`\x1b` 등)를 그대로 보여준다. 추가 escape를 덧씌우지 않는다.
- 외부 링크 자동 방문·`eval`·ANSI 재해석 없음. 런타임 외부 CDN 요청 0(폰트 포함).

## 6. 산출물

| 파일 | 역할 |
|---|---|
| `src/devharness/dashboard/web/index.html` `styles.css` `app.js` | 제품 화면 |
| `src/devharness/dashboard/server.py` | 정적 allowlist + 문서 CSP |
| `pyproject.toml` | 패키지 자산 포함 |
| `tests/test_dashboard_web.py` | F01–F14 중 자동 검증 가능한 범위 |
| `docs/m5-r/dashboard-design.md` | 디자인 원문 보존 + 정합화 변경 이력 |
| `docs/m5-r/dashboard-ui-contract.md` | 화면·상태·API 필드 대응표 |
| `docs/m5-r/dashboard-issue05-verification.md` | 검증 Evidence |

## 7. 진행 순서

1. 디자인 원문 보존 + 정합화표 문서화.
2. 실패 fixture 작성 → RED 확인.
3. 정적 제공 + CSP → 화면 자산 → 생성/폴링 계약 순으로 최소 구현.
4. 대상 테스트 → 전체 회귀 → mutation.
5. **실제 브라우저**로 로그인 → 목록 → 상세 → Drawer → 근거 → 복귀, 새로고침·deep link·키보드 확인.
6. 검증 문서 작성 → 독립 재검수 → 작은 PR (`Refs #89`, `Closes #97`).

## 8. 이번 이슈에서 하지 않는 것

- 실제 모델 18출력 의미 품질, 사용자 60초 pilot — 이슈 6.
- dark mode, 분석 차트, 다중 사용자, 원격 배포.
- Claim/Review 재평가, 원본 쓰기, HumanDecision.
- 팔레트 채도 변경(사용자 선택 대기) — 시안 원본 값을 쓴다.

# Dashboard WI-04 Verification — HTTP API · 세션 보안 · Evidence 전달 (#95)

## 범위와 기준

- 대상: `/api/dashboard/v1` read endpoints와 `presentation/ensure`, 64KiB Evidence content 전달,
  loopback 고정 bind, session token → cookie 교환, Host/Origin/CSRF, 안정된 error envelope,
  로그 redaction, `devharness dashboard` 시작 명령.
- 기준 main: `6c1d8e058e4c8dabaffec509e8ac9b39d032d6a5` (PR #94 병합 커밋).
- 실행 브랜치: `feat/dashboard-wi04-http-api`.
- 환경: Python `3.12.14`, macOS 로컬 fixture, stdlib 전용(신규 의존성 0).
- 원칙: transport는 SQL도 평가도 하지 않는다. 이슈 1~3의 read-only reader와 Presentation Service만
  호출하며 원본 Lifecycle/Evidence에는 쓰지 않는다.

## Baseline 재측정

병합된 main에서 새 worktree를 만든 뒤 구현 전에 다시 실행했다.

```text
PYTHONPATH=src uv run --python 3.12 python -m unittest discover -s tests
Ran 520 tests — OK

PYTHONPATH=src uv run --python 3.12 python tests/run_claim_mutations.py
9/9 mutations killed, errors 0
```

## TDD 관찰

`tests/test_dashboard_api.py`의 F01–F14 fixture 23개를 구현 전에 작성했다. 최초 실행은 23/23이
`Dashboard HTTP server is not implemented` **단언 실패**로 RED였다(fixture import 오류 아님).
최소 구현 후 GREEN. 독립 재검수에서 나온 4건도 각각 실패 fixture를 먼저 확인한 뒤 고쳤다.
최종 신규 테스트는 29개(F01–F14 23 + 재검수 회귀 4 + CLI 2)다.

## F01–F14 결과

| ID | 고정 입력/공격 | 관찰 결과 |
|---|---|---|
| F01 | readonly 원본 반복 GET, 그리고 source DB가 없는 data root | GET 전후 data root inventory 동일. 원본이 아예 없으면 `GET /reviews`는 **200 + 빈 목록**이고 직접 key는 404이며, 질의 검증(400)은 그대로 선행한다. 어느 경로에서도 **파일을 하나도 만들지 않는다**(migration/reconcile 0) |
| F02 | 없는 snapshot key, 없는 claim id, 다른 Snapshot의 evidence key, 없는 evidence key | 모두 404이고 `error` 본문이 **바이트 단위로 동일**. 범위 밖 key와 없는 key를 구분할 수 없다 |
| F03 | 6개 GET 경로 ×2회, writer/evaluator spy + provider ledger | `append/activate/bind_evidence/evaluate_review/put/purge` 호출 0, provider 호출 0 |
| F04 | ensure miss → hit ×3, GET presentation, 실패 provider, 다른 worker의 유효 lease, 잘못된 view_intent | miss만 생성(호출 1), 이후 hit 0. 변경된 파일은 `dashboard-presentation.sqlite3` 하나뿐. status 매핑은 `ready` 200 / `pending` **202** / cooldown `failed` 200이며 read-only polling GET은 항상 200이다. Presentation 상태는 transport 오류와 섞이지 않는다(`error` 키 없음). `drawer`/빈 값/누락 intent는 400 |
| F05 | 200KiB UTF-8 raw, 두 Evidence의 cursor 교차 | 모든 chunk ≤64KiB, 4개 이상으로 분할, 이어붙인 결과가 원문과 완전 일치. cursor는 opaque(경로·evidence id 노출 0)이며 다른 evidence·잘못된 값·빈 값·없는 field는 400 |
| F06 | 정상 text / purged / binary / 미수집 field / missing / reference_only | `available` / `purged` / `unsupported(binary_content)` / `not_collected` / `missing` / `unsupported(reference_only)`로 정확히 구분. binary는 text `null`이며 강제 디코딩 0 |
| F07 | `<script>`, ANSI `\x1b[31m`, `onerror=`, BEL | `Content-Type: application/json`, `X-Content-Type-Options: nosniff`, `Content-Security-Policy: default-src 'none'`. 제어 바이트는 `\x1b` 형태의 보이는 escape로만 전달되고 원문 markup은 데이터로 보존 |
| F08 | `../../etc/passwd`, `%2f` 인코딩, `path=`/`field=file://` 주입, `data_root`·`project_id` query | 응답에 `/etc/passwd`·`root:` 흔적 0. scope는 서버 소유이며 query로 덮이지 않는다 |
| F09 | 미인증 GET, 잘못된 token, query string token | 401 `UNAUTHENTICATED`. query token은 인증되지 않고 token/`token=`이 로그에 남지 않는다. cookie는 `HttpOnly`·`SameSite=Strict`이며 session id와 token은 응답 body에 없다(body는 `csrf_token`뿐) |
| F10 | 외부 Host/Origin, `null` Origin, 다른 port, CORS preflight, CSRF 누락/오류 | 모두 403이고 `Access-Control-Allow-Origin` 미발급, preflight는 405. CSRF 실패 시 provider 호출 0이며 올바른 header로는 200 |
| F11 | 잘못된 filter/limit/cursor/q, recipe 불일치, 계속 변하는 source | 400 `INVALID_QUERY`, 409 `RECIPE_CHANGED`(provider 호출 0), 409 `SOURCE_CHANGED`(`retryable=true`). envelope는 `{error{code,message,retryable}, request_id}` 고정 |
| F12 | 읽는 중 raw 내용 변조, 크기 변경, 창별 무결성 | 변조 후 이어읽기는 `corrupt`(text `null`, cursor `null`) 또는 503이며 변조된 바이트가 응답에 절대 섞이지 않는다. 창마다 size/hash를 다시 검증한다 |
| F13 | token/csrf/cookie/raw 본문/query 값/key/credential/data root | 로그에는 `request_id`, method, **route template**(`/snapshots/{snapshot_key}`), status, code, latency만 남는다. 위 9종 중 어느 것도 로그에 없다 |
| F14 | `0.0.0.0`, `::`, `192.168.1.10`, `example.com`, 빈 문자열 / 정상 loopback 3종 | 비-loopback은 시작 전에 `ValueError`. `127.0.0.1`·`::1`·`localhost`만 bind되고 실제 주소가 loopback임을 확인 |

CLI는 `dashboard` 명령이 data root·project·host·port를 그대로 전달하고, 비-loopback host를 서비스
시작 전에 거부하는 것까지 확인했다.

## 구현이 고정한 계약

- **status 매핑**: 400 `INVALID_QUERY` / 401 `UNAUTHENTICATED` / 403 `ORIGIN_DENIED`·`CSRF_FAILED` /
  404 `NOT_FOUND` / 405 `METHOD_NOT_ALLOWED` / 409 `SOURCE_CHANGED`·`LIST_CHANGED`·`RECIPE_CHANGED` /
  503 `SOURCE_UNAVAILABLE`·`UNSUPPORTED_SCHEMA`·`SOURCE_INTEGRITY_ERROR`.
  성공 status도 고정했다: `ensure`는 `ready` 200 / `pending` 202 / cooldown `failed` 200이고,
  polling GET은 항상 200이다.
  `SOURCE_INTEGRITY_ERROR`는 **503**으로 고정했다. SDD §6.3이 "원본 journal 손상은 503"으로 이미
  정하고 있고, 이것은 서버 결함이 아니라 원본 상태이기 때문이다. message는 고정 문구뿐이다.
- **cookie**: `HttpOnly; SameSite=Strict; Path=/api/dashboard/v1`. **`Secure`는 v1에서 켜지 않는다.**
  서버가 평문 loopback에만 bind하고 `Secure` cookie의 loopback 취급이 브라우저마다 달라 로그인이
  깨질 수 있기 때문이다. 대신 bind를 loopback으로 강제하고 Host/Origin 검사를 유지한다. 외부 origin
  허용 완화가 아니며, TLS 종단이 생기면 그때 켠다.
- **CSRF**: 세션 교환 응답 body의 `csrf_token`을 `X-OwnHands-CSRF` header로 되돌려 보내야 한다.
  cookie에 넣지 않으므로 cross-site 스크립트가 읽어낼 수 없다.
- **content**: field는 `raw|stdout|stderr|diff|command`. chunk 상한 64KiB(바이트). cursor는
  `{snapshot_key, evidence_key, field, content_hash, offset}`에 묶인 checksum opaque 값이다.
  제공 직전 `EvidenceStore.read_content`로 size/hash를 다시 검증한다.
- **요청당 store**: 요청마다 read-only Catalog/Lifecycle과 Presentation Service를 새로 열고 닫는다.
  sqlite 연결이 thread를 넘지 않게 하는 가장 단순한 방법이며, 같은 cache key의 중복 생성은 WI-03의
  SQLite lease가 막는다. 서로 다른 key 사이의 FIFO(SDD §7.2.3)는 process-wide lock 하나로 구현했다.

## 실행 결과

```text
PYTHONPATH=src uv run --python 3.12 python -m unittest tests.test_dashboard_api \
  tests.test_dashboard_presentation tests.test_dashboard_read_model tests.test_dashboard_readonly \
  tests.test_skill_routing_fixtures tests.test_skills tests.test_skill_discovery_contract
Ran 161 tests — OK

PYTHONPATH=src uv run --python 3.12 python -m unittest discover -s tests
Ran 550 tests — OK

PYTHONPATH=src uv run --python 3.12 python tests/run_claim_mutations.py
9/9 mutations killed, errors 0

git diff --check
exit 0
```

전체 회귀 출력의 `M3 live probe refused or failed: live fixture content drift: AGENTS.md`는 기존
테스트가 예상하는 진단이며 suite exit는 0이었다. **이번 구현은 M3 live 미확인을 해소하지 않는다.**

## 독립 재검수

7건을 보고받았다. 실제 결함 4건은 실패 fixture를 먼저 확인(RED)한 뒤 고쳤고, 1건은 승인된 SDD와
충돌해 **수정하지 않고 계약을 확인하는 테스트로 바꿨다**.

| # | 발견 | 처리 |
|---|---|---|
| 1 | `_guard`에서 거부된 POST가 request body를 읽지 않아 keep-alive 연결이 어긋났다. 실측에서 403 다음 GET이 **`<!DOCTYPE HTML>` 400 페이지**로 돌아왔다 | 경로 파싱 직후 body를 먼저 drain하도록 바꿨다. 64KiB 초과는 응답 후 연결을 닫는다. `test_f10_a_rejected_post_leaves_the_connection_usable` 추가 |
| 2 | `hmac.compare_digest`가 str에서 비-ASCII를 거부해 `TypeError`로 연결이 끊겼다. `/session`은 인증 전 경로라 누구나 도달 가능했다 | bytes로 비교하는 `_same`을 도입하고 `TypeError`도 envelope로 처리한다. `test_f10_a_non_ascii_credential_is_refused_not_crashed` 추가 |
| 3 | HEAD 응답에 body를 실어 보냈다 | HEAD는 body 없이 `Content-Length: 0`으로 응답한다. `test_f10_a_head_request_carries_no_body` 추가 |
| 4 | 성공 응답을 쓰다 실패하면 오류 응답을 같은 스트림에 한 번 더 썼다 | `_sent` 플래그를 두어 이미 전송된 뒤에는 오류를 덮어쓰지 않는다 |
| 5 | content 창마다 객체 전체를 다시 읽고 해시한다 | **수정하지 않았다.** SDD §6.4가 "전체 hash 검증 후 64KiB 구간을 반환"을 요구하므로 이것이 명세된 동작이다. 대신 창마다 검증이 실제로 일어남을 고정하는 `test_f12_every_window_is_integrity_verified_before_delivery`를 넣고, 비용 상한을 아래 «미실행 및 후속 범위»에 남긴다 |
| 6 | `_template`의 쓰이지 않는 `names` dict | 삭제 |
| 7 | session이 만료되지 않고 무한히 쌓인다 | 상한 8개로 제한하고 가장 오래된 것을 버린다. 단일 사용자 로컬 범위임을 주석으로 명시 |

재검수 후 Critical/Important 미해결 **0**.

## PR #96 검토 반영

merge 전 검토에서 승인 SDD와 어긋난 계약 2건을 지적받았다. 둘 다 실패 fixture를 먼저 확인(RED)한 뒤
수정했고, 그 밖의 설계·범위는 바꾸지 않았다.

| # | 지적 | 처리 |
|---|---|---|
| 1 | 원본 DB가 없을 때 `/reviews`가 503 `SOURCE_UNAVAILABLE`이었다. SDD §6.3은 **200 + 빈 목록**이다 | catalog 파일이 없으면 `DashboardReadModel.empty_list`가 질의 검증을 거친 빈 페이지를 돌려준다. 직접 Snapshot/Claim/Evidence/Presentation key와 `ensure`는 404를 유지하고, 파일은 여전히 하나도 만들지 않는다. 파일이 있는데 읽을 수 없는 원본은 계속 503이다. `test_f01_a_missing_source_lists_empty_and_creates_nothing`으로 대체 |
| 2 | `ensure`가 `pending`에도 200을 돌려줬다. SDD §6.3은 **202**다 | `ready` 200 / `pending` 202 / cooldown `failed` 200으로 고정했다. 다른 worker가 유효 lease를 쥔 상태를 만들어 202를 확인하고, read-only polling GET은 200 유지임을 함께 고정했다. 응답에 `error` 키가 없다는 것도 확인한다. `test_f04_generation_in_flight_is_202_and_settled_states_are_200` 추가 |

두 항목 반영 후 대상 161 / 전체 550 / mutation 9-9가 모두 통과했다.

## 미실행 및 후속 범위

- 브라우저 UI, 3페이지+Drawer, 접근성·반응형 관찰은 **미실행**이다 — 이슈 5. 이 WI는 HTTP 계약만
  검증했고 화면 조작 증거(E03)는 만들지 않았다.
- 실제 모델 18출력 의미 품질은 여전히 `semantic_quality=unverified`이며 사용자 60초 이해도 pilot도
  미실행이다 — 이슈 6.
- 실제 브라우저(Chrome/Firefox/Safari)에서의 cookie·CSRF·CSP 동작은 관찰하지 않았다. 검증은
  `http.client` 기반 fixture뿐이다.
- content 전달은 창마다 객체 전체를 읽고 해시한다. 64MiB 객체를 64KiB씩 페이징하면 누적 I/O가
  크다. SDD §6.4가 요구하는 동작이므로 유지하되, 완화가 필요하면 SDD 개정이 선행되어야 한다.
- TLS 종단과 `Secure` cookie는 보류했다(위 «구현이 고정한 계약»의 이유).
- Claim/Review 재평가, 원본 쓰기, HumanDecision/merge는 이번에도 하지 않았다.
- M3 live는 기존 `AGENTS.md` fixture drift로 미확인이며 이번 구현을 해소 근거로 쓰지 않는다.
- 이 WI의 완료는 **HTTP/보안/Evidence 전달 계층 완료**만 의미한다. #89는 이슈 1–6과 통합 수용 검증이
  끝날 때까지 OPEN으로 유지한다.

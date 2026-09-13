# Dashboard WI-04 실행 계획 — HTTP API · 세션 보안 · Evidence 전달 (#95)

기준 main: `6c1d8e058e4c8dabaffec509e8ac9b39d032d6a5` (PR #94 병합).
브랜치: `feat/dashboard-wi04-http-api`.
Baseline 재실행: 전체 520 tests OK, Claim mutation 9/9 killed.

제품 방향은 #89 / #95 / `docs/m5-r/dashboard-sdd.md` §6에서 승인됐다. 이 계획은 재설계가 아니라
현재 main 정합성과 구현 세부 계약만 고정한다.

## 1. 산출물

| 파일 | 역할 |
|---|---|
| `src/devharness/dashboard/server.py` | loopback HTTP transport, 세션/Origin/Host/CSRF, error envelope, 로그 redaction, 생성 worker FIFO |
| `src/devharness/dashboard/read_model.py` | `read_content` 추가 (64KiB chunk + opaque cursor + 무결성 재검증) |
| `src/devharness/__main__.py` | `dashboard` 시작 명령 |
| `tests/test_dashboard_api.py` | F01–F14 |
| `docs/m5-r/dashboard-issue04-verification.md` | 검증 Evidence |

새 의존성 없음. `http.server`, `secrets`, `hmac`, `base64`, `json`, `logging` 등 stdlib만 쓴다.

## 2. 고정하는 구현 계약

### 2.1 라우트와 계층 경계

`/api/dashboard/v1` 고정. transport는 SQL도 평가도 하지 않고 이슈 1~3의 reader만 호출한다.

```text
POST /session                                             세션 교환 (인증 전 유일 허용)
GET  /reviews                                             read_list
GET  /snapshots/{key}                                     read_detail
GET  /snapshots/{key}/claims/{claim_id}                   read_claim
GET  /snapshots/{key}/evidence/{evidence_key}             read_evidence
GET  /snapshots/{key}/evidence/{evidence_key}/content     read_content   ← 신규
GET  /snapshots/{key}/presentation                        read_presentation
POST /snapshots/{key}/presentation/ensure                 ensure_presentation
```

`read_content`는 transport가 아니라 read model에 둔다. Snapshot closure 도달성·scope 검사·hash
재검증을 WI-01/02의 공통 경로로 재사용해야 하고, 별도 약한 구현을 만들지 않기 위해서다.

### 2.2 요청당 store 수명과 생성 FIFO

`ThreadingHTTPServer`를 쓰고 **요청마다** read-only Catalog/Lifecycle과 Presentation Service를 새로
연다. sqlite 연결이 thread를 넘지 않게 하는 가장 단순한 방법이며, WI-03의 20-thread single-flight
fixture가 이미 같은 형태를 검증했다. 같은 cache key의 중복 생성은 WI-03의 SQLite lease가 막는다.

서로 다른 key 사이의 FIFO(SDD §7.2.3)는 server worker의 정책이므로 process-wide lock 하나로
구현하고, 그 상한을 코드에 명시한다.

### 2.3 인증

- 시작 시 `secrets.token_urlsafe(32)` boot token을 만들어 **stdout으로만** 출력한다. URL·query·로그·
  응답에 넣지 않는다.
- `POST /api/dashboard/v1/session`, body `{"token": "..."}`. 비교는 `hmac.compare_digest`.
- 성공 시 `Set-Cookie: ownhands_dashboard=<session id>; HttpOnly; SameSite=Strict; Path=/api/dashboard/v1`.
  응답 body는 `{"csrf_token": "..."}`이며 session id는 body에 넣지 않는다.
- **`Secure` 속성은 v1에서 설정하지 않는다.** 서버가 평문 loopback HTTP에만 bind하고, `Secure`
  cookie의 loopback 취급이 브라우저마다 달라 로그인 자체가 깨질 수 있기 때문이다. 대신 bind를
  loopback으로 강제하고 Host/Origin 검사를 유지한다. TLS 종단이 생기면 그때 `Secure`를 켠다.
  이것은 외부 origin 허용 완화가 아니다.
- session id와 csrf token은 서버 메모리에만 둔다. 디스크·DB에 저장하지 않는다.
- `/session` 외의 모든 경로는 유효 cookie가 없으면 401 `UNAUTHENTICATED`.

### 2.4 Host / Origin / CSRF

- `Host` header가 실제 bind한 `host:port`와 다르면 403 `ORIGIN_DENIED`.
- `Origin`이 있으면 `http://<bind host>:<port>`와 정확히 같아야 한다. 그 외 Origin과 모든 CORS
  preflight는 403. CORS 허용 header를 아예 내보내지 않는다.
- 상태를 바꾸는 `POST`는 `X-OwnHands-CSRF` header가 세션의 csrf token과 같아야 한다(`compare_digest`).
  없거나 다르면 403 `CSRF_FAILED`이며 ensure는 실행하지 않는다. `/session` POST는 인증 전이라
  cookie가 없으므로 CSRF 검사 대상이 아니다.
- GET은 부작용이 없다. 어떤 GET도 ensure를 호출하지 않는다.

### 2.5 오류 envelope와 status 매핑

성공은 JSON, 실패는 `{"error":{"code","message","retryable"},"request_id"}`.

| code | status |
|---|---|
| `INVALID_QUERY` | 400 |
| `UNAUTHENTICATED` | 401 |
| `ORIGIN_DENIED` / `CSRF_FAILED` | 403 |
| `NOT_FOUND` | 404 |
| `METHOD_NOT_ALLOWED` | 405 |
| `SOURCE_CHANGED` / `LIST_CHANGED` / `RECIPE_CHANGED` | 409 |
| `SOURCE_UNAVAILABLE` / `UNSUPPORTED_SCHEMA` / `SOURCE_INTEGRITY_ERROR` | 503 |

`SOURCE_INTEGRITY_ERROR`는 **503**으로 고정한다. SDD §6.3이 "원본 journal 손상은 503
SOURCE_INTEGRITY_ERROR"로 이미 정하고 있고, 이것은 서버 결함이 아니라 원본 상태이기 때문이다.

message는 고정 문구만 쓴다. 내부 경로, DB 경로, credential, raw 본문, provider endpoint를 넣지 않는다.
Presentation의 `pending/failed/unavailable/ready`는 200 정상 응답이며 transport 오류로 바꾸지 않는다.

### 2.6 Evidence content 전달

`read_content(snapshot_key, evidence_key, field, cursor=None)` → FieldVM.

- `field`는 `raw|stdout|stderr|diff|command`만 허용. 그 외는 `INVALID_QUERY`.
- chunk 상한 **64KiB(바이트 기준)**. 전체를 한 번에 반환하지 않는다.
- cursor는 `_encode_cursor`를 재사용한 opaque 값이며 `{snapshot_key, evidence_key, field,
  content_hash, offset}`에 묶인다. 다른 Evidence·다른 field·다른 내용 hash의 cursor는
  `INVALID_QUERY`. 클라이언트는 파일 경로·offset을 직접 넘길 수 없다.
- 제공 직전 `EvidenceStore.read_content`로 size/hash를 재검증한다. 읽는 중 원본이 바뀌면 섞지 않고
  `corrupt` availability 또는 `SOURCE_INTEGRITY_ERROR`로 끝낸다.
- availability는 `available/not_collected/missing/purged/corrupt/denied/unsupported/redacted/
  too_large`를 구분한다. `reference_only`는 `unsupported`, 64MiB 초과는 `too_large`이며 원본은
  삭제하지 않는다.
- **binary는 강제 디코딩하지 않는다.** NUL 바이트가 있거나 UTF-8 디코딩이 실패하면 `unsupported`.
  chunk 경계가 multi-byte 문자를 자르는 경우에만 최대 3바이트를 되돌려 문자 경계에 맞춘다.
- 반환 text에서 C0 제어문자(`\t\n\r` 제외)와 DEL은 보이는 `\xNN` 형태로 치환한다. ANSI escape는
  실행 가능한 형태로 나가지 않는다.
- HTML/script 문자열은 **원문 그대로 데이터로** 반환한다. 여기서 바꾸면 Evidence 충실도가 깨지고,
  JSON 문자열에서는 실행되지 않는다. 대신 모든 응답에 `Content-Type: application/json`,
  `X-Content-Type-Options: nosniff`, `Content-Security-Policy: default-src 'none'`를 붙이고
  `text/html`을 절대 내보내지 않는다. 렌더 시점 escape는 WI-05 책임이다.
- 외부 URL을 자동 fetch하지 않는다. metadata에 없는 command/stdout/stderr/diff를 합성하지 않는다.

### 2.7 bind와 고정 scope

- `127.0.0.1`(또는 `::1`)만 허용. 그 외 주소는 시작 시 `ValueError`로 거부한다.
- data root와 project scope는 시작 시 고정하며 요청으로 바꿀 수 없다. scope는 응답에서 서버가 정한다.
- 원본은 `open_readonly` 경로만 사용한다. source DB 없음·미지원 schema·journal 손상을 자동
  migration/복구/생성으로 처리하지 않는다.

### 2.8 로깅

`request_id`, method, **route template**(실제 key가 아닌 `/snapshots/{key}` 형태), status, latency,
error code만 남긴다. token/cookie/credential/raw 본문/stdout/stderr/diff/파일 경로/prompt는 남기지
않는다. 쿼리 문자열도 통째로 남기지 않는다.

## 3. 진행 순서 (RED → GREEN)

1. `tests/test_dashboard_api.py`에 F01–F14를 먼저 작성하고 기능 부재로 인한 **단언 실패**를 확인한다.
2. `read_model.read_content` → `server.py` → `__main__.py` 순으로 최소 구현.
3. 대상 테스트 → 전체 회귀 → `tests/run_claim_mutations.py`.
4. `docs/m5-r/dashboard-issue04-verification.md` 작성. 브라우저 UI·실제 사용자·실제 모델은 `unverified`.
5. 독립 재검수 → Critical/Important 미해결 0.
6. 작은 PR 1개 (`Refs #89`, `Closes #95`). merge는 사용자 확인 후.

## 4. 이번 WI에서 하지 않는 것

- 브라우저 UI, 디자인/반응형/접근성 — 이슈 5
- 실제 모델 18출력 의미 품질, 사용자 60초 pilot — 이슈 6
- Claim/Review 재평가, 원본 Lifecycle/Evidence 쓰기, HumanDecision/merge
- 외부 네트워크 bind, 다중 사용자 인증, 임의 파일 브라우저/다운로드 서버
- TLS 종단과 `Secure` cookie (§2.3의 이유로 보류)

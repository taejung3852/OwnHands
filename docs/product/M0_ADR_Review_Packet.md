# M0 ADR 검토 패킷

- **상태:** 사용자 ADR 승인 반영, 단일 M0 PR 검증·병합 대기
- **기준일:** 2026-09-04
- **M1 기능 구현:** 금지 상태 유지

## 한눈에 보는 결론

M0 필수 Spike와 schema 결정은 검토 가능한 상태다. 사용자는 ADR-0001~0006과 OD-09을 제안대로 승인했고, ADR-0007은 **B 색상 방향 범위만 Accepted**로 유지했다. M1 구현은 시작하지 않았으며 단일 M0 PR 검증·병합 전에는 M0 완료를 주장하지 않는다.

| 항목 | 제안 결론 | 현재 Evidence | 결정 상태 |
|---|---|---|---|
| Codex 통합 | App-Server-managed Task + snapshot-only Imported Desktop Task | 공식 문서, CLI help와 disposable protocol schema Probe | ADR-0001 Accepted, runtime Probe는 M3 |
| Control Validation | Configured/Loaded/Enforced 독립 check + check별 Observed/Inferred/Unobserved basis | 공식 문서 비교, schema/example | ADR-0002 Accepted, runtime Probe는 M3 |
| Guarantee | versioned JSON Matrix와 작업별 Report 분리 | 전체 문서 범주·Task mode 추적, strict schema와 합성 fail-safe fixture | ADR-0003 Accepted |
| Event/Evidence Store | SQLite catalog + content-addressed local files; 초기 rollback journal | SQLite/Apple 공식 문서, 합성 저장 Probe | ADR-0004 Accepted |
| Superpowers | `dev-harness/*` 선택 subset; global router 제외; MIT; commit pin | upstream/local hash 비교 | ADR-0005 Accepted, Non-blocking, vendoring 미승인 |
| 구현 순서 | M2 Preflight draft / M4 post-change assurance 분리; M1–M4 review packet 유지 | 문서 간 lifecycle·roadmap 비교 | ADR-0006 Accepted |
| Brand 색상 기반 | B — Warm Paper Neutral + Ledger Indigo | 동일 M0-06 Fixture 3안, Light/Dark 18상태, 접근성·layout Probe | ADR-0007 Accepted(색상 범위), UI/UX는 M5 Gate |

## M0 Gate 상태

| Gate | 산출물 | 상태 |
|---|---|---|
| Codex 통합 결정 | ADR-0001, M0-02 Spike | 승인됨, read-only capability Probe 통과, runtime은 M3로 이관 |
| Control Validation 표·schema | ADR-0002, M0-03 Spike | 승인됨, read-only capability Probe 통과, runtime은 M3로 이관 |
| Guarantee Matrix v1 | ADR-0003, Matrix/Report schema | 승인됨, strict schema·합성 Probe 통과 |
| Event/Evidence 저장 결정 | ADR-0004, M0-06 Spike | 승인됨, 합성 Probe 통과 |
| Superpowers 원칙 | ADR-0005, M0-05 Spike | 승인됨, Non-blocking, 실제 vendoring 제외 |
| 문서 충돌 해소 | ADR-0006, Conflict 목록 | 승인됨 |
| Brand 색상 기반 | ADR-0007, M0-07 시안 | B 색상 범위 승인, UI/UX는 M5 승인 Gate 대기 |

ADR 결정 Gate는 통과했지만 M0 종료 Gate는 아직 통과로 표시하지 않는다. 단일 M0 PR의 검증·병합과 Issue별 수용 기준 재확인이 남아 있다.

## Issue별 로컬 준비 상태

| Issue | 분류 | 로컬 산출물·검증 | 현재 주장 가능 범위 | 아직 필요한 것 |
|---|---|---|---|---|
| M0-01 | 충족(로컬 Evidence) | 기준선 hash 4개, 내부 link, Raw Evidence ignore Probe 통과 | 제품·Repository 기준선이 2026-09-04 로컬/원격 조회 범위에서 추적됨 | PR 검증·병합; 그 전 Issue 종료 금지 |
| M0-02 | 충족(승인된 M0 범위) | 통합 비교, 여섯 질문, ADR-0001, stdio initialize/help/default schema Probe | 로컬 App Server handshake와 문서화된 snapshot/managed protocol/schema availability | PR 검증·병합; task runtime·live Desktop attach는 OD-09에 따라 M3에서 Probe |
| M0-03 | 충족(승인된 M0 범위) | Control coverage, fail-open 경계, ADR-0002, capability Probe | Configured/Loaded/Enforced와 basis 분리 계약이 승인됨 | PR 검증·병합; repository-specific enforcement는 M3 전까지 Unobserved |
| M0-04 | 충족(로컬 Evidence) | 16개 기준 범주, Matrix version·Claim·Task mode·requirement ID·전체 Control record gate, strict schema, adversarial fixture Probe | fail-open fixture 7개를 거부하고 관찰된 fail·충돌은 `contradicted`, 불충분 상태는 `not_evaluated`로 판정함 | PR 검증·병합; 실제 Task evaluator는 M1 이후 별도 구현 |
| M0-05 | 충족(로컬 Evidence) | include/exclude, MIT, immutable pin, hash 비교, ADR-0005 | vendoring 경계가 승인됨 | PR 검증·병합; 실제 vendoring 금지 유지 |
| M0-06 | 충족(로컬 Evidence) | hybrid store 비교, 복구 경계, 합성 저장 Probe, ADR-0004 | clean close와 killed writer rollback, idempotency/hash/rebuild 결과와 저장 결정을 승인 | PR 검증·병합; power-loss/disk-full/concurrency 등은 Unobserved |
| M0-07 | 충족(로컬 Evidence) | 3안, Light/Dark 18 capture, capture별 computed token 회귀 검사, static/browser Probe, ADR-0007 | B 색상 방향이 승인됐고 현재 UI/UX는 M5 참고 시안으로 보존됨 | PR 검증·병합; M5 UI/UX 별도 승인 전 Production UI 금지 |

모든 Issue는 외부에서 open 상태다. 위 표의 “충족”은 승인된 M0 문서·Probe 범위의 PR 후보 판정이며, PR 검증·병합 전 Issue 완료·M0 종료 또는 제품 동작 보장을 뜻하지 않는다.

## 확인된 것과 확인되지 않은 것

### Observed

- 최초 Git commit과 원격 `main`은 네 제품 기준선 문서만 포함한다.
- GitHub repository는 Private이며 M0–M8 Milestone, 승인 Label, 상위 추적 Issue, M0-01–07 Issue가 존재한다.
- Milestone 설명은 한국어로 등록되어 있다.
- 설치 Codex CLI version과 read-only help surface를 확인했다.
- disposable stdio App Server의 `initialize` handshake가 exit 0으로 완료됐다. 설치 CLI가 생성한 default protocol schema에서 `thread/read`, approval request/resolution, `instructionSources`, synchronous `hook/started`/`hook/completed` 이름을 확인했다. generator와 task/control runtime 동작은 별개다.
- Guarantee 합성 fixture에서 Matrix version 불일치, 알 수 없는 Claim, requirement ID 누락·추가·중복, Imported Task의 Managed-only `supported`, 연결 Control record의 pass/fail 충돌을 거부했다. 필요한 requirement·Control의 관찰된 `fail`과 충돌 Evidence는 `contradicted`, Evidence 부족·`not_run`·`unobserved`는 `not_evaluated`가 됐다.
- Imported Task에서 Managed-only claim은 합성 check가 pass여도 `not_evaluated`가 됐고, Matrix/Control/Task Report JSON은 strict draft 2020-12 validation을 통과했다.
- SQLite 합성 fixture에서 clean close와 killed writer의 uncommitted row rollback, duplicate no-op, content hash, Projection rebuild, Git 제외를 확인했다.
- 사용자가 M0-07의 B — Warm Paper Neutral + Ledger Indigo 색상 방향을 승인하고, UI/UX 설계는 M5에서 현재 시안을 이어서 진행하도록 결정했다.
- M0-07의 18개 capture에서 방향·테마별 computed color token이 기대값과 일치하고 A/B/C × Light/Dark의 고유 palette 여섯 개가 구분됐다.
- 사용자가 ADR-0001~0006과 OD-09을 제안대로 승인했다. task runtime·집행 Probe는 M3 Hard Evidence Gate로 이관되며 현재 결과를 소급해 Observed로 바꾸지 않는다.

### Documented but not locally enforced

- App Server의 `thread/read`, managed thread Event/approval protocol
- Codex config precedence, trusted project 조건, Rules/Hook/Sandbox/Approval 동작과 제한
- SQLite transaction atomicity와 WAL 제약
- Superpowers MIT license와 upstream tagged source

### Unobserved

- 이미 실행 중인 Desktop Task에 대한 non-disruptive passive live attachment
- 이 repository에서 DevHarness Control이 실제로 Loaded/Enforced된 결과
- 실제 power-loss, disk-full, concurrent writer, orphan recovery
- 실제 사용자 작업의 Guarantee 결과
- Superpowers 실제 vendoring, activation, behavior compatibility
- Pretendard Variable 실제 font file metric, screen reader별 M0-07 시안 사용성, 실제 사용자 검토 시간 감소
- 배포, 공개 전환, package 게시

## 승인된 결정

1. **OD-09:** M0-02/03 task runtime·집행 Probe를 M3 Hard Evidence Gate로 이관
2. **ADR-0001:** Managed Task와 Imported snapshot mode 분리
3. **ADR-0002/0003:** 독립 Control check schema와 Guarantee Matrix/Report 판정 규칙
4. **ADR-0004:** hybrid 저장소와 rollback-journal 우선 원칙
5. **ADR-0005:** Non-blocking Superpowers vendoring 경계. 실제 vendoring은 미승인
6. **ADR-0006:** Preflight/Post-change Assurance 2단계와 M1–M4 review artifact 계약
7. **ADR-0007:** B — Ledger Indigo 색상 범위만 승인. UI/UX는 M5에서 별도 검토

## ADR 승인 후에도 M1 전에 남는 제품 결정

| 결정 | 추천안 | 이유 |
|---|---|---|
| Raw Evidence 기본 보존 기간 | M1에서 사용자 선택형 정책을 먼저 만들고, 자동 삭제 기본값은 실제 도그푸딩 전까지 두지 않음 | 임의 기간은 감사 가능성과 개인정보 요구를 모두 왜곡할 수 있음 |
| app-level encryption-at-rest | M1 v1에서는 미지원임을 명시하고 비밀정보 수집 최소화·사용자 전용 OS data path·권한 제한부터 검증 | key 관리와 복구 정책 없이 암호화를 추가하면 오히려 데이터 손실/허위 안전 주장이 생김 |
| WAL 전환 | SQLite 3.51.3 이상과 실제 병목 Evidence가 모두 있을 때 별도 amendment | 현재 3.51.0은 공식 결함 영향 범위이며 동시성 필요가 아직 Unobserved |

이 세 항목은 ADR-0004의 저장 엔진 결정을 뒤집지 않지만, M1-03의 완료 기준을 확정하기 전에 사용자 결정이 필요하다.

## 외부 변경 경계

- 이미 수행한 승인 범위: Private repository 생성, 최초 기준선 push, Milestone/Label/Issue #1~#8 생성, Milestone 설명 한국어화
- 이번 사용자 승인 범위: M0-07 GitHub 기록 갱신, `m0/product-technical-baseline` push, 단일 M0 PR 생성
- 아직 수행하지 않거나 승인되지 않은 변경: PR merge, Issue 종료, public 전환, deployment, package publish, Superpowers vendoring, M1 구현
- 현재 지시를 따라 M0-01~07을 하나의 M0 baseline PR 범위로 제출한다. Roadmap의 일반적인 Issue별 PR 규칙과의 차이는 OD-08에 기록했다.

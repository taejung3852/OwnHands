# M0 ADR 검토 패킷

- **상태:** 사용자 검토 대기
- **기준일:** 2026-09-04
- **M1 기능 구현:** 금지 상태 유지

## 한눈에 보는 결론

M0 필수 Spike와 schema 제안은 준비됐다. 현재 어떤 ADR도 승인된 것으로 기록하지 않았으며, M1 구현을 시작하지 않았다.

| 항목 | 제안 결론 | 현재 Evidence | 결정 상태 |
|---|---|---|---|
| Codex 통합 | App-Server-managed Task + snapshot-only Imported Desktop Task | 공식 문서, CLI read-only help | ADR-0001 Proposed |
| Control Validation | Configured/Loaded/Enforced 독립 check + check별 Observed/Inferred/Unobserved basis | 공식 문서 비교, schema/example | ADR-0002 Proposed |
| Guarantee | versioned JSON Matrix와 작업별 Report 분리 | 전체 문서 범주 추적, 합성 fail-safe fixture | ADR-0003 Proposed |
| Event/Evidence Store | SQLite catalog + content-addressed local files; 초기 rollback journal | SQLite/Apple 공식 문서, 합성 저장 Probe | ADR-0004 Proposed |
| Superpowers | `dev-harness/*` 선택 subset; global router 제외; MIT; commit pin | upstream/local hash 비교 | ADR-0005 Proposed, Non-blocking |
| 구현 순서 | M2 Preflight draft / M4 post-change assurance 분리; M1–M4 review packet 유지 | 문서 간 lifecycle·roadmap 비교 | ADR-0006 Proposed |
| Brand·Dashboard 기반 | Graphite Neutral + Signal Teal/Cyan, Evidence-first 3단계 drill-down | 동일 M0-06 Fixture 3안, Light/Dark 18상태, 접근성·layout Probe | ADR-0007 Proposed, M5 Gate |

## M0 Gate 상태

| Gate | 산출물 | 상태 |
|---|---|---|
| Codex 통합 결정 | ADR-0001, M0-02 Spike | 사용자 검토 대기 |
| Control Validation 표·schema | ADR-0002, M0-03 Spike | 사용자 검토 대기 |
| Guarantee Matrix v1 | ADR-0003, Matrix/Report schema | 합성 Probe 통과, 사용자 검토 대기 |
| Event/Evidence 저장 결정 | ADR-0004, M0-06 Spike | 합성 Probe 통과, 사용자 검토 대기 |
| Superpowers 원칙 | ADR-0005, M0-05 Spike | Non-blocking, 사용자 검토 대기 |
| 문서 충돌 해소 | ADR-0006, Conflict 목록 | 사용자 검토 대기 |
| Brand·Dashboard 디자인 기반 | ADR-0007, M0-07 시안 | M0 Non-blocking, M5 승인 Gate 대기 |

M0 종료 Gate는 아직 통과로 표시하지 않는다. Proposed ADR의 사용자 결정과 그 결과의 문서 반영이 남아 있다.

## 확인된 것과 확인되지 않은 것

### Observed

- 최초 Git commit과 원격 `main`은 네 제품 기준선 문서만 포함한다.
- GitHub repository는 Private이며 M0–M8 Milestone, 승인 Label, 상위 추적 Issue, M0-01–07 Issue가 존재한다.
- Milestone 설명은 한국어로 등록되어 있다.
- 설치 Codex CLI version과 read-only help surface를 확인했다.
- Guarantee 합성 fixture에서 불충분 Evidence는 `not_evaluated`, 충돌 Evidence는 `contradicted`가 됐다.
- SQLite 합성 fixture에서 uncommitted row rollback, duplicate no-op, content hash, Projection rebuild, Git 제외를 확인했다.

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

## 사용자 검토가 필요한 결정

1. **ADR-0001:** Managed Task와 Imported snapshot mode를 분리할지
2. **ADR-0002/0003:** 독립 Control check schema와 Guarantee Matrix/Report 판정 규칙을 승인할지
3. **ADR-0004:** hybrid 저장소와 rollback-journal 우선 원칙을 승인할지
4. **ADR-0006:** Preflight/Post-change Assurance 2단계와 M1–M4 review artifact 계약을 승인할지
5. **ADR-0005:** Non-blocking Superpowers 범위를 함께 승인·수정·보류할지
6. **ADR-0007:** M5 디자인 기준으로 A Signal Graphite를 승인·수정·대안 선택할지. 이 결정은 M1~M4를 막지 않음

## ADR 승인 후에도 M1 전에 남는 제품 결정

| 결정 | 추천안 | 이유 |
|---|---|---|
| Raw Evidence 기본 보존 기간 | M1에서 사용자 선택형 정책을 먼저 만들고, 자동 삭제 기본값은 실제 도그푸딩 전까지 두지 않음 | 임의 기간은 감사 가능성과 개인정보 요구를 모두 왜곡할 수 있음 |
| app-level encryption-at-rest | M1 v1에서는 미지원임을 명시하고 비밀정보 수집 최소화·사용자 전용 OS data path·권한 제한부터 검증 | key 관리와 복구 정책 없이 암호화를 추가하면 오히려 데이터 손실/허위 안전 주장이 생김 |
| WAL 전환 | SQLite 3.51.3 이상과 실제 병목 Evidence가 모두 있을 때 별도 amendment | 현재 3.51.0은 공식 결함 영향 범위이며 동시성 필요가 아직 Unobserved |

이 세 항목은 ADR-0004의 저장 엔진 결정을 뒤집지 않지만, M1-03의 완료 기준을 확정하기 전에 사용자 결정이 필요하다.

## 외부 변경 경계

- 이미 수행한 승인 범위: Private repository 생성, 최초 기준선 push, Milestone/Label/Issue #1~#8 생성, Milestone 설명 한국어화
- 아직 수행하지 않은 변경: M0 결과 문서 push, public 전환, deployment, package publish, Superpowers vendoring
- M0 결과 문서의 원격 push는 최초 기준선 push와 별도이므로 사용자 승인 없이 수행하지 않는다.

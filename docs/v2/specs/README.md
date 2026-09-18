# V2 Intent, Spec & Plan 작성 가이드

> **핵심 원칙**:
> - "의도(Intent)는 경계가 생명이고, 명세(Spec)는 극대화된 기술 디테일이 생명이다." — [ADR-0004](../adr/0004-intent-spec-specification.md)
> - "계획(Plan)은 실행 단위 분해와 신선한 검증 증거(Fresh Evidence)가 생명이다." — [ADR-0007](../adr/0007-plan-artifact-and-build-feedback-loop.md)

---

## 1. 개요 및 생명주기
 
 구조적 설계나 아키텍처 변경이 수반되는 작업의 경우, 아래의 3단계 아티팩트 체인을 **기본 권장 흐름(Default Flow)**으로 삼습니다:
 
 ```text
 [문제/아이디어]
       ↓
 Stage 1 (Plan)       ➔  intent.md 작성 (인간 작성 / "왜, 무엇을?")
       ↓
 [🛡️ Checkpoint 1 (권장)] ➔  사람과 intent.md 검토 (문제 정의 및 비목표 합의)
       ↓
 Stage 2 (Design)     ➔  spec.md 작성 (AI 분석 생성 / "어떤 구조로?")
       ↓
 [🛡️ Checkpoint 2 (권장)] ➔  사람과 spec.md 검토 (인터페이스, 엣지케이스, 수용조건)
       ↓
 Stage 3 (Build)      ➔  plan.md 작성 및 단위 피드백 루프 (AI 실행 / "어떻게 구현·검증?")
       ↓
 [🛡️ Checkpoint 3 (필수)] ➔  신선한 검증 증거(Fresh Evidence) & Verifier Subagent Gate
 ```
 
 > ⚠️ **적용 범위 안내**: 오타 수정, 단순 버그 픽스 등 사소한 작업까지 intent/spec/plan 아티팩트 작성을 의무 강제하지 않습니다.  
 > 개발 시스템이 무거워지지 않도록 "어떤 작업에 이 흐름을 적용할 것인가"의 세부 기준은 후속으로 정립합니다.

### 저장 위치 규칙
모든 작업 문서는 `docs/v2/specs/<feature-name>/` 아래에 영구 보존합니다:
```text
docs/v2/specs/
└── <feature-name>/
    ├── intent.md     # 의도와 경계
    ├── spec.md       # 기술 설계 청사진 및 수용 기준 (AC)
    └── plan.md       # 실행 단위 분해 및 검증 증거 체크리스트
```

### 개발 지침 및 조직 거버넌스 확장 안내
- **팀/모듈별 개발 지침**: 저장소 root의 `AGENTS.md` 또는 특정 서브디렉터리의 `AGENTS.override.md`를 활용합니다.
- **조직 강제 정책 (보안·권한)**: 프롬프트 지침이 아닌 Codex Enterprise의 관리자 설정(Managed Config 등)으로 분리합니다 ([ADR-0005](../adr/0005-policy-layering-boundary.md)).

---

## 2. `intent.md` 템플릿

`intent.md`는 코드를 작성하기 전 **"인간의 의도를 기계가 명확히 이해하도록 번역하는 원형 명세(Proto-spec)"**입니다. 불필요한 구현 코드는 배제하고 목적과 경계를 엄밀히 정의합니다.

```markdown
# Intent: [기능 / 과제 이름]

- **작성자**: [이름 / GitHub Handle]
- **일자**: YYYY-MM-DD
- **관련 Issue**: [#이슈번호](URL)

---

## 1. 문제 및 배경 (Why)
- **현재 상황과 고통**: 어떤 문제가 발생하고 있는가? 사용자가 겪는 구체적 불편은 무엇인가?
- **대상 사용자 (페르소나)**: 이 작업의 직접적인 영향을 받는 대상은 누구인가?

## 2. 목표 결과 및 가치 (What)
- **달성하고자 하는 결과**: 이 작업이 끝나면 무엇이 달라지는가?
- **성공 기준**: 어떤 상태가 되었을 때 성공으로 판단할 것인가? (정량적/정성적 기준)

## 3. 비목표 (Non-goals & Boundaries)
> ⚠️ **과잉 엔지니어링 방지**: 이번 작업에서 의도적으로 하지 않는 것(Out of Scope)을 명확히 정의합니다.
- [ ] 이번 작업에 포함하지 않는 부가 기능이나 대형 리팩토링
- [ ] 미래로 미루거나 별도 이슈로 분리할 항목

## 4. 핵심 제약 조건 (Constraints)
- **플랫폼 / 환경 제약**: Codex 런타임 제약, 32 KiB 지침 상한 등
- **의존성 및 리소스 제약**: 추가 라이브러리 도입 금지, 시간/토큰 제약 등
```

---

## 3. `spec.md` 템플릿

`spec.md`는 코딩 에이전트가 Build 단계에서 **데이터 타입, 인터페이스, 엣지 케이스를 자의적으로 상상(환각)하지 못하도록 통제하는 정밀 엔지니어링 청사진(Technical Contract)**입니다. 최대한 구체적이고 디테일하게 작성합니다.

```markdown
# Spec: [기능 / 과제 이름]

- **기반 Intent**: [`intent.md`](intent.md)
- **작성 주체**: AI 에이전트 분석 (사람 검토 및 승인 필요)
- **일자**: YYYY-MM-DD
- **상태**: Draft / Approved

---

## 1. 기술적 요구사항 (Requirements)
- **기능 요구사항**:
  - `REQ-01`: [입력, 처리 로직, 기대 출력 명세]
  - `REQ-02`: [상태 변경 및 데이터 흐름 명세]
- **비기능 요구사항**: 성능, 멱등성, 보안, 플랫폼 호환성.

## 2. 시스템 아키텍처 및 인터페이스 (Architecture & Interfaces)

### 2.1 대상 파일 및 컴포넌트 목록
- `[NEW]` `경로/파일명`: 생성 목적 및 책임
- `[MODIFY]` `경로/파일명`: 수정 범위 및 변경 함수

### 2.2 인터페이스 / API / 데이터 모델 스키마
```typescript / python / json / toml
// 구체적인 타입 정의, 함수 시그니처, 스키마 명세
```

### 2.3 데이터 흐름 및 상태 전이
- 호출 흐름(Sequence) 및 컴포넌트 간 상호작용 명세.

## 3. 엣지 케이스 및 예외 처리 (Edge Cases)
| 시나리오 / 경계 조건 | 기대 동작 및 처리 방식 |
|---|---|
| 입력값이 null/비어있을 때 | 명시적 에러 반환 및 로그 기록 |
| 타임아웃 또는 네트워크 실패 시 | 재시도 정책 및 Fallback 정의 |
| 권한 또는 파일 시스템 실패 시 | Read-only 보존 및 안전한 롤백 |

## 4. 수용성 기준 및 검증 계획 (Acceptance Criteria)

### 4.1 수용성 기준 (Acceptance Criteria)
- [ ] 기준 1: 구체적인 기대 결과 및 상태 확인
- [ ] 기준 2: 엣지 케이스 처리 동작 확인

### 4.2 자동화 검증 명령어
```bash
# 실행할 테스트 명령어 및 예상 성공 출력
npm test / pytest / gh 명령어 등
```
```

---

## 4. `plan.md` 템플릿

`plan.md`는 에이전트가 코드를 수정하기 전 **"작업을 작은 단위로 쪼개고, 각 AC를 어떤 전략과 신선한 증거로 검증할 것인가를 정의하는 실행 계약(Execution Contract)"**입니다 ([ADR-0007](../adr/0007-plan-artifact-and-build-feedback-loop.md)).

```markdown
# Plan: [기능 / 과제 이름]

- **기반 Spec**: [`spec.md`](spec.md)
- **작성 주체**: AI 에이전트 (사람 검토 및 승인 권장)
- **일자**: YYYY-MM-DD
- **상태**: Draft / Approved / In Progress / Completed

---

## 1. 구현 맥락 및 대상 파일 (Context & Target Files)
- **구현 목표 요약**: Spec에서 확정된 핵심 인터페이스 및 로직 구현.
- **대상 파일 목록 및 책임 경계 (Blast Radius Guard)**:
  - `[NEW]` `경로/파일명`: 생성 목적 및 모듈 책임
  - `[MODIFY]` `경로/파일명`: 수정 범위 및 기존 동작 보존 경계
  - ⚠️ 위 목록에 없는 파일의 무단 수정은 결함(Blast Radius Violation)으로 간주합니다.

## 2. 작업 단위 분해 (Task Breakdown)
> ⚠️ **원자적 단위(Atomic Unit)**: 한 번에 모든 것을 고치지 않고, "작은 변경 단위 ➔ 해당 Task에 적합한 Verification 수행 ➔ Evidence 확인 ➔ 다음 Task" 순서로 진행합니다. (TDD 전략이 지정된 Task에 한해 Red ➔ Green ➔ Refactor 적용)
- [ ] **Task 1: [단위 작업명]**
  - 작업 내용: 인터페이스 정의 및 실패하는 단위 테스트 작성 (TDD 대상)
  - 예상 변경 파일: `...`
- [ ] **Task 2: [단위 작업명]**
  - 작업 내용: 설정 및 연동 로직 수정과 정적 분석/타입 검증 (비TDD 대상)
  - 예상 변경 파일: `...`

## 3. AC별 검증 전략 매핑 (Verification Strategy Mapping)
> ⚠️ **양방향 추적성 & 테스트 설계 기법**: spec.md의 모든 AC는 최소 1개 이상의 전략과 관측 가능한 증거에 유연하게 매핑되어야 합니다 (1:1 강제 금지). 테스트 케이스 설계 시 ISTQB 동등 분할(EP) 및 경계값 분석(BVA) 기법을 활용하여 누락 없이 케이스를 도출합니다.
| AC ID | 검증 전략 (Strategy) | 관측 증거 (Evidence) | 통과 기준 (Pass Criteria) |
|---|---|---|---|
| `AC-01` | 단위 테스트 (TDD) | 최신 테스트 실행 로그 | 테스트 패스 (0 exit code) |
| `AC-02` | 정적 분석 / 린트 | `npm run lint` 등 정적 검사 | 에러/경고 0건 |
| `AC-03` | 수동 / 브라우저 점검 | 렌더링 스크린샷 또는 관측 기록 | 기대 레이아웃/동작 일치 |

## 4. 실행 및 신선한 검증 증거 (Execution & Fresh Evidence Checklist)
> ⚠️ **The Iron Law**: "신선한 관측 증거(Fresh Evidence) 없는 완료 주장 금지"
- [ ] **Task 1 검증 증거**:
  - 실행 명령어 또는 관측 대상: `...`
  - 실행/관측 결과 요약: `...`
- [ ] **Task 2 검증 증거**:
  - 실행 명령어 또는 관측 대상: `...`
  - 실행/관측 결과 요약: `...`
- [ ] **회귀 테스트 (Regression Gate)**:
  - 실행 명령어: `npm test` / `pytest` / native build check 등
  - 결과: 실행된 회귀 스위트 범위 내 실패 미관측(No failures observed) 증거 확보
  - *(기존 테스트 부재 시)*: `[NO_EXISTING_REGRESSION_SUITE]` 선언, 프로젝트에 존재하는 applicable native checks를 실행하고 존재하지 않는 검사는 `[UNOBSERVED]`로 기록
- [ ] **최종 Acceptance Criteria 역추적 대조 (Verifier Subagent Gate)**:
  - Verifier 판정: `PASS / FAIL / UNOBSERVED`
```

---

## 5. 권장 점검 체크리스트
 
- [ ] **Checkpoint 1 (Plan)**: `intent.md`의 문제 정의와 비목표(Non-goals)가 명확하게 합의되었는가?
- [ ] **Checkpoint 2 (Design)**: `spec.md`에 타입, 인터페이스, 엣지 케이스가 구체적으로 기술되어 있는가?
- [ ] **Checkpoint 3 (Build Plan)**: `plan.md`의 대상 파일 범위(Blast Radius)가 통제되고, 모든 AC가 적절한 검증 전략에 양방향 추적 가능하게 매핑되어 있는가?
- [ ] **The Iron Law**: 모든 완료 주장에 대해 실제 실행 및 관측을 통한 신선한 증거(Fresh Evidence)가 확보되었는가?
- [ ] **회귀 방어선 & 기준선 테스트 보존**: 기존 테스트는 시스템 동작의 기준선(Baseline)이며, 단순 실패 은폐를 위한 임의 수정/삭제/완화가 없었는가? (스펙 변경에 따른 수정 시 합법적 사유 명시 여부)
- [ ] **단일 진실 원칙 & 기준선 버전 관리**: 코드가 `spec.md`를 임의로 왜곡하거나 스펙 기준을 낮추지 않고, 모순 발생 시 사람 승인을 거쳐 갱신했는가?

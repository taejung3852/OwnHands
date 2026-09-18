# ADR-0007 — plan.md 아티팩트 규격과 SDD 기반 Build Feedback Loop

- **상태:** Accepted — 사용자 합의
- **일자:** 2026-09-19
- **관련 Issue:** [#123](https://github.com/taejung3852/OwnHands/issues/123) (선행: [#121 Research Gate](https://github.com/taejung3852/OwnHands/issues/121))
- **관련 PR:** [#122](https://github.com/taejung3852/OwnHands/pull/122), [#124](https://github.com/taejung3852/OwnHands/pull/124)

---

## 1. Context (배경 및 문제)

1. **설계(Spec)와 코드 구현(Build) 사이의 실행 공백**:
   - V2-M2를 통해 의도(`intent.md`)와 설계 청사진(`spec.md`)의 규격이 확립되었다.
   - 그러나 정밀한 `spec.md`가 있더라도, 에이전트가 코드를 작성할 때 "어떤 단위로 쪼개어 변경하고, 어떤 순서로 구현하며, 무엇으로 자체 검증할 것인가"의 **실행 계획(Implementation Plan)**이 없으면 작업이 탈선하거나 자가합리화에 빠진다.

2. **AI 코딩 환경의 3대 회귀 참사 (The AI Regression Problem)**:
   - AI 에이전트는 목표 달성 편향(Goal Bias)과 컨텍스트 한계로 인해, 새로운 기능을 구현할 때 주변 시스템을 파괴하는 고질적 실패 패턴을 보인다:
     1. **공통 모듈 오염 (Silent Breakage of Shared Modules)**: 신규 요구사항을 쉽게 통과시키기 위해 공통 유틸리티(`utils.ts` 등)나 설정의 시그니처/동작을 슬그머니 수정하여, 다른 팀원이 만든 무관한 기능들을 연쇄 파괴함.
     2. **테스트 베이스라인 침식 (Regression Silencing / Test Tampering)**: 변경 중 기존 테스트가 실패하면, 문제를 해결하는 대신 **남이 짜둔 기존 테스트 코드를 임의로 수정하거나 주석 처리하여 억지로 통과**시킴.
     3. **무단 파일 수정 (Blast Radius Explosion)**: 구현 대상 파일 범위를 벗어나 수십 개 파일을 건드려 변경 반경을 통제 불능으로 만듦.
   - ⚠️ **TDD 루프의 한계**: Focused TDD loop만 실행할 경우, 현재 수정 중인 파일의 단위 테스트에만 집중하므로 변경과 직접 관련 없는 기존 기능의 회귀를 놓칠 수 있다.

3. **1차 자료 조사 결과 및 네이티브 활용 경계 ([docs/v2/research/m3-build-feedback-loop.md](../research/m3-build-feedback-loop.md))**:
   - **Codex 네이티브 기능**: `/plan`(다단계 계획 모드), `/goal`(Outcome-Constraints-Verification), `/review`(전담 리뷰어), `/worktree`(작업 격리)를 기본 탑재하고 있다.
   - **경계**: 특정 호스트의 대화 세션 기반 `/plan`은 편리한 상호작용 도구이지만, 저장소의 감사 추적(Audit Trail)과 코드-명세 일치성을 보장하는 **영구 Git 아티팩트**를 대체하지 못한다.
   - **Superpowers 원칙의 선별 흡수**: 14개 대형 스킬을 통째로 복제하는 대신, `verification-before-completion`(Fresh Evidence 원칙)과 `writing-plans`(작은 작업 분해 패턴)의 핵심 원칙을 OwnHands의 가벼운 지침 규약(Thin Harness)으로 흡수한다.

4. **ISTQB CTFL 테스팅 원칙 참고 및 위계 명확화**:
   - OwnHands는 ISTQB CTFL의 테스트 설계 기법(블랙박스 기법), 양방향 추적성(Bidirectional Traceability), 회귀 테스팅 원칙을 참고하여 빌드 피드백 루프를 설계한다.
   - ⚠️ **위계 사실 정합화**: `SDD > Verification Strategy > TDD`는 ISTQB 표준 위계가 아니라, OwnHands가 시스템 안정성을 위해 **독자적으로 설계한 아키텍처 위계**이다.
   - 스펙과 AC가 정의되면, 적합한 테스트 설계 기법(동등 분할, 경계값 분석, 의사결정 테이블, 상태 전이 등)을 활용해 구체적인 테스트 케이스와 증거를 도출한다 (AC-테스트 1:1 강제 배제).

---

## 2. Decision (결정)

OwnHands는 V2-M3(`Build & Feedback Loop`)의 실행 규약으로 **`plan.md` 아티팩트 정식 규격**과 **SDD 기반 Build Feedback Loop 6대 원칙**을 확정한다.

### 2.1 저장 위치 및 생명주기

모든 작업의 실행 계획은 Git 저장소 내 `docs/v2/specs/<feature-name>/` 아래에 영구 보존한다:

```text
docs/v2/specs/<feature-name>/
├── intent.md     # Stage 1 (Plan): 인간의 의도·문제·경계
├── spec.md       # Stage 2 (Design): AI 분석 기술 청사진 및 수용 기준 (AC)
└── plan.md       # Stage 3 (Build): 구현 단위 분해, 회귀 방어선, 신선한 검증 증거
```

- `plan.md`는 임시 메모가 아니며, 기능 브랜치 작업과 함께 커밋되어 PR 머지 시 저장소 메인 히스토리에 영구 보존된다.
- 이를 통해 **"의도(Why) ➔ 설계(What) ➔ 계획(How) ➔ 검증(Evidence)"**의 전 생명주기 감사 추적성(Audit Trail)을 완성한다.

---

### 2.2 `plan.md` 규격 — "실행 단위 분해와 신선한 증거"

- **주요 작성자**: AI 에이전트 (사람 검토 및 승인 권장)
- **핵심 질문**: *"어떤 단위로 구현하고, 회귀 없이 어떻게 신선하게 검증할 것인가?"*
- **필수 4대 엔지니어링 필드**:

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
> ⚠️ **양방향 추적성**: spec.md의 모든 AC는 최소 1개 이상의 전략과 관측 가능한 증거에 유연하게 매핑되어야 합니다 (동등분할/경계값 기법 고려, 1:1 강제 금지).
| AC ID | 검증 전략 (Strategy) | 테스트 설계 기법 | 관측 증거 (Evidence) | 통과 기준 (Pass Criteria) |
|---|---|---|---|---|
| `AC-01` | 단위 테스트 (TDD) | 경계값 분석 (BVA) | 최신 테스트 러너 실행 출력 | 테스트 통과 (0 exit code) |
| `AC-02` | 정적 분석 / 린트 | 정적 검사 | `npm run lint` 실행 로그 | 에러/경고 0건 |
| `AC-03` | 수동 / 브라우저 점검 | 상태 전이 관측 | 렌더링 스크린샷 또는 관측 기록 | 기대 레이아웃 일치 |

## 4. 실행 및 신선한 검증 증거 (Execution & Fresh Evidence Checklist)
> ⚠️ **The Iron Law**: "신선한 관측 증거(Fresh Evidence) 없는 완료 주장 금지"
- [ ] **Task 1 검증 증거**:
  - 실행 명령어 또는 관측 대상: `...`
  - 실행/관측 결과 요약: `...`
- [ ] **Task 2 검증 증거**:
  - 실행 명령어 또는 관측 대상: `...`
  - 실행/관측 결과 요약: `...`
- [ ] **회귀 검증 게이트 (Regression Gate)**:
  - 영향 분석(Impact Analysis): 변경에 따른 영향 범위 식별
  - 실행 명령어: `npm test` / `pytest` / `npm run build` 등
  - 결과: 실행된 회귀 스위트 범위 내 실패 미관측(No failures observed) 확인
  - *(기존 테스트 부재 시)*: `[NO_EXISTING_REGRESSION_SUITE]` 선언 및 전체 빌드/린트/타입체크 무에러 확인
- [ ] **최종 Acceptance Criteria 역추적 대조 (Verifier Subagent Gate)**:
  - Verifier 판정: `PASS / FAIL / UNOBSERVED`
```

---

### 2.3 SDD 기반 Build Feedback Loop 6대 원칙

#### 원칙 1. SDD > Verification Strategy > TDD 위계 및 테스트 설계
```text
[상위 계약] Spec-Driven Development (spec.md)
   │  • Requirements, Architecture, Interfaces
   │  • Acceptance Criteria (기준선 Baseline)
   ▼
[실행 계획] Implementation Plan (plan.md)
   │  • 작업 단위 분해 (Task Breakdown)
   │  • 적합한 Test Technique 선택 (동등분할, 경계값분석, 의사결정테이블 등)
   │  • AC별 Verification Strategy 매핑 (TDD, 정적분석, 벤치마크, 수동 등)
   ▼
[단위 피드백] Build Feedback Loop
   │  • 로직/API 구현: TDD (Red 실패 ➔ Green 최소 구현 ➔ Refactor)
   │  • 비로직 작업: 정적 분석, 빌드 확인, 렌더링 관측 증거 확보
   ▼
[회귀 방어선] Regression Gate
   │  • 영향 분석(Impact Analysis) 기반 회귀 테스트 범위 결정 및 실행
   │  • 실행된 스위트 내 실패 미관측(No failures observed) 확인
   ▼
[독립 판정] Verifier Subagent Gate
      • spec.md의 AC 체크리스트와 Evidence 역추적 대조
      • PASS / FAIL / UNOBSERVED 엄격 판정
```
- **위계 정의**: 스펙(`spec.md`)이 최상위 계약이며, TDD는 실행 가능한 로직을 단위 검증하기 위한 핵심 내부 루프이다 (OwnHands의 자체 설계).
- **테스트 케이스 설계**: AC가 확정된 후, 테스트 케이스를 설계할 때 ISTQB의 **동등 분할(Equivalence Partitioning)**, **경계값 분석(Boundary Value Analysis)** 등의 블랙박스 기법을 활용하여 누락 없이 케이스를 도출한다.

#### 원칙 2. Flexible AC Mapping & 양방향 추적성 (Traceability Matrix)
- **금지**: "AC 1개당 테스트 함수 1개 1:1 강제". (과도한 래핑 및 설계 왜곡 초래)
- **채택**: 모든 AC는 적어도 하나 이상의 검증 전략과 관측 가능한 증거에 유연하게 매핑된다 (1:N, N:1 허용).
- ISTQB의 양방향 추적성(Bidirectional Traceability)에 따라 `요구사항` ➔ `수용기준` ➔ `검증전략/테스트기법` ➔ `증거`가 누락 없이 상호 추적되어야 한다.

#### 원칙 3. The Iron Law of Fresh Evidence (신선한 관측 증거 필수)
- 에이전트는 **현재 변경에 대해 직접 관측하고 수집한 신선한 증거(Fresh Evidence)** 없이 작업을 완료했다고 주장할 수 없다.
- 과거 턴의 로그 재인용, 코드 작성만 해두고 "정상 동작할 것"이라고 추측하는 행위는 원천 차단된다.
- **증거 유형**:
  - Unit Test / API: 최신 테스트 러너 실행 출력 (`exit code 0`, 통과 건수).
  - UI / Layout: 브라우저 렌더링 관측 또는 스크린샷 증거.
  - Lint / Type / Policy: 정적 분석 도구의 에러 0건 확인 출력.
  - Performance: 최신 벤치마크 측정 수치.

#### 원칙 4. Versioned Baseline (Existing tests are baseline, not immutable)
- **기준선으로서의 테스트**: 기존 테스트는 시스템 동작의 기준선(Baseline)이다. 에이전트는 **단순히 실패를 피하거나 은폐하기 위해 테스트를 임의로 수정, 완화, 삭제할 수 없다.**
- **기존 테스트의 합법적 수정 조건**:
  1. 승인된 `spec.md`의 요구사항/AC 변경으로 기대 동작이 바뀐 경우.
  2. 기존 테스트 자체의 결함이나 오류를 수정하는 경우.
  3. 수정 이유와 변경된 기대값을 `plan.md` 및 커밋 로그에 명확히 기록하는 경우.
  4. 테스트 assert 완화나 `@skip` 처리를 통한 실패 침식(Silencing)이 아닐 것.

#### 원칙 5. 2단계 검증 게이트 (Builder Self-Loop ➔ 독립 Verifier Gate)
- **1단계 (구현 중 루프)**: 구현자(Builder)가 자기 단위 작업마다 적합한 검증 전략을 돌려 Fresh Evidence를 확보하며 전진한다.
- **2단계 (완료 선언 직전)**: 구현을 완료했다고 판단하면, 독립된 read-only Subagent인 `verifier`([ADR-0001](0001-initial-subagent-roles.md))를 호출하여 `spec.md`의 AC 전량과 수집된 Evidence를 역추적 대조하여 `PASS / FAIL / UNOBSERVED` 판정을 받는다.
- ⚠️ **Verifier 런타임 권한 경계**: 현재 `verifier.toml`은 `sandbox_mode = "read-only"`이므로, M3에서는 "검증 실행 및 증거 생성은 Builder, 독립 역추적 대조 및 판정은 Verifier"로 역할을 분리한다. Verifier가 테스트를 직접 재실행하는 권한/환경 확정은 런타임 실측 후 M4(`Test & Assurance`)에서 다룬다.

#### 원칙 6. 회귀 테스트(Regression Testing) & 부재 시 방어선
- **회귀 검증의 엄밀한 한계 인정**:
  - 다익스트라(Dijkstra)의 원리대로, 테스팅은 결함의 존재를 보일 뿐 결함의 부재(0 회귀)를 증명하지 못한다.
  - 따라서 회귀 테스트 통과가 의미하는 것은 **"실행된 회귀 스위트 범위 내에서 실패가 관측되지 않았다(No failures observed)"**는 사실에 한정된다.
- **기존 테스트가 존재하는 경우**:
  - 변경 영향 분석(Impact Analysis)을 통해 회귀 범위를 판단하고, 적절한 회귀 테스트 스위트를 실행하여 실패 미관측을 확인한다 (`Regression Gate`).
- **기존 테스트가 존재하지 않는 경우 (레거시 / 신규 과제)**:
  - 기존 자동화 테스트가 없더라도 다음 **3대 대체 방어선**을 적용한다:
    1. **변경 반경(Blast Radius) 엄격 통제**: `plan.md`의 `Target Files`에 선언되지 않은 파일에 diff가 발생하면 결함으로 판정한다.
    2. **네이티브 프로젝트 검사(Native Project Checks) 실행 증거**: 해당 프로젝트 환경에 존재하는 applicable checks(빌드, 타입 검사, 린트 등)를 실행하고 무에러 통과 로그를 증거로 제출한다. 환경상 존재하지 않는 검사는 `[UNOBSERVED]`로 명시하여 거짓 증명을 배제한다.
    3. **명시적 선언(Explicit Declaration)**: `plan.md`에 `[NO_EXISTING_REGRESSION_SUITE]`를 명시하고, 실행된 검사 범위와 미관측(UNOBSERVED) 범위를 정직하게 기록한다.

---

## 3. Consequences (결과 및 트레이드오프)

### 긍정적 효과
- **AI 회귀 참사 차단**: 공통 모듈 오염, 테스트 베이스라인 침식, Blast Radius 폭증을 시스템적으로 방지한다.
- **엔지니어링 엄밀성 확보**: "0 회귀 증명" 같은 과장을 배제하고, 실행된 범위와 미관측 범위를 정직하게 기록하는 OwnHands 철학(`UNOBSERVED`)을 수호한다.
- **정상적인 소프트웨어 진화 지원**: `Existing tests are baseline, not immutable` 원칙을 통해 스펙 변경 시의 합법적 테스트 리팩토링을 가로막지 않는다.
- **자가합리화 원천 봉쇄**: 신선한 증거(Fresh Evidence)와 독립 Verifier 게이트를 통해 에이전트의 허위 완료 선언을 차단한다.

### 트레이드오프 및 관리 비용
- **아티팩트 증가**: 정식 작업 시 문서가 3개로 늘어나므로, 사소한 작업에는 적용을 면제하는 실용적 예외 규칙을 유지한다.
- **영향 분석 오버헤드**: 회귀 테스트 범위를 결정하기 위한 변경 영향 분석에 주의를 기울여야 한다.

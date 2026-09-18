# ADR-0007 — plan.md 아티팩트 규격과 SDD 기반 Build Feedback Loop

- **상태:** Accepted — 사용자 합의
- **일자:** 2026-09-19
- **관련 Issue:** [#123](https://github.com/taejung3852/OwnHands/issues/123) (선행: [#121 Research Gate](https://github.com/taejung3852/OwnHands/issues/121))
- **관련 PR:** [#122](https://github.com/taejung3852/OwnHands/pull/122) (M3 Research Gate 완료)

---

## 1. Context (배경 및 문제)

1. **설계(Spec)와 코드 구현(Build) 사이의 실행 공백**:
   - V2-M2를 통해 의도(`intent.md`)와 설계 청사진(`spec.md`)의 규격이 확립되었다.
   - 그러나 정밀한 `spec.md`가 있더라도, 에이전트가 코드를 작성할 때 "어떤 단위로 쪼개어 변경하고, 어떤 순서로 구현하며, 무엇으로 자체 검증할 것인가"의 **실행 계획(Implementation Plan)**이 없으면 다음과 같은 현업 실패 패턴이 발생한다:
     - **한 번에 수십 개 파일 수정 후 파탄**: 변경 폭을 통제하지 못하고 대형 diff를 생성하여 디버깅 불능 상태에 빠짐.
     - **자가합리화 및 환각 검증**: 테스트하기 쉬운 것만 작성하거나, 실제 터미널 실행 없이 "테스트 통과함"이라고 허위 완료 주장.
     - **베이스라인 무단 침식**: 구현 중 스펙의 모순이나 새 제약을 만났을 때, 사람과의 소통 없이 자의적으로 테스트 기대값을 낮춤.

2. **1차 자료 조사 결과 및 네이티브 활용 경계 ([docs/v2/research/m3-build-feedback-loop.md](../research/m3-build-feedback-loop.md))**:
   - **Codex 네이티브 기능**: `/plan`(다단계 계획 모드), `/goal`(Outcome-Constraints-Verification), `/review`(전담 리뷰어), `/worktree`(작업 격리)를 기본 탑재하고 있다.
   - **경계**: 특정 호스트의 대화 세션 기반 `/plan`은 편리한 상호작용 도구이지만, 저장소의 감사 추적(Audit Trail)과 코드-명세 일치성을 보장하는 **영구 Git 아티팩트**를 대체하지 못한다.
   - **Superpowers 원칙의 선별 흡수**: 14개 대형 스킬을 통째로 복제하는 대신, `verification-before-completion`(Fresh Evidence 원칙)과 `writing-plans`(작은 작업 분해 패턴)의 핵심 원칙을 OwnHands의 가벼운 지침 규약(Thin Harness)으로 흡수한다.

3. **프로세스 경직성 안티패턴 방지**:
   - "스펙의 Acceptance Criteria(AC) 1개당 테스트 함수 1개를 무조건 1:1 매핑한다"는 식의 규칙은 벤치마크, 정적 분석, 보안 권한 검사 등 다양한 검증 형태를 수용하지 못하고 불필요한 테스트 래퍼만 양산한다.
   - 따라서 **계약(AC)은 엄격히 검증하되, 검증 전략(Verification Strategy)과 구현 형태는 유연하게 분리**해야 한다.

---

## 2. Decision (결정)

OwnHands는 V2-M3(`Build & Feedback Loop`)의 실행 규약으로 **`plan.md` 아티팩트 정식 규격**과 **SDD 기반 Build Feedback Loop 5대 원칙**을 확정한다.

### 2.1 저장 위치 및 생명주기

모든 작업의 실행 계획은 Git 저장소 내 `docs/v2/specs/<feature-name>/` 아래에 영구 보존한다:

```text
docs/v2/specs/<feature-name>/
├── intent.md     # Stage 1 (Plan): 인간의 의도·문제·경계
├── spec.md       # Stage 2 (Design): AI가 분석한 기술 청사진 및 수용 기준 (AC)
└── plan.md       # Stage 3 (Build): 구현 단위 분해 및 신선한 검증 증거 체크리스트
```

- `plan.md`는 임시 메모가 아니며, 기능 브랜치 작업과 함께 커밋되어 PR 머지 시 저장소 메인 히스토리에 영구 보존된다.
- 이를 통해 **"의도 ➔ 설계 ➔ 실행 계획 ➔ 검증 증거"**의 전 생명주기 감사 추적성(Audit Trail)을 완성한다.

---

### 2.2 `plan.md` 규격 — "실행 단위 분해와 신선한 증거"

- **주요 작성자**: AI 에이전트 (사람 검토 및 승인 권장)
- **핵심 질문**: *"어떤 단위로 구현하고, 어떻게 신선하게 검증할 것인가?"*
- **필수 4대 엔지니어링 필드**:

```markdown
# Plan: [기능 / 과제 이름]

- **기반 Spec**: [`spec.md`](spec.md)
- **작성 주체**: AI 에이전트
- **일자**: YYYY-MM-DD
- **상태**: Draft / Approved / In Progress / Completed

---

## 1. 구현 맥락 및 대상 파일 (Context & Target Files)
- **구현 목표 요약**: Spec에서 확정된 핵심 인터페이스 및 로직 구현.
- **대상 파일 목록 및 책임 경계**:
  - `[NEW]` `경로/파일명`: 생성 책임
  - `[MODIFY]` `경로/파일명`: 수정 범위 및 기존 동작 보존 경계

## 2. 작업 단위 분해 (Task Breakdown)
> ⚠️ **원자적 단위(Atomic Unit)**: 한 번에 모든 것을 고치지 않고, "실패하는 테스트 ➔ 최소 구현 ➔ 통과 확인 ➔ 커밋"의 작은 단위로 쪼갭니다.
- [ ] **Task 1: [단위 작업명]**
  - 작업 내용: 대상 함수/인터페이스 정의 및 단위 테스트 추가
  - 예상 변경 파일: `...`
- [ ] **Task 2: [단위 작업명]**
  - 작업 내용: 핵심 로직 구현 및 통합 검증
  - 예상 변경 파일: `...`

## 3. AC별 검증 전략 매핑 (Verification Strategy Mapping)
> ⚠️ **유연한 매핑**: spec.md의 모든 AC는 최소 1개 이상의 전략과 관측 가능한 증거에 연결되어야 합니다 (1:1 강제 금지).
| AC ID | 검증 전략 (Strategy) | 관측 증거 (Evidence) | 통과 기준 (Pass Criteria) |
|---|---|---|---|
| `AC-01` | 단위 테스트 (TDD) | 터미널 테스트 실행 로그 | 테스트 패스 (0 exit code) |
| `AC-02` | 정적 분석 / 린트 | `npm run lint` 등 정적 검사 | 에러/경고 0건 |
| `AC-03` | 수동 / 브라우저 점검 | CLI 출력 결과 또는 렌더링 확인 | 기대 출력 문자열 일치 |

## 4. 실행 및 신선한 검증 증거 (Execution & Fresh Evidence Checklist)
> ⚠️ **The Iron Law**: "신선한 터미널 실행 증거 없는 완료 주장 금지"
- [ ] **Task 1 검증 증거**:
  - 실행 명령어: `...`
  - 실행 결과 요약: `...`
- [ ] **Task 2 검증 증거**:
  - 실행 명령어: `...`
  - 실행 결과 요약: `...`
- [ ] **최종 Acceptance Criteria 역추적 대조 (Verifier Subagent Gate)**:
  - Verifier 판정: `PASS / FAIL / UNOBSERVED`
```

---

### 2.3 SDD 기반 Build Feedback Loop 5대 원칙

#### 원칙 1. SDD > Verification Strategy > TDD 위계 구조
```text
[상위 계약] Spec-Driven Development (spec.md)
   │  • Requirements, Architecture, Interfaces
   │  • Acceptance Criteria (기준선 Baseline)
   ▼
[실행 계획] Implementation Plan (plan.md)
   │  • 작업 단위 분해 (Task Breakdown)
   │  • AC별 Verification Strategy 매핑 (TDD, 정적분석, 벤치마크, 수동 등)
   ▼
[단위 피드백] Build Feedback Loop
   │  • 실행 가능한 코드 로직: TDD (Red 실패 ➔ Green 최소 구현 ➔ Refactor)
   │  • 비테스트 항목: 정적 분석, 렌더링 확인, CLI 실행 증거 확보
   ▼
[독립 판정] Verifier Subagent Gate
      • spec.md의 AC 체크리스트와 Evidence 역추적 대조
      • PASS / FAIL / UNOBSERVED 엄격 판정
```
- **위계 정의**: 스펙(`spec.md`)이 최상위 계약(Contract)이며, TDD는 실행 가능한 동작을 단위 검증하기 위한 핵심 내부 루프(Feedback Loop)이다.
- TDD가 스펙을 지배하지 않으며, 스펙의 모든 기준이 반드시 단위 테스트 코드여야 하는 것도 아니다.

#### 원칙 2. Flexible AC Mapping (수용 기준 유연 매핑)
- **금지**: "AC 1개당 테스트 함수 1개 1:1 강제". (과도한 래핑 및 설계 왜곡 초래)
- **채택**: 모든 AC는 적어도 하나 이상의 검증 전략과 관측 가능한 증거에 연결되어야 한다 (1:N, N:1 유연 매핑 허용).
- 계약(AC)은 엄격하게 검증하되, 구현 세부사항(내부 함수명, 클래스 구조 등)에 대한 검증은 느슨하게 유지하여 리팩토링 저항성을 낮춘다.

#### 원칙 3. The Iron Law of Fresh Evidence (신선한 실행 증거 필수)
- 에이전트는 **자신이 직접 실행하여 성공한 최신 터미널 출력(Exit code 0, 출력 결과)** 없이 작업을 완료했다고 주장할 수 없다.
- 과거 턴의 로그 재인용, 코드 작성만 해두고 "정상 동작할 것"이라고 추측하는 행위, 테스트를 건너뛰는 행위는 원천 차단된다.

#### 원칙 4. Versioned Baseline (기준선 버전 관리)
- 스펙은 불변이 아니지만, 구현자가 임의로 축소할 수 있는 대상도 아니다.
- 구현 중 숨겨진 기술적 모순이나 새로운 제약이 발견되면:
  1. 즉시 구현을 멈춘다.
  2. 모순 사실과 대안을 사람에게 보고하고 `spec.md` 수정을 요청한다.
  3. 사람이 승인한 후 `spec.md`를 갱신하고, 그에 맞춰 `plan.md`와 테스트를 재정렬한다.

#### 원칙 5. 2단계 검증 게이트 (구현자 Self-Loop ➔ 독립 Verifier Gate)
- **1단계 (구현 중 루프)**: 구현자가 자기 단위 작업마다 테스트/명령을 돌려 Fresh Evidence를 확보하며 빠르게 전진한다.
- **2단계 (완료 선언 직전)**: 구현을 완료했다고 판단하면, 독립된 read-only Subagent인 `verifier`([ADR-0001](0001-initial-subagent-roles.md))를 호출하여 `spec.md`의 AC 전량과 터미널 실행 증거를 역추적 대조하여 `PASS / FAIL / UNOBSERVED` 판정을 받는다.

---

## 3. Consequences (결과 및 트레이드오프)

### 긍정적 효과
- **추적성 완성**: `intent.md`(왜) ➔ `spec.md`(무엇을) ➔ `plan.md`(어떻게) ➔ Git Commit/PR의 전체 SDLC 감사 추적성이 확보된다.
- **자가합리화 원천 봉쇄**: 신선한 증거(Fresh Evidence)와 독립 Verifier 게이트를 통해 에이전트의 허위 완료 선언을 차단한다.
- **설계 유연성 유지**: TDD를 SDD 안의 핵심 단위 루프로 조화롭게 배치함으로써, AC 1:1 강제에 따른 프레임워크 경직성을 방지한다.
- **Thin Harness 준수**: 무거운 런타임 훅 스크립트나 빌드 프레임워크를 개발하지 않고, 마크다운 계약과 Codex 네이티브 기능만으로 동작한다.

### 트레이드오프 및 관리 비용
- **아티팩트 증가**: 정식 작업 시 문서가 3개로 늘어나므로, 오타 수정이나 단순 1-liner 픽스 등 사소한 작업에는 적용을 면제하는 실용적 예외 규칙을 유지한다.
- **스펙-플랜 동기화 비용**: 구현 중 스펙이 변경될 경우 `plan.md`도 함께 수정해야 하는 유지보수 오버헤드가 발생한다 (이는 베이스라인 통제를 위한 의도된 비용임).

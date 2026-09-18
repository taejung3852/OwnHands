# V2-M3 Research Gate: Codex 계획 기능 및 Build 피드백 루프 공식 자료 조사

- **일자**: 2026-09-18
- **관련 Issue**: [#121 (V2-M3 조사 — Codex 계획 기능 및 Build 피드백 루프 공식 자료 조사)](https://github.com/taejung3852/OwnHands/issues/121)
- **상위 마일스톤**: [V2-M3 — Build & Feedback Loop](https://github.com/taejung3852/OwnHands/milestone/16)
- **조사자**: 박태정 (@taejung3852) & Antigravity

---

## 1. 조사 목적 및 배경 (Why)

V2-M2(Plan & Design)를 통해 `intent.md`(의도)와 `spec.md`(설계)의 정식 규격 및 도출 도우미(`grill-spec`)가 안착되었다.  
V2-M3(Build & Feedback Loop)의 최상위 목표는 **"설계된 명세(`spec.md`)를 실제 동작하는 코드로 전환할 때, 작업 근거(`plan.md`)와 실행·확인·수정 루프(TDD, Verifier)를 연결하여 에이전트의 탈선과 자가합리화를 방지하는 것"**이다.

OwnHands의 개발 원칙에 따라, 구현에 착수하기 전 **Codex 최신 공식 문서, Anthropic Playbook, 로컬 Superpowers 플러그인**을 1차 자료로 조사하여 네이티브 지원 범위를 확인하고, 직접 구현할 최소 경계(Thin Harness)를 확정한다.

---

## 2. 1차 출처 및 확인 환경 (Primary Sources)

1. **Codex 공식 문서 (`learn.chatgpt.com`)** (확인일: 2026-09-18)
   - [`/docs/reference/slash-commands.md`](https://learn.chatgpt.com/docs/reference/slash-commands.md): `/plan`, `/goal`, `/review`, `/worktree` 명령어 사양.
   - [`/docs/long-running-work.md`](https://learn.chatgpt.com/docs/long-running-work.md): Goal mode, Outcome-Constraints-Verification 구조.
   - [`/docs/code-review.md`](https://learn.chatgpt.com/docs/code-review.md): Codex 내장 dedicated reviewer 및 diff 검토 범위.
   - [`/docs/developer-commands.md`](https://learn.chatgpt.com/docs/developer-commands.md): CLI/TUI 명령어 및 `--sandbox`, `--ask-for-approval` 사양.
2. **Anthropic AI-Native SDLC Playbook** (확인일: 2026-09-16)
   - 원문 대응표: [`docs/references/anthropic-playbook.md`](../../references/anthropic-playbook.md) (§2 세 가지 Artifact, §6 검증과 리뷰).
3. **Superpowers 플러그인 로컬 소스 코드** (확인일: 2026-09-18)
   - 경로: `/Users/parktaejung/.gemini/config/plugins/superpowers/skills/`
   - 분석 스킬: `verification-before-completion`, `writing-plans`, `test-driven-development`, `subagent-driven-development`.
4. **OwnHands 기존 아키텍처 및 V1 교훈**
   - [`docs/v2/overview.md`](../overview.md) (§3 세 문서는 다른 질문에 답한다, §5 Baseline과 Review의 재배치).
   - [`docs/v2/adr/0004-intent-spec-specification.md`](../adr/0004-intent-spec-specification.md) (산출물 4대 필드 규격).

---

## 3. 7대 조사 질문에 대한 분석 및 확인 사실

### Q1. Codex의 계획 기능 (Plan Mode & Goal Mode)
- **공식 확인 사실**:
  - Codex는 `/plan` 슬래시 커맨드를 네이티브로 제공한다 (`Toggle plan mode for multi-step planning`).
  - `/goal` 명령어로 장기 실행 목표(Goal Mode)를 설정할 수 있으며, 공식 문서는 **"결과가 불명확할 때는 먼저 `/plan`으로 인터뷰하고 제약을 파악한 뒤, 측정 가능한 완료 기준을 가진 `/goal`로 구체화하라"**고 명시한다.
  - 공식이 제시하는 Goal의 3대 필수 요소는 **Outcome(결과), Constraints(제약), Verification(완료를 증명하는 테스트/측정 기준)**이다.
- **OwnHands에 주는 의미**:
  - 특정 호스트의 `/plan` 대화 세션은 휘발될 수 있으므로, 프로젝트의 영구 Git 아티팩트인 `plan.md` 저장을 대체하지 않는다.
  - 하지만 Codex의 `/plan`과 `/goal`의 인터랙션 흐름은 OwnHands의 GORE(최상위 목표 닻) 및 `intent ➔ spec ➔ plan` 파이프라인과 완벽히 일치한다.

### Q2. Codex 네이티브 피드백 루프 (Review & Worktree)
- **공식 확인 사실**:
  - Codex는 `/review` 커맨드를 통해 변경 diff를 읽고 우선순위화된 실행 가능한 피드백을 제공하는 전담 리뷰어(dedicated reviewer)를 기본 탑재하고 있다.
  - `/worktree` 및 `/fork` 명령어로 메인 작업 트리를 더럽히지 않고 새 Git worktree에서 안전하게 작업을 격리 실행할 수 있다.
- **OwnHands에 주는 의미**:
  - Diff 리뷰 엔진이나 워크트리 생성기를 직접 바닥부터 개발할 필요가 없다.

### Q3. 공식 Testing / Verification 가이드
- **공식 확인 사실**:
  - 공식 문서는 "작업 완료(Definition of Done)를 정의할 때 테스트나 측정 기준(Verification criteria)을 포함하여 에이전트 스스로 완료 여부를 검증할 수 있게 하라"고 강조한다.
  - 테스트 실행 시 `--sandbox workspace-write` 모드를 통해 안전하게 로컬 테스트를 돌릴 수 있다.
- **OwnHands에 주는 의미**:
  - 스펙에 적힌 검증 기준을 기계가 실행 가능한 명령(Test script/command)으로 연결해야 에이전트의 자체 피드백 루프가 작동한다.

### Q4. Subagent의 Build 루프 연계
- **공식 확인 사실**:
  - Codex는 `.codex/agents/*.toml`을 통해 독립된 설정, 시스템 프롬프트, 도구를 갖는 커스텀 에이전트를 선언하고 호출할 수 있다.
- **OwnHands에 주는 의미**:
  - OwnHands는 이미 `ADR-0001`을 통해 `verifier.toml`(`sandbox_mode = "read-only"`)을 정의해 두었다.
  - 빌드 중 구현자가 자기 코드를 셀프 검증하는 TDD 루프와, 작업 완료 직전 독립된 `verifier`가 `spec.md` 기준선 전량을 역추적 대조하는 2단계 검증 구조로 자연스럽게 연결된다.

### Q5. Hooks / Scripts 최소 범위
- **공식 확인 사실**:
  - Codex의 hook 이벤트(`PreToolUse`, `PostToolUse` 등)가 존재하나, 복잡한 런타임 스크립트를 지금 작성하면 유지보수 부담이 커진다.
- **OwnHands에 주는 의미**:
  - M3 단계에서는 무거운 Hook 스크립트를 코드로 짜지 않고, 지침(`AGENTS.md`) 및 `plan.md` 프로토콜 기반의 Thin Harness 원칙을 유지한다. (Zero-Code 원칙 유지)

### Q6. Anthropic Playbook의 Build 단계 원문 분석
- **공식 확인 사실**:
  - Playbook은 `spec.md`(What/설계)에서 `plan.md`(How/구현 계획)로 넘어갈 때, 파일별 수정 계획과 테스트 전략을 포함하도록 명시한다.
  - 구현 중에는 에이전트가 테스트를 직접 실행하여 확인-수정 루프(Feedback Loop)를 돌도록 권장한다.
- **OwnHands에 주는 의미**:
  - `spec.md`와 `plan.md`의 책임을 명확히 구분한다:
    - `spec.md`: "어떤 설계로 무엇을 만족시킬 것인가?" (Requirements, Architecture, Edge Cases, Acceptance Criteria)
    - `plan.md`: "현재 코드베이스에서 어떤 파일들을 어떤 순서로 수정하고 어떻게 증명할 것인가?" (Files to touch, Bite-sized Tasks, Verification Strategy, Evidence)

### Q7. Superpowers 플러그인 분석 및 V1의 교훈
- **로컬 코드 분석 결과**:
  - Superpowers 플러그인은 14개의 대형 스킬을 포함하고 있으며, 독자적인 경로(`docs/superpowers/plans/`)와 worktree 도구에 강결합되어 있다.
  - **전량 복사 금지**: 14개 스킬을 그대로 복제하면 Codex의 **10,000 토큰 카탈로그 한도를 즉시 초과**하여 기존 스킬이 탈락하는 치명적 부작용이 발생한다.
  - **흡수할 3대 황금 원칙 (Golden Principles)**:
    1. **`verification-before-completion`의 The Iron Law**:
       > *"NO COMPLETION CLAIMS WITHOUT FRESH VERIFICATION EVIDENCE"*  
       (신선한 터미널 검증 실행 증거 없이 완료 주장을 절대 하지 못하게 차단).
    2. **`writing-plans`의 Bite-sized Task 분해**:
       작업 단위를 2~5분 크기("실패하는 테스트 작성 ➔ 최소 구현 ➔ 통과 확인 ➔ 커밋")로 쪼개어 에이전트의 컨텍스트 오버헤드와 탈선을 방지.
    3. **`subagent-driven-development`의 Context 격리**:
       구현 및 검증 시 불필요한 메인 대화 히스토리를 차단하고 핀포인트 정보만 전달하여 환각 억제.
- **V1의 교훈**:
  - V1은 검증을 위해 거대한 검증 프레임워크와 러너를 자체 제작하여 배보다 배꼽이 더 커졌다.
  - V2는 플랫폼 네이티브 기능(TUI, CLI, subagent) 위에 가벼운 규약만 얹는 **Thin Harness**를 철저히 고수해야 한다.

---

## 4. M3 산출물 규격을 위한 권장 설계 (Draft Architecture)

### 4.1 SDD 기반 Build Feedback Loop 위계
```text
[상위 계약] Spec-Driven Development (spec.md)
   │  • Requirements, Constraints, Edge Cases
   │  • Acceptance Criteria (기준선 Baseline)
   ▼
[실행 계획] Implementation Plan (docs/v2/specs/<feature>/plan.md)
   │  • 대상 파일 목록 및 책임 경계
   │  • Bite-sized Tasks (2~5분 단위 분해)
   │  • AC별 Verification Strategy (TDD, 벤치마크, 정적분석, 권한검사 등)
   ▼
[단위 루프] Build Feedback Loop
   │  • TDD (Red 실패 확인 ➔ Green 구현 ➔ Refactor)
   │  • The Iron Law: 신선한 실행 증거(Fresh Evidence) 확보
   ▼
[독립 판정] Verifier Subagent Gate
      • spec.md의 AC 체크리스트와 Evidence 역추적 대조
      • PASS / FAIL / UNKNOWN 엄격 판정
```

### 4.2 Acceptance Criteria 추적성 규칙
- **금지**: "AC 하나당 테스트 함수 하나 1:1 강제 매핑" (과도한 프로세스 경직성 및 구현 형태 고정 안티패턴).
- **채택**: "모든 AC는 최소 하나 이상의 Verification Strategy 및 Evidence에 유연하게 추적 가능해야 한다" (1:N, N:1 허용).
- **계약-구현 분리**: 계약(AC)은 강하게 검증하고, 구현 형태(특정 함수명, 코드 구조)는 느슨하게 검증한다.

### 4.3 Versioned Baseline 원칙
- 스펙은 불변(immutable)이 아니라 버전 관리되는 기준선(Baseline)이다.
- 구현 중 숨겨진 모순이나 새 제약이 드러나면 몰래 테스트 기준을 낮추지 않고, **`spec.md` 수정 ➔ 사람 승인 ➔ `plan.md`/테스트 재정렬** 흐름을 거친다.

---

## 5. 직접 만들지 않아도 되는 것 (Non-goals & Native First)

| 구분 | 플랫폼 제공 / 배제 대상 | OwnHands가 할 일 |
|---|---|---|
| **계획 도구** | Codex `/plan`, `/goal` 네이티브 모드 | `docs/v2/specs/<feature>/plan.md` 영구 아티팩트 템플릿 및 규약 제정 |
| **코드 리뷰** | Codex `/review` dedicated reviewer | PR 전담 `reviewer` Subagent 호출 지침 연계 |
| **작업 격리** | Codex `/worktree` | 필요 시 worktree 분리 안내 |
| **프레임워크** | 무거운 범용 SDD Engine / 독자 CLI 러너 개발 배제 | 마크다운 기반 얇은 계약(Thin Contract) 유지 |
| **플러그인** | Superpowers 14개 스킬 일괄 복제 배제 (토큰 천장 보호) | 3대 핵심 원칙(Iron Law, Task 분해, Context 격리)만 지침으로 흡수 |

---

## 6. 결론 및 다음 단계

Codex는 계획(`/plan`), 장기 목표(`/goal`), 리뷰(`/review`), 격리(`/worktree`)를 이미 네이티브로 제공하고 있다.  
따라서 OwnHands V2-M3는 거대한 빌드 시스템을 새로 만들지 않고, **Superpowers의 3대 철칙(Iron Law, Task 분해, Context 격리)을 흡수한 가벼운 `plan.md` 규약과 TDD 피드백 루프**를 정립하는 것으로 충분하다.

- **다음 단계**: Step ① 조사 결과를 PR로 제출하고, 승인 후 **Step ② `plan.md` 아티팩트 정식 규격 제정(ADR-0007)**으로 진입한다.

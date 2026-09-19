# Spec: grill-spec (GORE·인터뷰 기반 intent/spec 도출 도우미 Skill)

- **기반 Intent**: [`intent.md`](intent.md)
- **작성 주체**: AI 에이전트 분석 (사람 검토 및 승인 대상)
- **일자**: 2026-09-18
- **상태**: Approved

---

## 1. 기술적 요구사항 (Requirements)

### 1.1 Skill 메타데이터 및 인터페이스
- `REQ-01 (Skill 진입점)`: `.agents/skills/grill-spec/SKILL.md`는 고유한 `name: grill-spec`과 1~2문장의 간결한 `description`을 가진 YAML frontmatter로 시작해야 한다.
- `REQ-02 (Upstream 역할 및 추상화 계약)`:
  - Matt Pocock upstream skills를 무조건 재작성하지 않고, 고유의 역할을 존중하는 **Thin Orchestration Layer**로 동작한다:
    - `grilling`: 핵심 인터뷰 primitive. design tree와 frontier를 round 단위로 탐색하며, Agent는 Fact 수집을, User는 Decision을 전담한다.
    - `grill-me`: stateless wrapper (repo 없는 일반 plan/design 대상).
    - `grill-with-docs`: repo-aware wrapper (domain-modeling 포함. OwnHands 아티팩트 체계와 충돌하지 않는 경우 선택적 연계).
    - `wayfinder`: 한 세션으로 감당하기 어려운 대형/불명확 작업을 decision-ticket map으로 쪼개는 planning 도구 (일반 기능에서는 사용하지 않음).
    - `to-spec`: upstream 자체 규격이므로 직접 산출물 생성기로 쓰지 않고 대화 합성 패턴만 참고.
  - **Upstream 재사용 및 Fallback 계약**:
    - upstream skill이 설치되어 있고 현재 harness에서 호출 가능하면 재사용한다.
    - Codex 환경에서 cross-skill invocation이 지원되지 않거나 upstream이 부재할 경우, `references/interview-guide.md`에 정의된 **OwnHands 최소 fallback interview contract**로 자연스럽게 전환하여 작업이 중단되지 않는다.
    - upstream 코드를 실질적으로 복사/수정하여 vendor하는 경우 MIT License attribution 고지를 유지한다.

### 1.2 실행 프로토콜 및 오케스트레이션
- `REQ-03 (8단계 실행 프로토콜)`:
  1. **Route**: 작업 규모 및 저장소 유무에 따라 최적의 인터뷰 경로를 결정한다.
  2. **GORE Anchor**: 사용자의 입력에서 최상위 Goal 후보를 도출하고, 불명확하면 Grilling을 통해 사용자와 확인한 뒤 Anchor로 확정한다.
  3. **Fact Gathering**: 현재 실행 환경에서 사용 가능한 repository search/read 도구와 필요 시 Subagent를 이용해 코드·설정·문서를 조사하여 기술적 팩트를 확보한다.
  4. **Grilling**: 의존성이 풀린 frontier 단위로 날카로운 질문 라운드를 진행하여 사용자의 결정을 도출한다.
  5. **intent.md Draft**: 확인된 의도, 목표, 비목표(Non-goals), 제약을 ADR-0004 규격에 맞춰 작성한다.
  6. **Human Checkpoint 1 (Default Barrier)**: 기본적으로 사용자 확인을 기다리며, 승인되지 않은 Intent를 확정된 근거로 취급해 Spec 작성을 직행하지 않는다. (단, 과도한 hard-stop 문구는 쓰지 않음)
  7. **spec.md Draft**: 승인된 Intent와 팩트를 기반으로 요구사항, 아키텍처, 엣지케이스, 수용성 기준을 작성한다.
  8. **Human Checkpoint 2**: 작성된 `spec.md`에 대해 사람의 엔지니어링 검토 및 승인을 거친다.

### 1.3 라우팅 (Route) 기준
- `ROUTE-A (No-Repo / Simple Idea)`: 저장소가 없거나 순수 개념 설계 ➔ `grill-me` / `grilling` 호출 또는 fallback 인터뷰.
- `ROUTE-B (Repo-Aware / Single-Session Feature)`: 저장소가 있고 한 세션 내 완결 가능한 일반 기능 (기본 경로) ➔ `grilling` 기반 인터뷰 + repository fact exploration.
- `ROUTE-C (Multi-Session / Heavy Effort)`: 단일 세션 범위를 초과하는 거대하고 불명확한 과제 ➔ `wayfinder` 후보로 안내하여 decision map을 먼저 정리한 뒤 OwnHands intent/spec 흐름으로 복귀.

### 1.4 Stage Modes & 3대 안전장치 (단계 분리 보장)
- `REQ-04 (Explicit Stage Modes)`: 고정 CLI 구문 대신 자연어 요청과 결합된 3가지 실행 경로를 지원한다:
  1. **`intent-only` 모드** ("intent만 잡아줘"): GORE 닻 내리기 ➔ Grilling ➔ `intent.md` 생성 후 종료 (Stage 1 Plan 완결).
  2. **`spec-from-intent` 모드** ("기존 intent 기준으로 spec 만들어보자"): 기존 `intent.md` 로드 ➔ 현재 Intent 유효성 확인 ➔ repo Fact Gathering ➔ Grilling ➔ `spec.md` 생성 (Stage 2 Design 완결).
  3. **`full-flow` 모드** (기본): intent 작성 ➔ Checkpoint 1 ➔ 승인 후 spec 작성.
- `REQ-05 (Artifact Traceability & Frontier)`:
  - 질문 수에 인위적 숫자 제한을 두지 않고, 의존성이 풀린 frontier를 1 round 단위로 묻고 다음 frontier를 계산한다.
  - `spec.md`는 반드시 `기반 Intent: intent.md` 헤더를 유지하여 추적성을 보장한다.
  - 미승인/불명확 Intent의 결정을 에이전트가 임의로 채우지 않으며 `Open Questions`나 `Assumptions`로 명시한다.

---

## 2. 시스템 아키텍처 및 인터페이스 (Architecture & Interfaces)

### 2.1 대상 파일 및 컴포넌트 목록
- `[NEW] .agents/skills/grill-spec/SKILL.md`: Skill 진입점, 트리거 정의, 실행 프로토콜 가이드.
- `[NEW] .agents/skills/grill-spec/references/interview-guide.md`:
  - GORE Anchor 판정 기준
  - Upstream Skill 라우팅 및 Fallback 인터뷰 계약
  - Fact vs Decision 구분 가이드
  - 2단계 Human Checkpoint 규칙
  - Intent ➔ Spec 추적성(Traceability) 매핑 규칙
  - MIT License 고지문
- `[MODIFY] docs/specs/grill-spec/intent.md`: 본 작업의 Intent 아티팩트 (개정 완료).
- `[MODIFY] docs/specs/grill-spec/spec.md`: 본 작업의 정밀 기술 청사진 (본 문서).

### 2.2 디렉터리 및 아티팩트 산출 경로
```text
docs/specs/<feature-name>/
├── intent.md     # Checkpoint 1 승인 대상 (Why, What, Non-goals, Constraints)
└── spec.md       # Checkpoint 2 승인 대상 (Requirements, Arch, Edge cases, Criteria)
```

---

## 3. 엣지 케이스 및 예외 처리 (Edge Cases)

| 시나리오 / 경계 조건 | 기대 동작 및 처리 방식 |
|---|---|
| 기존 `intent.md`가 이미 존재하는 작업일 때 | 생략하지 않고 기존 Intent를 읽어 Goal/Non-goals의 유효성을 점검하며, 현재 저장소 코드베이스와의 괴리를 Fact Gathering으로 조사한 뒤 필요한 Decision만 다시 연다. |
| 신규 영역이라 관련 구현 코드가 전혀 없을 때 | "관련 구현 없음" 자체를 확인된 팩트로 기록하고, 저장소 전체 구조, `AGENTS.md`, 의존성, 유사 모듈의 컨벤션을 조사하여 설계 제약으로 반영한다. |
| 작업 규모가 너무 거대하여 한 세션으로 감당 불가능할 때 | 한 세션에서 억지로 `spec.md`까지 완성하려 하지 않고, `ROUTE-C(Wayfinder)` 후보로 안내하여 태스크 맵 분할을 먼저 권고한다. |
| Upstream skill이 미설치되었거나 호출 실패할 때 | 에러로 중단되지 않고, `references/interview-guide.md`의 fallback interview contract를 직접 실행하여 동일한 산출물을 도출한다. |
| 사용자가 "그냥 알아서 다 정해줘"라고 위임하려 할 때 | 팩트는 에이전트가 채우되, 아키텍처 선택이나 비목표 같은 Decision은 기본 가정(Default Assumption)을 제시하고 "이 가정이 맞는지" 확인 질문으로 전환한다. |

---

## 4. 수용성 기준 및 검증 계획 (Acceptance Criteria)

### 4.1 수용성 기준 (Acceptance Criteria)
- [ ] **기준 1 (Skill 구조)**: `.agents/skills/grill-spec/SKILL.md` 및 `references/interview-guide.md`가 유효하게 생성되고, MIT License attribution이 포함된다.
- [ ] **기준 2 (Routing 정확성)**: 일반 기능에서 Wayfinder를 과호출하지 않고 `ROUTE-B`로 진입하며, 대형 과제는 `ROUTE-C`로 안내한다.
- [ ] **기준 3 (Fact vs Decision 분리)**: 코드베이스 팩트는 도구/탐색으로 직접 찾고, 비목표 및 정책 결정은 사용자에게 질문한다.
- [ ] **기준 4 (추적성)**: 각 핵심 Requirement가 최소 하나 이상의 Goal, Constraint 또는 확인된 Fact에 추적 가능해야 하며, Non-goals를 침범하지 않는다.
- [ ] **기준 5 (Human Checkpoint 준수)**: Checkpoint 1, 2 없이 산출물을 임의 확정하거나 Build로 직행하지 않는다.
- [ ] **기준 6 (Fallback 동작)**: Upstream 도구가 없는 환경에서도 최소 인터뷰 규칙으로 `intent.md`와 `spec.md` 완성이 가능하다.
- [ ] **기준 7 (Continuous Eval)**: `docs/evals/0004-skill-grill-spec.md` 평가를 추가하여 위 기준을 체계적으로 검증한다.

### 4.2 자동화 검증 명령어
```bash
# 1. 파일 구조 검증
test -f .agents/skills/grill-spec/SKILL.md && test -f .agents/skills/grill-spec/references/interview-guide.md
# 2. YAML frontmatter 검증
grep -q "name: grill-spec" .agents/skills/grill-spec/SKILL.md
# 3. MIT License 고지 확인
grep -q "MIT License" .agents/skills/grill-spec/references/interview-guide.md
```

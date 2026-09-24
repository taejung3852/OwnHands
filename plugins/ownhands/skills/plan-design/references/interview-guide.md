# plan-design 인터뷰 및 오케스트레이션 가이드

이 문서는 `plan-design` Skill이 실행될 때 참조하는 세부 프로토콜, 라우팅 규칙, Fallback 계약, 추적성 가이드입니다.

---

## 1. GORE 최상위 Goal 닻 내리기 (Anchor)

구현 세부사항(데이터베이스 테이블, 프레임워크 선택 등)으로 직행하기 전에, 항상 사용자의 최상위 목표에 닻을 내립니다:
- **검증 질문**: *"이 작업이 완료되었을 때 대상 사용자가 얻게 되는 본질적 가치(Outcome)는 무엇인가요?"*
- **Anchor 확정 원칙**: 에이전트가 임의로 Goal을 단정하지 않고, 도출된 Goal 후보를 사용자에게 제시하여 동의를 얻은 후 1줄로 확정합니다.

---

## 2. Fact(조사) vs Decision(결정) 분리 원칙

| 구분 | 🤖 **에이전트의 책임 (Fact Gathering)** | 👤 **사람의 책임 (Decision Making)** |
|---|---|---|
| **대상 영역** | • 저장소의 기존 디렉터리 및 모듈 구조<br>• 사용 중인 라이브러리 및 언어 버전<br>• 기존 함수 시그니처, 데이터 타입 정의<br>• `AGENTS.md` 및 프로젝트 규칙 문서 | • 이번에 해결하려는 핵심 고통과 사용자 가치<br>• **비목표(Non-goals)**: "절대 하지 않을 것"<br>• 예외 및 장애 발생 시 비즈니스 처리 정책<br>• 기술 대안 중 최종 트레이드오프 선택 |
| **철칙** | **코드베이스에 이미 존재하는 사실을 사용자에게 되묻지 않는다.** (도구로 직접 탐색) | **사람만이 결정할 수 있는 정책을 에이전트가 자의적으로 상상해 확정하지 않는다.** |

repository-specific Fact Gathering은 [Target Repository](github-workflow.md)가 확정된 뒤에만 수행합니다. 대상이 없거나 여러 후보라면 Repository 선택을 먼저 요청하고, 저장소 없는 아이디어라면 No-Repo로 인터뷰합니다.

### 2.1 Decision-bearing Section Review Loop

Artifact 전체를 작성하기 전에, 현재 Frontier에서 사용자의 선택에 따라 Goal의 경계, 요구사항, 인터페이스, 실패 정책 또는 수용 기준이 달라지는 Decision만 Review합니다.

- 저장소에서 확인 가능한 Fact, 표현만 다듬는 문장, 사용자가 이미 명확히 확정한 Decision은 다시 묻지 않습니다.
- 독립적인 Decision은 한 라운드에 묶을 수 있지만, 한 Decision Card에는 하나의 Decision 또는 강하게 결합된 하나의 Decision cluster만 담습니다.
- Section Review는 작은 Decision의 이해와 방향을 확인하며, 완성된 Artifact 전체를 승인하는 Checkpoint 1·2를 대체하지 않습니다.

#### 3-way 응답 계약

사용자가 정확한 표제어 대신 같은 의미의 자연어로 답해도 의미에 따라 처리합니다.

1. **맞다**: 현재 Decision을 확정하고 다음 Frontier로 진행합니다.
2. **아니다**: 최상위 Goal을 유지하는 대안 2~3개와 각 트레이드오프를 제시한 뒤 다시 선택받습니다.
3. **무슨 소리인지 모르겠다**: 전문 용어를 줄이고 쉬운 예시와 선택별 차이를 같은 Decision Card의 핵심 불릿 안에서 설명한 뒤 같은 Decision을 다시 묻습니다.

사용자가 결정을 유보하거나 재설명 뒤에도 선택하지 못하면 임의 확정하지 않고 `Open Question` 또는 미승인 `Assumption`으로 남깁니다.

#### Decision Card 표시 계약

```markdown
### 결정할 것

[한 문장 Decision]

- [핵심 배경 또는 차이 1]
- [핵심 배경 또는 차이 2]
- [핵심 배경 또는 차이 3 — 필요한 경우에만]

### 추천

- [추천안과 이유 1줄]

### 선택

1. 추천대로 진행
2. 다른 방식 보기
3. 예시로 다시 설명
```

- 핵심 불릿은 최대 3개, 각 1줄로 제한합니다.
- 쉬운 재설명도 카드 밖의 별도 서문이나 목록으로 만들지 않고 핵심 불릿에 포함합니다.
- 사용자 선택에 필요하지 않은 대상 파일, 검증 명령, 내부 프로토콜은 카드에 나열하지 않습니다.
- 실제 식별자가 선택에 필요할 때만 인라인 코드 표현을 사용합니다.

#### Stage Mode 적용

- `intent-only`: Intent Decision Review와 Checkpoint 1까지만 수행합니다.
- `spec-from-intent`: 승인된 Intent의 유효성을 확인한 뒤 Spec Decision Review와 Checkpoint 2를 수행합니다.
- `full-flow`: Intent와 Spec 각각에서 Section Review 후 기존 Checkpoint를 수행합니다.

---

## 3. Upstream Skill 라우팅 및 Fallback 계약

### 3.1 라우팅 기준

- **`ROUTE-A` (No-Repo / Pure Idea)**:
  - 저장소가 없거나 단순한 아키텍처/개념 정리.
  - Upstream `grill-me` 또는 `grilling` 호출.
- **`ROUTE-B` (Repo-Aware / Single-Session Feature — 기본 경로)**:
  - 현재 저장소가 존재하며, 단일 세션에서 설계 가능한 일반 기능.
  - 코드베이스 Fact 탐색 ➔ `grilling` 인터뷰 (필요 시 `grill-with-docs` 연계).
- **`ROUTE-C` (Multi-Session / Heavy Effort)**:
  - 단일 세션 범위를 초과하는 거대하고 불명확한 에포트.
  - 무리하게 `spec.md` 작성을 강행하지 않고 `wayfinder` 후보로 안내하여 decision-ticket map을 먼저 정리한 뒤 intent로 복귀.

### 3.2 Upstream 부재 시 Fallback Interview Contract

실행 환경에 Matt Pocock upstream skills가 설치되어 있지 않거나 크로스 스킬 호출이 지원되지 않는 경우, 에이전트는 다음 자체 계약으로 인터뷰를 진행합니다:

1. **Frontier 단위 질의**:
   - 인위적인 질문 수 제한(3~4개 등)을 두지 않는다.
   - 선행 질문에 종속되지 않은 현재의 미결정 항목(Frontier)을 1 라운드로 묶어 질문한다.
   - 사용자의 답변을 반영한 뒤 다음 Frontier를 계산하여 후속 질문을 이어간다.
2. **핵심 3대 필수 확인 축**:
   - ① **비목표(Non-goals)**: 이번 스코프에서 확실히 뺄 것은 무엇인가?
   - ② **장애/경계 시나리오(Edge Cases)**: 외부 호출 실패나 빈 값 입력 시 기대 동작은 무엇인가?
   - ③ **수용성 기준(Acceptance Criteria)**: 성공 여부를 판정할 구체적 테스트 커맨드나 기준은 무엇인가?
3. **미해결 사항 처리**:
   - 사용자가 결정을 유보하거나 불명확한 항목은 임의로 확정하지 않고 `Open Questions` 또는 `Assumptions`로 명시한다.

---

## 4. Stage Checkpoints

Checkpoint 1은 [Intent](intent-guide.md), Checkpoint 2는 [Spec](spec-guide.md)의 전체 내용 승인이다. Section Review는 이를 대체하지 않는다. 각 Stage 전체 완성 후 자동 ELI5를 한 번 제공하고 Content Approval을 받는다. 사용자의 명시적 ELI5 요청은 인터뷰 중에도 수행할 수 있으나 Stage 완료·승인 상태를 자동 변경하지 않는다. 저장은 별도 Persistence Approval 후 Stage 단위로 수행한다. intent-only도 승인·저장 선택과 상태 안내 후 종료한다.

---

## 5. Intent ➔ Spec 추적성(Traceability) 규칙

- **기반 헤더 필수**: `spec.md` 상단에는 반드시 `- 기반 Intent: [`intent.md`](intent.md)` 링크를 표기합니다.
- **요구사항 매핑**: `spec.md`의 각 핵심 요구사항(`REQ-xx`)은 최소 하나 이상의 `intent.md` Goal, Constraint 또는 확인된 Fact에 추적 가능해야 합니다.
- **비목표 침범 금지**: `intent.md`의 Non-goals에 명시된 항목이 `spec.md`의 요구사항이나 아키텍처에 은근슬쩍 포함되어서는 안 됩니다.

---

## 6. 라이선스 고지 (License Attribution)

본 Skill의 인터뷰 및 라우팅 설계는 Matt Pocock의 [skills](https://github.com/mattpocock/skills) 저장소(`grilling`, `grill-me`, `wayfinder`)의 아이디어와 개념을 참고 및 활용하였습니다.

```text
MIT License
Copyright (c) Matt Pocock
Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:
The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.
```

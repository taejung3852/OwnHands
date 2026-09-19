# Intent: grill-spec Section Review Loop

- **작성자**: 박태정 (@taejung3852) & Codex
- **일자**: 2026-09-20
- **상태**: Approved — 사용자 확인 (2026-09-20)
- **관련 Issue**: [#142](https://github.com/taejung3852/OwnHands/issues/142)

---

## 1. 문제 및 배경 (Why)

- **현재 상황과 고통**:
  - 현재 `grill-spec`은 GORE Anchor, Fact Gathering, Decision 인터뷰, `intent.md`/`spec.md` 작성, 두 번의 Human Checkpoint를 제공한다.
  - 그러나 각 Artifact를 완성한 뒤 전체를 검토하는 Checkpoint만 있고, 주요 결정을 문서에 반영하기 전에 사용자가 그 의미와 트레이드오프를 이해했는지 확인하는 명시적 상호작용 계약은 없다.
  - 이 때문에 사용자가 이해하지 못한 결정이 초안에 들어간 뒤 전체 검토 단계에서 뒤늦게 발견되거나, 에이전트 제안을 사용자의 결정처럼 취급할 수 있다.
- **대상 사용자 (페르소나)**:
  - AI가 대신 결정하는 문서를 받는 것이 아니라, 기획·설계의 핵심 선택을 이해하고 직접 확정한 뒤 Build로 넘기려는 AI-Native 소프트웨어 엔지니어.

## 2. 목표 결과 및 가치 (What)

- **최상위 목표**:
  > **사용자가 기획·설계의 주요 결정을 이해하고 직접 소유하게 하되, 코드베이스 Fact 재확인이나 불필요한 질문으로 `grill-spec` 흐름을 무겁게 만들지 않는다.**
- **달성하고자 하는 결과**:
  - `intent.md`와 `spec.md`의 실제 Decision-bearing section을 작성하기 전에 사용자의 이해와 방향을 확인한다.
  - 사용자의 반응을 `맞다`, `아니다`, `무슨 소리인지 모르겠다`의 세 경로로 처리한다.
  - 코드베이스에서 확인 가능한 Fact는 Review 대상으로 만들지 않는다.
  - Section Review를 작은 결정 확인으로, 기존 Human Checkpoint를 완성된 Artifact 전체 승인으로 유지한다.
- **성공 기준**:
  - 명확한 Decision에만 Section Review가 적용되고 Fact에는 승인을 요구하지 않는다.
  - `맞다`면 결정을 기록하고 다음 미결정 항목으로 진행한다.
  - `아니다`면 같은 Goal을 유지하는 대안 2~3개와 트레이드오프를 제시한 뒤 다시 선택받는다.
  - `무슨 소리인지 모르겠다`면 쉬운 언어, 짧은 예시, 선택별 차이로 다시 설명한 뒤 같은 선택을 재확인한다.
  - 사용자가 결정하지 못한 항목은 임의 확정하지 않고 Open Question 또는 Assumption으로 남긴다.
  - 사용자에게는 한 번에 하나의 Decision Card만 보여주고, 핵심 설명과 선택지를 시각적으로 분리한다.
  - 기존 Checkpoint 1·2와 Thin Orchestration 원칙이 유지된다.

## 3. 비목표 (Non-goals & Boundaries)

> ⚠️ **과잉 상호작용 방지**: 이번 작업에서 의도적으로 하지 않는 것

- [ ] 모든 문장이나 고정된 모든 문서 섹션을 사용자에게 승인받기
- [ ] 코드·설정·문서에서 확인 가능한 Fact를 사용자에게 되묻기
- [ ] 질문 수나 Review 횟수를 인위적으로 늘리기
- [ ] 기존 Human Checkpoint를 Section Review로 대체하기
- [ ] 새로운 Agent, Runner, Hook 또는 인터뷰 프레임워크 만들기
- [ ] `plan.md` 작성 단계까지 같은 Review Loop를 확장하기
- [ ] 사용자가 이해하지 못하거나 유보한 결정을 에이전트가 대신 확정하기

## 4. 핵심 제약 조건 (Constraints)

- **Decision 기반 적용**: Review 대상은 섹션 이름으로 고정하지 않고, 사용자 선택에 따라 결과가 달라지는 Decision 단위로 판별한다.
- **Thin Skill 본문**: `SKILL.md`에는 Section Review의 존재, 적용 경계, Checkpoint와의 관계만 두고 상세 3-way 프로토콜은 `references/interview-guide.md`에 둔다.
- **기존 계약 보존**: ADR-0004의 Artifact 규격과 ADR-0006의 Fact/Decision 분리, Stage Mode, Default Barrier를 유지한다.
- **Plan 범위 제외**: 이번 #142에서는 Intent/Spec 흐름만 다루며 `plan.md` 재사용 여부는 실제 관측 후 별도로 판단한다.
- **정직한 상태 기록**: Section Review에서 확정된 Decision과 미해결 Open Question/Assumption을 Artifact에서 구분한다.
- **가독성 우선**: 사용자 메시지는 `결정할 것 → 핵심 불릿 → 추천 → 선택` 순서의 Decision Card로 제시한다. 핵심 불릿은 최대 3개, 각 1줄로 제한하고 구현·검증 세부사항을 같은 위계에 섞지 않는다.

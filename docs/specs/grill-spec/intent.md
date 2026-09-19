# Intent: grill-spec (GORE·인터뷰 기반 intent/spec 도출 도우미 Skill)

- **작성자**: 박태정 (@taejung3852) & Antigravity
- **일자**: 2026-09-18
- **관련 Issue**: [#119](https://github.com/taejung3852/OwnHands/issues/119)
- **상위 마일스톤**: [V2-M2 — Plan & Design](https://github.com/taejung3852/OwnHands/milestone/15)

---

## 1. 문제 및 배경 (Why)

- **현재 상황과 고통**:
  - `ADR-0004`를 통해 `intent.md`와 `spec.md`의 정식 4대 필드 규격을 확정했으나, 개발자가 빈 템플릿을 마주하면 "무엇을 어떻게 적어야 할지" 막막함을 느낀다.
  - 반대로 AI 에이전트에게 단순 프롬프트로 스펙 작성을 맡기면, 코드베이스의 실제 맥락을 확인하지 않은 채 겉핥기식 요약을 하거나, 엣지 케이스와 제약 조건을 임의로 상상(환각)하여 쓸모없는 문서를 만든다.
  - 특히 **"코드베이스에서 확인 가능한 팩트(Fact)"**를 사람에게 되묻고, **"사람만이 결정할 수 있는 의도·경계·비목표(Decision)"**를 에이전트가 자의적으로 확정해 버리는 주객전도가 빈번하게 발생한다.
- **상호작용 구조의 한계와 해결 방향**:
  - 복잡한 기획 작업을 별도 서브에이전트에 격리하면 실시간 대화 흐름이 단절되기 쉽다.
  - 따라서 **의사결정 인터뷰는 메인 대화 세션의 Live HITL(Human-in-the-Loop)로 유지**하되, **코드베이스나 외부 문서의 팩트 수집은 필요에 따라 탐색 도구 및 Subagent에 유연하게 위임**하는 얇은 오케스트레이션(Thin Orchestration)이 필요하다.
- **대상 사용자 (페르소나)**:
  - 새 기능이나 변경 작업을 시작할 때, AI의 환각을 방지하고 요구사항의 경계와 기술 설계를 체계적으로 묶어두고 싶은 AI-Native 소프트웨어 엔지니어.

---

## 2. 목표 결과 및 가치 (What)

- **최상위 목표**:
  > **"사용자의 러프한 개발 의도를 GORE의 최상위 Goal에 연결하고, 코드베이스의 확인된 사실과 사용자의 결정을 명확히 분리하면서, OwnHands 표준 `intent.md`와 `spec.md`를 신뢰할 수 있게 도출한다."**
- **달성하고자 하는 결과**:
  - GORE(목표 닻 내리기), Matt Pocock의 grilling(frontier 기반 심문 인터뷰), 팩트 탐색을 결합한 공식 도우미 Skill `.agents/skills/grill-spec/SKILL.md` 구축.
  - 작업 규모와 환경에 따라 최적의 인터뷰 경로를 라우팅(Route)하고,
  - 단계별 Human Checkpoint를 거쳐 `intent.md` ➔ `spec.md` 초안을 사람과 함께 완성하는 표준 워크플로우 확립.
- **성공 기준**:
  - 러프한 요구사항이 주어졌을 때 의도 닻 내리기 ➔ 팩트 탐색 ➔ 프론티어 인터뷰 ➔ 검토 체크포인트를 거쳐 ADR-0004 4대 필드를 만족하는 산출물이 도출되는가.
  - 코드베이스 팩트(Agent 책임)와 의사결정(User 책임)이 엄격히 분리되는가.
  - Upstream 외부 도구 유무와 무관하게 자체 Fallback으로 정상 완결되는가.

---

## 3. 비목표 (Non-goals & Boundaries)

> ⚠️ **과잉 엔지니어링 방지 및 역할 경계**: 이번 작업에서 의도적으로 하지 않는 것
- [ ] **Matt Pocock upstream skills의 완전한 자체 재구현 금지**: upstream의 좋은 primitive(grilling 등)를 재사용하거나 최소 fallback contract만 두며, 불필요한 바퀴를 다시 발명하지 않는다.
- [ ] **에이전트의 미해결 결정 자의적 확정 금지**: 사람이 확정하지 않은 결정은 에이전트가 임의로 확정하지 않고 Open Question이나 Assumption으로 남긴다.
- [ ] **모든 기능에 Wayfinder 강제 실행 금지**: 한 세션에 끝나는 일반적인 기능에 heavy한 decision-ticket map 도구(wayfinder)를 무차별 적용하지 않는다.
- [ ] **M3(Build) 코드 구현 영역 침범 금지**: 본 스킬은 기획(Plan) 및 설계(Design) 산출물 도출까지만 책임지며, 코드 구현이나 브랜치 자동화는 다루지 않는다.

---

## 4. 핵심 제약 조건 (Constraints)

- **플랫폼 / 환경 제약**: Codex REPO scope (`.agents/skills/grill-spec/SKILL.md`), 10,000 토큰 카탈로그 예산 보호를 위해 `description`은 1~2문장으로 간결화하고 깊은 지침은 `references/`로 분리.
- **규격 준수**: 산출물은 `ADR-0004`([`docs/specs/README.md`](../README.md))의 4필드 규약을 100% 만족해야 함.
- **라이선스 준수**: Matt Pocock upstream skills의 개념이나 프롬프트를 실질적으로 인용/흡수하는 경우 MIT License attribution 조건을 준수함.

---
name: grill-spec
description: Sharpens development intent and technical specifications into OwnHands intent.md and spec.md artifacts through GORE goal anchoring, codebase fact gathering, and frontier grilling. Use when planning features, defining requirements, designing architectures, or explicitly invoked as $grill-spec.
---

# grill-spec

새로운 기능이나 변경 작업을 기획·설계할 때 호출한다. 사용자의 개발 의도를 **GORE(목표 지향 요구공학) 최상위 Goal**에 닻 내리고, **Fact(코드베이스 사실)**와 **Decision(사용자 의사결정)**을 엄격히 분리하여 `docs/specs/<feature-name>/` 아래에 `intent.md`와 `spec.md`를 도출한다.

## 3가지 실행 모드 (Stage Modes)

사용자의 요청 자연어에 따라 모드를 유연하게 선택한다:
1. **`intent-only` 모드** (*"intent만 잡아줘"*, *"의도 먼저"*): GORE 닻 내리기 ➔ Grilling ➔ `intent.md` 생성 후 종료 (Stage 1 Plan 완결).
2. **`spec-from-intent` 모드** (*"기존 intent로 spec 만들자"*): 기존 `intent.md` 로드 ➔ 현재 Intent 유효성 확인 ➔ Fact Gathering ➔ Grilling ➔ `spec.md` 생성 (Stage 2 Design 완결).
3. **`full-flow` 모드** (기본): Intent 도출 ➔ Checkpoint 1 ➔ 승인 후 Spec 도출.

## 9단계 실행 프로토콜

1. **Route (경로 결정)**:
   - `Route A (No-Repo / Simple Idea)`: 순수 개념 ➔ `grill-me` / `grilling` 호출 또는 fallback 인터뷰.
   - `Route B (Repo-Aware / Single-Session Feature)`: 일반 기능 (기본) ➔ `grilling` 인터뷰 + repository fact exploration.
   - `Route C (Multi-Session / Heavy Effort)`: 대형 과제 ➔ `wayfinder` 후보 안내 (decision map 분할 후 intent로 복귀).
2. **GORE Anchor (목표 닻 내리기)**:
   - 사용자의 입력에서 최상위 Goal 후보를 도출하고, 불명확하면 Grilling으로 확인하여 1줄 Anchor로 확정한다.
3. **Fact Gathering (팩트 탐색 — Agent 책임)**:
   - 현재 실행 환경의 도구(search/read)로 코드·설정·문서를 직접 조사한다. 코드에 이미 있는 팩트를 사용자에게 되묻지 않는다.
4. **Grilling (심문 인터뷰 — User 결정 도출)**:
   - 질문 수에 인위적 숫자 제한을 두지 않고, 의존성이 풀린 frontier를 1 round 단위로 질문한다.
   - 비목표(Non-goals), 실패 시나리오, 엣지케이스 등 사람만이 내릴 수 있는 Decision을 묻는다.
   - 결과가 달라지는 Decision-bearing section은 초안에 반영하기 전에 Section Review한다. Fact나 사용자가 이미 명확히 확정한 Decision은 다시 묻지 않는다.
   - Review와 쉬운 재설명은 한 Decision Card 안에 `결정할 것 → 핵심 불릿 → 추천 → 선택`만 보여준다. 선택은 동의, 대안 요청, 쉬운 재설명의 3-way로 처리하며 기존 Artifact Checkpoint를 대체하지 않는다.
5. **intent.md Draft**:
   - Why, What, Non-goals, Constraints 4대 필드를 `docs/specs/<feature-name>/intent.md`로 작성한다.
6. **Human Checkpoint 1 (Default Barrier)**:
   - 사용자 확인을 기다리며, 승인되지 않은 Intent를 확정된 근거로 취급해 Spec 작성을 직행하지 않는다.
7. **Spec Fact & Decision Review**:
   - 승인된 Intent를 기준으로 Spec에 필요한 코드베이스 Fact를 조사한다.
   - 인터페이스, 실패 정책, 수용 기준처럼 Spec에서 새로 생기는 Decision-bearing section을 같은 Section Review 계약으로 확인한다.
8. **spec.md Draft**:
   - 승인된 Intent와 수집된 팩트를 기반으로 Requirements, Architecture, Edge cases, Acceptance criteria를 `docs/specs/<feature-name>/spec.md`로 작성한다. 상단에 `- 기반 Intent: intent.md` 헤더를 반드시 유지한다.
9. **Human Checkpoint 2**:
   - 작성된 `spec.md`에 대해 사용자의 엔지니어링 검토 및 승인을 받는다.

Section Review 대상 판별과 3-way 처리, 세부 인터뷰 지침, Upstream 도구 fallback 계약, 추적성 매핑 규칙은 `references/interview-guide.md`를 참고한다.

# Spec: grill-spec Section Review Loop

- **기반 Intent**: [`intent.md`](intent.md)
- **작성 주체**: AI 에이전트 분석 (사람 검토 및 승인 필요)
- **일자**: 2026-09-20
- **상태**: Approved — 사용자 확인 (2026-09-20)
- **관련 Issue**: [#142](https://github.com/taejung3852/OwnHands/issues/142)

---

## 1. 기술적 요구사항 (Requirements)

- `REQ-01` — `grill-spec`은 Artifact 초안을 완성하기 전, 현재 Frontier에서 사용자 선택에 따라 결과가 달라지는 주요 Decision을 식별해야 한다.
- `REQ-02` — 저장소·설정·기존 문서에서 확인 가능한 Fact, 사용자가 입력에서 이미 명확히 확정한 Decision, 표현만 다듬는 문장은 Section Review 대상으로 만들지 않아야 한다.
- `REQ-03` — Decision Review는 다음 의미 기반 3-way 응답을 처리해야 한다. 사용자가 정확한 표제어 대신 동등한 자연어로 답해도 같은 의미로 분류한다.
  1. **맞다**: 현재 Decision을 확정하고 다음 Frontier로 진행한다.
  2. **아니다**: 최상위 Goal을 유지하는 대안 2~3개와 각 트레이드오프를 제시한 뒤 다시 선택받는다.
  3. **무슨 소리인지 모르겠다**: 쉬운 언어, 짧은 예시, 선택에 따른 차이로 다시 설명한 뒤 같은 Decision을 재질문한다.
- `REQ-04` — 사용자가 결정을 유보하거나 반복 설명 뒤에도 선택하지 못하면 에이전트가 임의 확정하지 않고 `Open Question` 또는 `Assumption`으로 표시해야 한다. Assumption은 승인된 Decision처럼 취급하지 않는다.
- `REQ-05` — Section Review는 기존 Checkpoint를 대체하지 않는다. Section Review는 개별 Decision의 이해·방향 확인이고, Checkpoint 1·2는 완성된 Artifact 전체의 최종 승인이다.
- `REQ-06` — 세 Stage Mode에 다음과 같이 적용한다.
  - `intent-only`: Intent의 Decision Review와 Checkpoint 1까지만 수행한다.
  - `spec-from-intent`: 승인된 Intent의 유효성을 확인하고 Spec의 Decision Review와 Checkpoint 2를 수행한다.
  - `full-flow`: Intent와 Spec 각각의 Decision Review 및 Checkpoint를 순서대로 수행한다.
- `REQ-07` — 상세 3-way 절차와 예시는 `references/interview-guide.md`에 두고, `SKILL.md`에는 적용 조건·핵심 분기·Checkpoint 관계만 유지한다.
- `REQ-08` — 이번 변경은 `plan.md` Review, 새 Agent, Runner, Hook, 별도 인터뷰 기록 Artifact를 추가하지 않는다.
- `REQ-09` — Section Review 질문은 한 번에 하나의 Decision Card로 제시한다. 카드의 기본 순서는 `결정할 것 → 핵심 불릿 → 추천 → 선택`이다. 핵심 불릿은 최대 3개, 각 1줄로 제한하고 구현·검증 세부사항은 사용자 선택과 같은 시각적 위계에 섞지 않는다.

## 2. 시스템 아키텍처 및 인터페이스 (Architecture & Interfaces)

### 2.1 대상 파일 및 책임

- `[MODIFY] .agents/skills/grill-spec/SKILL.md`
  - 8단계 프로토콜의 Grilling과 Draft 사이에 Decision-bearing section Review를 명시한다.
  - 상세 분기 처리를 `references/interview-guide.md`로 라우팅한다.
- `[MODIFY] .agents/skills/grill-spec/references/interview-guide.md`
  - Section Review 대상 판별, 3-way 응답, 미결정 처리, Checkpoint와의 관계를 상세 계약으로 정의한다.
- `[MODIFY] docs/specs/README.md`
  - Section Review와 Artifact Checkpoint의 역할 차이를 생명주기 안내에 짧게 추가한다.
- `[MODIFY] docs/adr/0006-grill-spec-orchestration-tradeoffs.md`
  - 기존 Thin Orchestration과 Default Barrier를 유지하면서 Section Review를 추가한 후속 결정을 기록한다.
- `[MODIFY] docs/decisions.md`
  - `grill-spec` 확정 방향에 Decision-bearing Section Review와 3-way 계약을 추가한다.
- `[MODIFY] docs/evals/task-set.json`
  - 기존 `EVAL-0004`의 정적 계약에 Section Review 핵심 표식을 추가한다. 새 Eval 과제나 Runner는 만들지 않는다.
- `[NEW] docs/specs/grill-spec-section-review/plan.md`
  - 승인된 Spec을 구현 Task와 Fresh Evidence에 연결한다.

### 2.2 Decision Review 상태 흐름

```text
현재 Frontier의 미확정 Decision 식별
        ↓
제안 + 이유 + 선택 시 차이 설명
        ↓
사용자 반응의 의미 분류
  ├─ 맞다      → Confirmed Decision → 다음 Frontier
  ├─ 아니다    → 대안 2~3개 + Trade-off → 재질문
  ├─ 모르겠다  → 쉬운 설명 + 예시 + 차이 → 재질문
  └─ 유보      → Open Question / Assumption 표시
        ↓
Artifact Draft 완성
        ↓
기존 Human Checkpoint에서 전체 승인
```

### 2.3 Review 대상 판별 규칙

Section Review는 고정 섹션 목록이 아니라 다음 질문으로 판별한다.

> 이 선택이 달라지면 Goal의 경계, 요구사항, 인터페이스, 실패 정책 또는 수용 기준이 실질적으로 달라지는가?

- **예**: Review 대상 Decision.
- **아니오**: Fact 또는 편집 세부사항으로 처리하고 승인 질문을 만들지 않는다.
- 서로 독립적인 Decision은 기존 Frontier 규칙에 따라 한 라운드로 묶을 수 있지만, 사용자가 이해하기 어려울 정도로 여러 선택을 한 질문에 압축하지 않는다.

### 2.4 기존 계약과의 호환성

- ADR-0004의 Intent/Spec 4대 필드와 저장 위치는 바꾸지 않는다.
- ADR-0006의 Thin Orchestration, Fact/Decision 분리, Stage Mode, Default Barrier를 유지한다.
- 사용자가 최초 요청에서 명확히 확정한 Decision은 다시 승인받지 않고 Artifact에 반영한다.
- Section Review 결과를 위한 새 로그 파일이나 상태 저장 형식은 만들지 않는다.

### 2.5 Decision Card 표시 계약

```markdown
### 결정할 것
[한 문장으로 표현한 Decision]

- [핵심 배경 또는 차이 1]
- [핵심 배경 또는 차이 2]
- [핵심 배경 또는 차이 3 — 필요한 경우에만]

**추천**
[추천안과 이유 한 문장]

**선택**
1. 추천대로 진행
2. 다른 방식 보기
3. 예시로 다시 설명
```

- 한 카드에는 하나의 Decision 또는 서로 강하게 결합된 하나의 Decision cluster만 담는다.
- 핵심 설명은 서술형 문단 대신 최대 3개의 1줄 불릿으로 제시한다.
- 사용자에게 당장 필요하지 않은 대상 파일, 검증 명령, 내부 프로토콜은 카드 본문에 나열하지 않는다.
- 코드 식별자가 실제 선택에 필요할 때만 인라인 코드 표현을 사용한다.
- 선택 문구는 문맥에 맞게 구체화할 수 있지만 `동의 / 대안 / 재설명`의 세 의미는 유지한다.

## 3. 엣지 케이스 및 예외 처리 (Edge Cases)

| 시나리오 | 기대 동작 |
|---|---|
| 한 섹션에 Fact와 Decision이 섞여 있음 | Fact는 조사 결과로 알리고, 결과를 바꾸는 Decision만 분리해 질문한다. |
| 사용자가 `좋아`, `그걸로 하자`처럼 답함 | 정확한 단어 일치를 요구하지 않고 `맞다` 의미로 처리한다. |
| 사용자가 `아니다`만 말함 | Goal을 유지하는 대안 2~3개와 트레이드오프를 먼저 제시하고 재질문한다. |
| 사용자가 설명을 이해하지 못함 | 용어를 줄이고 작은 실제 예시와 선택별 결과 차이로 다시 설명한다. |
| 설명 후에도 결정을 유보함 | Open Question 또는 미승인 Assumption으로 남기고 확정 사실처럼 쓰지 않는다. |
| 사용자 입력에 이미 선택이 명시됨 | 같은 결정을 다시 묻지 않고 확인된 사용자 Decision으로 사용한다. |
| Decision이 없는 단순 변경 | Section Review를 억지로 만들지 않고 기존 Checkpoint만 적용한다. |
| Section Review는 통과했지만 전체 문서를 거절함 | 해당 Artifact를 수정하고 기존 Checkpoint에서 다시 전체 승인을 받는다. |
| 한 화면에 여러 기술 결정과 검증 정보가 함께 있음 | 현재 Decision 하나만 카드에 남기고 나머지는 다음 Review나 Artifact 본문으로 이동한다. |

## 4. 수용성 기준 및 검증 계획 (Acceptance Criteria)

### 4.1 수용성 기준

- [ ] `AC-01` — `SKILL.md`가 Decision-bearing section만 Review하며 Fact는 재질문하지 않는다고 명시한다.
- [ ] `AC-02` — `interview-guide.md`가 `맞다 / 아니다 / 무슨 소리인지 모르겠다`의 세 의미 분기와 재질문 동작을 정의한다.
- [ ] `AC-03` — 미해결 Decision을 Open Question 또는 Assumption으로 남기고 임의 확정하지 않는 계약이 존재한다.
- [ ] `AC-04` — Section Review와 Checkpoint 1·2의 역할이 구분되고 기존 Checkpoint가 유지된다.
- [ ] `AC-05` — 세 Stage Mode에서 Section Review의 적용 범위가 명확하다.
- [ ] `AC-06` — Skill 본문은 얇게 유지되고 상세 프로토콜은 기존 Reference에만 추가된다.
- [ ] `AC-07` — `docs/specs/README.md`, ADR-0006, `docs/decisions.md`가 새 계약과 모순되지 않는다.
- [ ] `AC-08` — 기존 EVAL-0004 정적 검사가 새 핵심 계약을 포함하며 Static Preflight 회귀가 0건이다.
- [ ] `AC-09` — 단일 read-only Runtime 관측에서 모호한 설명에 대한 사용자 반응을 가정하지 않고 3-way 확인을 제시하는 동작이 관측된다.
- [ ] `AC-10` — 새 Agent, Runner, Hook, plan Review 체계가 추가되지 않는다.
- [ ] `AC-11` — Section Review가 `결정할 것 → 핵심 불릿 → 추천 → 선택` 구조의 단일 Decision Card로 표시되고, 핵심 불릿은 최대 3개·각 1줄이며 긴 동일 위계 목록이나 불필요한 코드 강조를 만들지 않는다.

### 4.2 검증 계획

```bash
git diff --check
node scripts/run-evals.js --static-only

codex exec --json --sandbox read-only \
  '$grill-spec을 사용해 작은 기능의 요구사항을 정리해줘. 사용자가 결정해야 할 핵심 정책은 설명하되 아직 사용자의 선택은 주어지지 않았다. 파일은 수정하지 마.'
```

- Runtime 관측은 전체 Eval Suite가 아니라 위 단일 핀포인트 실행만 사용한다.
- 실행 전후 Git 상태가 동일해야 한다.
- 출력에서 Fact를 승인 질문으로 만들지 않고, Decision에 대해 이해 가능한 제안과 3-way 확인을 제시해야 한다.

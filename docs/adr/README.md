# OwnHands ADR — 주제별 결정과 현재 적용 상태

**현재 집중: SDLC의 Build·Test 재설계 — ADR-0013·0014·0018.**

Chat Plan & Design은 [PR #160](https://github.com/taejung3852/OwnHands/pull/160)으로 main에 반영한 기준점이다. 다음 작업은 첫 E2E 회고를 바탕으로 구현·실패 복구·테스트·독립 검증의 연결을 개선하는 것이다. ADR-0015의 자동 Hook/Gate 정리와 ADR-0016의 기록 분류는 후순위다.

- **구현 확인 기준:** `main@cbce2d47332bd051a474102ea8cce6b3f21c2190`. 이때 `develop@eb21ce9913e526feda51d04045aceb0bf1cac1de`와 파일 트리는 같다.
- **우선순위 근거:** PR #160 이후 사용자 결정 — Build·Test와 외부 Skill 활용을 함께 검토하고, 0015·0016은 나중에 진행한다.
- **진행 연결:** [Issue #154](https://github.com/taejung3852/OwnHands/issues/154) · [첫 E2E 회고](../feedback/2026-09-22-first-e2e-retrospective.md) · [현재 Chat Plan & Design Spec](../specs/chat-plan-design-flow/spec.md).

## 이 인덱스를 읽는 방법

| 구분 | 읽을 내용 | 확인할 근거 |
|---|---|---|
| **당시 결정** | 무엇을 선택했고 어떤 대안을 검토했는가 | 해당 ADR의 Context·Decision·변경 이력 |
| **현재 적용** | 그 결정 중 무엇이 유지·조정·대체됐고 어떤 자산이 남았는가 | 아래 표의 현재 파일과 후속 ADR·Spec |
| **실제 관측** | 어떤 버전·시나리오에서 무엇을 확인했는가 | PR·Evidence·사용자 dogfooding 기록 |

`Accepted`는 결정 승인 상태다. 파일 존재, 구현 반영, 실제 실행 성공은 각각 구분한다. 아래의 **유지 / 일부 조정 / 대체 / 후속 예정**은 현재 관계를 설명하는 말이며, 원본 ADR의 공식 상태를 일괄 변경한 것이 아니다.

오래된 ADR에 있는 “구현 미진행”은 그 기록 시점의 상태다. 현재 흐름은 후속 결정을 함께 읽는다. 결정이 바뀌었더라도 과거 맥락과 실패 기록은 남긴다.

## 먼저 구분할 과거와 현재

| 과거 문서에서 보이는 이름·방식 | 현재는 어떻게 읽는가 |
|---|---|
| **`explain`으로 시각 설명** | **Chat Plugin의 승인 설명은 ELI5**가 맡는다. 다만 Codex 쪽 [explain Skill](../../.agents/skills/explain/SKILL.md)과 reference는 아직 존재한다. “Chat에서 ELI5 사용”과 “Codex explain 삭제 완료”는 다르다. Core·Companion 정리는 0018에서 이어간다. |
| **`grill-spec`으로 기획·설계** | 기존 Skill은 제거되고 [Chat `plan-design`](../../plugins/ownhands/skills/plan-design/SKILL.md)으로 이전됐다. GORE·Fact/Decision·Stage 구분은 이어지며, 현재 라우팅은 후속 Spec과 PR #159를 따른다. |
| **OwnHands MCP로 작성 Skill 제공** | 현재 결정은 **Skills-only Plugin + 기존 GitHub 연결 도구**다. `0012-authoring-skills-via-ownhands-mcp.md` 파일명은 참조 호환성을 위해 남았지만 본문은 Skills-only다. |
| **모든 구현에 `plan.md`가 필요한 흐름** | 현재는 **Light / Planned**로 나눈다. `plan.md`는 Planned의 승인된 구현 계획이고, Light는 요청·diff·적용 가능한 검증으로 진행한다. |
| **단일 Verifier / 자동 Gate 제거 방향** | 후속 결정과 현재 구현을 구분한다. 지금은 `verify`·`review`, `verifier`·`reviewer`, OwnHands Hook/Gate가 남아 있다. 통합은 이번 검토, Gate 정리는 후순위다. |

## 주제별 ADR

한 ADR이 여러 단계에 걸칠 수 있다. 아래는 주된 읽기 위치이며, 각 행에서 후속 결정과 현재 자산으로 이동한다.

### Plan · Design — 의도·설계와 Chat 승인

| ADR | 당시 결정 | 현재 적용·남은 범위 | 현재 기준·근거 |
|---|---|---|---|
| [0004](0004-intent-spec-specification.md) | Intent와 Spec의 역할·저장 규격 | **기반 유지, 적용 경로 조정.** Chat이 기획·설계를 담당하며 작은 작업의 문서 생략은 후속 Light 계약으로 구체화됐다. | [작성 가이드](../specs/README.md), 0012·0013·0019 |
| [0006](0006-grill-spec-orchestration-tradeoffs.md) | 단일 grill-spec, GORE 인터뷰와 Stage Mode | **실행 Skill 대체.** grill-spec은 제거됐다. 유효한 인터뷰 원칙은 plan-design에 남고, 예전 ROUTE·도구 호출 규칙 전체를 현재 구현으로 간주하지 않는다. | [plan-design](../../plugins/ownhands/skills/plan-design/SKILL.md), [인터뷰](../../plugins/ownhands/skills/plan-design/references/interview-guide.md), [PR #159](https://github.com/taejung3852/OwnHands/pull/159) |
| [0012](0012-authoring-skills-via-ownhands-mcp.md) | Skills-only Chat Plugin, Chat 전용 plan-design, GitHub 도구 분리 | **구현 반영, 사용 사례 보고.** Chat Plugin과 Codex 설치 자산이 분리됐다. 모든 호스트의 정책 적용까지 실측 완료한 것은 아니다. | [Plugin](../../plugins/ownhands/plugin.json), [Spec REQ-01–06](../specs/chat-plan-design-flow/spec.md), [PR #160](https://github.com/taejung3852/OwnHands/pull/160) |
| [0017](0017-guided-planning-and-visual-approval.md) | GORE, 단계 표시, ELI5와 내용·저장 승인 분리 | **Chat Plugin에 핵심 UX 반영.** Intent 경로의 실행 보고가 있다. 남은 질문 수·예상 시간 표시와 모든 Spec 경로의 실측은 별도다. | [Intent checkpoint](../../plugins/ownhands/skills/plan-design/references/intent-guide.md), [Spec checkpoint](../../plugins/ownhands/skills/plan-design/references/spec-guide.md), [PR #160](https://github.com/taejung3852/OwnHands/pull/160) |

### Build · Test — 구현·실패 복구와 품질 확인

| ADR | 당시 결정 | 현재 적용·남은 범위 | 현재 기준·근거 |
|---|---|---|---|
| [0001](0001-initial-subagent-roles.md) | researcher·verifier·reviewer의 역할과 위임 | **기존 3역할이 남아 있다.** 0014의 단일 독립 검증 방향은 아직 구현에 반영되지 않았다. | [Agent 정의](../../.codex/agents/), 0014 |
| [0007](0007-plan-artifact-and-build-feedback-loop.md) | plan.md, SDD 기반 구현·검증 루프 | **Planned의 기반 유지.** 현재 Light는 plan.md를 요구하지 않는다. 계획·Task·조건부 TDD·증거 연결은 이번에 다시 검토한다. | [Build](../../.agents/skills/build/SKILL.md), [TDD](../../.agents/skills/build/references/tdd-loop.md), 0013 |
| [0008](0008-verification-references-and-verifier-protocol.md) | 검증 reference, Before/After, 독립 Evidence 감사 | **현재 Test의 기반.** verifier는 AC와 Evidence를 대조하는 감사 역할이며, 별도 review가 뒤따른다. Test의 책임·재검증 범위는 0014와 함께 설계한다. | [Verify](../../.agents/skills/verify/SKILL.md), [Verifier](../../.codex/agents/verifier.toml), 0014 |
| [0013](0013-build-planning-and-execution.md) | Build가 준비·실행을 연결하고 Light/Planned 분기 | **진입 분기 구현, 실행 흐름 재검토 대상.** Light 문서 작업 사례가 있지만 이를 Build 재설계 전체 완료로 보지 않는다. | [Build](../../.agents/skills/build/SKILL.md), [PR #158](https://github.com/taejung3852/OwnHands/pull/158), [E2E 회고](../feedback/2026-09-22-first-e2e-retrospective.md) |
| [0014](0014-single-independent-verification.md) | Verify·단일 독립 Verifier 중심 통합 | **방향 확정, 통합 구현 예정.** 요구 충족과 중요한 변경 위험 확인을 보존하며 검사·Finding·재검증·저장 계약을 정한다. | 현재 [Verify](../../.agents/skills/verify/SKILL.md)와 [Review](../../.agents/skills/review/SKILL.md)는 분리 상태 |

### Deploy · Governance — 외부 변경과 승인·통제

| ADR | 당시 결정 | 현재 적용·남은 범위 | 현재 기준·근거 |
|---|---|---|---|
| [0005](0005-policy-layering-boundary.md) | 가상 조직 정책 엔진 대신 네이티브 연결 안내 | **경계 결정 유지.** 실제 조직 정책 도입·검증은 별도이며 이번 Build·Test 검토의 선행 과제가 아니다. | 원문 0005의 적용 경계 |
| [0010](0010-review-human-ci-governance.md) | 별도 Review, diff-bound Evidence, Hook, Human Gate | **기존 구현이 남아 있다.** Review 통합은 0014, 자동 강제 장치 정리는 0015가 조정한다. 사람 승인·검증과 자동 차단 장치는 다른 책임이다. | [Review](../../.agents/skills/review/SKILL.md), [Hook](../../.codex/hooks.json), [Review Gate](../../scripts/review-gate.js) |
| [0015](0015-defer-automatic-ci-and-hook-enforcement.md) | OwnHands 자동 CI·Hook/Gate를 걷어내고 재설계 후순위 | **제거 방향 유지, 작업 후순위.** 현재 파일·설치 의존성은 남아 있다. 사용자 원래의 CI/Hook과 제품 검사는 별도다. | [Hook](../../.codex/hooks.json), [설치 계약](../installation.md) |

### Maintain · Evals — 사용 경험과 개선의 검증

| ADR | 당시 결정 | 현재 적용·남은 범위 | 현재 기준·근거 |
|---|---|---|---|
| [0009](0009-continuous-evals-task-set-and-runner.md) | Task Set·경량 Eval Runner·Baseline | **평가 자산 유지, 과제 일부 갱신.** 현재 EVAL-0004는 grill-spec 대신 Chat plan-design의 정적 계약을 확인한다. 정적 PASS와 Chat runtime PASS는 별개다. | [Task Set](../evals/task-set.json), [Runner](../../scripts/run-evals.js) |
| [0016](0016-artifact-classification-and-feedback.md) | 제품 요구·ADR·결함과 Harness 피드백을 저장 전에 분류 | **분류 정책 정렬은 후순위.** 기존 capture·triage·follow-up은 존재하지만, 모든 기록의 재분류가 끝난 것은 아니다. | [Feedback](../../.agents/skills/feedback/SKILL.md), [기록·전달 계약](../../.agents/skills/feedback/references/feedback-contract.md) |

### 공통 — 역할·협업 표현·Companion과 GitHub 상태

| ADR | 당시 결정 | 현재 적용·남은 범위 | 현재 기준·근거 |
|---|---|---|---|
| [0002](0002-explain-visual-story-cards.md) | OwnHands explain의 시각 설명 방식 | **Chat 설명 경로는 ELI5, Codex explain은 잔존.** 과거 explain 전용 구성과 현재 Companion 방향을 구분한다. ELI5 자체 수정이나 explain 삭제를 완료 처리하지 않는다. | [Codex explain](../../.agents/skills/explain/SKILL.md), [Chat ELI5](../../plugins/ownhands/skills/eli5/SKILL.md), 0018 |
| [0003](0003-work-item-human-brief.md) | Issue·PR의 Human Brief와 접힌 상세 | **표현 규칙과 Skill 유지.** 전용 Core 소유권과 함께 설치하는 편의는 0018에서 구분한다. | [write-issue-pr](../../.agents/skills/write-issue-pr/SKILL.md), 0018 |
| [0011](0011-chat-codex-ownership-and-handoff.md) | Chat 기획·설계 / Codex 구현·검증 | **역할 분리와 기본 인계 반영.** 당시 미결정이던 저장·인계 일부는 후속 Spec에 정해졌다. 전체 SDLC 재정렬은 진행 중이다. | [현재 Spec](../specs/chat-plan-design-flow/spec.md), [Handoff](../../plugins/ownhands/skills/plan-design/references/handoff-guide.md), 0019 |
| [0018](0018-core-and-companion-skills.md) | Core와 ELI5·Ponytail의 소유권·재사용·배포 분리 | **Chat ELI5 포함, Codex 활용 방식은 이번 검토.** 기존 원본 재사용 방향을 출발점으로 Superpowers 흡수 범위, Ponytail 흡수/원본 사용, 업데이트 평가·채택을 비교한다. 세부 선택·자동 업데이트는 미확정이다. | [ELI5 출처](../../plugins/ownhands/skills/eli5/UPSTREAM.md), 아래 진행 순서 |
| [0019](0019-github-centered-sdlc-and-stage-commits.md) | Issue optional, 단일 작업 Branch, 두 승인, Stage 저장·Reconcile | **기본 계약 반영, 저장 사례 보고.** 현재 경로 선택 시점·승인 의미는 후속 Spec과 GitHub reference를 따른다. 충돌·재연결 전체 실측은 별도다. | [GitHub workflow](../../plugins/ownhands/skills/plan-design/references/github-workflow.md), [현재 Spec](../specs/chat-plan-design-flow/spec.md), [PR #158](https://github.com/taejung3852/OwnHands/pull/158) |

## 지금 할 일과 다음에 할 일

### 지금 — Build·Test의 현재 모습과 목표 합의

1. [첫 E2E 회고](../feedback/2026-09-22-first-e2e-retrospective.md)의 5·6·7·8·13·14번을 현재 Build·Verify·Review와 대조한다. 계획 저장, 구현 중 테스트, 실패 복구, 독립 검증에서 유지할 것과 끊긴 곳을 찾는다.
2. **0013·0014·0018을 한 묶음으로 설계**한다. Superpowers에서 필요한 능력과 이미 흡수한 부분을 구분하고, Ponytail의 원칙 흡수 / 고정 revision 원본 / 원본과 얇은 연결 규칙을 비교한다. 채택 방식은 비교 후 합의한다.
3. Build 중 테스트, SDLC Test의 최종 품질 판단, OwnHands 행동 Eval을 구분한다. Light/Planned별 테스트 선택·재검증·완료 근거와 외부 Skill 후보의 비교 기준을 정한다.

### 다음 — 합의한 범위만 구현·평가·채택

승인된 설계를 작은 변경으로 구현하고 대표 실제 작업으로 dogfooding한다. 기존 방식과 변경한 방식의 요구 충족·회귀·재작업·시간/비용을 가능한 범위에서 비교한다. 충분한 근거가 생긴 범위를 develop에서 검토하고 main의 다음 기준점으로 올린다.

외부 Skill 업데이트는 **현재 채택 revision → 후보 변경 확인 → 별도 평가 → 결과 검토 → 채택 또는 현재판 유지** 흐름을 설계 대상으로 둔다. 주기적 모니터링·자동 평가는 후속 설계 대상이며, 이번 README 수정에서는 설정하지 않는다.

### 후순위 — 현재 방향을 보존하고 착수는 나중에

ADR-0015의 자동 Hook/Gate 정리와 ADR-0016의 기록 분류를 이어간다. Build·Test를 바꾸면서 현행 Gate와의 호환성이 문제가 되면 그 의존성만 먼저 확인하고, 별도 제거 작업의 범위를 함께 확정한다.

## 합의된 출발점과 근거 수준

**Light/Planned는 구현 계획 필요성과 위험으로 나눈다.** Light도 검증한다. Planned는 실제 Codex Plan Mode의 승인 결과를 쓰기 가능한 모드에서 plan.md로 보존한다. 독립 Verifier는 Light의 기본 의무가 아니다. 이는 0013과 현재 Build·Verify의 출발점이며 이번에는 그 내부 실행 품질을 재검토한다.

**0017의 핵심 적용 위치는 OwnHands Chat Plugin이다.** 인터뷰와 Intent/Spec reference가 ELI5·내용 승인·저장 선택을 연결한다. 예상 시간·남은 질문 표시 전체를 구현·실측 완료로 묶지 않는다.

[PR #160](https://github.com/taejung3852/OwnHands/pull/160)은 main 승격과 로컬 검사, 사용자 제공 Chat 실행 보고를 기록한다. Repository 확인 후 Fact 조회와 승인 UX의 관측은 해당 시나리오의 근거이며, 모든 모델·호스트에서의 성공이나 전체 SDLC 완료를 뜻하지 않는다. 이 인덱스 수정 중 제품 테스트나 Chat E2E를 새로 실행한 것은 아니다.

과거 회고·ADR·Feedback에는 당시의 MCP 전제, `grill-spec`, FAIL·UNOBSERVED가 남아 있을 수 있다. 해당 기록은 당시 근거로 보존하고, 후속 Spec·PR의 변경 및 관측을 함께 읽는다. 이 README는 원본 ADR의 재승인, Skill 삭제, Gate 제거 또는 전체 기록 이동을 수행하지 않는다.

# OwnHands ADR 인덱스

## 현재 결정 기록

- 기록일: 2026-09-22
- 관련 이슈: [#154 — 첫 E2E 회고와 책임 재정렬](https://github.com/taejung3852/OwnHands/issues/154)
- 문서 브랜치: `docs/e2e-feedback-decisions`
- 최초 조사 기준 main: `41d030cdfe5ecacb85e5649081aa3a74236323aa`
- [사용자 피드백 1~15번과 근거 수준](../feedback/2026-09-22-first-e2e-retrospective.md)
- **Chat Plan & Design:** [Intent](../specs/chat-plan-design-flow/intent.md) 승인·저장 완료 → [Spec](../specs/chat-plan-design-flow/spec.md) 사용자 내용·GitHub 저장 승인

이 브랜치는 E2E 회고·ADR과 후속 SDLC 설계의 승인 산출물을 보존한다. 이번 Spec 승인 커밋은 문서만 변경한다. 실행 코드, Skill, Hook, 설치기, Eval 구현이 완료됐다는 뜻은 아니다. PR·Merge·릴리스·마일스톤 종료도 수행하지 않는다.

ADR의 `Accepted`는 사용자 결정 상태이며 런타임 구현·검증 완료가 아니다. 확정되지 않은 플랫폼 지원 여부는 Spec 15절에서 기술 확인 대상으로 남긴다. 후속 구현에서 새 방향과 충돌하는 활성 지침을 승인된 변경 범위 안에서 정렬한다.

## E2E 이후 방향 — ADR-0011~0019

| ADR | 결정 | 사용자 피드백/후속 | 현재 상태 |
|---|---|---|---|
| [0011](0011-chat-codex-ownership-and-handoff.md) | ChatGPT는 기획·설계, Codex는 구현 준비·실행·검증 | 9-2, 10, 15 | 방향 유지 / 인계 계약은 승인 Spec·0019 참조 |
| [0012](0012-authoring-skills-via-ownhands-mcp.md) | Skills-only Agent Plugin, Chat 전용 plan-design, GitHub 저장 도구 분리 | 9-2 및 Spec 후속 결정 | Accepted / 구현·플랫폼 실측 미진행 |
| [0013](0013-build-planning-and-execution.md) | Build Light/Planned 진입, 사용자 Plan Mode 전환, 승인 계획 보존 | 5, 6, 7 및 Spec 후속 결정 | Accepted / Build·Light Verify 수정 미진행 |
| [0014](0014-single-independent-verification.md) | Verify Skill·독립 Verifier 중심으로 검증 통합 | 7, 8 | 통합 방향 유지 / 별도 후속 Build |
| [0015](0015-defer-automatic-ci-and-hook-enforcement.md) | 기존 자동 CI·Hook/Gate 제거 방향, 재설계·원인 조사 후순위 | 11, 12 및 후속 우선순위 결정 | 제거 방향 유지 / 별도 후속 Build |
| [0016](0016-artifact-classification-and-feedback.md) | 제품 요구·결정·결함과 OwnHands 피드백 분리 | 1, 7 | 분리 방향 유지 / 별도 후속 Build |
| [0017](0017-guided-planning-and-visual-approval.md) | 승인 직전 ELI5, 내용 승인과 저장 승인 분리, 단순 상태 표시 | 2, 3, 4, 10, 15 및 Spec | Accepted / UX 구현·실측 미진행 |
| [0018](0018-core-and-companion-skills.md) | Core와 ELI5·Ponytail의 소유권·배포 분리 | 9-1, 13, 14 | Chat ELI5는 이번 Spec / Codex 패키징 전체 계약은 후속 |
| [0019](0019-github-centered-sdlc-and-stage-commits.md) | Issue optional, 단일 Branch, 두 승인, Stage Commit, Reconcile, 가벼운 Handoff | Intent→Spec 사용자 결정 | Accepted / 승인 Spec에 정렬 |

## 이번 Spec의 목표 흐름

이 도식은 목표 구조이며 현재 런타임이 이미 이렇게 동작한다는 증거가 아니다.

```text
ChatGPT + Skills-only OwnHands Plugin
  plan-design Core + ELI5 Companion
  ↓
기존 관련 Issue/Branch 확인
  Issue 없음 → Issue 생성 / Branch만 생성 / 기획만 계속을 사용자에게 선택받음
  ↓
Intent 논의 → ELI5 → 내용 승인 → 저장 승인 → intent.md + 관련 ADR 일괄 Commit
  ↓
Spec 논의 → ELI5 → 내용 승인 → 저장 승인 → spec.md + 관련 ADR 일괄 Commit
  ↓
강한 실행 명령 없는 Handoff 메시지
  ↓
Codex $build
  Light: 명확한 요청 → 구현 → Verify Summary
  Planned: 사용자 실제 Plan Mode 전환 → 계획 승인 → plan.md 보존 → Build → Verify
  ↓
외부 작업은 별도 사용자 승인
  PR 생성 시 검증 결과 연결 / Merge·Deploy 등은 별도 판단
```

GitHub는 승인 산출물의 durable Source of Truth다. Issue는 선택 사항이며, 저장 불가 시 수동 파일·가이드를 제공한다. 재연결만으로 자동 생성·저장하지 않고 최신 상태를 Reconcile한다.

이번 변경은 Verify/Review 전체 통합이나 기존 Hook/Gate 제거를 수행하지 않는다. 해당 목표 구조는 별도 후속 계약과 구현에서 다룬다.

## 기존 결정 — ADR-0001~0010

기존 결정과 관측 이력을 삭제하지 않는다. 후속 ADR·Spec이 변경한 항목은 그 범위를 구분해서 읽으며 기존 실행 자산이 이미 대체됐다고 해석하지 않는다.

| ADR | 주제 |
|---|---|
| [0001](0001-initial-subagent-roles.md) | 초기 Subagent 역할 |
| [0002](0002-explain-visual-story-cards.md) | Explain 시각 설명 |
| [0003](0003-work-item-human-brief.md) | Issue·PR Human Brief |
| [0004](0004-intent-spec-specification.md) | Intent·Spec 작성 |
| [0005](0005-policy-layering-boundary.md) | 정책 계층과 경계 |
| [0006](0006-grill-spec-orchestration-tradeoffs.md) | grill-spec 실행·인터뷰 |
| [0007](0007-plan-artifact-and-build-feedback-loop.md) | Plan과 Build 피드백 루프 |
| [0008](0008-verification-references-and-verifier-protocol.md) | 독립 검증과 Evidence |
| [0009](0009-continuous-evals-task-set-and-runner.md) | Continuous Evals |
| [0010](0010-review-human-ci-governance.md) | Review·Human Gate·CI Governance |

## 읽는 순서와 다음 경계

[Intent](../specs/chat-plan-design-flow/intent.md)의 최상위 목표와 후속 변경 안내, [승인 Spec](../specs/chat-plan-design-flow/spec.md), 관련 ADR을 함께 읽는다. Spec 11절은 이후 구현 변경 범위이고, 12절은 이번에 제외한 후속 작업이며, 15절은 미검증 플랫폼 항목이다.

이 승인 커밋은 Codex의 구현 계획 작성이나 Build 실행을 완료한 기록이 아니다. 이미 합의한 방향을 다시 질문하지 않되, 구현 시 발견한 미결정·충돌은 추측하지 않는다.

## Private Web Chat 연결 후속

- [ADR-0020: 읽기 전용 Skill Provider](0020-private-chat-skill-provider.md) — ADR-0012의 MCP 제외 범위에 대한 제한된 후속 변경. [Spec](../specs/plugin-tunnel-connect/spec.md). 연결·Skill 노출 성공은 별도 실측 대상이다.

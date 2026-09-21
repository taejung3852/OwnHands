# OwnHands ADR 인덱스

## 현재 결정 기록

- 기록일: 2026-09-22
- 관련 이슈: [#154 — 첫 E2E 회고와 책임 재정렬](https://github.com/taejung3852/OwnHands/issues/154)
- 문서 브랜치: `docs/e2e-feedback-decisions`
- 조사 기준 main: `41d030cdfe5ecacb85e5649081aa3a74236323aa`
- [사용자 피드백 1~15번과 근거 수준](../feedback/2026-09-22-first-e2e-retrospective.md)

이 브랜치는 E2E 회고·ADR과 후속 SDLC 설계의 승인 산출물을 보존한다. 실행 코드, Skill, Hook, 설치기, Eval 구현이 완료됐다는 뜻은 아니다. PR·Merge·릴리스·마일스톤 종료도 아직 수행하지 않는다.

새 ADR의 `방향 확정`은 사용자가 선택한 방향을 뜻한다. 각 문서의 `미결정 상세`는 아직 승인된 구현 계약이 아니다. 기존 ADR을 삭제하거나 과거 결정을 없던 일로 만들지 않는다. 후속 구현에서 새 방향과 충돌하는 활성 지침을 함께 정렬한다.

## E2E 이후 방향 — ADR-0011~0019

| ADR | 결정 | 사용자 피드백/후속 | 현재 상태 |
|---|---|---|---|
| [0011](0011-chat-codex-ownership-and-handoff.md) | ChatGPT는 기획·설계, Codex는 구현 준비·실행·검증 | 9-2, 10, 15 | 방향 확정 / 일부 인계 상세 미결정 |
| [0012](0012-authoring-skills-via-ownhands-mcp.md) | OwnHands MCP는 Intent·Spec·ADR 작성 Skill 제공, GitHub는 문서 저장 | 9-2 및 후속 정정 | 방향 확정 / 전달 방식 상세 미결정 |
| [0013](0013-build-planning-and-execution.md) | Build 준비와 실행 연결, 승인된 계획의 plan.md 저장 책임 | 5, 6, 7 | 방향 확정 / Skill 수정 미진행 |
| [0014](0014-single-independent-verification.md) | Verify Skill·독립 Verifier 중심으로 검증 통합 | 7, 8 | 통합 방향 확정 / 상세 계약 미결정 |
| [0015](0015-defer-automatic-ci-and-hook-enforcement.md) | 기존 자동 CI·Hook/Gate 제거 방향, 재설계·원인 조사 후순위 | 11, 12 및 후속 우선순위 결정 | 제거 방향 확정 / 실제 제거 미진행 |
| [0016](0016-artifact-classification-and-feedback.md) | 제품 요구·결정·결함과 OwnHands 피드백 분리 | 1, 7 | 분리 방향 확정 / 기존 기록 이동 미진행 |
| [0017](0017-guided-planning-and-visual-approval.md) | GORE 인터뷰, 단계 표시, 동적 진행, 시각 승인 | 2, 3, 4, 10, 15 | UX 방향 확정 / 표시·추정 상세 미결정 |
| [0018](0018-core-and-companion-skills.md) | Core와 ELI5·Ponytail 등 범용 보조 Skill의 소유권·배포 분리 | 9-1, 13, 14 | 재사용 방향 확정 / 패키징 상세 미결정 |
| [0019](0019-github-centered-sdlc-and-stage-commits.md) | GitHub 중심 SDLC, Work Item/단일 Branch, Stage 승인 시 일괄 Commit | Chat Plan & Design Intent 논의 | Accepted / 구현 상세는 Spec 대상 |

중심 흐름은 다음과 같다. 이 도식은 목표 구조이며 현재 런타임이 전부 이렇게 동작한다는 증거가 아니다.

```text
아이디어 / 요청
  ↓ 실제 개발 결정
GitHub Issue (없으면 생성) → 단일 작업 Branch
  ↓
ChatGPT + OwnHands 작성 Skill
  Intent 논의 → 사용자 승인
  ↓
GitHub
  intent.md + 관련 ADR 일괄 Commit
  ↓
ChatGPT + OwnHands 작성 Skill
  Spec 논의 → 사용자 승인
  ↓
GitHub
  spec.md + 관련 ADR 일괄 Commit
  ↓ Handoff
Codex + Build
  Implementation Plan → 사용자 승인 → plan.md 보존
  → Build
  ↓
Verify Skill + 독립 Verifier
  요구 충족 감사 + 중요한 변경 위험 검사
  ↓
PR → 사용자 판단 / Human Gate → Merge
```

GitHub가 Issue, Intent, Spec, ADR, plan.md, Commit, PR의 durable Source of Truth를 제공하고 ChatGPT와 Codex는 그 상태를 앞뒤에서 다루는 작업 인터페이스다.

## 기존 결정 — ADR-0001~0010

기존 파일의 내용과 상태는 새 방향의 구현이 끝나기 전까지 이미 대체됐다고 해석하지 않는다.

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

## 읽는 순서와 다음 작업

먼저 회고의 원래 번호를 확인하고 ADR-0011·0012·0017·0019와 [승인된 Chat Plan & Design Intent](../specs/chat-plan-design-flow/intent.md)를 읽는다. 이어 Spec에서 Plugin/Skill 전달 구조, GitHub 동작, Handoff reference, 충돌·실패 처리를 구체화한다.

이미 결정된 방향을 다시 승인 질문으로 돌리지 않는다. 실제 인터페이스, 플랫폼 제약, 충돌 처리처럼 결과가 달라지는 미결정 사항만 추가로 논의한다.

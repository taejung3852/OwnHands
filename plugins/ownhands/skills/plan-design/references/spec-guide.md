# Spec Stage

승인된 Intent를 읽고 유효성을 확인한다. 확인된 목표·제품 결정을 다시 인터뷰하지 않는다. Spec에 새로 필요한 인터페이스나 실패 정책의 Decision만 인터뷰 가이드로 확인한다.

`docs/specs/<feature-name>/spec.md` 후보 상단에 `- 기반 Intent: [intent.md](intent.md)`와 Draft / Approved 상태를 둔다. Requirements, Architecture, Interfaces, State / Data Flow, Failure Handling, Edge Cases, Acceptance Criteria, Validation Strategy, 변경 범위와 제외 범위를 작성한다. 요구사항은 Intent Goal/Constraint 또는 확인된 Fact에 추적 가능해야 한다. 플랫폼 지원 추정은 Fact로 승격하지 않는다.

## Checkpoint 2

1. Spec 전체를 검토 가능한 상태로 제시한다.
2. sibling ELI5 Skill을 읽고 주요 구성요소·데이터/제어 흐름·실패 경로·검증 기준을 Topic으로 한 번 실행한다. 인터뷰 중 매 결정마다 호출하지 않는다.
3. ELI5 설명 후 Spec 전체 Content Approval을 요청한다. 수정 요청이면 후보를 수정하고 다시 검토한다.
4. 승인받으면 `Spec 승인 완료 / GitHub 저장: 대기`를 안내한다.
5. [GitHub workflow](github-workflow.md)에 따라 구체적인 write 대상·내용을 보여주고 Persistence Decision을 한 번 요청한다. Issue가 없으면 Issue/Branch 세 경로를 제시하며 1/2 선택 자체를 Persistence Approval로 취급한다. 기존 경로는 그 경로로 저장할지 한 번만 묻는다.
6. 저장 승인 후 최신 상태를 재조회하고, 충돌이나 대상 상태 변경이 없으면 추가 write 승인 없이 spec.md와 Design에서 생성/수정한 관련 ADR을 한 Stage commit으로 저장한다. Decision마다 commit하지 않는다. 실패 시 Approved는 유지하고 저장 실패와 수동 대안을 안내한다.
7. [Handoff](handoff-guide.md)를 제공한다. Spec 승인이나 저장 승인은 Build 실행·Push·PR·Merge의 일괄 승인이 아니다.

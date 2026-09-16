# Requirements Traceability

이 문서는 제품 기준선의 요구사항 범주가 Milestone과 GitHub Issue에서 누락되지 않는지 추적한다.

| 요구사항 범주 | 기준 문서 | M0 Evidence/Decision | 구현 Milestone | 현재 상태 |
|---|---|---|---|---|
| 사람의 이해·검토·판단 병목 감소 | Design Rationale, Dashboard | M0-01 기준선 | M5, M6 | Blocked by Evidence |
| Dashboard와 Control 동등성 | 전체 | M0-01, ADR-0006 | M1~M5 | M0 Verified · M1 #10~#15 merged/Verified |
| Managed / Imported Task | Control, Dashboard | M0-04 machine-readable Claim applicability, ADR-0001/0003 | M1~M3 | M3 계약 구현 · authorized path-closure runtime Evidence · Pass / Observed; Rules·Hooks와 사람 Desktop 마찰은 Unobserved |
| Project Baseline / Task Overlay / Contract | Control | M0-03 validation semantics | M2 | M2 #25~#28 구현 후보 · 검토 전 |
| Context Placement / Task Harness Manifest | 전체 | ADR-0002/0005, M1.5 #16/#17 | M1.5, M2 | ADR-0009 Accepted · 사용자 사전 위임에 따른 에이전트 결정 |
| Context Lint / Applicability Gate | Control | M1.5 #18/#19 deterministic Probe | M1.5, M2 | M1.5 검증됨 · M2 dry-run Compiler/Lint 후보 · 검토 전 |
| Config·AGENTS·Rules·Hooks·Sandbox·Approval | Control | M0-02, M0-03, ADR-0001/0002 | M2, M3 | fake orchestration 검증 · 7번째 live claim에서 approval request/decline/resolution/terminal item 관찰 · `turn/completed`와 별도 sandbox-denial Evidence 부족으로 전체 Loaded/Enforced Unobserved |
| Configured / Loaded / Enforced 및 Evidence 근거 | 전체 | M0-03, M0-04, ADR-0002/0003 | M1, M3, M5 | 독립 상태/basis packet 구현 · live Evidence 부족으로 M3 Blocked |
| Canonical Event Log / Projection | Control, Dashboard | M0-02, M0-06, ADR-0004 | M1 | M0 Verified · M1 #11/#13 merged/Verified |
| Raw Evidence / Redaction / Local-only | 전체 | M0-06, ADR-0004 | M1, M5 | M0 Verified · M1 #12 merged/Verified |
| Guarantee Matrix / Task Guarantee Report | 전체 | M0-04, ADR-0003 | M1, M5 | M0 Verified · M1 #14 merged/Verified |
| Context Guarantee / Active Context·Controls | Control, Dashboard | M1.5 #20/#21 Matrix·Status 계약 | M1.5, M5 | 9-run 기계 지표 Observed · C 추천 · 사람 지표 Unobserved |
| Impact / Test Design / Regression Gate | 전체 | ADR-0006, M0-04 | M2, M4 | M4 #44~#49 contract-bound local slice 구현 · synthetic review Evidence · actual branch Gate는 `docs/reviews/m4/observed-gate-summary.json`에서 추적 |
| Workspace Restore Point / Worktree 분리 | Control | M0-06 storage boundary | M1, M4 | tracked patch를 disposable clone에서 재구성 · untracked/submodule/symlink 및 외부 효과는 명시적 제외/Unobserved |
| Task Review / Feature Validation / Harness Status | Dashboard | ADR-0006 review artifact contract | M1~M5 | M2 local Preview 후보 · M5 UI/UX Gate 유지 |
| Skill / MCP / Plugin 계층 및 Hybrid Contract | Control, 전체 | ADR-0010, M4.5 #63 | M4.5 | Option C 계약 확정 · M4.5-01 완료 |
| Brand 색상 방향 | Dashboard, Design Rationale | M0-07 3안·Probe, ADR-0007 Accepted(색상 범위) | M5 | B 색상 방향 승인 |
| 정보 위계·글쓰기·상호작용·접근성 기반 | Dashboard, Design Rationale | M0-07 참고 시안·Probe | M5 | M5 UI/UX Gate Review |
| Audit & History | Dashboard | Event/Evidence contracts | M5 | Blocked by Evidence |
| HWPX 도그푸딩, Core 비종속 | 전체 | M0-01 기준선 | M6 | Blocked by Evidence |
| Superpowers 선택적 Vendoring | Design Rationale, Control | M0-05, ADR-0005 Non-blocking | M7 | 경계 Accepted · 실제 vendoring 미승인 |
| Packaging / Release | 향후계획 | M0 범위 추적 | M7 | Blocked by Evidence |
| Usage & Cost Analytics | Design Rationale, Dashboard | Preflight 제외 확인 | M8 | Deferred |
| Codex 외 Adapter | 전체 | Core/Adapter 경계 | M8 | Deferred |

GitHub 상위 추적 Issue: <https://github.com/taejung3852/own-hands/issues/7>

M3의 committed example은 sanitization과 schema fixture이며 runtime 성공 Evidence가 아니다. 단 한 번의 disposable live probe가 실패·중단되면 그대로 최종 결과로 보존하고 M3 Gate를 차단한다. 사람의 Desktop workflow 마찰은 `not_run / unobserved`이며 [issue #38](https://github.com/taejung3852/own-hands/issues/38)에서 추적한다.

M4의 committed Assurance packet example은 합성 fixture다. Raw test output과 실제 branch packet은 저장소 밖 local data root에만 두며, 커밋되는 실제 결과는 allowlisted Gate 요약으로 제한한다. GM-013의 “관련 테스트 실행”과 M4의 비교 성공·Gap 판정은 서로 다른 의미로 유지한다.

# Requirements Traceability

이 문서는 제품 기준선의 요구사항 범주가 Milestone과 GitHub Issue에서 누락되지 않는지 추적한다.

| 요구사항 범주 | 기준 문서 | M0 Evidence/Decision | 구현 Milestone | 현재 상태 |
|---|---|---|---|---|
| 사람의 이해·검토·판단 병목 감소 | Design Rationale, Dashboard | M0-01 기준선 | M5, M6 | Blocked by Evidence |
| Dashboard와 Control 동등성 | 전체 | M0-01, ADR-0006 | M1~M5 | ADR Review |
| Managed / Imported Task | Control, Dashboard | M0-04 Claim applicability | M1~M3 | Blocked by Evidence |
| Project Baseline / Task Overlay / Contract | Control | M0-03 validation semantics | M2 | Blocked by Evidence |
| Config·AGENTS·Rules·Hooks·Sandbox·Approval | Control | M0-02, M0-03, ADR-0001/0002 | M2, M3 | ADR Review |
| Configured / Loaded / Enforced 및 Evidence 근거 | 전체 | M0-03, M0-04, ADR-0002/0003 | M1, M3, M5 | ADR Review |
| Canonical Event Log / Projection | Control, Dashboard | M0-02, M0-06, ADR-0004 | M1 | ADR Review |
| Raw Evidence / Redaction / Local-only | 전체 | M0-06, ADR-0004 | M1, M5 | ADR Review |
| Guarantee Matrix / Task Guarantee Report | 전체 | M0-04, ADR-0003 | M1, M5 | ADR Review |
| Impact / Test Design / Regression Gate | 전체 | ADR-0006, M0-04 | M2, M4 | ADR Review |
| Workspace Restore Point / Worktree 분리 | Control | M0-06 storage boundary | M1, M4 | Blocked by Evidence |
| Task Review / Feature Validation / Harness Status | Dashboard | ADR-0006 review artifact contract | M1~M5 | ADR Review |
| Brand·정보 위계·Light/Dark·접근성 기반 | Dashboard, Design Rationale | M0-07 3안·Probe, ADR-0007 | M5 | M5 Gate Review |
| Audit & History | Dashboard | Event/Evidence contracts | M5 | Blocked by Evidence |
| HWPX 도그푸딩, Core 비종속 | 전체 | M0-01 기준선 | M6 | Blocked by Evidence |
| Superpowers 선택적 Vendoring | Design Rationale, Control | M0-05, ADR-0005 Non-blocking | M7 | ADR Review |
| Packaging / Release | 향후계획 | M0 범위 추적 | M7 | Blocked by Evidence |
| Usage & Cost Analytics | Design Rationale, Dashboard | Preflight 제외 확인 | M8 | Deferred |
| Codex 외 Adapter | 전체 | Core/Adapter 경계 | M8 | Deferred |

GitHub 상위 추적 Issue: <https://github.com/taejung3852/devharness/issues/7>

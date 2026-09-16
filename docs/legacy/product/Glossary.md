# DevHarness Glossary

| 용어 | 기준 정의 |
|---|---|
| Understand | 기능·사용자 흐름·연관 기능의 변화를 사람이 자기 말로 설명할 수 있는 상태 |
| Prove | 설명과 판정이 실제 Evidence 및 확인 범위로 추적되는 상태 |
| Decide | 사용자가 수용·수정·거절·추가 검증·위험 수용을 구분해 판단하는 상태 |
| Project Baseline | 프로젝트에 반복 적용되는 공통 통제와 실행·검증 기준 |
| Task Overlay | 특정 작업에만 적용되는 제한, 임시 권한, 승인 및 검증 조건 |
| Task Execution Contract | Project Baseline과 Task Overlay를 결합한 작업별 실행 계약 |
| Managed Task | DevHarness Preflight와 Contract 승인 후 시작된 작업 |
| Imported Task | 이미 시작됐거나 끝난 뒤 DevHarness에 들어온 작업. 과거 통제와 행동은 기본적으로 보장하지 않음 |
| Configured | Control이 설정 또는 파일에 정의됐는지 검증하는 독립 단계 |
| Loaded | Control이 현재 실행에서 읽혔는지 검증하는 독립 단계 |
| Enforced | Control이 실제 행동 경계를 허용·차단·제한했는지 검증하는 독립 단계 |
| Observed | 직접 관찰된 Evidence 근거 방식. 성공 여부를 뜻하지 않음 |
| Inferred | 다른 관찰 결과에서 추론한 Evidence 근거 방식. 추론 원천을 요구함 |
| Unobserved | 확인 경로가 없거나 검증하지 못한 Evidence 근거 방식 |
| Control Check Result | Configured/Loaded/Enforced 각 단계의 `Pass`, `Fail`, `Not Run`, `Not Applicable` 결과 |
| Guarantee Matrix | 어떤 Evidence가 있어야 어떤 주장을 할 수 있는지 정의한 재사용 규칙표 |
| Task Guarantee Report | 한 작업의 실제 Evidence에 Guarantee Matrix를 적용한 결과 |
| Verification Status | Passed, Failed, Not Run, No Adequate Test, Inconclusive, Unknown 중 검증 결과 |
| Claim Verdict | Guarantee Matrix 적용 결과인 Supported, Contradicted, Not Evaluated. 제한적 확인은 별도 Verdict가 아니라 scope와 남은 위험을 함께 보여 주는 표현 |
| Gate State | Pass, Soft Block, Hard Block 중 작업 계약에 따른 진행·수용 판단 상태 |
| Workspace Restore Point | Git 작업공간을 기준 상태로 복구하기 위한 참조. 외부 효과 복구는 포함하지 않음 |
| Canonical Event Log | 중요한 사건을 순서대로 보존하는 append-only 원본 |
| Projection | Event Log에서 재생성 가능한 Dashboard용 파생 상태 |
| Raw Evidence | 로그, 명령, 이벤트, 환경 등 민감정보를 포함할 수 있는 로컬 전용 원본 |

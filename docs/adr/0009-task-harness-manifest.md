# ADR-0009 — Task Harness Manifest와 Context 적용성

- **상태:** Proposed
- **일자:** 2026-09-05
- **관련 Issue:** #16–#21

## Context

M0/M1 계약은 Configured/Loaded/Enforced와 Observed/Inferred/Unobserved를 분리했지만, Task가 실제로 받은 Context와 실행 경계를 강제한 Control을 하나의 최종 taxonomy로 정하지 않았다. Context source와 Control source를 합치면 파일 존재를 runtime load나 enforcement로 승격하고, Task 지침을 안전 Control과 같은 override 대상으로 다루는 오류가 생긴다.

## Decision

1. 상위 machine-readable 객체 이름은 `Task Harness Manifest`이며 versioned JSON으로 둔다.
2. `context_sources`와 `control_sources`는 구조적으로 분리한다. 같은 `source_id`가 두 배열에 나타날 수 없다.
3. Task 한정 Context는 `instruction_overlay`, 결정적 실행 Control은 `control_overlay`에 기록한다.
4. source identity는 type, locator, SHA-256, version, scope, freshness를 가진다. Task identity는 project/worktree/task/commit/cwd/environment를 고정한다.
5. applicability decision, realization의 configured/loaded/enforced check, 각 판단의 evidence basis를 독립 필드로 둔다.
6. observed 판단/check는 Evidence reference와 timestamp를 요구하고, inferred는 inference provenance를 요구한다. `not_run`은 Unobserved로 남긴다.
7. Manifest의 Event/Evidence reference는 M1 store에서 해소되어야 한다. JSON Schema가 검사하지 못하는 cross-array class와 reference closure는 semantic validator가 fail-closed로 검사한다.
8. Applicability Gate는 Task 시작, scope 확장, phase 전환, 외부 효과·권한 추가, 완료 주장 전에만 재평가한다. canonical input fingerprint가 같을 때만 cache hit이며 scope/phase/permission/source hash가 바뀌면 invalidate한다.
9. 결정적 안전 Control은 applicability 결과로 약화하거나 자동 제외할 수 없다. 알 수 없는 적용 경로는 `Unobserved`다.
10. Context Lint는 finding의 evidence, location, impact, suggestion을 출력하고 자동 수정하지 않는다.
11. 비교 평가는 A(추가 Context 없음), B(최소 `AGENTS.md`), C(수동 Context Profile)를 같은 Fixture에서 각 3회 실행한다. 모델, effort, prompt, commit, environment와 Control을 고정하고 Context만 변경한다.
12. `Loaded`만으로 improvement를 주장하지 않는다. token은 runtime receipt가 있을 때만 observed 값으로 기록하며 사람 이해도·검토 시간은 사람 기록 전까지 Unobserved다.
13. Harness Status 계약은 Active Context와 Active Controls를 분리하고 모든 요약을 Evidence로 drill-down한다. M5 전 Production UI는 구현하지 않는다.

## Alternatives

- **하나의 `sources` 배열:** source class 혼합과 잘못된 overlay 참조를 구조적으로 허용해 기각한다.
- **Task Overlay 하나:** 상황 지침과 안전 Control의 override 권한이 섞여 기각한다.
- **단일 상태 enum:** applicability, realization, evidence basis의 조합을 잃어 기각한다.
- **매 Step LLM 판정:** 불필요한 비용과 비결정성을 만들어 정해진 transition Gate + fingerprint cache로 대체한다.
- **Lint 자동 수정:** 의미적 오탐이 지침을 삭제할 수 있어 M1.5에서는 finding만 생성한다.

## Consequences

- Dashboard 계약은 active Context와 active Control을 별도로 표시할 수 있다.
- Schema validation 외에 reference closure와 Matrix-aware semantic validation이 필요하다.
- lexical lint는 재현 가능하지만 의미적 충돌을 완전하게 찾지 못한다.
- M2 Compiler는 이 ADR 승인 뒤 별도 구현해야 하며 M1.5 prototype을 Production runtime으로 승격하지 않는다.

## Evidence

- [Context Placement Policy](../product/Context_Placement_Policy.md)
- [Task Harness Manifest schema](../product/task-harness-manifest.schema.json)
- [Managed example](../product/task-harness-manifest.managed.example.json)
- [Imported example](../product/task-harness-manifest.imported.example.json)
- [M1.5 review package](../reviews/m1.5/README.md)
- `tests/test_context_architecture.py`의 독립 behavioral/adversarial tests

## Acceptance gate

이 ADR은 실제 1 Fixture × A/B/C × 3회(총 9회) 비교와 독립 검토 전까지 `Proposed`다. gate 충족 뒤 승인 기록의 결정 주체 표기는 `사용자 사전 위임에 따른 에이전트 결정`으로 남긴다. 현재 문서는 그 결정을 실행하거나 Accepted로 표시하지 않는다.

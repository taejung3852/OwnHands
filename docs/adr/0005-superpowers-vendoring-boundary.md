# ADR-0005 — Superpowers Skill Vendoring 경계

- **상태:** Proposed — 사용자 검토 대기
- **일자:** 2026-09-04
- **관련 Issue:** [M0-05](https://github.com/taejung3852/devharness/issues/5)
- **Blocking:** No. M0 종료 Gate의 필수 항목이 아니다.

## Context

DevHarness는 유일한 상위 Routing Layer를 유지해야 한다. Superpowers의 일부 방법론은 재사용 가치가 있지만 전체 plugin이나 global bootstrap을 함께 활성화하면 Preflight, Contract, Evidence, 완료 판단의 책임이 겹칠 수 있다. M0에서는 vendoring을 실행하지 않고 범위·license·namespace·upstream pin만 결정한다.

## Decision

실제 vendoring이 별도 승인될 경우 다음 경계를 사용한다.

### Include candidate

- `brainstorming`
- `test-driven-development`
- `systematic-debugging`
- `writing-plans`
- `verification-before-completion`
- `requesting-code-review`
- `receiving-code-review`

이들은 DevHarness Preflight와 Contract 승인 뒤 호출되는 **하위 workflow guidance**로만 사용한다. 어떤 skill도 자체적으로 Guarantee `Pass`를 만들 수 없다.

### Defer pending adapter Evidence

- `executing-plans`
- `subagent-driven-development`
- `dispatching-parallel-agents`
- `using-git-worktrees`
- `finishing-a-development-branch`

위 skill은 Task/Worktree identity, delegation, integration/cleanup에 영향을 줄 수 있어 DevHarness adapter와 approval model의 behavior test 전에는 포함하지 않는다.

### Exclude

- `using-superpowers`: global bootstrap/router가 DevHarness의 단일 top-level router와 충돌
- `writing-skills`: 현재 DevHarness 사용자 작업 lifecycle 범위 밖이며 skill-authoring 필요 시 별도 검토
- upstream plugin manifest, installer/updater, marketplace/bootstrap asset: 전체 plugin activation과 자동 update를 피하기 위해 제외

### Namespace

Vendored copy는 `dev-harness/<skill-name>` namespace만 사용한다. upstream `superpowers:*`와 DevHarness copy를 동시에 활성화하지 않는다.

### License와 provenance

- License: MIT, copyright Jesse Vincent (2025)
- notice와 permission text를 모든 copy/substantial portion 및 이를 포함한 배포물에 동봉
- 권장 경로: `LICENSES/superpowers-MIT.txt`, `THIRD_PARTY_NOTICES.md`
- 수정본은 upstream path, source hash, 수정 여부를 기록하고 upstream endorsement를 암시하지 않음

### Upstream pin

- repository: `https://github.com/obra/superpowers.git`
- release tag: `v6.3.0`
- immutable commit: `b36e0829c6d0140e93cfef2ca599b1b07d4a7797`
- tag는 사람이 읽는 version, commit SHA는 실제 재현 pin으로 사용
- floating branch, `latest`, marketplace cache path만으로 import하지 않음

## Alternatives

- **전체 plugin vendoring/activation:** router와 update/install 동작까지 들어와 기각한다.
- **외부 plugin을 runtime 의존성으로만 사용:** version·availability·router priority를 DevHarness가 통제하기 어려워 core workflow 의존성으로 기각한다.
- **방법론을 출처 없이 재작성:** license/provenance와 behavioral equivalence를 잃으므로 기각한다.
- **아무것도 재사용하지 않음:** 중복 작성은 줄지만 검증된 workflow guidance의 이점을 잃는다. 선택적 subset이 더 적절하다.

## Consequences

- DevHarness가 Routing, Contract, Evidence, Guarantee 책임을 유지한다.
- 실제 import 전 skill별 supporting file inventory와 behavior test가 필요하다.
- upstream update는 새 commit 선택, diff/license 검토, behavior regression, notice 갱신을 거치는 명시적 변경이어야 한다.
- 이 ADR 승인만으로 어떤 파일도 vendoring되거나 활성화되지 않는다.

## Evidence

- [M0-05 Superpowers Vendoring Spike](../spikes/superpowers-vendoring.md)
- [공식 upstream repository](https://github.com/obra/superpowers)
- [v6.3.0 MIT License](https://github.com/obra/superpowers/blob/v6.3.0/LICENSE)
- 공식 Git ref와 설치 cache 비교에서 tag commit과 대표 Skill hash를 확인했다. 설치 manifest는 upstream manifest와 hash가 달라 import source of truth로 사용하지 않는다.

## Follow-up gate

실제 vendoring은 후속 Milestone의 별도 Issue와 사용자 승인 뒤에만 수행한다. 그 Issue는 namespace discovery, router ordering, Evidence wording, Task/Worktree, notice packaging behavior test를 포함해야 한다.

이 ADR은 사용자 승인 전까지 `Proposed`이며 실제 vendoring을 허가하지 않는다.

# ADR-0001 — Codex Desktop 통합 경로

- **상태:** Proposed — 사용자 검토 대기
- **일자:** 2026-09-04
- **관련 Issue:** [M0-02](https://github.com/taejung3852/devharness/issues/2)

## Context

DevHarness는 Codex Desktop-first 제품이지만 기존 Desktop UX를 임의로 대체하거나, 관찰을 위해 사용자의 작업을 resume·steer·approve해서는 안 된다. 동시에 Event, approval, config, hook의 실제 Evidence가 필요하다. 공식 문서와 설치된 Codex CLI 0.153.0의 read-only help를 기준으로 통합 경계를 정해야 한다.

## Decision

두 가지 명시적 Task mode를 제안한다.

1. **Managed Task:** DevHarness가 preflight 뒤 App Server로 새 Task를 시작하고, 자신이 수신한 안정 API 범위의 Event와 approval transaction을 canonical Event Log에 기록한다.
2. **Imported Desktop Task:** 사용자가 명시적으로 선택한 기존 Task를 App Server `thread/read` 기반 snapshot/status로만 읽는다. live Event, 과거 approval, config, hook, sandbox enforcement는 `Unobserved`로 둔다.

Hooks, project config, AGENTS.md는 Managed Task의 보완 Evidence source다. Codex SDK는 DevHarness-owned automation/fixture용이며 Desktop Task attach 수단으로 사용하지 않는다. Rules는 실험 기능이므로 core guarantee의 필수 조건으로 삼지 않는다.

기존 Desktop Task에 passive live subscriber를 붙이는 구현은 공식적으로 보장된 경로가 확인될 때까지 보류한다.

## Alternatives

- **SDK로 Desktop Task 연결:** 공식 SDK는 automation/CI용 start/run 흐름이며 Desktop-owned Task attach가 문서화되지 않아 기각한다.
- **Hook만으로 수집:** hosted/specialized path와 fail-open 경로가 있어 전체 Event source로 사용할 수 없다.
- **session log/transcript parsing:** format과 completeness가 안정 계약이 아니므로 canonical adapter로 사용하지 않는다.
- **기존 Task를 resume해 관찰:** 사용자 UX와 client ownership을 바꿀 수 있어 passive 관찰로 간주하지 않는다.

## Consequences

- Managed Task는 구조화 Event와 approval lifecycle을 강하게 추적할 수 있다.
- Imported Task는 familiar Desktop UX를 유지하지만 보장 범위가 snapshot과 이후 직접 수집한 Evidence로 제한된다.
- Desktop live integration 목표는 삭제하지 않고 M3 Hard Evidence Gate로 유지한다.
- adapter가 제공하지 않는 경로를 `Unobserved`로 표시해야 하므로 Dashboard도 두 mode를 구분해야 한다.

## Evidence

- [M0-02 Codex Desktop Integration Spike](../spikes/codex-desktop-integration.md)
- OpenAI [App Server](https://developers.openai.com/codex/app-server)는 `thread/read`를 resume/subscription 없는 stored thread read로 설명하고, managed client의 turn/item/approval Event를 문서화한다.
- 같은 App Server 문서는 synchronous lifecycle Hook의 `hook/started`와 `hook/completed` notification을 문서화한다. 설치 CLI 0.153.0의 default generated schema에서도 두 이름을 확인했지만 실제 Hook 실행이나 Desktop-owned Task에서의 수신은 확인하지 않았다.
- OpenAI [Codex SDK](https://developers.openai.com/codex/codex-sdk)는 SDK를 automation/CI에, custom client Event·approval에는 App Server를 안내한다.
- OpenAI [Hooks](https://developers.openai.com/codex/hooks)는 local lifecycle 확장과 함께 coverage/failure 한계를 문서화한다.
- 로컬에서는 [read-only capability Probe](../spikes/probes/m0-02-03-codex-capability-probe.sh)로 CLI 0.153.0의 help, disposable-CWD stdio `initialize` handshake, default protocol schema를 확인했다. Task/turn은 만들지 않았고 기존 사용자 Task, daemon session 목록, private transcript는 열지 않았다. user/global config를 열거·기록하지 않았지만 App Server의 내부 default layer loading 여부는 확인하지 않았으므로 active config source는 `Unobserved`다.

## Required M3 probes

1. 새 disposable Task에서 `thread/read` snapshot이 Desktop 상태를 바꾸지 않는지 확인한다.
2. 별도 App-Server-managed Task에서 stable Event와 approval request/decision/result를 수집한다.
3. harmless local Hook으로 지원 lifecycle과 failure/timeout을 각각 확인한다.
4. 기존 개인 Task, remote control, daemon 재시작, global config 변경은 Probe 대상에서 제외한다.

이 ADR은 사용자 승인 전까지 `Proposed`이며 M1 구현을 허가하지 않는다.

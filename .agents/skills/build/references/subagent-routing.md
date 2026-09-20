# 조건부 Subagent Routing

기본 실행 주체는 현재 Builder다. 위임 이점이 작업 분리 비용보다 명확할 때만 다음 후보를 사용한다.

| 조건 | 후보 | 기본 model / effort |
|---|---|---|
| 구현과 분리 가능한 외부 자료 조사가 필요함 | `researcher` | `gpt-5.6-terra` / `medium` |
| 파일 책임과 완료 조건을 독립적으로 나눌 수 있는 큰 Task | Codex native `worker` | 호출 시 별도 선택 |
| 구현 완료 후 AC와 Fresh Evidence의 독립 감사 | 기존 `verifier` | `gpt-5.6-sol` / `high` |

단순하거나 강하게 결합된 Task, 위임 오버헤드가 더 큰 Task에는 위임하지 않는다. Task마다 fresh subagent를 강제하지 않는다.

호출 전 `.codex/agents/model-policy.md`를 읽고 위험에 따른 default/downgrade/escalation을 선택한다. 모든 custom role dispatch는 model과 reasoning effort를 함께 명시하고 `agent_role`, `requested_model`, `requested_reasoning_effort`, `selection_basis`를 기록한다.

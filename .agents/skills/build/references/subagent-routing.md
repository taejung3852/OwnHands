# 조건부 Subagent Routing

기본 실행 주체는 현재 Builder다. 위임 이점이 작업 분리 비용보다 명확할 때만 다음 후보를 사용한다.

| 조건 | 후보 |
|---|---|
| 구현과 분리 가능한 외부 자료 조사가 필요함 | `researcher` |
| 파일 책임과 완료 조건을 독립적으로 나눌 수 있는 큰 Task | Codex native `worker` |
| 구현 완료 후 AC와 Fresh Evidence의 독립 감사 | 기존 `verifier` |

단순하거나 강하게 결합된 Task, 위임 오버헤드가 더 큰 Task에는 위임하지 않는다. Task마다 fresh subagent를 강제하지 않는다.

# Subagent model, reasoning, and permission policy

이 문서는 OwnHands의 `researcher`, `verifier`, `reviewer` dispatch Source of Truth다. custom-agent TOML의 `model`과 `model_reasoning_effort`는 호출 시 선택보다 우선하므로 TOML에 고정하지 않는다. 호출자는 작업 난이도와 위험에 맞는 pair를 아래에서 고르고 **model과 reasoning effort를 모두 명시**한다. 우연한 parent/default inheritance는 정상 경로가 아니다.

| 역할 | 기본 model / reasoning | 비용·속도·판단 근거 | 명시적 override |
|---|---|---|---|
| `researcher` | `gpt-5.6-terra` / `medium` | 읽기·검색에 충분한 판단력과 중간 비용 | 좁은 추출은 `gpt-5.6-luna` / `low`; 상충하는 다중 출처·고위험 조사는 `gpt-5.6-sol` / `high` |
| `verifier` | `gpt-5.6-sol` / `high` | AC와 Evidence 역추적에 필요한 다단계 판단 | 기계적 소규모 감사는 `gpt-5.6-terra` / `medium`; 보안·데이터 손실·교차 시스템은 `gpt-6-astra` / `high` 또는 `xhigh` |
| `reviewer` | `gpt-6-astra` / `high` | Human Gate 직전 전체 diff의 독립 판단 품질 우선 | 좁은 targeted re-review는 `gpt-5.6-sol` / `high`; 보안·동시성·대규모 변경은 `gpt-6-astra` / `xhigh` 또는 `max` |

현재 공식 상대 비용은 Luna < Terra < Sol < Astra다. 하나의 모델을 영구 고정하지 않고 가장 낮은 충분한 tier를 선택한다. 지정 모델이 계정/호스트에서 제공되지 않으면 같은 위험 tier의 가용 모델을 **명시적으로** 선택하고 이유를 기록한다. model 또는 effort를 생략해 상속으로 후퇴하지 않는다.

모든 dispatch record에는 다음을 남긴다.

```text
agent_role
requested_model
requested_reasoning_effort
selection_basis = default | downgrade | escalation
```

실제 runtime model/effort가 UI나 실행 결과에서 관측되지 않으면 requested 값을 actual로 바꾸어 쓰지 않고 `actual_model = UNOBSERVED`, `actual_reasoning_effort = UNOBSERVED`로 둔다. 첫 E2E provenance에는 OwnHands commit/tag, Codex CLI version, 위 요청/관측 값과 agent role을 함께 기록한다.

세 TOML은 모두 `sandbox_mode = "read-only"`를 선언한다. 이는 “수정하지 말라”는 instruction-only 규칙과 별개인 실제 agent 기본 sandbox다. 다만 부모 세션의 live permission override가 custom-agent 기본값보다 우선할 수 있으므로 absolute security boundary로 주장하지 않는다.

근거: [Codex Subagents](https://developers.openai.com/codex/subagents), [OpenAI model catalog](https://developers.openai.com/api/docs/models), [Superpowers model selection](https://github.com/obra/superpowers/blob/main/skills/subagent-driven-development/SKILL.md). Superpowers의 전체 구조를 복제하지 않고 “가장 낮은 충분한 tier를 선택하며 모든 spawn에 model/effort를 명시한다”는 선택 원칙만 OwnHands 역할에 적용한다.

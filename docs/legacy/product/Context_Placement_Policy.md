# ownhands Context Placement Policy v1

- **상태:** M1.5 검토안
- **관련 Issue:** #16–#21
- **결정 경계:** Context는 모델이 작업을 이해하고 판단하도록 제공하는 정보이고, Control은 실행 경계를 결정적으로 제한하거나 관찰하는 장치다. 같은 요구를 설명하고 강제할 수는 있지만 같은 source로 합치지 않는다.

## 1. 배치 분류표

| 정보 유형 | 기본 배치 | 기본 scope / load | 예외 조건 | Context / Control |
|---|---|---|---|---|
| 저장소 공통 작업 규약 | 얇은 root `AGENTS.md` | project / 매 실행 시작 | 하위 디렉터리만 다른 규약은 가까운 `AGENTS.override.md` | Context |
| Task 한정 목표·제약 | `instruction_overlay` | task 또는 phase / Gate가 추가 | 여러 Task에 반복되고 명확한 trigger가 있으면 Skill로 승격 검토 | Context |
| 재사용 절차 | Skill `SKILL.md` | trigger 일치 시 on-demand | 짧고 항상 필요한 저장소 규약이면 `AGENTS.md` | Context |
| 상세 설명·API·파일 지도 | Reference | Skill 또는 Task가 필요할 때 | 매 작업의 필수 한두 문장만 `AGENTS.md`에 요약 | Context |
| 명령 허용·차단 | Rule | command boundary / 실행 시 | 설명은 Context에 링크할 수 있으나 Rule을 자연어로 대체하지 않음 | Control |
| lifecycle 관찰·검증 | Hook | event boundary / event 발생 시 | 단순 절차 설명은 Skill; 집행 결과는 Evidence | Control |
| 파일·네트워크 경계 | Sandbox | environment boundary / 전체 실행 | Task 상황에 맞춰 약화하지 않음 | Control |
| 외부 효과 승인 | Approval Policy | action boundary / 승인 필요 시 | Task Overlay가 자동 승인으로 승격하지 않음 | Control |
| 실제 로드·호출·차단·검증 결과 | Evidence | task + exact scope / 사건 후 | 미래 지침이나 Control source로 재사용하지 않음 | Evidence |

Codex는 실행 시작 전에 `AGENTS.md` instruction chain을 만들고 root에서 현재 디렉터리까지 파일을 합치며 가까운 파일을 나중에 적용한다. 따라서 Task 한정 지침을 root `AGENTS.md`에 두면 관련 없는 작업에도 상시 주입된다. [공식 OpenAI AGENTS.md 문서](https://learn.chatgpt.com/docs/agent-configuration/agents-md)

Skill은 이름·설명으로 먼저 노출되고 선택된 뒤 전체 `SKILL.md`를 읽는 progressive disclosure 방식이며, explicit 또는 description 기반 implicit trigger로 활성화된다. 상세 절차와 큰 Reference를 상시 Context에서 분리하는 근거다. [공식 OpenAI Skill 문서](https://learn.chatgpt.com/docs/build-skills)

Rule은 sandbox 밖에서 실행할 명령의 allow/prompt/forbidden 결정을 통제한다. instruction 문장과 달리 여러 match 중 가장 제한적인 결정을 적용하는 실행 Control이므로 `context_sources`에 넣지 않는다. [공식 OpenAI Rules 문서](https://learn.chatgpt.com/docs/agent-configuration/rules)

Hook은 agentic loop의 lifecycle 지점에서 script나 MCP tool을 실행하며, 여러 source의 matching hook이 함께 실행될 수 있고 비관리 hook은 hash 기반 trust 검토를 거친다. 파일 존재와 실제 호출을 분리해 기록해야 한다. [공식 OpenAI Hooks 문서](https://learn.chatgpt.com/docs/hooks)

Sandbox와 Approval은 파일·네트워크·외부 효과의 실행 경계다. `workspace-write`에서도 보호 경로가 존재하고 sandbox 안의 행동과 approval이 필요한 행동이 구분되므로 자연어 지침이나 `Loaded` 상태로 `Enforced`를 대신할 수 없다. [공식 OpenAI Agent approvals & security 문서](https://learn.chatgpt.com/docs/agent-approvals-security)

## 2. 얇은 `AGENTS.md`

포함한다:

- 저장소 전체에서 변하지 않는 build/test 명령과 최소 완료 기준
- 공개 API, 보안 경계, 문서 위치처럼 모든 작업이 알아야 하는 짧은 규약
- 더 구체적인 Skill·Reference로 가는 trigger와 링크

포함하지 않는다:

- 한 Issue의 목표, 임시 조사 지시, 현재 phase의 체크리스트
- 전체 파일 목록·긴 아키텍처 설명·API 사전
- Rule·Hook·Sandbox·Approval의 강제 내용을 복제한 자연어
- 실행 결과, token 수, 성공 주장, 현재 `Loaded`/`Enforced` 상태
- 호출 조건이 있는 Skill의 전체 절차

## 3. 예시와 반례

| 실제 경로 | SHA-256 | 올바른 분류 | 반례 |
|---|---|---|---|
| `docs/product/Control_layer.md` | `7c43d869603e2e514d26ed6e26528a7029061d70200a607eb6bb01ef2fca73a8` | 제품 Reference | 전체 문서를 root `AGENTS.md`에 복사해 항상 로드 |
| `docs/product/향후계획.md` | `62fe3d4d667976260e7767a919d5158035dbca1445ab0833b8d49ecde5f915e9` | milestone Reference | 현재 Issue 부분만 구분하지 않고 모든 Task의 Overlay로 사용 |
| `docs/spikes/superpowers-vendoring.md` | `7f1e0e55c1158bba313df2456c2dfbd408af19eeb0b187934ec0fc6fbe3e47b5` | 과거 Spike Evidence/Reference | 설치된 Skill 또는 enforced router로 주장 |
| `docs/product/control-validation.schema.json` | `bf85233a6dadde46e527aee4fa28aba6ebc204833e3db41caef5bdb9f4571d85` | machine-readable contract Reference | schema 파일 존재를 runtime `Loaded`/`Enforced`로 승격 |

충돌 예: root `AGENTS.md`의 `test_command = python -m unittest`와 Task 문서의 `test_command = pytest`가 동시에 active이면 하나의 authority를 고르기 전까지 해당 source는 `forbidden` 또는 `unobserved`다. 중복 예: Rule이 `git push`를 prompt로 강제하는데 `AGENTS.md`가 “Always allow git push”라고 반복하면 자연어가 Control과 drift할 수 있으므로 삭제가 아니라 lint finding과 수정 제안을 낸다.

## 4. Router와 Overlay 책임

- ownhands Router는 Task 시작과 정해진 전환점에서 source applicability를 판정하고 `instruction_overlay`와 `control_overlay`를 별도로 기록한다.
- Skill은 선택된 workflow를 수행하고 직접 읽은 Reference와 호출 Event를 반환한다. Skill이 Sandbox·Approval·Rule을 약화하지 않는다.
- Superpowers-derived Skill은 workflow provenance다. ownhands Router와 동일 trigger를 서로 독립적으로 소유하지 않는다. 충돌 시 한 Router를 authority로 지정하고 다른 쪽은 명시적으로 route한다.
- `instruction_overlay`는 Task에 제공할 Context만 바꾼다. `control_overlay`는 결정적 Control의 활성 집합을 기록하되 안전 Control 제외 요청을 거부한다.

## 5. 세 독립 축

1. **Applicability:** `maintain | add_for_task | exclude_for_task | replace_with_specific | forbidden | unobserved`
2. **Realization:** source마다 `configured`, `loaded`, `enforced` check를 독립 기록
3. **Evidence basis:** 각 판단/check마다 `observed | inferred | unobserved`

`add_for_task + loaded/pass + observed`는 가능한 조합이지만, `loaded/pass + unobserved`는 불가능하다. `Configured`는 파일 또는 설정 존재만 말하고, `Loaded`나 결과 개선을 뜻하지 않는다. Context는 보통 `Enforced/not_applicable` 또는 `not_run`일 수 있고, Control은 실제 경계 probe가 없으면 `Enforced/not_run + Unobserved`다.

## 6. Lint 한계

M1.5 prototype은 선언된 UTF-8 Markdown/Text/JSON/TOML/Rules source에서 exact duplicate, `key = value` conflict, missing path/command/Skill, 현재 코드에 없는 declared symbol, router metadata collision, task-only always-loaded placement, Control repetition, 광범위 표현, 10개를 넘는 정적 file inventory와 명시적으로 uninvoked인 Skill을 결정적으로 찾는다. 자동 수정하지 않는다. 의미적 바꿔쓰기, 생성된 prompt, binary format, dynamic path와 실제 runtime load는 `Unobserved`이며 사람 검토가 필요하다.

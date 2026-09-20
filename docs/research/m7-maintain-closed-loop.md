# V2-M7 Research Gate — Maintain & Closed Loop

- 조사일: 2026-09-20
- 관련 Issue: [#150](https://github.com/taejung3852/OwnHands/issues/150)
- 목표: 운영·사용·개발 피드백을 다음 Intent와 Eval 후보로 연결한다.
- 범위: 공식 기능과 기존 자산으로 가능한 최소 연결을 조사한다. 아래 결정 후보는 아직 승인된 구현 계약이 아니다.
- 확인 환경: `origin/main`의 M6 merge commit `b2f6d2f`, 로컬 저장소 읽기와 공식 문서 조회. Runtime Eval은 재실행하지 않았다.

## 현재 저장소에서 확인한 것

| 재사용 자산 | 현재 Fact | M7에서 남은 공백 |
|---|---|---|
| [Spec 규약](../specs/README.md), `grill-spec` | Intent의 목표·비목표와 사람 검토 경로가 있다. | 어떤 피드백을 새 Intent로 올릴지 정하지 않았다. |
| [M6 Plan](../specs/deploy-governance/plan.md) | Fresh Evidence, Finding의 Status/Resolution, Hook `UNOBSERVED` 기록이 있다. | 해결된 Finding과 후속 개선 후보를 연결하는 규약이 없다. |
| [Task Set](../evals/task-set.json), [runner](../../scripts/run-evals.js) | 정적/Runtime 구분, 단일 `--task` 실행, 3-State 비교가 구현돼 있다. | 실제 피드백의 Task Set 편입 기준이 없다. |
| [현재 baseline](../evals/baselines/current.json) | EVAL-0001/2/4/5 PASS, EVAL-0003 FAIL을 저장한다. 이는 과거 실행 기록이며 이번 실측이 아니다. | 상태 요약만으로 원래 실패 입력·원인·후속 판단을 모두 복원할 수 없다. |
| [Review Skill](../../.agents/skills/review/SKILL.md) | 독립 Review, Evidence, 단계별 Human Gate를 담당한다. | 운영 피드백의 수집·선별 책임은 정의하지 않는다. |

`run-evals.js`의 baseline 갱신은 명시적 옵션이며 회귀 발견 시 갱신을 거부한다. M7 후보를 시험한다는 이유로 현재 baseline을 덮어쓰지 않는다. 이 보호 로직은 코드를 읽어 확인했고 이번에 재실행하지 않았다.

## Anthropic Maintain 방향과 OwnHands 적용 경계

[AI-Native SDLC Playbook — Maintain](https://claude.com/blog/the-ai-native-sdlc-playbook)은 관측 신호로 진단을 시작하고 다음 `intent.md`로 연결하며, 해결된 장애를 Eval 사례에 반영하는 방향을 제시한다. control-band·자율 실행·조직 역할은 글의 예시이며 Codex 기능이나 OwnHands 확정 요구가 아니다.

OwnHands가 이미 채택한 것은 피드백을 다음 Intent와 Eval로 연결한다는 방향이다. 초기 적용 범위와 자동화 정도는 아래 미결정 사항으로 둔다.

## 공식 자료에서 확인한 범위

### S1. 예약 작업 — 반복 실행 수단

[Scheduled tasks](https://learn.chatgpt.com/docs/automations?surface=app)

- 데스크톱 예약 작업은 로컬 프로젝트 또는 worktree에서 실행할 수 있다. 로컬 파일이 필요하면 컴퓨터와 앱이 실행 중이어야 한다.
- 기존 대화에 돌아오는 예약 작업과 매 실행마다 새 대화를 만드는 예약 작업을 구분한다. Skill과 결합할 수 있다.
- 예약 작업은 기본 sandbox 설정으로 무인 실행된다. 공식은 필요한 최소 접근권한부터 시작하도록 안내한다.
- Gmail·Slack·GitHub 이벤트 기반 실행은 지원 요금제의 웹·모바일 기능이다. 현재 문서는 데스크톱·CLI·IDE에서 지원하지 않는다고 명시한다.
- 기존 Codex URL `developers.openai.com/codex/app/automations`는 위 페이지로 이동한다.

### S2. AGENTS.md / Skill — 재사용 가능한 개선의 저장 위치

[Best practices](https://learn.chatgpt.com/guides/best-practices)

- 공식은 반복 실수를 관측한 뒤 짧고 정확한 `AGENTS.md` 규칙을 추가하는 방식을 권한다.
- 반복 가능한 작업 흐름은 Skill로 묶고, Skill마다 한 가지 역할·분명한 입력과 출력을 두도록 안내한다.
- 대표 작업부터 개선하고, 안정적인 흐름을 자동화하는 순서를 권한다. 새 도구는 실제 반복 작업을 줄일 때 추가하도록 안내한다.
- 이는 기능·권고이며 OwnHands의 승격 기준이나 승인 절차를 공식이 정해 준다는 뜻은 아니다.
- 기존 Codex URL `developers.openai.com/codex/learn/best-practices`는 위 페이지로 이동한다.

### S3. Codex Skill Eval — 실제 실패를 관측 가능한 사례로 편입

[Testing Agent Skills Systematically with Evals](https://developers.openai.com/blog/eval-skills)

- Skill 호출 누락·출력 이탈을 발견하면 Eval 데이터에 새 사례를 추가하는 점진적 확장을 제안한다.
- `codex exec --json`의 JSONL 이벤트를 저장하고 실제 실행 행동에 작은 deterministic check를 적용하는 예제를 제공한다.
- 명령·파일 존재 검사는 기본 행동을 확인하지만 질적 적합성까지 증명하지는 않는다. 필요한 경우 구조화된 rubric 평가를 추가한다.
- 무거운 검사와 Runtime smoke는 선택적으로 적용하며, 수동 수정에서 드러난 실제 실패를 테스트로 바꾸도록 권한다.
- 블로그 예제의 runner·옵션은 예시다. OwnHands가 같은 runner나 권한 옵션을 복제해야 한다는 요구가 아니다.

### S4. 평가 원칙 — 피드백과 실제 데이터를 평가에 반영

[Evaluation best practices](https://developers.openai.com/api/docs/guides/evaluation-best-practices)

- 평가 목표·데이터·지표를 정의하고 실제 운영 데이터, 이력, 사용자 피드백으로 사례를 확장하도록 안내한다.
- 자동 점수와 사람의 판단을 함께 사용하며, 사람의 피드백으로 평가 기준을 보정하도록 권한다.
- 이 페이지는 API 평가 문맥의 일반 지침이다. OwnHands 로컬 M5 runner가 Evals API이거나 API 도입이 필요하다는 근거가 아니다.

## OwnHands 결정 후보 — 공식 보장과 구분

- 기존 Issue·Review Results·M5 관측 결과에서 시작해, 원본 근거와 기대/실제 행동을 붙인 피드백 후보를 만든다.
- 후보를 다음 Intent, Eval 사례, 기존 지침 수정, 보류 중 어디로 보낼지 사람이 판단한다. 이 승격 경계는 OwnHands가 정할 정책이다.
- 처음에는 명시 요청으로 후보를 정리하고, 반복 수요가 확인되면 기존 예약 기능 사용을 검토한다.
- 승인된 Spec·AGENTS.md·Skill·Eval baseline의 자동 변경이나 새 수집 플랫폼은 현재 목표의 필수 전제로 두지 않는다.

### 최소 흐름 후보

```text
사용자가 제시한 실제 피드백 + 원본 근거
  → 기대/실제 행동과 영향 확인
  → 기존 작업과 중복 확인
  → 기존 작업 연결 / 새 Intent 후보 / 회귀 사례 후보 / 보류
  → 사람 판단 후 기존 설계·Build·Verify·Review 흐름
```

- 기록은 기존 Issue/Plan을 재사용하는 안을 우선 검토한다. 별도 feedback DB·파일 형식·새 Skill은 아직 선택하지 않는다.
- 제품 버그는 해당 프로젝트 native test, OwnHands의 Skill·Agent 계약 문제는 M5 Eval 후보로 구분한다. 모든 피드백에서 Intent와 Eval을 둘 다 만들지는 않는다.
- 최소 근거 후보는 원본 링크, 당시 버전/환경, 기대·실제 결과, 영향이다. 추정 원인과 재현된 원인은 구분한다.
- 중요한 단일 실패도 후보가 될 수 있다. 횟수를 채울 때까지 기다리는 규칙이나 자동 승격 임계값은 채택하지 않았다.

### 기존 사례로 살펴본 후보 분류 — 새 실측 아님

| 실제 기록 | 연결 후보 | 주장할 수 없는 것 |
|---|---|---|
| M6 Hook 실제 활성화 `UNOBSERVED` | 기존 #148/Plan을 링크해 관측 공백과 다음 확인 후보로 보존 | 제품 결함으로 확정하거나 PASS로 전환 |
| #149의 Build/Review 책임 분리 | 해결 기록 재사용; 재발 방어 필요성을 검토 | 새 기능 Issue를 중복 생성하거나 Eval을 자동 추가 |
| M5 EVAL-0003 baseline FAIL | 기존 실패 기록과 현재 개선 목표의 관련성을 먼저 판단 | M7 착수만으로 Researcher 개선 범위를 추가 |

## Step ②에서 결정할 세 가지

1. **첫 적용 범위**: OwnHands 자체 사용/개발 피드백부터 시작할지, 사용 프로젝트 운영 신호까지 포함할지. 추천 후보는 OwnHands 실제 사례부터 검증하는 것이다.
2. **기록·분류 계약**: 기존 Issue/Plan에 최소 근거와 연결을 남길지, 별도 기록이 필요한지. 추천 후보는 기존 기록 재사용과 중복 연결이다.
3. **실행 경계**: 명시 요청 시 후보를 정리할지, 예약 수집을 도입할지. 추천 후보는 요청 시 실행이며 Intent/Eval·정책 변경은 기존 승인 흐름으로 넘긴다.

이 추천들은 사용자 승인 전의 제안이다. 설계 단계에서는 `docs/specs/` 규약으로 Intent를 먼저 검토한다.

## 이번 단계에서 만들지 않는 것

새 Skill/Agent/Hook/Runner, 상시 수집 서비스, Dashboard, 예약 작업, API 기반 평가 시스템, 자동 Spec·baseline 수정, 전체 Runtime Suite. 이번 산출물은 근거가 있는 Research와 설계 질문이며 작동하는 Maintain 구현이 아니다.

## 미확인 / 관측 한계

- 공식 문서 조사만 수행했다. 이 계정에서 예약 작업의 실행·권한·비용 또는 로컬 Hook 활성화를 실측하지 않았다.
- 로컬 대화·운영 로그 전체가 자동 수집된다는 보장은 위 출처에서 확인하지 못했다. 연결된 도구·접근 가능한 파일·제공된 입력 범위를 구분해야 한다.
- Intent/Eval 승격 시점, 중복 판정, 최소 근거, 보류 기준 및 사용자 승인 방식은 위 기능만으로 결정되지 않는다.
- 자동화 실행 자체가 Human Gate 승인, 개선 효과 또는 현재 M5 baseline 통과를 보증하지 않는다.

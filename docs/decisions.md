# V2 결정 상태표

> 이 문서는 **무엇이 확정이고 무엇이 아직 아닌지**를 한곳에서 구분한다.
> 이 저장소의 다른 문서와 충돌하면 **이 문서가 기준**이다.

## 읽는 법

**방향이 정해진 것과 구현이 끝난 것은 다르다.**

| 상태 | 뜻 |
|---|---|
| ✅ **방향 확정** | 사용자가 확정한 방향. 다시 논의하지 않고 작업에 반영한다. |
| 🤔 **사용자 생각·검토 중** | 사용자가 현재 선호하는 안. **확정 규칙이 아니다.** 이대로 구현하지 않는다. |
| 💬 **함께 결정** | 사용자와 상의해 정해야 한다. 에이전트가 대신 확정하지 않는다. |
| ⏳ **후속 결정** | 해당 마일스톤 이슈에서 공식 자료 조사와 함께 결정한다. |

구현 상태는 별도 축이다.

| 구현 상태 | 뜻 |
|---|---|
| 🚧 미구현 | V2에서 아직 만들지 않았다. |
| 📦 V1 구현 기록 있음 | V1에 구현·검증 기록이 있으나 **V2로 자동 승계되지 않는다.** |

> **2026-09-19 기준 V2에 존재하는 실행 자산은 Skill 4개(`write-issue-pr`·`explain`·`grill-spec`·`verify`)와 커스텀 Subagent 3개(`verifier`·`reviewer`·`researcher`)다.**
> 그 외 제품 기능은 🚧 미구현이다. 이 문서는 방향 문서이지 완료 보고가 아니다.

---

## 1. 확정된 방향

| 주제 | 결정 내용 | 구현 |
|---|---|---|
| **제품 범위** | AI-native SDLC 전체를 연결하는 개발 시스템을 지향한다. | 🚧 |
| **제품 대상** | 개인 전용으로 제한하지 않는다. 조직 정책과 실행 환경을 연결할 수 있게 한다. | 🚧 |
| **V2 출발 방식** | 기존 Dashboard·Core 구조의 재사용이나 호환성을 전제로 하지 않는 **clean-slate 설계**다. | 🚧 |
| **실행 플랫폼** | **Codex를 먼저 대상으로 삼는다.** | 🚧 |
| **플랫폼별 구성** | 모델·코딩 에이전트별 차이를 존중하며 각각에 맞는 구성을 지향한다. | 🚧 |
| **근거의 중심** | Anthropic Playbook을 SDLC의 핵심 참고 자료로, **Codex 공식 문서를 실제 구성·지원 범위의 기준**으로 사용한다. 지원 여부 확인에서 멈추지 않고 **Skill·프로젝트 지침·(사용한다면) MCP의 내부 프롬프트를 어떻게 작성할지까지** 공식 자료를 참고한다. | — |
| **개발 방법** | 마일스톤 초기에 공식 자료와 네이티브 기능을 조사하고 **직접 만들 부분을 결정**한다. | — |
| **작업 수단 구분** | Skill·Reference·Agent·Tool·Script·Hook의 책임을 먼저 구분한다. 기존 플랫폼 기능을 불필요하게 다시 만들지 않는다. | 🚧 |
| **설명 기능** | 사용자가 **명시적으로 호출하는 Explain**을 사용한다. 상시 최신 화면 유지가 기본 책임이 아니다. | ✅ `explain` Skill (최소 구현) |
| **검증 지식** | 상황별 Reference를 **필요할 때 읽는** 구조를 사용한다. | 🚧 |
| **Agent/Subagent 구성** | 필요한 반복 커스텀 역할 **3개(`verifier`, `reviewer`, `researcher`)**를 정의한다. | ✅ `.codex/agents/` |
| **Continuous Evals** | Agent System 자체가 더 나아졌는지 평가하는 **핵심 축**이다. | 🚧 |
| **Eval 도입 시점** | **초기에 작은 Eval을 시작하고 M5에서 체계로 확장한다.** | ✅ `docs/evals/` |
| **상세 결정 순서** | 로드맵·마일스톤 순서를 먼저 정리하고, 내부 상세는 해당 이슈에서 조사·결정한다. | — |

### 초기 Skill 구성 — 2026-09-17 확정 ([#103](https://github.com/taejung3852/OwnHands/issues/103))

| 주제 | 결정 내용 | 구현 |
|---|---|---|
| **이름과 개수** | `write-issue-pr`, `explain`, `grill-spec`, `verify` **4개**. 이름은 고유하게 짓는다 — 이름이 겹칠 때 어느 것이 선택되는지는 공식 문서에 없다(`미확인`). | ✅ |
| **배치** | `.agents/skills/` — Codex REPO scope 탐색 경로다. V1의 `skills/`는 이 경로가 아니었다. | ✅ |
| **판단 축** (공식) | 공식이 제시하는 축은 셋이다 — *"Split workflows when they have different **triggers, inputs, or success criteria**."* **`or`다.** 셋 중 **하나만 달라도** 공식 기준으로는 분할 근거가 된다. | — |
| **분할 게이트** (OwnHands) | **공식보다 엄격하게 쓴다.** 세 축이 **모두** 뚜렷하게 다를 때만 새 Skill 후보로 본다. (`verify`는 Trigger: 구현 후 검증, Input: Spec/Plan/Evidence, Success: PASS/FAIL/UNOBSERVED 판정으로 3축 모두 상이하여 분할 충족). 근거는 10,000 토큰 천장과 description 상호 모순 위험이며, **공식이 요구하는 것이 아니라 우리가 과분할을 막으려고 좁힌 것이다.** | — |
| **분할 게이트의 비용** | ⚠️ **과소분할을 감수하는 선택이다.** 트리거는 같은데 재료·판정이 다른 2/3 사례에서 공식은 나누라 하고 이 게이트는 말린다. 그런 사례가 실제로 오면 게이트를 재검토한다. | — |
| **추가 근거** | ① 위 게이트를 통과하거나, ② Eval에서 관측한 뒤 **description → 본문** 순으로 고쳐도 안 잡힐 때. **빈도는 근거가 아니다.** | — |
| **삭제·병합** | 두 Skill이 서로의 영역에서 오발하면 합치고, 쓰이지 않으면 지운다. 늘리는 규칙만 두지 않는다. | — |
| **지식의 배치** | 깊이는 Skill이 아니라 `references/`로 늘린다. `references/`는 카탈로그 예산을 먹지 않는다. 단 `SKILL.md`가 가리키고 언제 읽을지 적어야 로드된다. | ✅ |
| **공통 규율의 자리** | 기본은 **각 Skill 안**이다. `AGENTS.md`에는 **반복해서 고쳐야 했던 것만** 올린다. ⚠️ "관측 후에 올린다"는 OwnHands의 판단이다. 공식 문서는 `Working agreements`·`Repository expectations`도 `AGENTS.md` 내용으로 들며, **관측 전에 두면 안 된다고 말하지 않는다.** | ✅ |
| **`AGENTS.md`의 현재 내용** | **한 줄뿐이다** — "우리 결정을 플랫폼이 정한 것처럼 쓰지 않는다." 2026-09-17 세션에서 **세 번 고쳐야 했기 때문에** 올렸다. 상상해서 추가하지 않는다. | ✅ |
| **Claude Code 대응** | `CLAUDE.md`는 `@AGENTS.md` **한 줄 import**다. 공식이 제시한 패턴이고, 내용을 두 벌로 관리하지 않는다. Claude Code는 `AGENTS.md`를 직접 읽지 않는다. | ✅ |
| **Explain의 출력 형태** | **HTML 스토리 카드를 기본으로 한다.** ELI5 시각 모델(카드당 최대 2줄, 시각 메타포, 퀴즈 토글)을 수용하되 엔지니어링 도메인 어휘를 보존한다 ([ADR-0002](adr/0002-explain-visual-story-cards.md)). | ✅ `shape.md` |
| **링크 전달 방식** | 스킴을 고정하지 않는다. 표면이 정한다 — Codex는 `file_opener`(기본 `vscode`)로 정하고, 렌더링하는 표면은 직접 표시한다. | ✅ |

> ⚠️ **개수 제한은 실제 수치다.** Skill 목록 예산의 천장은 **10,000 토큰**이고(`skills.max_context_tokens`의 명시값 상한), 초과하면 description이 깎이는 데 그치지 않고 **Skill이 목록에서 빠진다.** → [Codex 공식 문서 §2.5](references/codex-official.md)

### Work Item(Issue/PR) 표기 규격 — 2026-09-18 확정 ([#108](https://github.com/taejung3852/OwnHands/issues/108), [ADR-0003](adr/0003-work-item-human-brief.md))

| 주제 | 결정 내용 | 구현 |
|---|---|---|
| **표기 구조** | **`Human Brief (3칸 고정)` + `<details>`(상세 맥락)** 구조를 사용한다. | ✅ `write-issue-pr` |
| **3칸 고정 규칙** | PR은 `무엇이 바뀌었나`·`왜 이렇게 했나`·`리뷰할 것`, Issue는 `무엇이 필요한가`·`왜 지금인가`·`결정할 것`. 4번째 칸은 추가하지 않는다. | ✅ |
| **분리 기준** | 독자(사람/기계)가 아닌 **깊이(Depth)**로 나눈다. `<details>`는 비공개가 아니라 심층 기록이다. | ✅ |
| **단일 진실 원칙** | Human Brief는 상세 맥락의 축약 투영(Projection)이다. 상세가 뒷받침하지 않는 독립 사실을 만들지 않는다. | ✅ |
| **Explain과의 경계** | GitHub 본문은 가벼운 마크다운으로 유지하고, 시각화·쉬운 이해는 요청형 `explain` 아티팩트로 분리한다. | ✅ |

### Intent & Spec 산출물 규격 — 2026-09-18 확정 ([#116](https://github.com/taejung3852/OwnHands/issues/116), [ADR-0004](adr/0004-intent-spec-specification.md))

| 주제 | 결정 내용 | 구현 |
|---|---|---|
| **저장 위치** | `docs/specs/<feature-name>/` 아래 영구 Git 아티팩트로 보존 (`intent.md`, `spec.md`, `plan.md`). | ✅ `specs/README.md` |
| **`intent.md`** | **"의도와 경계의 엄밀함"**. 문제(Why), 목표(What), **비목표(Non-goals)**, 제약(Constraints) 필수 정의. | ✅ |
| **`spec.md`** | **"기술 구현의 극대화된 디테일"**. 에이전트 환각을 차단하기 위해 요구사항, 아키텍처/타입, 엣지케이스, 수용조건을 상세히 기술. | ✅ |
| **기본 흐름 (Default Flow)** | 의도 검토(intent) ➔ 설계 검토(spec) ➔ 구현·검증(plan & feedback loop)의 3단계를 기본 권장 흐름으로 둠. (사소한 작업에는 면제) | ✅ `ADR-0007` |

### plan.md 아티팩트 및 Build Feedback Loop — 2026-09-19 확정 ([#123](https://github.com/taejung3852/OwnHands/issues/123), [ADR-0007](adr/0007-plan-artifact-and-build-feedback-loop.md))

| 주제 | 결정 내용 | 구현 |
|---|---|---|
| **저장 위치** | `docs/specs/<feature-name>/plan.md` 아래 영구 Git 아티팩트로 보존. (`intent` ➔ `spec` ➔ `plan` 3단계 체인) | ✅ `specs/README.md` |
| **`plan.md` 규격** | **"실행 단위 분해와 신선한 증거"**. 대상 파일(Blast Radius Guard), 작은 작업 분해(Task Breakdown), 양방향 추적성 매핑, 신선한 증거 체크리스트 필수 기술. | ✅ `ADR-0007` |
| **위계 구조** | **SDD > Verification Strategy > TDD**. 스펙이 상위 계약이며, TDD는 실행 가능한 로직을 위한 단위 피드백 루프로 배치 (OwnHands 자체 설계). | ✅ `ADR-0007` |
| **수용 기준 매핑** | AC-테스트 1:1 강제 안티패턴을 배제하고, ISTQB 블랙박스 기법(동등분할/경계값 분석) 및 양방향 추적성에 따라 유연 매핑 (1:N, N:1 허용). | ✅ `ADR-0007` |
| **신선한 증거 (Iron Law)** | 직접 관측된 최신 증거(테스트 출력, 스크린샷, 정적 검사 무에러 등) 없이는 완료 주장을 할 수 없다. (자가합리화 및 허위 통과 차단) | ✅ `ADR-0007` |
| **회귀 방어선** | 작업 완료 전 회귀 테스트를 실행하여 실행된 회귀 스위트 범위 내 실패 미관측(No failures observed)을 확인. | ✅ `ADR-0007` |
| **테스트 부재 시 방어선** | 기존 테스트 부재 시 변경 반경 통제 + 네이티브 프로젝트 검사 무에러 증거 + 명시적 선언(미실행 검사는 `[UNOBSERVED]`). | ✅ `ADR-0007` |
| **기준선 테스트 보존** | `Existing tests are baseline, not immutable`. 실패 회피를 위한 무단 수정/삭제 금지, 승인된 스펙 변경 시 정상 수정 허용. | ✅ `ADR-0007` |
| **2단계 검증 게이트** | 구현자 자체 피드백 루프 ➔ 완료 직전 독립된 read-only `verifier` Subagent의 `PASS / FAIL / UNOBSERVED` 판정. | ✅ `ADR-0007` |
| **기준선 버전 관리** | 구현 중 스펙 충돌/새 제약 발견 시 자의적 수정 금지, `spec.md` 수정 ➔ 사람 승인 ➔ `plan.md` 재정렬 절차 준수. | ✅ `ADR-0007` |

### Continuous Evals 체계 및 Task Set 규격 — 2026-09-19 확정 ([#134](https://github.com/taejung3852/OwnHands/issues/134), [ADR-0009](adr/0009-continuous-evals-task-set-and-runner.md))

| 주제 | 결정 내용 | 구현 |
|---|---|---|
| **단일 Task Set 규격** | 5대 축적 Eval을 단일 선언형 JSON(`docs/evals/task-set.json`) 스키마로 관리하고, `execution_mode(static / runtime / composite)` 및 `sandbox_mode(read-only / isolated-write)`를 이원화한다. (2026-09-19 사용자 승인: Zero-Dependency 및 Thin Harness 우선) | ✅ `ADR-0009` |
| **Eval Orchestrator** | `scripts/run-evals.js`로 빠른 정적 Preflight를 실행하고, 런타임 인터페이스 및 바이너리 환경을 정직하게 감지(Preflight + Interface Detection)한다. (실제 codex exec 구동/Judge는 후속 연계) | ✅ `ADR-0009` |
| **자체 Dry-run 평가 환경** | Codex 공식 CLI에 generic `--dry-run` 플래그는 부재하므로, 외부 GitHub 이슈/PR 무단 생성 차단은 OwnHands 러너 격리 환경이 담당한다 (AGENTS.md 준수). | ✅ `ADR-0009` |
| **3-State Delta Matrix** | 단순 합격률(%) 착시를 배제하고, `docs/evals/baselines/current.json` 기준선 대비 `PASS ➔ UNOBSERVED/FAIL` 상태 전이를 핀포인트로 감지한다. | ✅ `ADR-0009` |

### 검증 가이드라인 및 Verifier 감사 프로토콜 — 2026-09-19 확정 ([#127](https://github.com/taejung3852/OwnHands/issues/127), [ADR-0008](adr/0008-verification-references-and-verifier-protocol.md))

| 주제 | 결정 내용 | 구현 |
|---|---|---|
| **가이드라인 캡슐화** | 사람이 읽는 `docs/` 공간을 어지럽히지 않고, 검증 지침을 `.agents/skills/verify/references/`에 온디맨드로 캡슐화한다. | ✅ `.agents/skills/verify/` |
| **Verifier 지침 내장** | Verifier의 감사 프로토콜을 외부 문서 참조에 의존하지 않고 `.codex/agents/verifier.toml`의 `developer_instructions`에 직접 내장한다. | ✅ `verifier.toml` |
| **독립 감사관 모델** | Verifier는 테스트 러너가 아니라 Builder가 제출한 applicable Fresh Evidence(테스트, UI 스크린샷, 벤치마크, 린트)를 AC와 역추적 대조하는 독립 감사관이다. | ✅ `ADR-0008` |
| **3대 상태 어휘** | Verifier 판정은 `PASS / FAIL / UNOBSERVED` 3종으로만 엄격하게 규정한다. | ✅ `ADR-0008` |
| **비교 주장 Before 기준선** | 버그 수정(`bugfix`) 및 성능 개선(`performance`) 주장 시 코드 수정 전 결함/수치 증거(Before Baseline)를 필수 확인하며, 부재 시 `[UNOBSERVED]`로 판정한다. | ✅ `ADR-0008` |



### grill-spec 인터뷰 도우미 설계 — 2026-09-18 확정 ([#119](https://github.com/taejung3852/OwnHands/issues/119), [ADR-0006](adr/0006-grill-spec-orchestration-tradeoffs.md))

| 주제 | 결정 내용 | 구현 |
|---|---|---|
| **오케스트레이션** | Matt Pocock upstream primitive를 재사용하고, OwnHands는 GORE 닻 내리기와 산출물 규약만 얹는 **Thin Orchestration**을 채택한다. (자체 재구현 배제) | ✅ `.agents/skills/grill-spec/` |
| **Skill 구성** | 인위적으로 2개 분할하지 않고 **단일 `grill-spec`**에 3대 Stage Mode(`intent-only`, `spec-from-intent`, `full-flow`)를 지원한다. | ✅ `SKILL.md` |
| **단계 분리 장치** | 무조건 턴 종료(Hard Barrier) 대신 **기본 대기선(Default Barrier)**을 두어 미승인 Intent의 Spec 오염을 차단한다. | ✅ `SKILL.md` |
| **책임 분리** | 코드베이스 팩트는 에이전트가 직접 조사하고, 비목표·정책 결정은 사용자에게 질문한다. | ✅ `interview-guide.md` |
| **Wayfinder 경계** | 일반 기능에 쓰지 않고, 단일 세션을 초과하는 대형 다중 세션 과제에만 후보로 안내한다. | ✅ `interview-guide.md` |


### 초기 Agent/Subagent 구성 — 2026-09-18 확정 ([#104](https://github.com/taejung3852/OwnHands/issues/104), [ADR-0001](adr/0001-initial-subagent-roles.md))

| 주제 | 결정 내용 | 구현 |
|---|---|---|
| **역할과 개수** | **3개** (`verifier`, `reviewer`, `researcher`). | ✅ `.codex/agents/*.toml` |
| **`verifier`** | 독립 수용성 검증 및 테스트 판정 전담. 구현자(부모)의 편향·자기합리화 차단 목적. `sandbox_mode = "read-only"`. | ✅ |
| **`reviewer`** | Git diff 및 프로젝트 규율(`AGENTS.md`) 검토 전담. `sandbox_mode = "read-only"`. | ✅ |
| **`researcher`** | 대량의 웹/문서 자료 조사 및 요약 전담. 메인 컨텍스트 윈도우 오염 방지 목적. | ✅ |
| **Build 전담** | 보류. 별도 커스텀 에이전트를 만들지 않고 필요시 Codex 내장 `worker`를 호출한다. | — |
| **Writer 전담** | 기각. `explain`과 `write-issue-pr`은 세션 맥락 직렬화 오버헤드를 피하기 위해 기존 **Skill 체제를 유지**한다. | — |

### 조직 정책 연결 경계 — 2026-09-18 확정 ([#105](https://github.com/taejung3852/OwnHands/issues/105), [ADR-0005](adr/0005-policy-layering-boundary.md))

| 주제 | 결정 내용 | 구현 |
|---|---|---|
| **Zero-Code 원칙** | Policy Resolver, 우선순위 가중치 계산기, 예외 처리 엔진을 코드로 구현하지 않는다. | ✅ |
| **지침 계층 분리** | `~/.codex/`는 개인 기본값, 저장소 root 및 하위 `AGENTS.override.md`는 프로젝트/모듈 지침으로 분리하고 설명 가이드만 제공한다. | ✅ `ADR-0005` |
| **조직 강제 정책 분리** | 보안·권한·컴플라이언스 등 전사 강제 규칙은 프롬프트 지침이 아닌 Enterprise Managed Config 영역으로 분리한다. | ✅ `ADR-0005` |
| **가상 정책 작성 배제** | 실제 조직 도입 및 검증 전까지 가상의 회사 정책을 임의로 작성하지 않는다 (Non-goal). | — |

### 확정 방향 중 특히 자주 오해되는 것

> **Eval은 M5에서 시작하는 것이 아니다.**
> 초기(`V2-M1`~`V2-M4`)부터 작은 Eval을 돌린다. `V2-M5`는 **시작이 아니라 확장** 지점이다.
> 반대로 M1부터 완전한 Eval 플랫폼을 만들지도 않는다. → [Eval 도입](#6-eval-도입-방식)

---

## 2. 사용자 생각 (확정 규칙이 아니다)

| 주제 | 현재 생각 | 주의 |
|---|---|---|
| *(현재 열린 생각 항목 없음)* | 2026-09-18: Company 정책은 복잡한 경우의 수 및 실효성 문제로 가상 작성을 배제하고 네이티브 설명 가이드(ADR-0005)로 방향 종결. | — |

---

## 3. 사용자와 함께 결정할 것

에이전트가 대신 확정하지 않는다. 현재 열려 있는 사용자 공동 결정 항목:

| 주제 | 결정할 내용 | 연결 |
|---|---|---|
| *(현재 열린 결정 항목 없음)* | 2026-09-19: M5 Continuous Evals 체계 및 Task Set 규격(ADR-0009) 사용자 승인으로 확정. | ✅ [ADR-0009](adr/0009-continuous-evals-task-set-and-runner.md) |

> ⚠️ `write-issue-pr`과 `explain`은 **확정된 Skill 이름**, `verifier`·`reviewer`·`researcher`는 **확정된 Subagent 이름**이다.
> 그 밖에 문서에 보이는 `intent`, `design` 같은 표현은
> **역할 설명 또는 후보이지 확정된 이름이 아니다.**

---

## 4. 후속 결정 — 해당 이슈에서 조사와 함께 정한다

| 주제 | 현재 상태 | 연결 |
|---|---|---|
| **다른 Vendor 지원** | adapter로 할지, 같은 저장소로 할지, 별도 저장소로 할지 **미정**. | ⏳ |
| **공통 추상화** | 두 번째 플랫폼의 **실제 필요를 확인하기 전에** 범용 adapter나 공통 실행 엔진을 확정하지 않는다. | ⏳ |
| **Artifact 형식** | `intent.md`·`spec.md`·`plan.md` 저장 경로와 필수 규격 확정(✅ [ADR-0004](adr/0004-intent-spec-specification.md), ✅ [ADR-0007](adr/0007-plan-artifact-and-build-feedback-loop.md)). 메타데이터 및 자동화 규칙은 ⏳ 후속 결정. | ✅ / ⏳ |
| **Eval 상세** | 초기 작은 Eval 5종(`0001`-`0005`) 수립 완료. V2-M5 Step ① 조사 및 Step ② 규격 제정(✅ [ADR-0009](adr/0009-continuous-evals-task-set-and-runner.md)) 완료, Step ③ 러너 및 5대 과제 구현 진행 중. | [#134](https://github.com/taejung3852/OwnHands/issues/134) |
| **Hooks 상세** | 적용 역할은 논의했으나 구체 이벤트·규칙·권한·구현은 후속 설계. | [#102](https://github.com/taejung3852/OwnHands/issues/102) |
| **마일스톤 내부 설계** | 이름·수·순서는 승인·등록됐다. 각 단계의 **내부 설계와 경계 조정**은 해당 이슈에서 정한다. | [#101](https://github.com/taejung3852/OwnHands/issues/101) |
| **개발 속도** | 공식 기능을 활용하면 더 빨라질 것으로 **기대**한다. 이미 시간을 절감했다고 쓰지 않는다. | — |

---

## 5. 마일스톤의 승인 상태

| 항목 | 상태 |
|---|---|
| M5의 **평가 확장 방향** | ✅ 확정 |
| 마일스톤 **이름·수·순서** | ✅ 2026-09-16 사용자 승인 (8개 그대로) |
| GitHub Milestone 등록 | ✅ [V2-M0 ~ V2-M7](https://github.com/taejung3852/OwnHands/milestones) |
| 각 마일스톤 **내부 설계** | ⏳ 해당 이슈에서 결정 |
| 마일스톤 **경계 조정** | ⏳ 이슈 분해 후 필요하면 사용자와 합친다 |

> ⚠️ **마일스톤이 등록됐다는 것과 그 안의 설계가 확정됐다는 것은 다르다.**
> 상세는 [로드맵](roadmap.md).

---

## 6. Eval 도입 방식

```text
초기 (V2-M1 ~ V2-M4)            V2-M5
──────────────────────         ──────────────────────
작은 Eval을 실제로 돌린다        축적한 과제를 체계로 확장
실제 Skill·지침·workflow를       task set · 기준선 · 지표
대표 작업으로 확인               replay · 비교 · 회귀 판단
사례와 결과를 축적               (정확한 구현은 그때 설계)
```

| 하지 않을 것 | 이유 |
|---|---|
| ❌ M5에서 처음 평가를 시작 | 확정 결정에 어긋난다 |
| ❌ M1부터 완전한 Eval 플랫폼 구축 | 과설계다 |

지표 후보(성공률·검증 누락·불필요한 수정·사람 개입·토큰·시간·오차단)는 **후보**이며 이 문서에서 수치나 채택 알고리즘을 고정하지 않는다.

주의: 과거 작업의 시작 상태와 결과를 구분한다. **동일 캐시를 여러 번 읽은 것을 독립 생성 평가로 세지 않는다.**

---

## 7. 이번 문서 작업에서 하지 않은 것

| 하지 않음 | 이유 |
|---|---|
| V2 제품 코드 구현 | 이번 작업은 문서·작업 관리 재구성이다 |
| V2용 패키지·MCP·플러그인·Skill 구조 신설 | 필요해지는 마일스톤에서 공식 문서를 조사하고 결정한다 |
| 미결정 사항의 대리 확정 | 사용자 결정 사항이다 |
| V1 문서 **내용** 수정 | 본문을 고치지 않고 태그에 보존했다 |
| V1 Git history 삭제·커밋 rewrite·force push | 이력은 그대로 둔다 |
| 저장소 공개 범위·권한 변경 | 이번 작업 범위가 아니다 |

**사용자 승인 후 수행한 것** (2026-09-16)

| 수행 | 내용 |
|---|---|
| GitHub Milestone 등록 | `V2-M0`~`V2-M7` 8개 |
| V1 추적 이슈 종료 | #7·#89·#99 — `not planned`로 닫고 **방향 변경에 의한 대체**로 기록. `완료`로 위장하지 않았다 |
| 저장소 설명 변경 | V1 문구 → V2 정의 |
| **V1 snapshot 태그 생성** | [`pre-v2-2026-09-16`](https://github.com/taejung3852/OwnHands/tree/pre-v2-2026-09-16) — 완성본·릴리스가 아니다 |
| **V1 실행 자산·원본 문서를 현재 tree에서 제거** | clean-slate 출발선을 비운다. 원본은 태그에 있다 |

---

## 관련 문서

- [프로젝트 여정](story/project-journey.md) · [왜 V2인가](story/why-v2.md)
- [V2 개요](overview.md) · [로드맵](roadmap.md) · [개발 방법](development-method.md)
- [Anthropic Playbook 대응](references/anthropic-playbook.md) · [Codex 공식 문서 확인](references/codex-official.md)

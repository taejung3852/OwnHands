# Codex 공식 문서 확인 기록

> **이 문서의 규칙**
> 실제로 읽은 것만 적는다. 읽지 못한 것은 `미확인`으로 남긴다.
> 기억에 의존해 설정 키나 지원 기능을 만들어내지 않는다. 커뮤니티 글로 조용히 대체하지 않는다.
> **근거의 성격을 구분한다.** `learn.chatgpt.com/docs` = 사양, `developers.openai.com/blog` = 권고,
> `developers.openai.com/api/docs` = **API 표면**. 세 층을 같은 무게로 섞지 않는다.
>
> **확인일: 2026-09-16** · 확인 방법: 문서 URL 직접 조회 + Markdown twin 원문 수령 + `llms-full.txt` 전량 grep

Codex는 V2의 1차 실행 플랫폼이므로, **실제 형식·기능·권한·제약의 기준은 Anthropic Playbook이 아니라 이 문서**다.

조사 경위는 [#102](https://github.com/taejung3852/OwnHands/issues/102). 조사 방법의 원칙은 [개발 방법](../v2/development-method.md).

---

## 0. 문서 위치와 원문을 받는 방법

### 0.1 경로 이동 (2026-09-16 확인, 재이동 없음)

기존에 참고하던 `developers.openai.com/codex/*` 경로는 **308 Permanent Redirect**로 이동했다.

| 이전 URL | 현재 URL | 상태 |
|---|---|---|
| `https://developers.openai.com/codex/` | <https://learn.chatgpt.com/docs> | 308 → 200 |
| `https://developers.openai.com/codex/skills` | <https://learn.chatgpt.com/docs/build-skills> | 308 → 200 |
| `https://developers.openai.com/codex/guides/agents-md` | <https://learn.chatgpt.com/docs/agent-configuration/agents-md> | 308 → 200 |

**재조사 시점에도 `learn.chatgpt.com/docs` 기준 경로는 그대로 유효하다.** 리다이렉트 없이 200이다.

⚠️ 단, **블로그는 이동하지 않았다.** `developers.openai.com/blog/*`와 `developers.openai.com/api/docs/*`는 현재도 그 호스트에 있다. "`developers.openai.com`은 옛 주소"가 아니라 **`/codex/*` 경로만 옮겨갔다.**

### 0.2 공식 Markdown twin이 존재한다

`build-skills.md`를 열면 문서 자체가 이렇게 밝힌다.

> "For the complete documentation index, see [llms.txt](https://learn.chatgpt.com/llms.txt). Markdown versions of documentation pages are available by appending `.md` to the page URL."

`llms.txt`의 첫 문장:

> "Use this as a compact map of ChatGPT docs for Codex. Each page has a Markdown twin at `/docs/<slug>.md` for direct ingestion."

공식이 제공하는 통합본:

| 파일 | 내용 |
|---|---|
| `https://learn.chatgpt.com/llms.txt` | 문서 전체 인덱스 (페이지별 1줄 설명) |
| `https://learn.chatgpt.com/docs/llms-full.txt` | **단일 파일 Markdown 전량 export** (확인 시 약 1.81 MB) |
| `https://learn.chatgpt.com/docs/codex-manual.md` | 문서 세트에서 생성된 기계용 압축 매뉴얼 |
| `https://developers.openai.com/blog/llms.txt` | 개발자 블로그 인덱스 |

**이것이 이 문서의 조사 방법이다.** 아래의 `미확인` 판정은 페이지 하나를 읽고 내린 것이 아니라 **`llms-full.txt` 전량 grep**으로 확인한 것이다. → [개발 방법](../v2/development-method.md)의 조사 절차에 반영한다.

예외 하나: `https://learn.chatgpt.com/guides/best-practices.md`는 **404**다(HTML 경로는 200). `.md` 규칙이 모든 페이지에 적용되지는 않는다.

### 0.3 문서의 적용 환경 표기 방식

문서는 `<ContentModeSwitch group="codex-surface" ids="...">` 블록으로 표면별 내용을 분리한다.

| id | 표면 |
|---|---|
| `web` | ChatGPT 웹 / Work |
| `app` | ChatGPT 데스크톱 앱 (macOS/Windows) |
| `cli` | Codex CLI |
| `ide` | Codex IDE extension |

**이 블록 밖의 문장은 표면 구분 없는 공통 서술이다.** 아래 각 절의 "적용 환경"은 이 표기를 근거로 적었다.

지원 표면 전체: Codex CLI · IDE extension · ChatGPT 웹 · **Codex cloud** · 데스크톱 앱 · 원격 연결.

> ⚠️ **Codex cloud는 별개 표면이다.** 데스크톱 앱이 아니다. `chatgpt.com/codex`에서 격리된 원격 환경에 작업을 위임해 백그라운드로 돌리는 기능이다 — "Run tasks in isolated cloud environments, work in parallel, and start work from the web, GitHub, GitLab, Linear, or Slack." 로컬 실행(CLI·앱·IDE)과 구분한다. → [§5.7](#57-codex-표면별-astra-가용성)

> Codex App/CLI/IDE와 일반 API·SDK의 적용 범위는 다르다. 아래 §1~§4는 **Codex 표면** 기준이고, §5.5~5.6은 **API 표면**이다.

---

## 1. AGENTS.md — 프로젝트 지침

출처: <https://learn.chatgpt.com/docs/agent-configuration/agents-md> · 확인일 2026-09-16

### 확인한 동작

**탐색 순서**

1. 전역: `~/.codex/AGENTS.override.md` 또는 `~/.codex/AGENTS.md` (먼저 존재하는 쪽)
2. 프로젝트: Git root에서 현재 디렉터리까지 내려오며 각 단계에서 `AGENTS.override.md` → `AGENTS.md` → fallback 파일명 순으로 확인

**병합 규칙**

> "Codex concatenates files from the root down, joining them with blank lines. Files closer to your current directory override earlier guidance because they appear later in the combined prompt."

- 같은 단계에서는 `AGENTS.override.md`가 `AGENTS.md`보다 우선
- 프로젝트 지침이 전역 지침을 덮어씀
- 디렉터리 트리에서 더 깊은 파일이 더 얕은 파일을 덮어씀

**제약**

- 빈 파일은 건너뜀
- 합산 크기가 `project_doc_max_bytes` (기본 **32 KiB**)에 도달하면 더 추가하지 않음
- `~/.codex/config.toml`에서 조정 가능

**권장 내용**: 작업 합의·프로젝트 규범, 코드 리뷰 규칙(`## Code Review Rules` 절), 저장소별 기대사항, 하위 디렉터리의 서비스/팀별 override

**갱신 권고** (출처: <https://learn.chatgpt.com/docs/customization/overview>)

> "**Updating `AGENTS.md`:** Start with only the instructions that matter. Codify recurring review feedback, put guidance in the closest directory where it applies, and tell the agent to update `AGENTS.md` when you correct something so future sessions inherit the fix."

> "- **Too much reading**: If it finds the right files but reads too many documents, add routing guidance (which directories/files to prioritize)."

### OwnHands에 주는 의미

- **지침 계층이 이미 네이티브로 존재한다.** 전역 default ↔ 프로젝트 override라는 구조가 이미 있다.
- 🤔 사용자가 생각 중인 "default + company 정책" 구분과 겹치는 지점이다. **단, 이것이 Company 우선 정책을 확정한다는 뜻은 아니다.** → [결정 상태표](../v2/decisions.md)
- 32 KiB 상한은 실질적 제약이다. 긴 지식을 지침에 넣지 말고 **Reference로 분리**할 근거가 된다.
- "routing guidance"라는 표현이 §5.2의 router 권고와 같은 방향이다.

### 직접 만들지 않아도 되는 것
- 지침 파일 탐색·병합·우선순위 처리
- 디렉터리 범위별 지침 override 메커니즘

### 아직 확인하지 못한 것
- **이 페이지에는 `Astra`가 한 번도 등장하지 않는다.** §5.3의 "지침에서 제거하라"는 권고는 **블로그에만 있고 이 사양 페이지에 반영돼 있지 않다.** docs 쪽 반영 시점은 미확인.
- `AGENTS.md`가 subagent에도 적용되는지 → [§4.6](#46-부모자식-컨텍스트-전달-범위--미확인)

---

## 2. Skills

출처: <https://learn.chatgpt.com/docs/build-skills> · <https://learn.chatgpt.com/docs/customization/overview> · <https://developers.openai.com/plugins/build/skills> · 확인일 2026-09-16

### 2.1 구조와 필수 필드

`SKILL.md`를 담은 디렉터리. frontmatter 필수 필드는 `name`, `description`.

> "A skill is a directory with a `SKILL.md` file plus optional scripts and references. The `SKILL.md` file must include `name` and `description`."

```text
<skill>/
├── SKILL.md            # 필수. frontmatter: name, description
├── scripts/            # 실행 코드
├── references/         # 문서
├── assets/             # 템플릿·리소스
└── agents/openai.yaml  # UI 메타데이터·호출 정책·도구 의존성
```

각 디렉터리의 용도(원문):

> "Keep `SKILL.md` concise and place detailed material next to it:
> - Use `references/` for policies, schemas, examples, and background material.
> - Use `assets/` for templates or files the workflow should copy or transform.
> - Use `scripts/` when the workflow needs deterministic computation or file processing."

> "Do not add a script when instructions and existing tools can complete the task reliably."

### 2.2 탐색 위치와 scope

문서는 이것을 우선순위가 아니라 **scope 표**로 제시한다.

> "Codex reads skills from repository, user, admin, and system locations."

| Scope | 위치 |
|---|---|
| REPO | `$CWD/.agents/skills` |
| REPO | `$CWD/../.agents/skills` (Git 저장소의 상위 폴더) |
| REPO | `$REPO_ROOT/.agents/skills` |
| USER | `$HOME/.agents/skills` |
| ADMIN | `/etc/codex/skills` |
| SYSTEM | Codex에 내장 (OpenAI 제공) |

**호출**: 명시적으로는 ChatGPT에서 `@skill`, Codex/IDE에서 `$skill`. 암묵적으로는 사용자 프롬프트가 skill의 `description`과 맞을 때.

**지원 표면**: 단독 skill은 ChatGPT 데스크톱 앱·Codex CLI·IDE extension. 플러그인 번들 skill은 웹·데스크톱·모바일의 Chat/Work에서도 동작.

### 2.3 같은 이름의 Skill — 문서는 그 이상을 말하지 않는다

> "If two skills share the same `name`, Codex doesn't merge them; **both can appear in skill selectors.**"

⚠️ **어느 것이 실제로 선택되는지는 문서에 없다. `미확인`이다.** `llms-full.txt` 전량 grep으로 확인했고, 이름 충돌을 다루는 문장은 위 하나뿐이다.

문서가 `precedence`를 말하는 곳은 전부 **다른 대상**이었다. 혼동하지 않도록 명시한다.

| 문서가 precedence를 말하는 대상 | 원문 |
|---|---|
| `AGENTS.md` 지침 체인 | "Discovery follows this precedence order" |
| custom agent 파일의 `model`/`model_reasoning_effort` | "the value in the file takes precedence" |
| **custom agent 이름 충돌** | "If a custom agent name matches a built-in agent such as `explorer`, your custom agent takes precedence." |
| `config.toml` 설정 레이어 | "Codex resolves values in this order (highest precedence first)" |

⚠️ **주의할 대비.** Codex는 **custom agent** 이름 충돌에는 우선순위를 명시하는데, **Skill** 이름 충돌에는 "합치지 않는다"까지만 쓴다. 이 차이는 의도적으로 보이지만, **Skill 쪽에 우선순위가 없다고 단정할 근거도 아니다.** 양쪽 다 추정하지 않는다.

**ADMIN scope이 USER/REPO를 덮어쓴다는 서술은 여전히 문서에 없다.**

### 2.4 progressive disclosure — `references/`는 필요할 때 읽는다

출처: <https://learn.chatgpt.com/docs/customization/overview> ("Skills" 절)

> "Codex uses progressive disclosure for skills:
> - It starts with metadata (`name`, `description`) for discovery
> - It loads `SKILL.md` only when a skill is chosen
> - **It reads references or runs scripts only when needed**"

> "This budget applies only to the initial skills list. When Codex selects a skill, it still reads the full SKILL.md instructions for that skill."

**답: 전량 선로딩이 아니다.**

⚠️ **다만 공짜가 아니다.** 저작 측 책임이 문서에 명시돼 있다.

> "**Reference supporting files from `SKILL.md` and explain when to load or run them.**"

즉 `references/`에 파일을 넣어 두기만 하면 읽히는 것이 아니라, **SKILL.md 본문이 그 파일을 가리키고 언제 읽을지 적어야** 한다. 자동 색인이나 의미 검색이 있다는 서술은 **없다.**

### 2.5 컨텍스트 예산 — 기존 기록 정정

출처: <https://learn.chatgpt.com/docs/build-skills> · <https://learn.chatgpt.com/docs/config-file/config-reference>

> "In Codex, the initial list also includes each skill's **file path**. To avoid crowding out the rest of the prompt, this list uses at most 2% of the model's context window, or 8,000 characters when the context window is unknown. If many skills are installed, Codex shortens skill descriptions first. **For large skill sets, Codex may omit some skills from the initial list and show a warning.**"

`config.toml`에서 확인된 `skills.*` 키는 다음 넷이 전부다(config reference 전수 확인).

| 키 | 타입 | 설명(원문) |
|---|---|---|
| `skills.max_context_tokens` | integer (positive) | "Token budget for the available-skills catalog. Defaults to 2% of the model's context window. **Explicit values are capped at `10000` tokens.**" |
| `skills.config` | array\<object\> | "Per-skill enablement overrides stored in config.toml." |
| `skills.config.<index>.path` | string (path) | "Path to a skill folder containing `SKILL.md`." |
| `skills.config.<index>.enabled` | boolean | "Enable or disable the referenced skill." |

인접 키 하나: `features.skill_mcp_dependency_install` (boolean) — "Allow prompting and installing missing MCP dependencies for skills (stable; on by default)."

**기존 기록 대비 정정 3건**

1. 초기 목록에는 `name`·`description`뿐 아니라 **파일 경로도 포함된다.** 경로가 길면 그만큼 예산을 먹는다.
2. 상한은 조정 가능하지만 **명시값은 10,000 토큰으로 캡된다.** Astra의 컨텍스트 1,050,000에 2%를 적용하면 21,000이지만 **실제 천장은 10,000이다.**
3. description이 짧아지는 것으로 끝이 아니다. **Skill이 목록에서 아예 빠질 수 있다.** 빠지면 모델은 그 Skill의 존재를 모른다.

> ⚠️ **"모델 컨텍스트가 커지면 Skill을 많이 둬도 된다"는 가정은 틀렸다.** 천장이 10,000 토큰으로 고정돼 있다. 여기에 §5.6의 272K 초과 과금까지 겹치면, 컨텍스트를 크게 쓰는 방향은 **위아래로 막혀 있다.**

### 2.6 frontmatter 선택 필드 — OpenAI 공식 문서에는 목록이 없다

`llms-full.txt` 전량 grep 결과, OpenAI 공식 문서는 "must include `name` and `description`"까지만 말한다. **선택 필드를 하나도 나열하지 않는다.** corpus 안의 모든 SKILL.md 예시(`commit`, `meeting-follow-up`, `recent-code-bugfix`, `tabletop-dice`, `skill-name`) frontmatter에도 그 둘 외의 키가 없다.

**→ 선택 필드 전체 목록은 `미확인`이다.**

다만 공식 문서가 상위 표준을 지목한다.

> "Skills build on the [open agent skills standard](https://agentskills.io)."

> ⚠️ **아래 표는 `agentskills.io/specification`(200, 확인일 2026-09-16)에서 읽은 것이며 OpenAI 공식 문서가 아니다.**
> OpenAI 문서가 "이 표준 위에 만들어졌다"며 링크한 **외부 표준 사양**이다.
> **Codex가 이 필드들을 실제로 읽는다는 것은 OpenAI 공식 문서로 확인되지 않았다.** 근거의 층이 다르므로 분리해 둔다.

| 필드 | 필수 | 외부 표준이 명시한 제약 |
|---|---|---|
| `name` | Yes | 최대 64자. 소문자·숫자·하이픈만. 하이픈으로 시작/종료 불가. 연속 하이픈 불가. **부모 디렉터리 이름과 일치해야 함** |
| `description` | Yes | 최대 1024자. 비어 있을 수 없음 |
| `license` | No | 라이선스 이름 또는 번들된 라이선스 파일 참조 |
| `compatibility` | No | 최대 500자. 환경 요구사항 |
| `metadata` | No | 임의의 key-value 매핑 (string → string) |
| `allowed-tools` | No | 공백 구분 문자열. 사전 승인된 도구. **(Experimental)** |

⚠️ `allowed-tools`는 외부 표준에서도 Experimental이고 OpenAI 문서에 없다. **Skill별 도구 제한을 이것으로 설계하지 않는다.** Codex에서 도구 범위를 좁히는 확인된 수단은 subagent의 `mcp_servers`·`sandbox_mode`다([§4](#4-subagents)).

### 2.7 `agents/openai.yaml` — 예시는 있고 스키마 표는 없다

출처: <https://learn.chatgpt.com/docs/build-skills> ("Optional metadata")

> "Add `agents/openai.yaml` to configure UI metadata in the ChatGPT desktop app, to set invocation policy, and to declare tool dependencies for a more seamless experience with using the skill."

문서가 제시하는 전체 예시:

```yaml
interface:
  display_name: "Optional user-facing name"
  short_description: "Optional user-facing description"
  icon_small: "./assets/small-logo.svg"
  icon_large: "./assets/large-logo.png"
  brand_color: "#3B82F6"
  default_prompt: "Optional surrounding prompt to use the skill with"

policy:
  allow_implicit_invocation: false

dependencies:
  tools:
    - type: "mcp"
      value: "openaiDeveloperDocs"
      description: "OpenAI Docs MCP server"
      transport: "streamable_http"
      url: "https://developers.openai.com/mcp"
```

동작이 서술된 유일한 키:

> "`allow_implicit_invocation` (default: `true`): When `false`, Codex won't implicitly invoke the skill based on user prompt; explicit `$skill` invocation still works."

의존성의 한계:

> "A dependency makes the required tool available; it does not replace clear workflow instructions."

⚠️ **이것은 예시이지 스키마 표가 아니다.** 필드별 타입·필수 여부·기본값을 정리한 표가 없고, 기본값이 명시된 키는 `allow_implicit_invocation` 하나뿐이다.

적용 환경: `interface` 블록은 **ChatGPT 데스크톱 앱** UI 메타데이터로 명시. `policy`·`dependencies`는 표면 명시 없음.

### 2.8 공식 작성 가이드는 있다 — 여러 공식 자료에 분산돼 있다

⚠️ 아래 표의 항목은 **성격이 서로 다르다.** ③은 권고(blog), ⑥은 API 표면 문서다. 개수로 뭉뚱그리지 않는다.

| # | 출처 | 성격 | 적용 환경 |
|---|---|---|---|
| ① | <https://learn.chatgpt.com/docs/build-skills> "Best practices" | docs / 사양+권고 | Codex 공통 |
| ② | <https://developers.openai.com/plugins/build/skills> | docs / 저작 가이드 | plugin 저작 |
| ③ | [Astra 블로그](https://developers.openai.com/blog/rethinking-skills-and-prompts-for-gpt-6-astra) | **blog / 권고** | 표면 명시 없음 → [§5](#5-gpt-6-astra--권고와-모델-사양) |
| ④ | <https://learn.chatgpt.com/docs/customization/overview> "Skills" | docs / 개념+예시 | Codex 공통 |
| ⑤ | `$skill-creator` (SYSTEM scope 내장 Skill) | 도구 | ChatGPT Work(`@`) / Codex(`$`) |
| ⑥ | <https://developers.openai.com/api/docs/guides/latest-model> | docs / **API 권고** | **API·SDK** → [§5.5](#55-astra-행동-특성--api-표면) |

①의 Best practices (원문 전량):

> - "Keep each skill focused on one job."
> - "Prefer instructions over scripts unless you need deterministic behavior or external tooling."
> - "Write imperative steps with explicit inputs and outputs."
> - "Test prompts against the skill description to confirm the right trigger behavior."

①의 `description` 작성법:

> "Because implicit matching depends on `description`, write concise descriptions with clear scope and boundaries. **Front-load the key use case and trigger words so a host can still match the skill if descriptions are shortened.**"

②의 workflow 경계 체크리스트 (원문 전량):

> "Connect every skill to one or more use cases. The instructions should make the following clear:
> - What input the workflow expects.
> - Which steps the model should follow.
> - What output the user should receive.
> - Which facts the model must not infer.
> - When the workflow should ask a question, stop, or decline.
> - Which supporting files the model should consult."

> "Prefer one focused skill over a large collection of loosely related instructions. Split workflows when they have different triggers, inputs, or success criteria."

②의 테스트 방법 (원문 전량) — **Skill Eval의 기성 형식이다**:

> "Test with representative requests from the use-case inventory:
> 1. Direct requests that should activate the skill.
> 2. Indirect requests that express the same goal.
> 3. Incomplete inputs that should trigger a follow-up question.
> 4. **Requests that should not activate the skill.**
> 5. Edge cases where the skill must avoid inventing information or taking an unsupported action.
>
> Review both activation and output quality. **Refine the description when the skill activates at the wrong time. Refine the instructions when it chooses the right workflow but produces an inconsistent result.**"

⑤의 기본값:

> "The creator asks what the skill does, when it should trigger, and whether it should stay instruction-only or include scripts. **Instruction-only is the default.**"

### OwnHands에 주는 의미

- ✅ **`SKILL.md` + `references/` 구조가 네이티브로 지원되고, 지연 로딩도 플랫폼 동작이다.** [개요 §5](../v2/overview.md)가 구상한 "상황별 Reference를 필요할 때 읽는" 구조는 별도 로더를 만들 필요가 없다. **다만 SKILL.md가 그 파일을 가리키고 언제 읽을지 적어야 작동한다.**
- ✅ 기존 기록의 판단("필요한 Reference를 언제 읽을지는 Skill의 실제 지침과 실행으로 후속 설계·검증한다")이 **공식 문서로 정확히 뒷받침된다.** 수정할 필요가 없다.
- ⚠️ **§2.5가 [#103](https://github.com/taejung3852/OwnHands/issues/103)에 직접 걸리는 정량 제약이다.** Skill 개수를 늘릴 때의 진짜 실패 모드는 description이 깎이는 것이 아니라 **Skill이 목록에서 누락되는 것**이다.
- ✅ **#103의 실무적 결론 하나: 이름 충돌을 설계 전제로 삼지 않는다.** 우선순위가 문서화돼 있지 않으므로 OwnHands Skill 이름은 **고유하게 짓는다.** 미확인 동작에 의존하지 않는 유일한 안전한 선택이다.
- ✅ **#103에서 필요한 frontmatter는 사실상 `name`과 `description`뿐이다.** 공식이 요구하는 것이 그 둘이고 공식 예시도 전부 그 둘만 쓴다. 선택 필드를 쓸 이유가 현재 없다.
- ✅ **`allow_implicit_invocation = false`가 실질적 선택지다.** 라우팅이 불안한 Skill을 지우지 않고 암묵 호출만 끌 수 있다. 다만 `interface` 블록은 데스크톱 앱 전용 UI 장식이므로 CLI 중심이면 쓸 이유가 없다.
- ✅ **자체 작성 규칙을 새로 쓰지 않는다.** [개발 방법](../v2/development-method.md) §1의 "공식 작성 가이드가 있으면 그것을 따른다"에서 — 있다.
- ✅ **②의 5항목 테스트 목록이 V2-M1 작은 Eval의 형식을 그대로 제공한다.** 특히 "4. Requests that should **not** activate the skill"이 과도한 트리거를 잡는 항목이다.
- ⚠️ **V1의 `skills/`는 Codex 탐색 경로(`.agents/skills`)가 아니었다.** 다른 호스트를 전제로 만들어졌다. 현재 tree에는 Skill이 없고, V2에서 어디에 둘지는 [#103](https://github.com/taejung3852/OwnHands/issues/103)에서 결정한다.

### 직접 만들지 않아도 되는 것
- 여러 scope에서의 Skill 탐색·등록
- `references/` 지연 로딩 메커니즘, 선로딩 방지를 위한 자체 분할 규칙
- Skill 목록 예산 관리, Skill별 활성/비활성
- Skill별 암묵 호출 on/off
- Skill 작성 규칙·템플릿·체크리스트, frontmatter 검증기
- Skill 트리거 Eval의 항목 설계 (②가 5항목 제공)
- Skill 초안 생성 (`$skill-creator`) · 설치 (`$skill-installer`)
- Skill의 MCP 의존성 선언·자동 연결

### 아직 확인하지 못한 것
- **같은 이름의 Skill이 여러 scope에 있을 때 어느 것이 실행되는지** (§2.3)
- **frontmatter 선택 필드 전체 목록** — OpenAI 문서에 없음 (§2.6)
- `agents/openai.yaml`의 필드 표(타입·필수·기본값), `interface`·`dependencies`·`policy` 하위 허용 키 전체
- `"only when needed"`의 판단 주체와 트리거 신호 — 모델인지 런타임인지 문서에 없음
- `references/` 파일 수의 상한, 컨텍스트 예산 계산 방식
- Skill 누락 경고의 표시 형태와 누락 선택 기준
- Codex가 `license`·`compatibility`·`metadata`·`allowed-tools`를 실제로 읽는지
- `name`·`description`의 Codex 측 길이 제한
- `$skill-creator`가 실제로 생성하는 SKILL.md의 형태

---

## 3. Hooks

출처: <https://learn.chatgpt.com/docs/hooks> · 확인일 2026-09-16

### 확인한 동작

**이벤트 이름(확인한 그대로)**

`SessionStart` · `SessionEnd` · `PreToolUse` · `PermissionRequest` · `PostToolUse` · `PreCompact` · `PostCompact` · `UserPromptSubmit` · `SubagentStart` · `SubagentStop` · `Stop` · `Interrupt`

**설정 위치**

- `~/.codex/hooks.json`
- `~/.codex/config.toml` (인라인 `[hooks]` 테이블)
- `<repo>/.codex/hooks.json`
- `<repo>/.codex/config.toml`
- 플러그인 번들: 플러그인 루트의 `hooks/hooks.json` 또는 매니페스트 지정 경로

**차단 응답 형식은 이벤트마다 다르다**

⚠️ 두 이벤트를 같은 형식으로 묶어 적지 않는다.

`PreToolUse` — `hookSpecificOutput.permissionDecision`

```json
{
  "hookSpecificOutput": {
    "hookEventName": "PreToolUse",
    "permissionDecision": "deny",
    "permissionDecisionReason": "Destructive command blocked by hook."
  }
}
```

문서는 이전 형식도 함께 설명한다("Codex also accepts this older block shape").

```json
{ "decision": "block", "reason": "Destructive command blocked by hook." }
```

종료 코드 `2`와 `stderr`로 차단 사유를 쓰는 방법도 있다.

`PermissionRequest` — `hookSpecificOutput.decision.behavior`

```json
{
  "hookSpecificOutput": {
    "hookEventName": "PermissionRequest",
    "decision": { "behavior": "deny", "message": "Blocked by repository policy." }
  }
}
```

> "If multiple matching hooks return decisions, any `deny` wins."

**`SubagentStart` — 자식에게 컨텍스트를 주입하는 확인된 지점**

> "Plain text on `stdout` is added as extra developer context for the subagent."

```json
{
  "hookSpecificOutput": {
    "hookEventName": "SubagentStart",
    "additionalContext": "Review the repository test conventions first."
  }
}
```

`SubagentStop`의 입력 필드에 **`agent_transcript_path`** (`string | null`, "Path to the subagent transcript file, if any") 와 `last_assistant_message`가 있다.

**그 밖에 할 수 있는 일**

| 유형 | 방법 |
|---|---|
| 경고·정보 제공 | `systemMessage`, `additionalContext` |
| 관찰 | `SessionEnd`·`PostToolUse`·`UserPromptSubmit` 등 |

같은 이벤트에 여러 command hook이 걸리면 동시에 실행된다.

### OwnHands에 주는 의미

- **실행 전 차단(`PreToolUse`, `PermissionRequest`)과 실행 후 탐지(`PostToolUse`)가 문서상 분리돼 있다.** V2가 Build·Test guardrail을 이야기할 때 이 구분을 그대로 쓸 수 있다.
- 지침(Skill)에 "하지 마라"라고 쓰는 것과 hook으로 **실제 차단**하는 것은 다르다. 이 문서가 그 차이를 뒷받침한다.
- `SubagentStart`의 `additionalContext`는 **역할별 고정 지침을 주입하는 확인된 지점**이다. 다만 이것을 쓸지는 후속 판단이다.
- ⚠️ **이벤트가 존재한다는 것이 OwnHands의 hook 설계가 끝났다는 뜻은 아니다.** 구체 규칙·권한·구현은 후속 설계다.
- 로컬 에이전트 hook과 CI/CD의 배포 통제는 다른 층이다. Deploy gate를 hook만으로 처리한다고 가정하지 않는다.

### 직접 만들지 않아도 되는 것
- 도구 실행 가로채기 메커니즘
- 권한 요청 시점의 개입 지점
- 세션 생명주기 이벤트
- 자식 실행 기록 보관 (`agent_transcript_path`)

### 아직 확인하지 못한 것
- hook 입출력 JSON 스키마 **전체**(위 세 이벤트의 형식만 확인했다)
- 나머지 이벤트의 응답 형식
- 각 이벤트의 정확한 실행 순서·타임아웃
- 실패 시 동작

---

## 4. Subagents

출처: <https://learn.chatgpt.com/docs/agent-configuration/subagents> · <https://learn.chatgpt.com/docs/config-file/config-reference> · 확인일 2026-09-16

**적용 환경: Codex 로컬 클라이언트만** (`app`/`cli`/`ide`). ChatGPT 웹/Work에는 custom agent 파일이 **없다** — "In local Codex clients, you can also define custom agents".

### 4.1 위치와 필수 필드

> "To define your own custom agents, add standalone TOML files under `~/.codex/agents/` for personal agents or `.codex/agents/` for project-scoped agents."

| Field | Type | Required | Purpose (원문) |
|---|---|:-:|---|
| `name` | string | Yes | "Agent name Codex uses when spawning or referring to this agent." |
| `description` | string | Yes | "Human-facing guidance for when Codex should use this agent." |
| `developer_instructions` | string | Yes | "Core instructions that define the agent's behavior." |

> "Codex identifies the custom agent by its `name` field. Matching the filename to the agent name is the simplest convention, but the `name` field is the source of truth."

### 4.2 전체 키 목록은 닫힌 목록이 아니다

> "Codex loads these files as configuration layers for spawned sessions, so **custom agents can override the same settings as a normal Codex session config.** That can feel heavier than a dedicated agent manifest, and **the format may evolve as authoring and sharing mature.**"

> "You can also include other supported `config.toml` keys in a custom agent file, **such as** `model`, `model_reasoning_effort`, `sandbox_mode`, `mcp_servers`, and `skills.config`."

⚠️ **"such as"이므로 화이트리스트가 아니다.** 필수 3개 위에 `config.toml` 지원 키를 얹는 구조이고, `config-reference`가 사실상의 상위 집합이다. **닫힌 목록은 문서에 없다.**

### 4.3 내장 에이전트 3종과 `[agents]` 전역 설정

> - "`default`: general-purpose fallback agent."
> - "`worker`: execution-focused agent for implementation and fixes."
> - "`explorer`: read-heavy codebase exploration agent."

> "If a custom agent name matches a built-in agent such as `explorer`, your custom agent takes precedence."

| 키 | 타입 | 설명(원문) |
|---|---|---|
| `agents.enabled` | boolean | "Enable or disable multi-agent tools (default: true)." |
| `agents.max_concurrent_threads_per_session` | number | "Maximum number of spawned-agent threads that can be open concurrently, excluding the primary thread." |
| `agents.max_threads` | number | "Legacy alias for `agents.max_concurrent_threads_per_session`." |
| `agents.default_subagent_model` | string | "Default model for spawned agents. An explicit spawn model takes precedence." |
| `agents.default_subagent_reasoning_effort` | string | "Default reasoning effort for spawned agents." |
| `agents.interrupt_message` | boolean | "Record a model-visible message when an agent turn is interrupted (default: true)." |
| `agents.<name>.description` | string | "Role guidance shown to Codex when choosing and spawning that agent type." |
| `agents.<name>.config_file` | string (path) | "Path to a TOML config layer for that role; relative paths resolve from the config file that declares the role." |

### 4.4 설정 해석 순서

> "If a custom agent file sets `model` or `model_reasoning_effort`, the value in the file takes precedence. Before applying the file, Codex resolves each setting from **an explicit spawn value, then the corresponding `[agents]` default, then the parent's value.** If an explicit spawn request or an `[agents]` default selects a model and neither supplies a reasoning effort, Codex uses that model's default effort. A custom agent file that sets only `model` preserves this previously resolved effort."

### 4.5 상속 — 설정과 권한

| 항목 | 원문 | 표면 |
|---|---|---|
| 샌드박스 정책 | "Subagents inherit your current sandbox policy." | app/cli/ide |
| 권한 모드 | "Subagents inherit the permission mode selected beneath the composer." | app/ide |
| 런타임 override 재적용 | "Codex also reapplies the parent turn's live runtime overrides when it spawns a child. That includes sandbox and approval choices you set interactively during the session, such as `/permissions` changes or `--yolo`, **even if the selected custom agent file sets different defaults.**" | cli |
| 모델·추론 강도 | "If you don't configure a subagent model or `model_reasoning_effort`, the subagent inherits the parent agent's model and reasoning effort." | app/cli/ide |
| 나머지 세션 설정 | "Other session settings, such as `sandbox_mode`, `mcp_servers`, and `skills.config`, **inherit from the parent when the custom agent file omits them.**" | app/cli/ide |
| 도구 | "Subagents use the tools available to the parent chat." | **web만** |

> ⚠️ **custom agent 파일의 `sandbox_mode`를 안전 보장으로 취급하면 안 된다.** 부모 턴에서 `--yolo`를 켜면 파일에 `read-only`라고 적어 둬도 무시된다. 실제 경계는 hook·권한이다(§3의 구분과 일치).

### 4.6 부모↔자식 컨텍스트 전달 범위 — `미확인`

⚠️ **자식이 부모의 대화 내용·이력·파일 읽기 결과 중 무엇을 보는지는 문서에 없다.** `llms-full.txt` 전량 grep(`inherit`, `parent`, `context`, `transcript`, `sees`, `carry`)으로 확인했다.

문서가 **결과 방향**에 대해 말하는 것은 있다.

> "Keep the **main agent** focused on requirements, decisions, and final outputs."
> "Run specialized **subagents** in parallel for exploration, tests, or log analysis."
> "**Return summaries** from subagents instead of raw intermediate output."
> "When many agents are running, Codex waits until all requested results are available, then returns a consolidated response."

간접 근거로 **자식이 자기 transcript를 따로 갖는다**는 것(§3의 `agent_transcript_path`)과 **시작 시점에 개발자 컨텍스트를 주입할 수 있다**는 것(§3의 `SubagentStart`)까지는 확인된다. **그것이 "부모 대화를 보지 않는다"는 뜻은 아니다.** 추정하지 않는다.

문서가 권하는 방법은 명시적 전달이다.

> "A good subagent prompt should explain how to divide the work, whether Codex should wait for all agents before continuing, and what summary or output to return."

### 4.7 중첩 위임 — `미확인`

**Subagents 문서는 중첩 위임을 허용한다고도, 금지한다고도 말하지 않는다.** 전량 grep(`nested`, `recursive`, `depth`, `spawn their own`, `one level`) 결과다.

추정하지 않기 위해, 관련은 있으나 **답이 아닌** 두 가지를 분리해 적는다.

**(가) app-server 프로토콜의 스레드 필터** — 적용 환경: **app-server API**(Codex를 제품에 임베드하는 개발자용)

> "`ancestorThreadId` - restrict results to spawned descendants of the given thread **at any depth**. This filter is experimental..."

→ 스레드 모델이 임의 깊이의 descendant를 표현한다. 하지만 이것은 **스레드 저장소 API의 필터 사양**이고 subagent 동작 서술이 아니다.

**(나) Astra API 프롬프팅 가이드의 문장** — 적용 환경: **일반 API·SDK (자체 harness)**

> "If at any point you can parallelize work by delegating tasks to another agent (**no matter if you are the root or subagent**), you should do so..."

→ 이 문장은 명시적으로 "your harness"를 전제한다. **Codex harness가 그것을 허용하는지는 다른 문제다.**

문서의 예시 2개(PR review, frontend debugging)는 전부 **1단계 병렬**이고, 비용 경고가 있다.

> "subagent workflows consume more tokens than comparable single-agent runs."

### 4.8 `skills.config` — 스키마가 완결돼 있다

config reference가 이 키를 완전히 정의한다(§2.5의 표와 동일). 하위 필드는 **`path`와 `enabled` 둘뿐이다.**

용법:

> "Use `[[skills.config]]` entries in `~/.codex/config.toml` to **disable a skill without deleting it**"

> "Restart Codex after changing `~/.codex/config.toml`."

> ⚠️ **기존 기록의 경고가 확정적으로 확인됐다.** 하위 필드가 둘뿐이므로 **`references/` 안의 특정 파일이 읽히는 범위를 제한하는 수단이 아니다.** 이것은 "문서가 설명하지 않는다"가 아니라 **"스키마에 그런 필드가 없다"**다.

⚠️ 문서 예시는 전부 **절대 경로**(`/Users/me/...`)다. 저장소에 체크인하는 `.codex/agents/*.toml`에 절대 경로를 넣으면 **다른 기계에서 깨진다.**

### OwnHands에 주는 의미

- ✅ **역할·모델·권한·도구를 에이전트별로 나누는 구조가 이미 있다.** V2가 "독립된 역할·맥락·도구를 받아 작업 수행"이라고 적은 Agent 책임과 맞물린다.
- ✅ **내장 에이전트 3종이 이미 있어서 [#104](https://github.com/taejung3852/OwnHands/issues/104)의 출발점은 0이 아니다.** 탐색 중심 역할은 내장 `explorer`가 이미 제공한다. **질문이 "역할을 몇 개 만들까"가 아니라 "내장 3종으로 부족한가"로 바뀐다.**
  ⚠️ 단, 문서의 표현은 `read-heavy`이지 **`read-only`가 아니다.** 엄격한 읽기 전용 경계나 추가 지침이 필요한지는 [#104](https://github.com/taejung3852/OwnHands/issues/104)에서 판단한다.
- ✅ **권한이 자식으로 새지 않는다.** 부모 턴이 read-only면 자식도 read-only다. 자체 권한 전파 층을 만들지 않는다.
- ⚠️ **`skills.config`에서 확인된 제어 단위는 Skill 활성/비활성이다.** `references/` 파일 단위의 enable/disable 설정은 **확인되지 않았다**(§4.8). 설정으로 더 세밀하게 나누려면 Skill을 쪼개야 하는데, 쪼개면 §2.5의 10,000 토큰 예산과 §5.1의 description 모순 문제를 동시에 산다. **이 트레이드오프가 [#103](https://github.com/taejung3852/OwnHands/issues/103)과 [#104](https://github.com/taejung3852/OwnHands/issues/104)를 묶는 지점이다.**
  ⚠️ 이것은 **설정 층의 이야기다.** 역할이 무엇을 읽을지는 `developer_instructions`·위임 프롬프트·`SubagentStart`의 `additionalContext`로도 좁혀진다(§3·§4.6). "설정으로 못 나눈다"를 "나눌 방법이 없다"로 읽지 않는다.
- ⚠️ **#104에서 "역할별로 무엇을 아는가"를 설계 전제로 삼을 수 없다.** 컨텍스트 전달 범위가 문서화돼 있지 않으므로, 자식에게 필요한 정보는 **위임 프롬프트에 명시적으로 넣는 것**이 확인된 유일한 방법이다.
- ⚠️ **중첩 위임을 전제한 역할 구조를 설계하지 않는다.** §4.7의 (가)(나)는 "아마 될 것"이라는 인상을 주지만 **인상은 근거가 아니다.**
- 필수가 3개뿐이고 나머지는 `config.toml` 키를 얹는 구조이므로 **최소 custom agent는 TOML 5줄이다.** 추상화를 만들 여지 자체가 없다.
- ⚠️ **문서 스스로 형식이 바뀔 수 있다고 경고한다.** custom agent 파일을 미리 많이 만들어 두지 않는다.

### 직접 만들지 않아도 되는 것
- 위임 실행 메커니즘
- 에이전트별 모델·샌드박스·MCP 서버 지정
- 에이전트별 Skill 활성/비활성
- 권한·샌드박스의 부모→자식 전파
- 결과 수집·통합

### 아직 확인하지 못한 것
- **자식이 부모의 대화 이력 중 무엇을 받는지** (§4.6)
- **`AGENTS.md`가 자식에게도 적용되는지** — 문서에 없다
- **중첩 위임 허용 여부와 깊이 제한** (§4.7)
- **부모에서 `enabled = false`로 끈 Skill을 자식 custom agent 파일이 되살릴 수 있는지**, 그리고 `skills.config` 상속이 **병합인지 대체인지** — 문서에 없다. 실측 대상이다.
- `skills.config.path`가 상대 경로를 받는지 (예시는 전부 절대 경로)
- custom agent TOML에서 유효한 `config.toml` 키의 실제 범위
- 자식이 부모에게 돌려주는 요약의 형식·길이 제한
- `agents.max_concurrent_threads_per_session`이 중첩된 자손까지 세는지

---

## 5. GPT-6 Astra — 권고와 모델 사양

> ⚠️ **이 절은 §1~§4와 근거의 층이 다르다.**
> §5.1~5.4는 **개발자 블로그(권고)**다. §5.5~5.6은 **API 표면 문서**다. §5.7만 Codex docs다.
> **여기의 내용을 Codex의 사양으로 취급하지 않는다.** 특히 `agents-md` 사양 페이지에는 `Astra`가 한 번도 등장하지 않는다(§1).

출처: <https://developers.openai.com/blog/rethinking-skills-and-prompts-for-gpt-6-astra> · 확인일 2026-09-16

**게시일: 미확인.** 페이지 Markdown 원문, 렌더된 HTML(`<time>`·`datePublished`·JSON-LD 모두 없음), 블로그 인덱스(`/blog`, `/blog/llms.txt`) 네 곳 어디에도 날짜가 없다.

**적용 표면: 명시 없음.** 본문은 "agents like Codex"라고만 하고 CLI/IDE/웹/cloud를 구분하지 않는다.

### 5.1 Skill `description` — 짧게, 그리고 트리거를 구체적으로

문제 진단(원문):

> "People now default to packaging a lot of skills into their projects, and each skill comes with a name and description that are loaded into the model's context so it knows when to use them. But many descriptions are far too long, and when you add too many skills, Codex starts shortening their descriptions to fit. The model ends up seeing less of each description, making it harder to know which skill to pick."

> "What's worse is that **descriptions can often contradict each other** or over-emphasize when skills should be used, leading the model to load instructions that don't actually help the task."

권고(원문):

> "First, skill descriptions should be **as short as possible while making it clear when the model should use them**"

블로그가 제시한 대비 예시(원문):

> **Bad**: `Create and validate Postgres schema migrations. Use when working with databases, queries, models, or persistence.`
> **Good**: `Create and validate Postgres schema migrations. Use when adding or changing a migration, or reviewing its rollout.`

> "Here, the bad skill description can push the model to use it anytime it touches anything related to a database, rather than only when it has to handle a migration."

**대비의 축은 길이가 아니라 트리거 조건의 구체성이다.** "무엇을 다룰 때"(대상 범주)가 아니라 "어떤 행위를 할 때"(작업 시점)로 쓴다.

### 5.2 SKILL.md 본문 — router는 조건부 권고다

> "Second, one of the key markers of a useful skill is progressive disclosure. Reading a skill takes up context, bringing you closer to compaction and introducing guidance that may not apply to the task. **For skills with multiple workflows, make the root document a minimal router that points to supporting docs and scripts.** Give the model enough guidance to know where to look without forcing it to read things that don't matter in the moment."

> "Third, many skills were written as **elaborate itineraries or recipes**. Models have gotten much better at understanding nuance and ambiguity, so **overly specific guidance can now hinder results** where it previously helped."

모델 혼재 환경 경고(원문):

> "Repository skills also guide other contributors' agents, which may use different models. **Guidance that helps Sol or Luna may overconstrain GPT-6 Astra**, so consider which models will use the instructions you leave behind."

⚠️ **정확한 표현에 주의한다.**
- "router"는 **조건부**로 쓰였다: `For skills with multiple workflows`. **모든 SKILL.md를 router로 만들라는 말이 아니다.** workflow가 하나면 쪼갤 이유가 없다.
- 대상은 `the root document`(= SKILL.md 본문)이고 가리키는 곳은 `supporting docs and scripts`다. **블로그는 `references/`라는 디렉터리 이름을 쓰지 않는다.** 그 연결은 §2.4의 docs 쪽 근거로 한다.

### 5.3 AGENTS.md — 제거할 것과 추가할 것

**제거 대상 (1) 모든 편집 전 선행 독서 요구**

> "Requiring a stack of docs or a full repo map before every edit is excessive for a typo fix. GPT-6 Astra can work out what it needs to read without being pushed to review the whole project before every change."

> **Bad**: `Before every edit, read architecture.md, database.md, and deployment.md.`
> **Good**: `Use architecture.md for service boundaries, database.md for schema changes, and deployment.md when preparing a deployment.`

> "Prompting the model to read files before every edit is a great way to burn context and slow work down. Pointing to some docs can still be helpful, however, so long as it is contextual."

**제거 대상 (2) 테스트를 강제하는 지침**

> "Previous models needed encouragement to run tests and check their work. **GPT-6 Astra does that on its own**, so the same instructions can lead to unnecessary testing."

**제거 대상 (3) 과거 모델을 막으려고 넣은 강한 경계 문구**

> "If a previous model did things on your behalf without permission, you may have added strong language to make it ask first. That can be useful, but GPT-6 Astra, as our most aligned model, has much better judgment and will not perform tasks unless it knows it is safe – so you should treat it as such."

> "If you stated boundaries previously because you wanted to prevent other models from going too far and you're now switching to GPT-6 Astra, consider updating that language: **Astra could take it too seriously and may stop work where you'd actually be happy for it to continue.**"

**추가하라는 것 — 안전한 워크플로에 대한 명시적 허가**

> "The local tests use disposable fixtures and have no production access. Run them, fix failures caused by the requested change, and rerun affected tests without asking for approval at each step."

> "GPT-6 Astra is thorough, but it can be more tentative about how far to take a task. Sometimes it needs a little push to keep going. You can use `AGENTS.md` to give it permission for a specific workflow you know is safe, such as a local test suite"

### 5.4 Task prompt — 완료를 먼저 정의한다

> "If you're used to GPT-5.6 Sol taking a request and continuing for long stretches, GPT-6 Astra can feel more tentative about when to stop. It may reach a first implementation and come back for your review while there's still work to do."

> "This is where it helps to **define completion before starting**. You might need to push Astra to continue until it's fully done. If the task includes getting the implementation running, inspecting the result, and fixing what fails, make that part of the request. **A requirement to stop for review after the first implementation will pull the model toward an earlier stopping point**, so check whether that's a decision you actually need to make."

> "If you want it to keep exploring beyond a first pass, say what you want explored and where it should stop."

### 5.5 Astra 행동 특성 — API 표면

출처: <https://developers.openai.com/api/docs/guides/latest-model> ("Using GPT-6 Astra") · 확인일 2026-09-16

> ⚠️ **적용 환경: 일반 API·SDK (Responses API).** "To build with Astra, set `model` to `gpt-6-astra` in a Responses API request." **Codex 표면 문서가 아니다.**
> 다만 Codex `plugins/build/skills` 문서가 Skill 작성 시 읽으라고 **링크한** 페이지다.

행동 특성(원문 목록):

> - "**Initiative and follow-through** – The model is designed to be a more effective collaborator and is thus more likely to ask the user a question when additional input could materially change the result."
> - "**Instruction following** – GPT-6 Astra is stronger at general instruction following than our previous models... It can be more sensitive to instructions contained in skills and other files, such as `AGENTS.md`. We **strongly recommend** auditing skills and other files accessible to your model for instructions that could influence its behavior."
> - "**Subagent delegation** – The model may delegate less often than desired for your workflow."
> - "**Testing and verification** – For coding tasks, the model tends to be thorough in testing before considering a task complete. For smaller tasks, this can result in broader tests than the task requires."

Skill 충돌에 대한 권고와 **제안 프롬프트 2개**(원문):

> "unclear or conflicting guidance in a skill file may cause the model to pause and block work early. Make the priority of user instructions and skills explicit."
>
> `The user's instructions take precedence over guidelines provided in a skill. If explicit user instructions conflict with a skill's instructions, prioritize the user's instructions.`

> `If a skill causes you to ask for permission or confirmation, pause, leave requested work unfinished, or diverge from the user's intent, name and link to the exact SKILL.md file you read, quote the relevant instruction, and briefly explain how it applies. Distinguish explicit skill requirements from your interpretation of guidelines.`
>
> "Use this prompt to find silent and conflicting guidance when your application loads many skills and instruction files such as `AGENTS.md`."

⚠️ **이 프롬프트들은 자체 harness를 만드는 API 사용자를 대상으로 쓰였다.** Codex는 자체 시스템 프롬프트를 갖고 있으므로 **그대로 붙여넣어 Codex에서 동작한다는 근거는 없다.** Eval로 확인할 대상이지 확정된 사양이 아니다.

### 5.6 모델 사양과 가격 — API 표면

출처: <https://developers.openai.com/api/docs/models/gpt-6-astra> · 확인일 2026-09-16

| 항목 | 값 |
|---|---|
| Context window | **1,050,000** |
| Maximum input tokens | 922,000 |
| Max output tokens | 128,000 |
| Knowledge cutoff | Apr 30, 2026 |
| Input / Output modalities | text, image / text |
| `reasoning.effort` | `low`, `medium`, `high`, `xhigh`, `max` |

Endpoints: `v1/responses` · `v1/chat/completions` · `v1/batch` **지원**. Realtime·Assistants·Fine-tuning·Embeddings **미지원**.
Supported tools에 **`skills`**가 명시돼 있다(그 외 `web_search`, `file_search`, `image_generation`, `code_interpreter`, `hosted_shell`, `apply_patch`, `computer_use`, `mcp`, `tool_search`).

가격 (Text tokens, 1M 기준):

| | ≤ 272K | > 272K |
|---|---|---|
| Input | $10 | **$20** |
| Cached input | $1 | **$2** |
| Cache writes | $12.5 | — |
| Output | $50 | **$75** |

> "Prompts with more than 272K input tokens are priced at **2x input and cache rates and 1.5x output for the full request**."

⚠️ **"for the full request"** — 272K를 넘는 순간 요청 전체가 할증이다. 앞부분만 정상가가 아니다.

⚠️ 이 가격·한도는 **API 기준**이다. ChatGPT 구독으로 Codex를 쓸 때의 소비 방식은 이 페이지가 다루지 않는다.

### 5.7 Codex 표면별 Astra 가용성

출처: <https://learn.chatgpt.com/docs/models> ("Recommended models" → `gpt-6-astra`) · 확인일 2026-09-16

| 표면 | 지원 |
|---|---|
| ChatGPT 데스크톱 앱 | **true** |
| ChatGPT 웹 | **true** |
| Codex CLI | **true** |
| Codex IDE extension | **true** |
| **Codex cloud** | **false** |
| ChatGPT Credits | true |
| API Access | true |

> "Availability depends on the rollout, your sign-in method, and your client."

> "Astra is off by default for ChatGPT [Enterprise] ... workspaces can enable Astra for users or groups"

Astra 전용 실험 기능:

> "On supported Codex clients, users signed in with ChatGPT Plus or Pro can opt in to experimental context management. Astra keeps notes across context windows and can search earlier messages and tool results from the same task. This experiment is off by default and isn't available with Business, Enterprise, or API-key sign-in at launch."

설정: `features.context_management.experimental_mode = true` (`config.toml`)

모델 선택 권고:

> "**Astra, for the hardest end-to-end work.** Choose Astra for complete workflows across code, apps, and research that need sustained reasoning and judgment. Give it the sources, templates, constraints, and checks that define a useful result."

### OwnHands에 주는 의미

- ✅ **§2.5의 컨텍스트 상한이 단순 제약이 아니라 작성 지침의 근거다.** "description을 짧게"와 "Skill을 적게"가 같은 문제의 양면이다.
- ⚠️ **Skill을 늘리는 비용은 컨텍스트만이 아니라 라우팅 정확도다.** description이 서로 모순될 수 있다는 지적(§5.1)과 Skill 본문의 모순이 작업을 조기 중단시킨다는 지적(§5.5)은 [#103](https://github.com/taejung3852/OwnHands/issues/103)의 직접 입력값이다.
- ✅ **[개요 §5](../v2/overview.md)의 "필요한 Reference만 읽는다"가 공식 권고와 같은 방향임이 확인됐다.** 단 공식은 "workflow가 여럿일 때"라는 조건을 단다.
- ⚠️ **방향이 뒤집혔다.** V1은 "AI가 멋대로 하지 않게 지침을 촘촘히 쓴다"는 전제였다. §5.3은 그 지침 자체가 이제 **품질을 떨어뜨리는 요인**이라고 말한다. "지침을 더 촘촘히 쓰는 것이 품질 개선이 아니다"는 V1의 교훈(배보다 배꼽)과 같은 지적이다.
- ⚠️ **§5.3의 (2)는 "테스트하지 말라"가 아니라 "테스트를 지침으로 강제하지 말라"다.** [개발 방법](../v2/development-method.md)의 "계약은 강하게 검증"은 그대로 유효하다. 다만 V2-M4 설계 시 **Astra가 스스로 검증한다는 전제**를 반영한다.
- ⚠️ **§5.3의 (3)은 안전 완화가 아니다.** 겨냥한 것은 "과거 모델이 월권했기 때문에 넣은 문구"다. 조직 정책·보안 경계는 별개 층이고, 그것은 hook·권한으로 강제하는 것이지 지침 문장으로 하는 것이 아니다(§3의 구분).
- ⚠️ **"검토를 위해 멈추라"는 요구가 공짜가 아니다**(§5.4). 승인 게이트를 **지침에 넣을지 hook/권한으로 걸지**의 선택이 품질에 영향을 준다. 지침에 넣으면 그 앞 작업까지 얕아진다. V2-M6 설계에 걸리는 사실이다.
- ⚠️ **모델 고정을 전제로 지침을 쓰지 않는다.** 저장소에 체크인한 Skill은 다른 기여자의 다른 모델도 읽는다(§5.2). **공식이 이 위험을 직접 인정한다.**
- ⚠️ **Codex cloud는 Astra를 지원하지 않는다.** 로컬(CLI·앱·IDE)에서는 영향이 없다. **다만 V2-M6에서 cloud/CI 실행을 채택하기로 하면, 로컬과 cloud가 서로 다른 모델로 같은 저장소 Skill을 읽는 조건이 된다.** 그때 §5.2의 경고가 실제로 걸린다.
- **Skill 목록 예산을 숫자로 계산할 수 있게 됐다.** 272K 초과 2x 과금은 컨텍스트를 크게 쓰는 것이 공짜가 아니라는 근거이고, §5.2의 progressive disclosure 권고와 같은 방향이다. [#106](https://github.com/taejung3852/OwnHands/issues/106)의 비용 상한 논의에 그대로 쓰인다.

### 직접 만들지 않아도 되는 것
- Skill description 작성 규칙 자체 제정 (공식 권고와 Bad/Good 예시가 있다)
- 지침 감사 도구 — 블로그가 직접 말한다: "ask GPT-6 Astra to do an audit based on what was discussed in this article"
- Skill 충돌 진단 도구 (§5.5의 프롬프트가 공식 제공본)
- Astra 마이그레이션 자동화 — 공식 Skill이 있다: `$openai-docs migrate this project to GPT-6 Astra`
- 작업 완료 조건 강제용 템플릿 엔진
- 모델별 표면 가용성 관리
- 컨텍스트 윈도를 넘는 작업의 노트 유지 (Astra의 experimental context management)

### 아직 확인하지 못한 것
- 블로그 **게시일과 저자**
- 블로그 권고가 어느 Codex 표면·버전부터 적용되는지
- `description` 길이의 정량 상한 — "as short as possible"까지만 말한다
- "minimal router"의 정량 기준(길이·항목 수), workflow가 몇 개부터 쪼개야 하는지
- §5.5의 프롬프트들이 Codex CLI/IDE에서 실제로 어떻게 작동하는지
- ChatGPT 구독 사용 시의 크레딧 소비 규칙
- Codex cloud가 Astra를 언제 지원할지
- `features.context_management.experimental_mode`의 상세 동작
- `https://developers.openai.com/api/docs/guides/latest-model/gpt-6-astra.md` (별도 심화 페이지) — 열지 않았다

---

## 6. Memories · Rules

### 6.1 Memories

출처: <https://learn.chatgpt.com/docs/customization/memories> · 확인일 2026-09-16

> "Memories let ChatGPT and Codex carry useful context from earlier work into future work. **ChatGPT web uses ChatGPT memory, while local Codex clients use a separate local memory store and controls.**"

로컬 Codex 클라이언트에 대한 경고(원문):

> "**Keep required team guidance in `AGENTS.md` or checked-in documentation. Treat memories as a helpful recall layer, not as the only source for rules that must always apply.**"

제어 수단: CLI/앱에서 `/memories`, Settings > Personalization.
config 키: `memories.generate_memories` (boolean) — "When `false`, newly created threads are not stored as memory-generation inputs. Defaults to `true`." · `memories.use_memories` (설명 미확인)

**OwnHands에 주는 의미**

- ✅ **공식 문서가 직접 선을 긋는다. 반드시 지켜져야 할 규칙은 memories가 아니라 `AGENTS.md`나 체크인된 문서에 둔다.** V2가 지침을 저장소 파일로 관리하는 방향이 공식 권고와 일치한다.
- ⚠️ **memories를 프로젝트 지식 전달 수단으로 설계하지 않는다.** 사용자별·기계별이고, 웹과 로컬이 서로 다른 저장소를 쓴다.

**아직 확인하지 못한 것**: 저장 위치·보존 기간·삭제 · `memories.use_memories`의 설명 · memories가 subagent에 전달되는지

### 6.2 Rules — 존재와 실험적 상태만 기록한다

출처: <https://learn.chatgpt.com/docs/agent-configuration/rules> · 확인일 2026-09-16

> "Use rules to control which commands Codex can run outside the sandbox."
> "**Rules are experimental and may change.**"

- 위치: 활성 config 레이어 옆 `rules/` 폴더의 `.rules` 파일 (예: `~/.codex/rules/default.rules`)
- 형식: Python 유사 문법의 `prefix_rule()` 호출. 필드 `pattern`·`decision`·`justification`·`match`·`not_match`
- `match`/`not_match`는 문서 표현으로 "inline unit tests"

⚠️ **이것은 sandboxing/approvals 영역이고 [#102](https://github.com/taejung3852/OwnHands/issues/102)의 범위 밖이다.** V2-M3/M6 착수 시 조사한다. `prefix_rule()`의 전체 필드·`decision` 허용값·레이어별 우선순위는 **의도적으로 조사하지 않았다.**

---

## 7. 아직 조사하지 않은 영역 (미확인)

각 마일스톤의 전체 기술 설계는 착수 시점에 조사한다.

| 영역 | 상태 | 조사 시점 |
|---|---|---|
| Plan mode / 계획 기능의 Codex 대응 | 미확인 | `V2-M3` |
| MCP 서버 구성 상세 | 미확인 | 도구 연결이 필요해질 때 |
| MCP 도구 설명·프롬프트 작성 방식 | 미확인 | 도구 연결 시 |
| Sandboxing · approvals · permission modes | 미확인 | `V2-M6` |
| **Rules 상세** (`prefix_rule()` 전체) | 미확인 (존재만 확인 → §6.2) | `V2-M3`/`V2-M6` |
| Codex cloud / CI 비대화형 실행 · GitHub Action | 미확인 | `V2-M6` |
| Plugins 패키징 | 미확인 | 배포 형태 결정 시 |
| 관리자·엔터프라이즈 managed configuration | 미확인 | 조직 정책 연결 시 |
| `learn.chatgpt.com/guides/best-practices` (HTML) | 미확인 (`.md`는 404) | 필요 시 |
| `docs/extend/record-and-replay` (Skill 생성의 또 다른 경로) | 미확인 | Skill 구성 결정 시 |

> ⚠️ `enterprise/skills`("Skill controls: Compare ChatGPT workspace, local filesystem, and plugin skill controls")는 **§2.3의 scope 우선순위에 대한 정보를 담고 있을 가능성이 있다.** 엔터프라이즈 관리 설정 영역이라 이번 범위에서 제외했다. [#103](https://github.com/taejung3852/OwnHands/issues/103)에서 scope 우선순위가 실제로 걸림돌이 되면 이 페이지를 먼저 연다.

> ⚠️ 특정 호스트의 Plan Mode를 사용했다고 프로젝트의 `plan.md` 저장과 검토가 자동으로 끝난다고 가정하지 않는다.

---

## 8. 이번 조사에서 얻은 결론

Codex는 **Skills · Hooks · Subagents · MCP · 샌드박스 · 지침 계층**을 이미 네이티브로 제공한다. 그리고 이번 조사에서 **작성 방식까지 공식 가이드가 있다는 것**을 확인했다.

> V1에서 커진 유지보수 부담의 일부는, **플랫폼이 제공하는 것을 직접 만들었기 때문일 수 있다.**
> 그래서 V2는 각 마일스톤 착수 시 **먼저 공식 문서를 조사하고, 직접 만들지 않아도 되는 것부터 결정한다.**

### 이번 조사가 결정에 넘기는 것

| 발견 | 걸리는 결정 |
|---|---|
| Skill 목록 예산의 실제 천장은 **10,000 토큰**이고, 초과 시 Skill이 **목록에서 누락된다** | [#103](https://github.com/taejung3852/OwnHands/issues/103) — "몇 개까지 둘 수 있나"가 이름보다 먼저다 |
| `skills.config`의 확인된 제어 단위는 **Skill 활성/비활성**이다 (파일 단위는 미확인) | [#103](https://github.com/taejung3852/OwnHands/issues/103) + [#104](https://github.com/taejung3852/OwnHands/issues/104) — 따로 결정할 수 없다 |
| **내장 에이전트 3종**(`default`/`worker`/`explorer`)이 이미 있다 | [#104](https://github.com/taejung3852/OwnHands/issues/104) — "만들까"가 아니라 "내장으로 부족한가" |
| 같은 이름 Skill의 scope 우선순위가 **문서에 없다** | [#103](https://github.com/taejung3852/OwnHands/issues/103) — 이름을 고유하게 지어 회피한다 |
| 272K 초과 시 요청 전체 **2x/1.5x 과금** | [#106](https://github.com/taejung3852/OwnHands/issues/106) — Eval 비용 상한 |
| Codex cloud는 **Astra 미지원** | `V2-M6` — cloud/CI 채택 시 모델 불일치를 전제한다 |
| Astra는 **스스로 테스트한다**, 지침으로 강제하면 불필요한 테스트를 부른다 | `V2-M4` — 검증 설계의 전제가 바뀐다 |
| Skill 트리거 테스트 **5항목 목록**이 공식 문서에 있다 | `V2-M1` 작은 Eval — 새로 설계하지 않는다 |

### 실측으로 넘기는 것

문서에 없어서 `미확인`으로 남긴 것 중, **실제로 돌려보면 답이 나오는 것**이다.

| 질문 | 관련 |
|---|---|
| 부모에서 `enabled = false`로 끈 Skill을 자식 custom agent가 되살릴 수 있는가 | §4.8 · [#103](https://github.com/taejung3852/OwnHands/issues/103)·[#104](https://github.com/taejung3852/OwnHands/issues/104) |
| `skills.config` 상속이 병합인가 대체인가 | §4.8 |
| 같은 이름 Skill 중 어느 것이 실행되는가 | §2.3 |
| 자식이 부모의 대화 이력 중 무엇을 받는가 | §4.6 |
| subagent가 다시 subagent를 띄울 수 있는가 | §4.7 |

> ⚠️ **실측 결과는 이 문서에 사양으로 적지 않는다.** 이 문서는 *공식 문서가 무엇을 말하는가*의 기록이다.
> 실측은 [개발 방법](../v2/development-method.md)의 근거 표에서 **"실행이 실제로 성공했는가"**에 해당하는 다른 층이고,
> 기록할 때는 `실측`임을 밝히고 **버전이 바뀌면 달라질 수 있다는 단서**를 함께 적는다. **관찰은 사양이 아니다.**

→ [개발 방법](../v2/development-method.md) · [결정 상태표](../v2/decisions.md)

---

## 관련 문서

- [V2 개요](../v2/overview.md) — Skill·Reference·Agent·Script의 책임 구분
- [개발 방법](../v2/development-method.md) — 이 조사를 수행한 절차
- [결정 상태표](../v2/decisions.md) — 확정 / 생각 / 미정
- [Anthropic Playbook 대응](anthropic-playbook.md) — SDLC 큰 틀, 가져온 것과 안 가져온 것

# Codex 공식 문서 확인 기록

> **이 문서의 규칙**
> 실제로 읽은 것만 적는다. 읽지 못한 것은 `미확인`으로 남긴다.
> 기억에 의존해 설정 키나 지원 기능을 만들어내지 않는다. 커뮤니티 글로 조용히 대체하지 않는다.
>
> **확인일: 2026-09-16** · 확인 방법: 문서 URL 직접 조회

Codex는 V2의 1차 실행 플랫폼이므로, **실제 형식·기능·권한·제약의 기준은 Anthropic Playbook이 아니라 이 문서**다.

---

## ⚠️ 0. 문서 위치가 이동했다 (2026-09-16 확인)

기존에 참고하던 `developers.openai.com/codex/*` 경로는 **308 Permanent Redirect**로 이동했다.

| 이전 URL | 현재 URL | 상태 |
|---|---|---|
| `https://developers.openai.com/codex/` | <https://learn.chatgpt.com/docs> | 308 → 200 |
| `https://developers.openai.com/codex/skills` | <https://learn.chatgpt.com/docs/build-skills> | 308 → 200 |
| `https://developers.openai.com/codex/guides/agents-md` | <https://learn.chatgpt.com/docs/agent-configuration/agents-md> | 308 → 200 |

**이후 조사는 `learn.chatgpt.com/docs` 를 기준으로 한다.**

문서 인덱스의 최상위 절(확인한 그대로): Get started · Foundations · Explore · Available on · Releases · Features · Configuration · Developers · Security Administration · Administration · Use Cases · Resources

지원 표면: Codex CLI · Codex IDE extension · ChatGPT 웹 · Codex cloud · ChatGPT 데스크톱 앱(macOS/Windows) · 원격 연결

> Codex App/CLI/IDE와 일반 API·SDK의 적용 범위는 다르다. 아래 내용은 **Codex 표면** 기준이다.

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

### OwnHands에 주는 의미

- **지침 계층이 이미 네이티브로 존재한다.** 전역 default ↔ 프로젝트 override라는 구조가 이미 있다.
- 🤔 사용자가 생각 중인 "default + company 정책" 구분과 겹치는 지점이다. **단, 이것이 Company 우선 정책을 확정한다는 뜻은 아니다.** → [결정 상태표](../v2/decisions.md)
- 32 KiB 상한은 실질적 제약이다. 긴 지식을 지침에 넣지 말고 **Reference로 분리**할 근거가 된다.

### 직접 만들지 않아도 되는 것
- 지침 파일 탐색·병합·우선순위 처리
- 디렉터리 범위별 지침 override 메커니즘

---

## 2. Skills

출처: <https://learn.chatgpt.com/docs/build-skills> · 확인일 2026-09-16

### 확인한 동작

**구조**: `SKILL.md`를 담은 디렉터리. frontmatter 필수 필드는 `name`, `description`.

선택 구성:

```text
<skill>/
├── SKILL.md            # 필수. frontmatter: name, description
├── scripts/            # 실행 코드
├── references/         # 문서
├── assets/             # 템플릿·리소스
└── agents/openai.yaml  # UI 메타데이터·도구 의존성
```

**탐색 우선순위**

1. `$CWD/.agents/skills`
2. `$CWD/../.agents/skills` (Git 저장소의 상위 디렉터리)
3. `$REPO_ROOT/.agents/skills`
4. `$HOME/.agents/skills`
5. `/etc/codex/skills` (관리자·시스템 범위)
6. 내장 시스템 skill

**호출**: 명시적으로는 ChatGPT에서 `@skill`, Codex/IDE에서 `$skill`. 암묵적으로는 사용자 프롬프트가 skill의 `description`과 맞을 때.

**제약**: 최초 skill 목록은 모델 컨텍스트 윈도의 **최대 2%, 컨텍스트 크기를 모를 때 8,000자**를 소비한다. skill이 많으면 description이 먼저 줄어든다.

**지원 표면**: 단독 skill은 ChatGPT 데스크톱 앱·Codex CLI·IDE extension. 플러그인 번들 skill은 웹·데스크톱·모바일의 Chat/Work에서도 동작.

### OwnHands에 주는 의미

- **`SKILL.md` + `references/` 구조가 네이티브로 지원된다.** V2가 구상한 "상황별 Reference를 필요할 때 읽는" 구조([개요 §5](../v2/overview.md))는 별도 로더를 만들 필요 없이 플랫폼 구조와 그대로 맞물린다.
- `description` 기반 암묵 호출이 있으므로 **`description` 작성이 실제 라우팅 동작**이다.
- 2% / 8,000자 상한은 **Skill 개수를 늘릴수록 각 description이 깎인다**는 뜻이다. → 💬 Skill 이름·수를 정할 때 실제 제약으로 다룬다.
- ⚠️ **현재 저장소의 `skills/` 위치는 Codex 탐색 경로(`.agents/skills`)와 다르다.** V1은 다른 호스트를 전제로 만들어졌다. V2에서 어디에 둘지는 후속 결정이다.

### 직접 만들지 않아도 되는 것
- Skill 탐색·등록·우선순위 처리
- Reference 파일을 담는 디렉터리 규약
- 명시적 호출 문법

### 아직 확인하지 못한 것
- `references/` 파일을 **어떤 조건에서 실제로 읽어 들이는지**(전량 선로딩인지 필요 시 읽기인지)
- frontmatter의 선택 필드 전체 목록
- `agents/openai.yaml`의 스키마

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

**할 수 있는 일**

| 유형 | 방법 |
|---|---|
| 차단 | `PreToolUse`·`PermissionRequest`에서 `"behavior": "deny"` 반환 |
| 경고·정보 제공 | `systemMessage`, `additionalContext` |
| 관찰 | `SessionEnd`·`PostToolUse`·`UserPromptSubmit` 등 |

같은 이벤트에 여러 command hook이 걸리면 동시에 실행된다.

### OwnHands에 주는 의미

- **실행 전 차단(`PreToolUse`, `PermissionRequest`)과 실행 후 탐지(`PostToolUse`)가 문서상 분리돼 있다.** V2가 Build·Test guardrail을 이야기할 때 이 구분을 그대로 쓸 수 있다.
- 지침(Skill)에 "하지 마라"라고 쓰는 것과 hook으로 **실제 차단**하는 것은 다르다. 이 문서가 그 차이를 뒷받침한다.
- ⚠️ **이벤트가 존재한다는 것이 OwnHands의 hook 설계가 끝났다는 뜻은 아니다.** 구체 규칙·권한·구현은 후속 설계다.
- 로컬 에이전트 hook과 CI/CD의 배포 통제는 다른 층이다. Deploy gate를 hook만으로 처리한다고 가정하지 않는다.

### 직접 만들지 않아도 되는 것
- 도구 실행 가로채기 메커니즘
- 권한 요청 시점의 개입 지점
- 세션 생명주기 이벤트

### 아직 확인하지 못한 것
- hook 입출력 JSON 스키마 전체
- 각 이벤트의 정확한 실행 순서·타임아웃
- 실패 시 동작

---

## 4. Subagents

출처: <https://learn.chatgpt.com/docs/agent-configuration/subagents> · 확인일 2026-09-16

> 조사 메모: 문서 인덱스에는 `Subagents`가 있으나 `/docs/subagents`는 404다. 실제 경로는 위와 같다.

### 확인한 동작

**정의 위치와 형식**: 단독 **TOML** 파일, 파일 하나가 에이전트 하나.

- 개인: `~/.codex/agents/`
- 프로젝트: `.codex/agents/`

**필수 필드**: `name` · `description` · `developer_instructions`

**선택 필드** (다른 `config.toml` 키 사용 가능): `model` · `model_reasoning_effort` · `sandbox_mode` · `mcp_servers` · `skills.config`

**호출**: 위임을 요청하는 프롬프트, `AGENTS.md`나 skill의 위임 지시, ultra 지능 수준의 선제적 위임.

**권한**: "Subagents inherit your current sandbox policy" — 부모 턴의 권한 모드를 상속한다. 개별 파일에서 `sandbox_mode`를 덮어쓸 수 있고, `mcp_servers`·`skills.config`로 에이전트별 도구 구성이 가능하다.

### OwnHands에 주는 의미

- **역할·모델·권한·도구를 에이전트별로 나누는 구조가 이미 있다.** V2가 "독립된 역할·맥락·도구를 받아 작업 수행"이라고 적은 Agent 책임과 맞물린다.
- `skills.config`로 에이전트별 skill 구성이 가능하다 → 역할별로 읽을 Reference를 좁히는 방법이 플랫폼에 있다.
- 💬 **초기 역할과 수는 여전히 사용자와 결정할 사항이다.** 플랫폼이 지원한다는 사실이 역할 구성을 정해주지 않는다.

### 직접 만들지 않아도 되는 것
- 위임 실행 메커니즘
- 에이전트별 모델·샌드박스·MCP·skill 범위 지정

### 아직 확인하지 못한 것
- TOML 파일의 전체 키 목록
- 위임 시 부모/자식 간 컨텍스트 전달 범위
- 중첩 위임 허용 여부

---

## 5. 아직 조사하지 않은 영역 (미확인)

이번 작업은 **문서 재구성에 필요한 조사와 링크 검증**까지만 수행했다. 각 마일스톤의 전체 기술 설계는 착수 시점에 조사한다.

| 영역 | 상태 | 조사 시점 |
|---|---|---|
| Plan mode / 계획 기능의 Codex 대응 | 미확인 | Build 단계 착수 시 |
| MCP 서버 구성 상세 | 미확인 | 도구 연결이 필요해질 때 |
| Sandboxing·approvals 상세 | 미확인 | Deploy·Governance 착수 시 |
| Memories / Rules | 미확인 | 지침 설계 시 |
| Plugins 패키징 | 미확인 | 배포 형태 결정 시 |
| Codex cloud / CI 비대화형 실행 | 미확인 | Deploy 착수 시 |
| 관리자·엔터프라이즈 managed configuration | 미확인 | 조직 정책 연결 시 |

> ⚠️ 특정 호스트의 Plan Mode를 사용했다고 프로젝트의 `plan.md` 저장과 검토가 자동으로 끝난다고 가정하지 않는다.
> Codex에서의 실제 방법은 후속 이슈에서 공식 문서로 결정한다.

---

## 6. 이번 조사에서 얻은 결론

Codex는 **Skills · Hooks · Subagents · MCP · 샌드박스 · 지침 계층**을 이미 네이티브로 제공한다.

이것은 V2의 개발 방법을 뒷받침한다.

> V1에서 커진 유지보수 부담의 일부는, **플랫폼이 제공하는 것을 직접 만들었기 때문일 수 있다.**
> 그래서 V2는 각 마일스톤 착수 시 **먼저 공식 문서를 조사하고, 직접 만들지 않아도 되는 것부터 결정한다.**

→ [개발 방법](../v2/development-method.md) · [결정 상태표](../v2/decisions.md)

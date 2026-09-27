# Spec: Chat Plan & Design — GitHub-centered SDLC

- **기반 Intent**: [`intent.md`](intent.md)
- **작성 주체**: ChatGPT 분석 — 사용자 검토 및 승인 대상
- **일자**: 2026-09-22
- **상태**: Approved — 사용자 내용 승인 및 GitHub 저장 승인 (2026-09-22)
- **2026-09-25 Dogfooding 반영**: 사용자 후속 결정에 따라 Target Repository Resolution, 단일 Persistence Decision, 명시적 ELI5 요청 예외를 추가한다. 2026-09-22 최초 승인 기록은 유지한다.
- **2026-09-25 Astra 재설계**: Plugin 0.0.2의 런타임 재현을 반영해 `target_repository` 상태를 root router가 확정하고, 필요한 reference만 읽도록 정렬한다. 이전 승인 이력은 유지한다.
- **관련 Issue**: #154
- **기반 ADR**: ADR-0011, ADR-0012, ADR-0013, ADR-0017, ADR-0018, ADR-0019

---

## 1. 기술적 요구사항

### REQ-01 — Agent Plugins 1.0 기반 Chat Plugin

OwnHands의 Chat Plan & Design 기능은 별도 MCP 서버가 아닌 **Skills-only Agent Plugin**으로 제공한다.

Plugin root는 OwnHands 저장소 내부의 다음 경로를 사용한다.

```text
plugins/ownhands/
├── plugin.json
└── skills/
```

`plugin.json`은 Agent Plugins 1.0 portable schema를 사용한다.

```json
{
  "$schema": "https://agent-plugins.org/schemas/1.0.0/plugin.schema.json",
  "name": "ownhands",
  "version": "...",
  "description": "..."
}
```

이번 범위에서는 `mcp.json`, 자체 daemon, 자체 원격 서버를 추가하지 않는다.

---

### REQ-02 — Plugin과 Codex npm 배포 표면 분리

하나의 GitHub Repository를 Source of Truth로 사용하되 배포 표면은 분리한다.

```text
OwnHands repository
│
├── plugins/ownhands/          # Agent Plugin
│
└── .agents/skills/            # npx ownhands → Codex 프로젝트 설치용
```

`plugins/ownhands/`는 `npm pack`과 `npx ownhands init`의 설치 대상이 아니다.

`npx ownhands init`으로 설치된 프로젝트에는 다음이 존재해서는 안 된다.

```text
plugins/ownhands/
.agents/skills/plan-design/
```

---

### REQ-03 — `plan-design`은 Chat 전용 Core Skill

기존 `.agents/skills/grill-spec`은 deprecated shim 없이 제거한다.

기존 `grill-spec`의 유효한 GORE·인터뷰·Fact/Decision 분리·Checkpoint 규칙은 새 `plan-design`으로 이전한다.

Canonical Skill은 다음 위치에 하나만 둔다.

```text
plugins/ownhands/skills/plan-design/
├── SKILL.md
├── agents/
│   └── openai.yaml
└── references/
    ├── interview-guide.md
    ├── intent-guide.md
    ├── spec-guide.md
    ├── adr-guide.md
    ├── github-workflow.md
    ├── handoff-guide.md
    └── manual-fallback.md
```

`plan-design`은 하나의 거대한 Skill이 모든 세부 규칙을 직접 포함하지 않는다.

`SKILL.md`는 짧은 description과 작은 router로 작업 맥락·`target_repository` 상태·필요한 Stage를 고른다. 관련 reference는 해당 흐름에 들어갈 때만 읽는다. 세부 GitHub 저장, 인터뷰, ADR, Handoff는 각각의 reference가 맡는다. 이는 OwnHands가 [OpenAI의 Astra Skill 작성 글](https://developers.openai.com/blog/rethinking-skills-and-prompts-for-gpt-6-astra)을 참고해 채택한 구조다.

```text
plan-design
   ├─ GORE 인터뷰       → interview-guide
   ├─ Intent            → intent-guide
   ├─ Spec              → spec-guide
   ├─ 중요 Decision     → adr-guide
   ├─ GitHub 상태/저장   → github-workflow
   ├─ Codex 인계         → handoff-guide
   └─ GitHub 사용 불가   → manual-fallback
```

---

### REQ-04 — `plan-design` 제품 노출과 호출 정책

`plan-design/agents/openai.yaml`에는 다음 정책 의도를 선언한다.

```yaml
interface:
  display_name: "Plan & Design"
  short_description: "Define intent and technical design before implementation."

policy:
  products:
    - CHAT
  allow_implicit_invocation: false
```

의도는 다음과 같다.

- ChatGPT에서 사용한다.
- Codex용 로컬 Skill로 설치하지 않는다.
- 일반 대화가 자동으로 OwnHands SDLC로 전환되지 않도록 명시적 호출을 기본 UX로 한다.
- `products: [CHAT]` 메타데이터만을 유일한 격리 장치로 신뢰하지 않는다.
- 실제 격리는 Plugin/npm 배포 경계와 E2E 관측으로 함께 검증한다.

사용자의 기본 진입 UX는 ChatGPT의 Skill picker를 이용한 명시 호출이다.

```text
@Plan & Design
```

또는 UI에 표시되는 해당 Skill을 `@` picker에서 선택한다.

---

### REQ-05 — ELI5는 Companion Skill

ELI5는 OwnHands Core 로직이 아니라 **같은 Plugin 내부에서 ****`plan-design`****을 보조하는 Companion Skill**로 취급한다.

제품 의도는 다음과 같다.

```yaml
policy:
  products:
    - CHAT
    - CODEX
```

ELI5 원본의 repository, revision, license를 확인하지 않고 OwnHands 전용 구현으로 새로 만들어 대체하지 않는다.

이번 Chat Plan & Design 구현에서는 Stage 승인 UX에 필요한 Chat 측 사용을 연결한다.

Codex용 ELI5 배포·버전·Ponytail과의 패키징 세부사항은 ADR-0018 후속 작업으로 남긴다.

---

### REQ-06 — ELI5 호출 시점

자동 ELI5는 인터뷰 중 매번 호출하지 않는다.

각 Stage의 **전체 내용이 검토 가능한 상태가 된 직후, Content Approval 직전**에 한 번 사용한다.

사용자가 ELI5를 명시적으로 요청하면 인터뷰 중 어느 시점이든 실행할 수 있다. 이 호출만으로 Stage 완료·Content Approval·Persistence Approval 상태를 변경하지 않는다.

```text
Intent 완성
→ ELI5 큰 그림
→ Content Approval
→ Persistence Decision (선택이 Persistence Approval)

Spec 완성
→ ELI5 구조·흐름
→ Content Approval
→ Persistence Decision (선택이 Persistence Approval)
```

Intent ELI5는 다음을 중심으로 설명한다.

- 목표
- 비목표
- 사용자 흐름
- 핵심 결정

Spec ELI5는 다음을 중심으로 설명한다.

- 주요 구성요소
- 데이터/제어 흐름
- 실패 경로
- 검증 기준

---

## 2. Plan & Design Workflow

### 2.1 시작

`plan-design`이 명시적으로 호출되면 먼저 현재 작업이 다음 중 어디에 해당하는지 확인한다. Root Skill은 이 맥락에서 repo-aware 여부와 필요한 reference를 정한다.

```text
아이디어 탐색
실제 개발 작업
기존 GitHub Work Item을 이어가는 작업
```

대상 Repository가 확정된 뒤 저장소에서 직접 확인 가능한 사실은 사용자에게 질문하지 않는다.

### REQ-33 — Target Repository Resolution

Root router가 현재 작업의 `target_repository` 상태를 결정한다.

```text
repo-aware 요청
→ 현재 요청 또는 현재 작업에서 사용자가 확인한 단일 Repository가 있음
   → target_repository = owner/repository
   → GitHub workflow → 해당 Repository의 Fact Gathering
→ 확인된 Repository가 없음
   → target_repository = unresolved
   → 사용자에게 Repository 확인 → 확정 후 GitHub workflow
```

Plugin source Repository는 사용자가 현재 작업 대상으로 확인한 Repository가 아니다. 후보가 여러 개여도 `unresolved`로 두고 사용자에게 선택을 요청한다. `unresolved`에서는 README, package.json, Issue, Branch 등 repository-specific Fact Gathering을 시작하지 않는다. 저장소가 필요 없는 아이디어는 No-Repo로 진행한다. Target Repository 확인과 Persistence topology 선택은 별개의 시점에 수행한다.

---

### 2.2 Issue가 이미 있는 경우

사용자가 Issue를 지정했거나 현재 작업과 명확히 연결된 Issue가 있으면 이를 사용한다.

연결된 작업 Branch가 하나로 명확하면 재사용을 우선한다.

Branch가 없으면 저장 시점에 작업 Branch 생성을 준비한다.

후보 Branch가 여러 개이거나 의미가 불명확하면 임의 선택하지 않고 사용자에게 선택을 요청한다.

Stage 전체의 Content Approval 뒤 기존 Issue·Branch와 저장할 Stage 파일·관련 ADR의 범위를 보여주고, 이 경로로 저장할지 한 번만 묻는다.

---

### 2.3 Issue가 없는 경우

Issue는 SDLC의 필수 단계가 아니다.

대상 Repository가 확정되고 관련 Issue가 없다면 `plan-design`은 기획 중 새 Issue·Branch 생성 방식을 묻거나 자동 생성하지 않는다. Stage 전체의 Content Approval 뒤 대상 Repository, Issue 초안·Branch 제안, 저장할 Stage 파일·관련 ADR과 commit 범위를 보여주고 Persistence Decision으로 다음 선택을 제시한다.

```text
1. Issue를 생성하고 Issue 기반 Branch로 진행
2. Issue 없이 작업 Branch만 생성
3. 지금은 GitHub 작업 없이 기획·설계 계속
```

1 또는 2를 선택한 행위 자체가 Persistence Approval이다. 3을 선택하면 GitHub write를 하지 않는다.

Issue를 만들지 않는다고 해서 GitHub 중심 SDLC 원칙이 깨지는 것은 아니다.

Issue 없이도 다음 durable artifact가 Source of Truth가 될 수 있다.

```text
Branch
Intent
Spec
ADR
Plan
Commit
PR
```

Branch 이름 기본안은 다음과 같이 단순하게 유지한다.

```text
Issue 있음: work/<issue-number>-<slug>
Issue 없음: work/<slug>
```

기존 Branch가 있으면 새 Branch 생성을 우선하지 않는다.

---

## 3. Intent Stage

### REQ-07 — Intent 작성

Intent는 최소 다음을 정의한다.

- 문제와 배경
- 대상 사용자
- 목표 결과
- 성공 기준
- 비목표
- 핵심 제약

중요한 구현 상세를 Intent 단계에서 미리 확정하지 않는다.

---

### REQ-08 — ADR 판단

Decision 하나마다 ADR 하나를 만들지 않는다.

다음과 같은 경우만 ADR 후보로 본다.

- 장기적으로 다시 참고할 아키텍처 선택
- 책임 경계 변경
- 중요한 정책 선택
- 의미 있는 대안을 기각한 결정
- 이후 Spec/Build가 반복적으로 의존할 결정

단순 문구 선택이나 지역적인 구현 상세는 Intent/Spec 안에 둔다.

---

### REQ-09 — Content Approval

Intent가 완성되면 ELI5 요약을 먼저 제공한다.

그 후 사용자에게 **내용 승인**을 받는다.

Content Approval은 다음 의미만 가진다.

```text
intent.md 내용에 사용자가 동의함
```

문서의 상태는 이때 `Approved`가 될 수 있다.

GitHub에 저장됐다는 의미까지 포함하지 않는다.

Chat UX에서는 별도로 다음 상태를 보여준다.

```text
Intent 승인 완료
GitHub 저장: 대기
```

---

### REQ-10 — Persistence Decision과 Approval

Content Approval 후 별도의 Persistence Decision을 한 번 요청한다. Issue가 없으면 2.3의 세 경로를 제시하며 1/2 선택 자체를 Persistence Approval로 취급한다. 기존 Issue·Branch 경로를 쓰는 경우에는 구체적인 대상과 내용을 보여주고 그 경로로 저장할지 한 번만 묻는다.

Content Approval만으로 GitHub write를 수행하지 않는다. Persistence Decision에서 승인한 Issue·Branch·Stage 파일·관련 ADR의 동일한 write를 다시 승인받지 않는다. Write 직전 최신 상태를 재조회하고, 대상 상태 변경·충돌·승인 범위 밖 write가 필요할 때만 차이를 보여주고 다시 확인한다.

---

### REQ-11 — Intent Stage Commit

저장이 승인되고 GitHub write가 가능하면 다음을 하나의 의미 있는 Stage commit으로 묶는다.

```text
intent.md
+ Intent 과정에서 생성된 ADR
+ Intent 과정에서 수정된 관련 ADR
```

Decision마다 커밋하지 않는다.

```text
Commit Boundary = Stage Approval Boundary
```

---

## 4. Spec Stage

### REQ-12 — Spec 작성

승인된 Intent를 기반으로 다음을 구체화한다.

- Requirements
- Architecture
- Interfaces
- State / Data Flow
- Failure Handling
- Edge Cases
- Acceptance Criteria
- Validation Strategy

Intent에서 이미 확정된 제품 결정을 다시 질문하지 않는다.

---

### REQ-13 — Spec 승인

Spec도 Intent와 동일하게 두 승인 단계로 처리한다.

```text
Spec 완성
→ ELI5 설명
→ Content Approval
→ Persistence Decision (선택이 Persistence Approval)
```

Persistence Approval 후 다음을 한 Stage commit으로 저장한다.

```text
spec.md
+ Design 과정에서 생성/수정된 관련 ADR
```

---

## 5. GitHub Write 및 Reconcile 계약

### REQ-14 — Write 직전 최신 상태 확인

GitHub write 직전 Branch의 최신 상태를 다시 읽는다.

마지막 확인 이후 HEAD가 바뀌었는지를 검사한다.

---

### REQ-15 — Branch가 전진했지만 충돌이 없는 경우

다른 commit이 추가됐더라도 현재 저장 대상과 충돌하지 않으면 최신 HEAD를 기준으로 작업을 이어갈 수 있다.

기존 commit을 되돌리거나 force push하지 않는다.

---

### REQ-16 — 같은 Artifact가 바뀐 경우

예:

```text
Chat이 만든 spec.md 후보
vs
GitHub에서 사용자가 이미 수정한 spec.md
```

자동 overwrite하지 않는다.

차이를 사용자에게 보여주고 다음 중 선택하도록 한다.

- GitHub 버전 유지
- Chat 버전 적용
- 둘을 병합
- 저장 취소

---

### REQ-17 — 자동 Recovery 금지

GitHub Plugin/Connector가 다시 사용 가능해졌다고 해서 자동으로 다음을 수행하지 않는다.

```text
Issue 생성
Branch 생성
파일 저장
```

그 사이 사용자가 수동으로 작업했을 수 있기 때문이다.

다시 write를 시도하기 전 현재 GitHub 상태를 재조회하여 **Reconcile**한다.

---

## 6. GitHub 사용 불가 Fallback

### REQ-18 — 기획·설계는 계속 가능

다음 상황에서도 Plan & Design 대화 자체는 계속할 수 있다.

- GitHub Plugin이 연결되지 않음
- 저장소 권한 부족
- Branch 생성 권한 부족
- Commit 실패
- 일시적 GitHub/API 오류

GitHub가 사고·설계를 수행하는 장소는 아니기 때문이다.

---

### REQ-19 — 저장 상태 표현

복잡한 상태 머신을 추가하지 않는다.

예:

```text
Intent 승인 완료
GitHub 저장: 대기
```

또는:

```text
Spec 승인 완료
GitHub 저장: 실패
```

문서 내용 자체의 상태는 `Approved`로 유지할 수 있다.

---

### REQ-20 — Manual Fallback

GitHub write가 불가능하면 사용자가 직접 저장할 수 있도록 다음 내용을 제공한다.

현재 진행 단계에 존재하는 것만 제공한다.

- Issue 초안 — 사용자가 Issue 경로를 선택한 경우에만
- `intent.md`
- 관련 ADR
- `spec.md`
- Handoff 텍스트
- 수동 저장 가이드

존재하지 않는 Issue 번호나 Branch 이름을 만들어낸 척하지 않는다.

---

### REQ-21 — 나중에 GitHub 사용 가능해진 경우

사용자가 다시 GitHub 저장을 요청하거나 연결이 가능한 상태에서 작업을 이어갈 때:

```text
현재 Repository 상태 조회
→ 이미 수동으로 수행된 작업 확인
→ 누락된 것만 식별
→ 기존 Persistence Decision의 승인 범위 내 누락 write 적용
```

재연결 자체만으로 자동 복구 workflow를 실행하지 않는다. 기존 Persistence Decision이 없다면 먼저 저장 여부와 경로를 선택받는다. 기존 승인 범위의 누락분은 같은 write를 다시 승인받지 않는다. Issue·Branch·대상 파일 상태가 바뀌었거나 충돌·승인 범위 밖 write가 필요하면 차이를 보여주고 다시 확인한다.

---

## 7. Handoff 계약

### REQ-22 — Normal Flow에서 `handoff.md`를 만들지 않음

Handoff는 Intent/Spec/ADR을 복제한 새로운 Source of Truth가 아니다.

정상 경로에서는 `handoff.md` 파일을 GitHub에 저장하지 않는다.

영구 보존되는 것은 작성 규칙인:

```text
references/handoff-guide.md
```

이다.

---

### REQ-23 — Handoff의 목적

Handoff의 책임은 Codex에게 강한 실행 명령을 내리는 것이 아니다.

**올바른 출발점에 세우는 것**이다.

최소 의미는 다음과 같다.

```text
Context
Approved Sources
Decisions
Open Questions
Suggested Entry Point
```

`Next Action`, `Do X`, 특정 구현 방식 강제와 같은 필드는 기본 Handoff에 두지 않는다.

---

### REQ-24 — Suggested Entry Point

예:

```text
승인된 Intent/Spec과 관련 ADR을 먼저 읽고
현재 저장소 상태를 확인한 뒤 구현 계획이 필요한지 판단한다.
아직 결정되지 않은 사항은 추측하지 않는다.
```

Build 시작 자체를 자동 승인하는 문장이 아니다.

---

## 8. Codex Build Entry

### REQ-25 — 작은 작업은 Chat Plan & Design을 생략할 수 있음

다음과 같은 작업은 바로 Codex `$build`에서 시작할 수 있다.

- 변경 위치와 기대 결과가 명확함
- 구현 방법에 의미 있는 선택지가 거의 없음
- 실패 영향 범위가 작음
- 새로운 제품/정책 결정이 필요하지 않음

사용자가 명시적으로 `plan-design`을 사용하고 싶다고 하면 작은 작업에도 사용할 수 있다.

---

### REQ-26 — `$build`가 Implementation Plan 필요성을 판단

고정된 파일 개수 같은 숫자 기준을 사용하지 않는다.

Plan Mode가 필요한 주요 신호:

- 여러 컴포넌트 또는 인터페이스가 연결됨
- 구현 방법에 의미 있는 대안이 있음
- 변경 순서가 중요함
- migration 또는 상태 전이가 중요함
- 실패 시 Blast Radius가 큼
- 구현자가 중요한 선택을 추측해야 함

---

### REQ-27 — Plan Mode가 필요 없는 경우

```text
$build
→ Light Flow 판정
→ 바로 구현
→ applicable Fresh Evidence
→ Verify
```

`plan.md`를 억지로 생성하지 않는다.

---

### REQ-28 — Plan Mode가 필요한 경우

Build가 스스로 Plan Mode를 켠 척하지 않는다.

사용자에게 명시적으로 안내한다.

```text
이 작업은 별도 구현 계획이 필요합니다.
`/plan` 또는 `Shift+Tab`으로 Plan Mode로 전환해주세요.
```

사용자가 실제 Plan Mode로 전환한 뒤:

```text
구현 계획 논의
→ 사용자 승인
→ 쓰기 가능한 모드
→ plan.md 저장
→ Build
```

으로 이어간다.

---

## 9. Light Flow Verification

### REQ-29 — Light Flow에는 `verification.md`를 만들지 않음

Light Flow에서 `plan.md`가 없다고 별도 Evidence 파일을 추가하지 않는다.

Verify는 현재 사용자 요청, diff, 실행한 native checks를 기준으로 Verification Summary를 반환한다.

예:

```text
Verification Summary

- npm test: PASS
- npm run lint: PASS
- 변경 범위: README.md
- UNOBSERVED: 없음
```

---

### REQ-30 — PR이 없는 Light Flow

Verification Summary는 현재 Codex 세션에서 사용자에게 완료 근거로 제공한다.

별도 파일로 영속화하지 않는다.

---

### REQ-31 — PR이 있는 Light Flow

별도의 `verification.md`를 만들지 않는다.

Verification Summary의 관련 내용을 PR 본문 검증 섹션으로 투영한다.

```text
Light Flow
→ Verify
→ Verification Summary
→ PR
   └─ 검증/Evidence 섹션
```

---

### REQ-32 — Light Flow의 독립 Verifier

Light Flow는 독립 Verifier를 기본 강제하지 않는다.

다음 중 하나가 발견되면 Light Flow를 계속 밀어붙이지 않고 Heavy/Planned Flow로 승격한다.

- 예상보다 변경 반경이 커짐
- 중요한 인터페이스 변경 발견
- 요구사항 모호성 발견
- 고위험 데이터/권한/마이그레이션 영향 발견
- deterministic check만으로 완료 판단이 불충분함

즉 작은 작업의 검수 비용을 과도하게 늘리지 않되, 작업이 더 이상 작지 않다는 증거가 나오면 경량 경로를 포기한다.

---

## 10. Plugin / Repository 구조

목표 구조:

```text
OwnHands/
│
├── plugins/
│   └── ownhands/
│       ├── plugin.json
│       └── skills/
│           ├── plan-design/
│           │   ├── SKILL.md
│           │   ├── agents/
│           │   │   └── openai.yaml
│           │   └── references/
│           │       ├── interview-guide.md
│           │       ├── intent-guide.md
│           │       ├── spec-guide.md
│           │       ├── adr-guide.md
│           │       ├── github-workflow.md
│           │       ├── handoff-guide.md
│           │       └── manual-fallback.md
│           │
│           └── eli5/
│               └── ...
│
├── .agents/
│   └── skills/
│       ├── build/
│       ├── verify/
│       ├── feedback/
│       └── ...
│
├── docs/
└── package.json
```

---

## 11. 기존 자산 변경 범위

### 제거

```text
.agents/skills/grill-spec/
```

deprecated alias는 두지 않는다.

---

### 수정

```text
.agents/skills/build/SKILL.md
.agents/skills/verify/SKILL.md
AGENTS.md
docs/specs/README.md
docs/installation.md
package.json 또는 npm packaging 관련 설정
tests/ownhands-cli.test.js
관련 Eval/Static assertions
```

필요한 ADR 정합성 수정:

```text
ADR-0012
- MCP 중심 설명 제거
- Skills-only Agent Plugin 방향 반영

ADR-0013
- Build가 Light/Planned Flow를 라우팅하도록 반영

ADR-0017
- 자동 ELI5 호출을 Stage Content Approval 직전으로 확정

ADR-0019
- Issue 필수 규칙 제거
- Issue optional + 사용자 선택
- Content Approval / Persistence Approval 분리
- Recovery 대신 Reconcile 반영
```

새로운 ADR을 불필요하게 추가하기보다 기존 ADR이 다루는 같은 결정의 후속 확정이면 기존 ADR을 정렬한다.

---

## 12. 이번 구현에서 명시적으로 제외

다음은 별도 후속 Build로 분리한다.

- Verify / Review 통합
- Reviewer 제거
- Review Skill 제거 또는 이관
- 기존 Hook / Gate 제거
- Hook 미차단 원인 분석
- Feedback 구조 재정렬
- Ponytail 적용 세부 정책
- ELI5의 Codex/npm 배포·업데이트 전체 계약
- 새로운 CI 강제 장치
- 전체 과거 문서 일괄 개명

현재 존재하는 Review/Hook 구조가 새 최종 구조라고 주장하지 않는다.

---

## 13. Acceptance Criteria

### Agent Plugin

- **AC-01**: `plugins/ownhands/plugin.json`이 Agent Plugins 1.0 portable manifest 형식을 따른다.
- **AC-02**: Plugin은 MCP server 없이 Skills-only로 유효하게 구성된다.
- **AC-03**: `plan-design`은 Plugin에 존재하고 `.agents/skills/`에는 존재하지 않는다.
- **AC-04**: 기존 `grill-spec` Skill은 제거되고 deprecated shim도 남지 않는다.
- **AC-05**: `plan-design`에는 `products: [CHAT]`과 `allow_implicit_invocation: false`가 선언된다.
- **AC-06**: ChatGPT에서 `@` Skill picker를 통해 `plan-design`을 명시적으로 선택해 실행할 수 있음을 실제 관측한다.
- **AC-07**: 일반 대화가 의도치 않게 Plan & Design workflow로 진입하지 않는지 실제 관측한다.
- **AC-08**: Codex/npm 설치 결과에서 `plan-design`이 Skill 후보로 설치되지 않는다.

### Distribution

- **AC-09**: `npm pack --dry-run` 결과에 `plugins/ownhands/`가 포함되지 않는다.
- **AC-10**: `npx ownhands init` 대상 프로젝트에 Plugin 파일 또는 `plan-design`이 복사되지 않는다.
- **AC-11**: 기존 Codex Build/Verify 자산은 필요한 범위에서 정상 설치된다.

### Plan & Design UX

- **AC-12**: Intent와 Spec 각각에서 자동 ELI5 설명이 Content Approval 직전에 한 번 호출된다. 사용자의 명시적 ELI5 요청은 언제든 수행할 수 있으나 Stage 완료·승인 상태를 자동 변경하지 않는다.
- **AC-13**: Content Approval과 Persistence Decision은 별도 사용자 결정으로 처리하며, Persistence Decision 뒤 동일 write에 대한 세 번째 승인을 요구하지 않는다.
- **AC-14**: Content Approval 이전에는 승인된 Artifact로 저장하지 않는다.
- **AC-15**: Persistence Approval 이전에는 GitHub write를 수행하지 않는다.
- **AC-16**: Stage commit은 Decision별 commit이 아니라 해당 Stage 산출물을 묶어 생성한다.

### GitHub Workflow

- **AC-17**: Issue가 존재하면 명확한 기존 작업 Branch를 우선 재사용한다.
- **AC-18**: Issue가 없으면 Content Approval 뒤 Persistence Decision에서 Issue 생성 / Branch만 생성 / GitHub 없이 계속의 3가지 선택을 제공한다. 1/2 선택 자체가 Persistence Approval이다.
- **AC-19**: Branch HEAD 변경을 감지하면 write 전에 최신 상태를 다시 읽는다.
- **AC-20**: 동일 Artifact 충돌 시 자동 overwrite 또는 force push를 하지 않는다.
- **AC-21**: GitHub가 다시 사용 가능해져도 자동 Recovery action을 실행하지 않고 현재 상태를 Reconcile한다. 기존 Persistence Decision 범위의 누락 write는 재승인 없이 적용하며 대상 상태 변경·충돌·범위 밖 write만 다시 확인한다.

### Fallback

- **AC-22**: GitHub write 불가 상태에서도 Intent/Spec 논의와 Content Approval은 가능하다.
- **AC-23**: 저장되지 않은 상태를 “GitHub 저장 대기/실패”로 명확히 표시한다.
- **AC-24**: 사용자가 직접 저장할 수 있는 Artifact 내용과 수동 가이드를 제공한다.
- **AC-25**: 존재하지 않는 Issue 번호·Branch·commit을 만들어내지 않는다.

### Handoff

- **AC-26**: 정상 경로에서 작업별 `handoff.md`를 생성하지 않는다.
- **AC-27**: `handoff-guide.md`에는 Context / Approved Sources / Decisions / Open Questions / Suggested Entry Point가 정의된다.
- **AC-28**: 기본 Handoff가 구현 방식이나 Build 실행을 강하게 명령하지 않는다.

### Build Routing

- **AC-29**: 명확한 작은 작업은 Chat Plan & Design 없이 `$build`에서 시작할 수 있다.
- **AC-30**: `$build`는 파일 개수 같은 단일 숫자 규칙이 아니라 구현 판단 필요성을 기준으로 Plan Mode 필요 여부를 결정한다.
- **AC-31**: Plan Mode 필요 시 모델이 전환한 척하지 않고 `/plan` 또는 `Shift+Tab` 사용을 안내한다.
- **AC-32**: 실제 Plan Mode에서 승인된 계획만 `plan.md`로 보존하고 Build로 이어간다.

### Light Verification

- **AC-33**: Light Flow에서는 `plan.md`와 `verification.md`를 억지로 생성하지 않는다.
- **AC-34**: applicable checks 결과를 Verification Summary로 사용자에게 제공한다.
- **AC-35**: PR이 생성되면 Verification Summary가 PR 검증/Evidence 내용으로 투영될 수 있다.
- **AC-36**: Light Flow 도중 위험·모호성·Blast Radius 증가가 발견되면 Heavy/Planned Flow로 승격한다.

### E2E

- **AC-37**: 실제 작은 사례에서 Chat `plan-design → Intent → Spec → GitHub 저장 → Handoff → Codex $build` 흐름을 관측한다.
- **AC-38**: Codex가 이미 승인된 중요한 제품 결정을 이유 없이 다시 인터뷰하지 않는다.
- **AC-39**: 구현 완료 후 applicable Fresh Evidence를 확인한다.
- **AC-40**: 이번 사이클에서 검증하지 않은 Plugin/Codex 런타임 동작은 `UNOBSERVED`로 남기고 PASS로 승격하지 않는다.

### Dogfooding Regression

- **AC-41**: 새 Chat의 repo-aware 요청에서 사용자가 Repository를 지정하지 않았고 현재 작업에서 확인한 Repository도 없으면 첫 응답의 `target_repository`는 `unresolved`다. 모델은 Repository 확인을 요청하고, 확인 전 README·package.json·Issue·Branch 등 repository-specific Fact를 조회하지 않는다. 확인 후 `owner/repository` 상태에서 GitHub workflow와 Fact Gathering을 진행한다. 정적 계약 통과와 Chat runtime 성공은 별도로 판정한다.

---

## 14. 추적성

| Intent 목표                 | Spec 요구사항           | 주요 AC                |
| ------------------------- | ------------------- | -------------------- |
| Chat이 Plan & Design 담당    | REQ-01\~06          | AC-01\~08            |
| GitHub 중심 Source of Truth | REQ-07\~21, REQ-33  | AC-12\~25, AC-41     |
| Codex로 안전한 인계             | REQ-22\~24          | AC-26\~28, AC-37\~38 |
| 작은 작업 경량 경로               | REQ-25\~32          | AC-29\~36            |
| 두 배포 표면 분리                | REQ-01\~05, 구조/변경범위 | AC-03, AC-08\~11     |
| 실제 E2E 확인                 | 전체                  | AC-37\~40            |

---

## 15. 구현 전 남겨두는 기술 검증

다음은 사용자 제품 결정이 아니라 구현자가 공식 문서/실측으로 확인해야 하는 사항이다.

1. Agent Plugins 1.0 manifest의 현재 validator와 OpenAI extension 필드.
2. `products: [CHAT]`이 실제 Chat/Codex 노출에 적용되는 범위.
3. `allow_implicit_invocation: false`가 Chat에서 실제 implicit activation을 억제하는지.
4. ELI5 upstream source, revision, license.
5. ChatGPT에서 GitHub Plugin이 없는 상태와 read-only/write-failure 상태를 구별할 수 있는 실제 tool surface.
6. Codex Plan Mode 전환 UI의 현재 `/plan` / `Shift+Tab` 동작.

확인되지 않은 플랫폼 동작은 Spec의 OwnHands 결정과 구분하고, 검증 결과에 따라 구현만 조정한다.

# V2-M4 조사 — 상황별 검증 Reference 구조 및 Verifier 런타임 권한·재배치 조사

- **일자**: 2026-09-19
- **관련 Issue**: [#125](https://github.com/taejung3852/OwnHands/issues/125)
- **선행 마일스톤**: V2-M3 ([#121](https://github.com/taejung3852/OwnHands/issues/121), [#123](https://github.com/taejung3852/OwnHands/issues/123), [ADR-0007](../adr/0007-plan-artifact-and-build-feedback-loop.md))
- **핵심 참고 자료**:
  - [Anthropic AI-Native SDLC Playbook 대응표](../../references/anthropic-playbook.md)
  - [Codex 공식 문서 확인](../../references/codex-official.md)
  - [V2 개요 §5 — 검증 지식은 필요할 때 읽는다](../overview.md)
  - [결정 상태표](../decisions.md)

---

## 1. Context & Background (배경 및 문제의식)

### 1.1 V1의 교훈: "배보다 배꼽이 더 커지는 검증 시스템의 비극"
- V1([project-journey.md](../../story/project-journey.md))은 AI가 만든 결과를 믿을 수 있게 만들기 위해 검증 스펙(Verification Spec), 베이스라인(Baseline), 리뷰(Review), 증거(Evidence), 실시간 대시보드(Dashboard)를 모두 코드로 구축했다.
- 그 결과, 수많은 커스텀 러너 스크립트, 소켓/캐시 관리, 정합성 검사 등 **검증 시스템 자체를 유지보수하는 부담이 실제 개발보다 더 커지는 주객전도**를 겪었다.
- **V2의 절대 원칙 (Thin Harness)**:
  - 거대한 검증 프레임워크, 독자 CLI 러너, 상시 모니터링 데몬을 직접 개발하지 않는다.
  - 플랫폼(Codex)이 이미 제공하는 네이티브 기능(Subagent, `references/` 지연 로딩, Git diff) 위에 가벼운 마크다운 지침과 프로토콜만 얹는다.

### 1.2 M3에서 M4로 넘어온 미결 과제
- V2-M3([ADR-0007](../adr/0007-plan-artifact-and-build-feedback-loop.md))를 통해 실행 계획인 `plan.md` 아티팩트와 Build Feedback Loop 6대 원칙을 메인 브랜치에 확정했다.
- 그러나 ADR-0007 원칙 5에 명시했듯이:
  > *"Verifier 런타임 권한 경계: 현재 `verifier.toml`은 `sandbox_mode = "read-only"`이므로... Verifier가 테스트를 직접 재실행하는 권한/환경 확정은 런타임 실측 후 M4(`Test & Assurance`)에서 다룬다."*
- 따라서 M4에서는 다음 질문에 답해야 한다:
  1. **검증 지식(Reference)**을 어떻게 배치해야 토큰을 낭비하지 않고 필요할 때만 핀포인트로 읽힐 수 있는가?
  2. **`verifier` Subagent**는 실제로 테스트를 직접 돌릴 수 있는가, 아니면 증거를 역추적 감사하는 역할이어야 하는가?
  3. **Before(구현 전 기준선)**를 확보하지 않고 개선을 주장하는 AI의 거짓말을 어떻게 시스템적으로 차단할 것인가?

---

## 2. Core Findings (1차 공식 자료 및 런타임 팩트)

### 2.1 Fact 1: Codex의 점진적 공개(Progressive Disclosure)와 `references/` 동작
- **공식 문서 확인 ([Codex 공식 문서 §2.4](../../references/codex-official.md))**:
  > *"Codex uses progressive disclosure for skills:*
  > *- It starts with metadata (`name`, `description`) for discovery*
  > *- It loads `SKILL.md` only when a skill is chosen*
  > *- **It reads references or runs scripts only when needed**"*
- **카탈로그 토큰 예산(10,000 토큰 천장)**:
  - Skill 목록은 초기 턴에서 최대 2% 또는 10,000 토큰으로 제한된다.
  - 하지만 Skill 폴더 내 `references/` 디렉터리에 둔 문서들은 초기 카탈로그 예산을 **전혀 소모하지 않는다**.
  - ⚠️ **동작 조건**: `references/`에 문서를 넣어두기만 하면 자동으로 읽히는 것이 아니다. 반드시 상위 `SKILL.md` 본문에서 "어떤 상황에서 이 문서를 읽어라"고 명시적 조건과 경로를 링크해야 로드된다.

### 2.2 Fact 2: `verifier` Subagent의 `sandbox_mode = "read-only"` 런타임 실측
- **현재 설정 (`.codex/agents/verifier.toml`)**:
  ```toml
  name = "verifier"
  description = "Independent verification agent that runs tests, executes assertions, and verifies acceptance criteria without implementation bias."
  sandbox_mode = "read-only"
  ```
- **런타임 제약 및 위험**:
  - `sandbox_mode = "read-only"` 상태의 에이전트는 파일시스템 수정(`workspace-write`)이 차단된다.
  - 대부분의 모던 테스트 러너(`pytest`, `jest`, `vitest`, `cargo test` 등)는 테스트 실행 시 임시 파일(`__pycache__`, `.pytest_cache`, `dist/`, `.tmp` 등)을 파일시스템에 쓰려고 시도한다.
  - 순수 `read-only` 샌드박스에서 테스트 러너를 실행하면 쓰기 권한 부족(`PermissionDenied` / `EACCES`)으로 인해 코드가 정상임에도 테스트 자체가 비정상 크래시될 위험이 높다.
  - 또한 Codex 공식 문서(§4.5)에 따르면, Subagent는 부모의 live runtime permissions/yolo 설정을 상속받으므로 `sandbox_mode`만으로 완벽한 격리를 보장할 수 없다.

### 2.3 Fact 3: V1 검증 자산 중 버릴 것과 가져올 것 (선별 기준)
- **버릴 것 (Deprecate & Exclude)**:
  - ❌ 커스텀 Verification Runner 및 CLI 바이너리 (시스템 복잡도 폭증의 원인).
  - ❌ 실시간 소켓/서버 기반 Dashboard (상시 연결 및 polling 비용 과다).
  - ❌ 복잡한 JSON 스키마 기반의 엄격한 기계식 assertion 파서.
- **가져올 것 (Preserve & Reposition)**:
  - ✅ **Before-After Baseline 원칙**: 버그 수정, 성능 개선 시 코드를 건드리기 전 "현재 상태의 실패 로그/측정값"을 먼저 기록으로 남기는 원칙.
  - ✅ **4대 상태 어휘의 가치**: `verified / failed / unobserved / unknown` — 모르는 것을 모른다고 정직하게 표시하는 단일 진실 원칙.
  - ✅ **역할 분리**: 구현자(Builder) 편향을 막는 독립 검수(Verifier)와 PR 리뷰(Reviewer)의 분리.

---

## 3. M4 설계 후보 및 트레이드오프 (Candidate Designs)

### 후보 1. 검증 Reference의 배치 구조: 독립 Skill vs 공유 Reference

| 안 | 구조 | 장점 | 단점 / 트레이드오프 |
|---|---|---|---|
| **안 1. 독립 `test` Skill** | `.agents/skills/test/`<br>├── `SKILL.md`<br>└── `references/*.md` | Codex의 점진적 공개를 완벽히 활용. `test` 스킬 호출 시에만 로드되어 컨텍스트 절약. | Skill 개수가 4개로 증가 (10,000 토큰 분할 게이트 고려 필요). |
| **안 2. 기존 Skill 확장 (grill-spec 내)** | `grill-spec/references/`<br>에 검증 지식 병합 | Skill 개수를 늘리지 않음 (3개 유지). | `grill-spec`의 책임이 '인터뷰 도우미'에서 '검증 지침'까지 과도하게 비대해짐. |
| **안 3. 영구 문서 디렉터리** | `docs/v2/references/`<br>에 검증 가이드 배치 | Skill 토큰 예산을 전혀 먹지 않고, `AGENTS.md`나 `plan.md`에서 직접 링크 가능. | 에이전트가 링크를 명시적으로 열어보지 않으면 자발적 적용 누락 가능성. |

> 💡 **추천 방향**: **안 1(독립 Test/Assurance Skill)과 안 3(문서)의 하이브리드** — 검증 실행 및 증거 감사를 전담하는 가벼운 스킬 또는 `plan.md`가 직접 가리키는 `docs/v2/references/` 방식의 실측 비교가 Step ②에서 필요.

---

### 후보 2. Verifier 서브에이전트의 런타임 실행 모델

| 안 | 메커니즘 | 장점 | 단점 / 트레이드오프 |
|---|---|---|---|
| **안 A. Fresh Evidence 감사관 모델 (ADR-0007)** | Builder가 테스트를 실행하고 터미널 증거를 남김 ➔ Verifier는 read-only로 AC와 증거를 역추적 대조만 수행 | `read-only` 샌드박스에서 완벽 동작. 테스트 러너의 파일 쓰기 충돌 없음. 가볍고 빠름. | Builder가 가짜 터미널 로그를 만들어낼 극단적 환각 시 감지 난이도 존재. |
| **안 B. 독립 재실행 모델 (Independent Runner)** | Verifier에게 격리된 샌드박스 실행 권한을 주고, 처음부터 끝까지 테스트를 직접 재실행 | 구현자 편향을 물리적으로 100% 차단. | 테스트 러너 임시 파일 쓰기 권한 필요. 빌드/테스트 시간이 2배로 소요됨. |

> 💡 **추천 방향**: **안 A(Fresh Evidence 감사관 모델)를 기본값으로 채택**.  
> 이유: V2의 핵심인 Thin Harness에 부합하며, 샌드박스 쓰기 충돌 없이 즉시 안정적으로 작동함. Verifier는 AC 항목별로 Builder가 제시한 터미널 출력(Exit code, Assertion 로그, 커밋 해시)의 신선도를 교차 검증함.

---

### 후보 3. Before-After Baseline 프로토콜

- **규칙 정의**:
  1. 작업 성격이 `bugfix` 또는 `performance`인 경우:
  2. 코드를 수정하기 전, **현재 브랜치에서 실패하는 테스트 로그 또는 현재 벤치마크 수치**를 `plan.md`의 `Before Baseline` 섹션에 먼저 기록한다.
  3. Before 로그가 없는 PR은 Verifier가 `FAIL (Baseline Missing)`으로 판정한다.
  4. 구현 완료 후, 동일한 조건에서 실행한 `After Evidence`를 대조하여 결함 해결 또는 성능 개선을 입증한다.

---

## 4. 직접 만들지 않아도 되는 것 (Non-goals & Native First)

| 구분 | 플랫폼 제공 / 배제 대상 | OwnHands V2-M4가 할 일 |
|---|---|---|
| **테스트 러너** | 언어별 네이티브 도구 (`npm test`, `pytest`, `cargo test` 등) | 러너를 직접 만들지 않고, 실행된 터미널 로그(Fresh Evidence)만 수집·대조 |
| **검증 대시보드** | 웹 서버, 소켓, DB, 상시 polling UI | 필요 시 명시적 `/explain` HTML 스토리 카드로 1회성 렌더링 |
| **복잡한 Assertion 파서** | AST 분석기, JSON 스키마 검증기 | Verifier Subagent의 LLM 추론을 활용한 AC 역추적 대조 (Zero-Code) |
| **환경 격리** | Docker, VM 컨테이너 자체 오케스트레이션 | Codex 내장 `sandbox_mode` 및 `worktree` 위임 |

---

## 5. 결론 및 다음 단계

1. **조사 요약**:
   - M4는 거대한 테스트 프레임워크를 만드는 것이 아니라, **"점진적 공개(Progressive Disclosure)를 통한 온디맨드 검증 지식 제공"**, **"Fresh Evidence 기반의 독립 Verifier 감사"**, **"구현 전 Before 기준선 확보"**의 3대 안전장치를 가벼운 규약(Thin Contract)으로 완성하는 마일스톤이다.
2. **다음 단계 (Step ②)**:
   - 본 조사 문서를 PR로 검토·머지한 후,
   - **ADR-0008: 검증 지식 구조 및 Verifier 감사 프로토콜(Before-After Baseline)**을 제정하여 M4의 구체적인 실행 규약을 확정한다.

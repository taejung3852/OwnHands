# M5-R3 Skill Lifecycle — #81

## 1. 목적과 배경

OwnHands는 작업을 검증 가능하게 정의하고 수행하도록 돕고, 근거를 사람이 이해해 최종 판단하게 하는 얇은 개발 하네스다.

- **#79 (M5-R1 Core 책임 매핑)**: 기존 206개 파일 및 25개 MCP 도구에 대한 `keep / compat / remove-later / historical-only` 경계를 확정하고, 무거운 실행통제 의존성을 분리하기로 결정했다.
- **#80 (M5-R2 Lifecycle 계약)**: `Work Issue → Verification Spec → Baseline → 수행·검사 → Review → Review Snapshot → Human Decision` 머신 계약(`devharness.lifecycle`) 및 저널 기반 SQLite 저장소(`LifecycleStore`), 상태 판정(`readiness.py`)을 구축했다.
- **#81 (M5-R3 Skill Lifecycle)**: 백엔드 머신 계약에 맞추어 AI 에이전트 스킬 계층을 전면 개편한다. 기존 4-tier harness(`context-validation`, `execution-control`, `harness-profiler`, `test-assurance`)의 무거운 연쇄 강제 호출을 걷어내고, **구체적인 개발 Work Item을 정의하거나 수행하는 lifecycle에서만 동작하는 얇은 Router(`using-ownhands`)와 5개 전문 스킬 체계**를 확립한다.

---

## 2. 4대 핵심 아키텍처 경계

### ① `work-map` vs `verification-spec`
- **`work-map`**: *"무엇을 하나의 작업 단위(Work Item)로 잡아야 하지?"*
  - 거대한 목표나 로드맵이 주어졌으나, 구현 가능한 단위가 아직 불명확할 때만 사용한다.
  - 목표를 달성하기 위해 필요한 선행 결정, 의존성, 작업 후보(Milestone, Epic, Work Item, Issue, Task, Decision)를 구조화한다.
  - GitHub Issue 생성이 스킬의 목적이 아니며, 이미 명확한 단일 Work Item이 주어진 경우에는 `work-map`을 건너뛰고 곧바로 `verification-spec`으로 진입한다.
- **`verification-spec`**: *"이 작업을 언제 완료라고 할 수 있지?"*
  - 단일 Work Item이 확정된 후, 코드 구현에 착수하기 전에 사용한다.
  - 요구사항을 합격 조건(Success), 기존 동작 유지(Preserve), 개선 조건(Improve), 실패 반례(Edge cases), 검증 방법(Evidence)으로 구체화하고 사람의 명시적 승인(`spec_approval`)을 받는다.

### ② `verification-spec` vs `review` 및 Observation Fallback
- **`verification-spec` (구현 전)**: "무엇을 증명해야 완료인가?"를 정의하고 사람 승인을 받는다.
- **`review` (구현 후 Orchestration)**: "그 조건들이 실제 구현 결과에서 증명되었는가?"를 확인한다.
  - 승인된 Spec을 읽어 관련 테스트/검사를 실행하고, After observation과 Evidence를 수집하며, 회귀와 영향 범위를 분석한다.
  - 판정 알고리즘 자체는 #82의 책임이며, `review` 스킬은 검증 기능을 언제 어떻게 호출하고 결과를 수집할지 안내하는 오케스트레이션 레이어다.
- **정식 Review 계약**: 반드시 `VerificationSpec + SpecApproval + 대상 CodeState`가 존재해야만 정식 `review` 레코드를 생성할 수 있다 (#80 계약).
- **Observation Fallback**: 승인된 Spec 없이 "검증해줘"를 요청받은 경우:
  - 권장 경로: `verification-spec`으로 라우팅하여 최소 Spec 작성 및 승인 유도.
  - 명시적 Fallback: 사용자가 Spec 작성을 명시적으로 거부하고 "단순 관찰만 해줘"라고 한 경우에만 `review`의 non-review fallback mode(`observation mode`)로 진입하여 제한적 Observation Report만 제공한다 (정식 Review 아님, ready 판정 없음, Claim 미평가, review 레코드 미생성).

### ③ SDD / TDD의 위치 (선택적 방법론)
- `sdd`, `tdd`라는 별도의 최상위 lifecycle 스킬을 추가하지 않는다.
- 두 방법론은 라이프사이클 전반에 걸쳐 선택적으로 적용되는 사고방식 및 실행 가이드로 내재화한다:
  - **SDD**: `work-map` 및 `verification-spec`의 사고방식과 표준 템플릿에 녹인다.
  - **TDD**: `verification-spec`에서 실패 반례(Red) 정의 ➔ `implementation`에서 Red-Green-Refactor ➔ `review`에서 해당 Evidence 및 회귀 결과 확인으로 연결한다.

### ④ 2단계 라우팅 검증 체계
- **Deterministic routing contract $\neq$ Deterministic LLM runtime behavior**
- 단위 테스트가 통과했다고 해서 "실제 LLM이 런타임에 항상 해당 스킬을 선택한다"고 과장하지 않는다.
  1. **Routing Contract Test**: 정의된 상태 전이 정책표가 모순 없이 완전하고 단일 스킬만 선택하는지 결정적으로 검증한다.
  2. **Agent Discovery Smoke/Eval**: 지원 에이전트 환경에서 대표 프롬프트를 넣었을 때 기대 스킬 discovery 및 Dormant 동작이 관찰되는지 확인한다.

---

## 3. 5개 전문 스킬 및 라우터 체계

```
using-ownhands (얇은 라우터)
       │
       ├─ work-map            ← 작업 단위가 불명확할 때만 구조화
       ├─ verification-spec   ← 구현 전 완료 조건 정의
       ├─ baseline            ← Before 상태 및 기준 관찰 기록 (Worktree 비강제)
       ├─ review              ← 사후 검증 orchestration (Spec 필수)
       └─ dashboard           ← 요청 시 사람용 표현 아티팩트 준비
```

### 1) `using-ownhands` (Root Thin Router)
- **역할**: 오직 다음 1개의 라이프사이클 스킬만 결정하는 얇은 라우터 (직접 검증/실행 안 함).
- **Frontmatter**:
```yaml
---
name: using-ownhands
description: "OwnHands lifecycle router. Determines the next single lifecycle skill (work-map, verification-spec, baseline, review, dashboard). STAY DORMANT during general conversation, research, brainstorming, and while code implementation is in-progress."
---
```

### 2) `work-map`
- **역할**: *"무엇을 하나의 작업 단위로 잡아야 하지?"* — 불명확한 목표 분해, 의존성 및 선행 결정 구조화.
- **Frontmatter**:
```yaml
---
name: work-map
description: "Use when a goal or oversized work item must be decomposed into concrete work items, dependencies, or unresolved decisions. STAY DORMANT when a concrete work item is already defined."
---
```

### 3) `verification-spec`
- **역할**: *"이 작업을 언제 완료라고 할 수 있지?"* — 작업의 합격 조건, 보존 조건, 개선 조건, 실패 반례를 명세화하고 사람 승인 획득.
- **Frontmatter**:
```yaml
---
name: verification-spec
description: "Use when drafting or updating verification specifications and acceptance criteria for a defined work item. STAY DORMANT when the current spec is already approved and fresh, or during code implementation."
---
```

### 4) `baseline`
- **역할**: *"바꾸기 전 상태는 무엇이지?"* — 코드 수정 직전 현재 환경 관찰 및 기록.
- **Worktree 정책**: Worktree 생성을 절대 강제하지 않는다. 현재 환경(branch, worktree, dirty state, commit, code fingerprint, Before observation)을 관찰·기록하는 것이 기본이며, 격리가 필요한 경우에만 선택적 안내한다.
- **Frontmatter**:
```yaml
---
name: baseline
description: "Use immediately before writing code to observe and capture pre-change code fingerprints, environment state, and Before observations. STAY DORMANT while code editing is in-progress or after baseline is already captured."
---
```

### 5) `review`
- **역할**: *"구현 결과가 실제 검수 조건을 만족했나?"* — 승인된 Spec 기준으로 사후 테스트 실행, Evidence 수집 및 오케스트레이션.
- **Frontmatter**:
```yaml
---
name: review
description: "Use after implementation completes to run verification tests, collect evidence, assess regressions, and compile the task review. Requires an approved spec for formal review. Without one, only handle an explicitly requested non-review observation fallback. STAY DORMANT while code editing is actively in-progress."
---
```

### 6) `dashboard`
- **역할**: *"사람이 이 결과를 어떻게 빠르게 이해하고 판단하지?"* — 저장된 Review 결과를 사람이 이해하기 쉬운 presentation artifact로 준비.
- **운영 원칙**:
  - Review 완료 시 자동 실행되지 않으며, 사용자가 시각화/요약을 요청할 때 온디맨드로 아티팩트를 준비·저장한다.
  - UI 조회나 새로고침은 이미 저장된 정적 아티팩트만 읽으며, 런타임 LLM이나 스킬 호출을 발생시키지 않는다.
  - 동일한 Spec/Review/CodeState fingerprint면 기존 설명과 다이어그램을 재사용한다 (캐싱).
- **Frontmatter**:
```yaml
---
name: dashboard
description: "Use when requested to prepare human-digestible presentation artifacts and visual summaries for a stored review. STAY DORMANT during active execution, or when review presentation is already current."
---
```

### 7) Legacy 4개 스킬 Discovery 경계 격리
`skills/{context-validation, execution-control, harness-profiler, test-assurance}/SKILL.md`
- 코드는 #83 분리 전까지 유지하되, Frontmatter description을 `[Legacy / Compat Only]`로 축소하여 신규 워크플로우에서 LLM이 직접 선택하는 discovery 충돌을 원천 차단한다.

---

## 4. 결정적 라우팅 상태 전이 테이블

| 입력 상황 및 문맥 (Context) | 라우팅 계약 결과 (Next Skill) | 비고 |
|---|---|---|
| 일반 잡담, 일상 대화 | **None (Dormant)** | 개입 금지 |
| 개념 질문, 언어 문법, 단순 설명 요청 | **None (Dormant)** | 개입 금지 |
| 일반 리서치, 코드베이스 단순 탐색 | **None (Dormant)** | 개입 금지 |
| 아이디어 탐색 및 브레인스토밍만 진행 중 | **None (Dormant)** | 개발 착수 전까지 침묵 |
| 코드 구현 및 단위 테스트 작성 진행 중 (In-progress) | **None (Dormant)** | 개발 흐름 방해 금지 |
| 큰 목표 주어짐 / 작업 단위 및 의존성 불명확 | **`work-map`** | 작업 단위 구조화 |
| 명확한 단일 Work Item 존재 & Spec 없음 | **`verification-spec`** | 완료 조건 구체화 |
| Spec 초안 작성됨 (사람 미승인 상태) | **`verification-spec`** | 승인 획득 대기 |
| **[구현 전]** Spec 승인 완료 & 유효 Baseline 없음 | **`baseline`** | Before 상태 관찰 (Worktree 강제 X) |
| 코드 구현 완료 / 검증 및 리뷰 요청 | **`review`** | After 관찰 및 Evidence 수집 |
| **[구현 완료 후]** 유효한 Before 관찰 없음 | **`review`** | 과거 Baseline 허위 생성 금지, `missing_before / gap` 기록 |
| Review 존재 + presentation 없음/stale + 시각화 요청 | **`dashboard`** | 온디맨드 표현 아티팩트 준비 |
| Review 존재 + presentation current + Dashboard 조회 | **None (Dormant)** | 캐시 Hit: 저장된 정적 아티팩트 읽기 (스킬 미호출) |
| **[Freshness]** 요구사항 / Issue / Criteria 의미 변경 | **`verification-spec`** | Spec 재검토 및 재승인 안내 |
| **[Freshness]** 코드 변경 발생 (After CodeState 불일치) | **`review`** | 기존 Review Stale ➔ 재검증 안내 |
| **[Freshness]** [구현 전] 환경 / 테스트 의미 변경 | **`baseline`** | Before 상태 및 비교 가능성 재수집 |
| **[Freshness]** [구현 후] 환경 / 테스트 의미 변경 | **`review`** | 기존 비교를 incomparable/stale로 처리 및 재검증 |

---

## 5. 예외 및 비정상 경로 처리 방안

1. **Spec 없는 상태에서 "검증해줘" 요청 시**:
   - 승인된 Spec 없이 정식 Review 생성 불가 (#80 계약 준수).
   - 기본 라우팅: `verification-spec`으로 연결하여 최소 Spec 작성 ➔ 승인 ➔ Review 진행.
   - 예외: 사용자가 Spec 작성을 거부하고 "단순 관찰만 해줘" 명시 시 `review`의 `observation mode`로 제한적 Observation Report만 제공.
2. **엄격한 Baseline 재사용 조건 (Idempotency)**:
   - 다음 4대 조건이 모두 일치할 때만 기존 Baseline을 재사용:
     1. 동일한 current Spec 및 SpecApproval
     2. 동일한 CodeState (fingerprint)
     3. 비교에 영향을 주는 동일한 Environment (환경 fingerprint)
     4. 동일한 Test meaning (실행 명령 및 파라미터)
3. **수정된 작업 트리(Modified tree) 및 사후 Baseline 허위 생성 금지 (시간 거스르기 금지)**:
   - 구현이 이미 완료된 후에 시간을 거슬러 Baseline 단계로 돌아가 허위 Before를 만들어내지 않는다.
   - Before 관찰이 누락된 채 구현된 경우, `review` 단계에서 `missing_before / gap`으로 솔직하게 기록한다.
4. **Current 승인 Spec 재질문 방지**:
   - 이미 활성 승인된 Spec이 존재하면 스펙 작성을 재질문하지 않고 즉시 Baseline 또는 구현 단계로 직행한다.

# Spec: Thin build Skill 연결

- 기반 Intent: [`intent.md`](intent.md)
- **작성 주체**: Codex 분석 초안 (사람 검토 및 승인 필요)
- **일자**: 2026-09-20
- **상태**: Approved — 사용자 확인 (2026-09-20)
- **관련 Issue**: [#140](https://github.com/taejung3852/OwnHands/issues/140)

---

## 1. 기술적 요구사항 (Requirements)

### 1.1 기능 요구사항

- **`REQ-01` — Build 단일 진입점**
  - `.agents/skills/build/SKILL.md`를 추가한다.
  - Skill은 승인된 `spec.md`와 `plan.md`를 기반으로 구현하는 Build 작업 또는 사용자의 명시적 `$build` 호출에서 사용한다.
  - Skill의 최상위 Goal은 Intent에 확정된 **설계·실행계획과 구현·검증 루프의 연결**이며, 범용 구현 프레임워크를 만드는 것이 아니다.

- **`REQ-02` — 실행 전 계약 확인**
  - 구현 전에 대상 기능의 `spec.md`와 `plan.md`를 찾고 승인 상태 및 상호 연결을 확인한다.
  - 둘 중 하나가 없거나 승인되지 않았다면 코드를 수정하지 않고 해당 Checkpoint로 돌아간다.
  - `plan.md`의 Target Files를 변경 반경 경계로 사용하며 새 포맷을 만들지 않는다.

- **`REQ-03` — Task 단위 순차 실행**
  - `plan.md`에서 다음 미완료 Task 하나를 선택한다.
  - 선택한 Task의 대상 파일과 연결된 AC·검증 전략을 확인한 뒤 구현한다.
  - 적용 가능한 Fresh Evidence를 확보하고 `plan.md`에 기록한 후에만 다음 Task로 이동한다.

- **`REQ-04` — 작업 성격에 따른 실행 방식 선택**
  - 실행 가능한 로직/API처럼 TDD가 적합한 Task에서만 `references/tdd-loop.md`를 로드하고 `Red → Green → Refactor`를 적용한다.
  - 문서·설정·정적 구조처럼 TDD가 부적합한 Task에는 기존 계획의 정적 검사, 빌드, 렌더링 관측 등 적합한 전략을 사용한다.
  - TDD 적용 여부는 `plan.md`의 Verification Strategy와 실제 Task 성격에 근거하며 모든 Task에 일괄 강제하지 않는다.

- **`REQ-05` — 직접 수행 기본값과 조건부 위임**
  - 기본 실행 주체는 현재 Builder다.
  - 위임을 검토할 때만 `references/subagent-routing.md`를 로드한다.
  - 외부 조사에는 `researcher`, 독립적으로 분리 가능한 큰 Task에는 Codex native `worker`, 최종 독립 검증에는 기존 `verifier`를 후보로 삼는다.
  - Task마다 fresh subagent를 강제로 생성하지 않으며, 위임할 수 없거나 이점이 없으면 Builder가 직접 수행한다.

- **`REQ-06` — 충돌 시 기준선 복귀**
  - 구현 중 `spec.md` 충돌이나 새로운 제약을 발견하면 기대값, 테스트 또는 AC를 자의적으로 바꾸지 않는다.
  - 구현을 멈추고 `spec.md` 수정 및 사람 승인 후 `plan.md`를 재정렬하는 기존 Versioned Baseline 흐름으로 돌아간다.

- **`REQ-07` — 완료 전 기존 verify 연결**
  - 모든 Task가 끝나면 새 검증 로직을 만들지 않고 기존 `verify` Skill을 호출한다.
  - `verify`가 회귀 방어, applicable Fresh Evidence, 독립 `verifier`의 `PASS / FAIL / UNOBSERVED` 판정을 담당한다.
  - 필요한 증거가 없거나 검증이 실패하면 완료를 주장하지 않는다.

- **`REQ-08` — 저장소 진입 규칙 연결**
  - root `AGENTS.md`에 다음 의미의 짧은 연결 문장 한 줄만 추가한다.
    - `승인된 spec.md / plan.md를 기반으로 구현하는 Build 작업은 build Skill을 사용한다.`
  - 세부 실행 규칙은 `AGENTS.md`에 복제하지 않고 Skill과 Reference에 둔다.

### 1.2 비기능 요구사항

- **`NFR-01` — Thin Harness**: Runner, Hook, Worktree 자동화, 상태 저장소, Agent orchestration framework를 추가하지 않는다.
- **`NFR-02` — Progressive Disclosure**: 기본 흐름은 `SKILL.md`에 짧게 두고, TDD와 위임 세부 규칙은 각각 필요한 경우에만 Reference에서 읽는다.
- **`NFR-03` — Source of Truth 재사용**: `ADR-0007`, `ADR-0008`, `docs/specs/README.md`, 기존 `verify` Skill의 책임을 복제하거나 재정의하지 않는다.
- **`NFR-04` — 정직한 상태 표현**: 실행하지 않은 검증을 통과로 취급하지 않고 `FAIL`과 `UNOBSERVED`를 구분한다.
- **`NFR-05` — 플랫폼 결정 구분**: 위 요구사항은 OwnHands의 설계 결정이며 Codex 플랫폼의 공식 정책으로 표현하지 않는다.

### 1.3 Intent 추적성

| 요구사항 | Intent 근거 |
|---|---|
| `REQ-01`, `REQ-03` | 최상위 Goal, Build 단일 진입점 |
| `REQ-02`, `REQ-06` | 승인된 계약 재사용, 명시적 경계 |
| `REQ-04` | 조건부 TDD |
| `REQ-05` | 직접 수행 기본값, 조건부 Subagent |
| `REQ-07` | 기존 `verify` 연결, Fresh Evidence |
| `REQ-08` | Build 작업의 짧은 저장소 진입 규칙 |
| `NFR-01`~`NFR-03` | Thin Harness, 플랫폼 우선, 비목표 전량 |

## 2. 시스템 아키텍처 및 인터페이스 (Architecture & Interfaces)

### 2.1 대상 파일 및 책임

- `[NEW]` `.agents/skills/build/SKILL.md`
  - Build 전제조건 확인, Task 선택, 실행 방식 선택, 구현·증거 기록, `verify` 연결의 순서만 정의한다.
- `[NEW]` `.agents/skills/build/references/tdd-loop.md`
  - TDD가 적합하다고 이미 판단된 Task에서 사용할 최소 `Red → Green → Refactor` 계약을 정의한다.
- `[NEW]` `.agents/skills/build/references/subagent-routing.md`
  - 직접 수행을 기본값으로 두고 `researcher`·`worker`·`verifier`를 선택적으로 사용하는 기준을 정의한다.
- `[MODIFY]` `AGENTS.md`
  - 승인된 `spec.md` / `plan.md` 기반 Build 작업과 `build` Skill을 연결하는 한 문장만 추가한다.
- `[MODIFY]` `.gitignore`
  - 전역 `build/` packaging 규칙에 묻히는 `.agents/skills/build/`만 정확히 다시 추적하도록 예외를 추가한다.
- `[NEW]` `docs/specs/build-feedback-loop/plan.md`
  - Spec 승인 후 기존 템플릿을 사용해 실제 구현 순서와 검증 증거를 기록한다.

이번 구현에서는 `scripts/run-evals.js`, `docs/evals/task-set.json`, `.codex/agents/verifier.toml`을 수정하지 않는다.

### 2.2 Skill frontmatter 인터페이스

```yaml
---
name: build
description: Executes approved spec.md and plan.md one task at a time, gathers fresh evidence, and hands completion to verify. Use when implementing from approved OwnHands specs/plans or explicitly invoked as $build.
---
```

별도의 `agents/openai.yaml`을 만들지 않는다. 승인된 Build 문맥에서는 root `AGENTS.md` 연결 문장과 Skill description으로 라우팅한다.

### 2.3 Build 제어 흐름

```text
승인된 spec.md / plan.md 확인
        ↓ 없거나 미승인
   해당 Checkpoint로 복귀하고 수정 중단
        ↓ 유효
plan.md에서 다음 미완료 Task 하나 선택
        ↓
Task 성격과 Verification Strategy 확인
        ├─ TDD 적합 → tdd-loop.md 온디맨드 로드
        ├─ 위임 이점 있음 → subagent-routing.md 온디맨드 로드
        └─ 그 외 → Builder 직접 수행
        ↓
구현 → 적용 가능한 Fresh Evidence 확보 → plan.md 기록
        ↓
남은 Task 있음 → 다음 Task
        ↓ 없음
기존 verify Skill 호출
        ↓
PASS만 완료 / FAIL·UNOBSERVED는 그대로 보고
```

### 2.4 Reference 계약

#### `tdd-loop.md`

- 진입 조건: Task가 실행 가능한 로직/API이고 `plan.md`의 전략이 TDD일 때.
- `Red`: 기대 동작을 표현하는 최소 실패 테스트를 작성하고 의도한 이유로 실패하는지 관측한다.
- `Green`: 테스트를 통과시키는 최소 구현만 추가하고 성공 출력을 관측한다.
- `Refactor`: 중복이나 명백한 구조 문제를 정리할 가치가 있을 때만 수행하고 테스트를 다시 실행한다.
- 기존 테스트를 실패 은폐 목적으로 완화·삭제·skip하지 않는다.

#### `subagent-routing.md`

- 기본값: Builder 직접 수행.
- `researcher`: 구현과 분리 가능한 외부 자료 조사가 필요할 때만.
- `worker`: 파일 책임과 완료 조건을 분리할 수 있는 충분히 큰 독립 Task일 때만.
- `verifier`: 구현 완료 후 기존 `verify` 흐름이 독립 감사에 사용할 때.
- 단순 Task, 강하게 결합된 Task, 위임 오버헤드가 더 큰 Task에는 위임하지 않는다.

## 3. 엣지 케이스 및 예외 처리 (Edge Cases)

| 시나리오 / 경계 조건 | 기대 동작 |
|---|---|
| `spec.md` 또는 `plan.md`가 없음 | 구현하지 않고 누락된 아티팩트를 명시한다. |
| 문서가 Draft이거나 승인 여부가 불명확함 | 사람 확인을 요청하고 구현을 중단한다. |
| `plan.md`에 미완료 Task가 없음 | 새 Task를 자의적으로 만들지 않고 `verify` 단계로 이동한다. |
| 선택한 Task가 TDD에 부적합함 | TDD를 강제하지 않고 계획된 정적·수동·렌더링 검증을 사용한다. |
| 적절한 Subagent가 없거나 위임 이점이 없음 | 현재 Builder가 직접 수행하며 작업을 막지 않는다. |
| 구현 중 Spec과 충돌하거나 새 제약 발견 | 구현과 기준 변경을 중단하고 `spec.md` 승인 흐름으로 복귀한다. |
| Target Files 밖 변경이 필요함 | 무단 수정하지 않고 `plan.md` 변경 반경 갱신과 필요한 승인을 먼저 처리한다. |
| 테스트 또는 검증 실패 | 실패를 숨기지 않고 수정 루프로 돌아가며 완료를 주장하지 않는다. |
| 검증을 실행할 수 없음 | `UNOBSERVED`로 기록하고 통과로 간주하지 않는다. |
| 기존 테스트가 없음 | `verify`의 기존 대체 방어선을 재사용하고 새 규칙을 만들지 않는다. |
| 작업 트리에 사용자의 기존 변경이 있음 | 관련 없는 변경을 보존하고 Target Files와 겹칠 때만 충돌을 보고한다. |

## 4. 수용성 기준 및 검증 계획 (Acceptance Criteria)

### 4.1 수용성 기준

- [ ] **`AC-01` — Skill 진입점**: `.agents/skills/build/SKILL.md`가 유효한 `name: build` frontmatter와 승인된 `spec.md` / `plan.md` 확인 절차를 포함한다.
- [ ] **`AC-02` — Task·Evidence 루프**: Skill이 `Task 하나 선택 → 구현 → Fresh Evidence 기록 → 다음 Task` 흐름을 명시하며 기존 `plan.md` 포맷을 재사용한다.
- [ ] **`AC-03` — 조건부 TDD**: `tdd-loop.md`가 존재하고, TDD가 적합한 Task에서만 로드·적용되며 `Red → Green → Refactor` 최소 계약과 테스트 침식 금지를 포함한다.
- [ ] **`AC-04` — 조건부 Subagent**: `subagent-routing.md`가 존재하고, Builder 직접 수행을 기본값으로 하며 `researcher`·`worker`·`verifier`의 제한된 후보 조건을 명시한다.
- [ ] **`AC-05` — 기존 verify 연결**: 모든 Task 완료 후 기존 `verify`를 사용하고 `PASS / FAIL / UNOBSERVED` 및 Fresh Evidence 원칙을 유지한다.
- [ ] **`AC-06` — 저장소 라우팅**: root `AGENTS.md`에 승인된 `spec.md` / `plan.md` 기반 Build 작업을 `build` Skill로 연결하는 짧은 문장만 추가된다.
- [ ] **`AC-07` — Thin Harness 경계**: Runner, Hook, Worktree 자동화, 새 Verifier, 새 `plan.md` 포맷, 범용 Agent orchestration framework가 추가되지 않는다.
- [ ] **`AC-08` — 핀포인트 Runtime 관측**: 단일 read-only `$build` dry-run에서 Codex가 `build` Skill을 실제로 읽고 대상 `spec.md` / `plan.md`에 따른 다음 행동을 설명하며 저장소를 수정하지 않는다.
- [ ] **`AC-09` — 기존 정적 회귀**: 현재 M5 Static Preflight가 회귀 없이 통과한다.

### 4.2 검증 전략 매핑

| AC ID | 검증 전략 | Fresh Evidence |
|---|---|---|
| `AC-01`~`AC-07` | 파일 존재·필수 문구·금지 범위 정적 점검, Git diff 검토 | 정적 검사 출력과 최종 diff |
| `AC-08` | `codex exec --json --sandbox read-only` 단일 명시 호출 | Skill 읽기 이벤트, 응답 요약, 실행 전후 Git 상태 동일 |
| `AC-09` | 기존 정적 Eval 실행 | `node scripts/run-evals.js --static-only`의 exit code 0 및 regression 0 |

### 4.3 검증 명령 후보

```bash
# 문서·Skill 정적 건전성
git diff --check

# 기존 정적 회귀 방어선
node scripts/run-evals.js --static-only

# 구현 후 단일 Runtime dry-run — 실제 실행 시 프롬프트와 전후 Git 상태를 plan.md에 기록
codex exec --json --sandbox read-only \
  '$build를 사용해 docs/specs/build-feedback-loop/spec.md와 plan.md를 읽고, 파일을 수정하지 않은 채 현재 다음 행동과 선택할 실행 방식만 말해줘.'
```

전체 Runtime Eval Suite는 이 기능의 수용 기준에 포함하지 않는다.

# Spec: Review Loop · Human Gate · CI Governance

- **기반 Intent**: [`intent.md`](intent.md)
- **작성 주체**: Codex 분석 (사람 검토 및 승인 필요)
- **일자**: 2026-09-20
- **상태**: Approved — 사용자 확인 (2026-09-20)
- **관련 Issue**: [#146](https://github.com/taejung3852/OwnHands/issues/146)

---

## 1. 기술적 요구사항 (Requirements)

### 1.1 Review Loop

- `REQ-01` — 필수 AC가 `verify → verifier`에서 모두 `PASS`가 된 뒤, `Push + PR` Human Gate를 제시하기 전에 기존 read-only `reviewer`를 1회 호출한다.
- `REQ-02` — 기본 Reviewer는 `.codex/agents/reviewer.toml`이며 새 Reviewer Agent, 네이티브 `/review`, GitHub `@codex review`를 기본 흐름에 추가하지 않는다.
- `REQ-03` — Reviewer에는 다음 최소 Review Packet만 전달한다.
  1. 변경 목표와 승인된 `spec.md`·`plan.md`
  2. base/head 또는 staged·unstaged·untracked를 포함한 정확한 diff scope
  3. 적용 가능한 Fresh Evidence, 관련 Before/M5 baseline과 변화, `UNOBSERVED`, known constraints
- `REQ-04` — 전체 대화 기록과 변경에 무관한 과거 로그는 Review Packet에서 제외한다.

### 1.2 Finding Adjudication

- `REQ-05` — Main Agent는 Reviewer Finding을 저장소 Fact, 승인된 Spec, Evidence에 대조한 뒤 아래 상태 중 하나로 판정한다.

| 상태 | 의미 | 후속 동작 |
|---|---|---|
| `accepted` | Finding이 현재 변경의 실제 결함·회귀·규칙 위반으로 확인됨 | 최소 수정 후 적용 가능한 Fresh Evidence 재확보 |
| `rejected-with-evidence` | 코드·테스트·Spec 근거로 Finding이 적용되지 않음을 입증함 | 근거 기록 후 수정하지 않음 |
| `needs-human` | 승인된 Spec·정책과 충돌하거나 위험 수용 결정이 필요함 | 구현을 멈추고 사용자에게 결정 요청 |

- 각 Finding의 상세 판단은 해당 작업의 `plan.md`에 있는 `Review Results` 섹션을 Source of Truth로 기록한다.

```markdown
### Finding `F-01`
- **Status**: `rejected-with-evidence`
- **Reviewer claim**: `foo()`가 `null`을 반환할 수 있음
- **Reason**: 승인된 contract와 회귀 테스트가 non-null 동작을 보장함
- **Evidence**:
  - `spec.md` `REQ-04`의 non-null contract
  - `foo.test.ts` null-path test PASS
```

- `rejected-with-evidence`에는 Reviewer claim, 기각 이유, 코드·Spec·Test 중 하나 이상의 구체적 Evidence가 모두 있어야 한다. 개수만 기록한 항목은 유효한 기각이 아니다.
- `REQ-06` — Reviewer의 의견을 자동 수정 명령이나 최종 Decision으로 취급하지 않는다.
- `REQ-07` — `accepted` Finding의 대상 영역을 수정했거나 위험 경계가 바뀐 경우에만 해당 범위를 targeted re-review한다. 문구 수정이나 무관한 변경에는 반복 리뷰를 강제하지 않는다.

### 1.3 Review Evidence와 Local Gate

- `REQ-08` — Review 완료 시 현재 diff scope에 결합된 machine-readable Review Evidence를 저장한다. JSON은 Finding 상세 DB가 아니라 fingerprint·verdict·최종 count 요약이며, 상세 reasoning은 `plan.md`에 남긴다. Evidence는 최소한 다음 정보를 포함한다.

```json
{
  "version": 1,
  "base_ref": "origin/main",
  "base_sha": "<resolved commit>",
  "head_sha": "<current HEAD>",
  "diff_fingerprint": "<tracked and untracked change fingerprint>",
  "reviewer": "reviewer",
  "verdict": "PASS",
  "finding_counts": {
    "accepted": 0,
    "rejected-with-evidence": 0,
    "needs-human": 0
  },
  "recorded_at": "<ISO-8601>"
}
```

- `REQ-09` — Review Evidence는 Git tracked artifact가 아니라 현재 checkout의 로컬 상태로 보관한다. Evidence 기록 자체가 diff를 바꾸거나 PR에 포함돼서는 안 된다.
- `REQ-10` — 현재 diff fingerprint가 Evidence와 다르거나 `accepted`·`needs-human` Finding이 미해결이면 Evidence를 유효한 PASS로 취급하지 않는다. `record`는 `plan.md`의 `Review Results`를 검증해 count를 계산해야 하며, Reason이나 Evidence가 비어 있는 `rejected-with-evidence`가 하나라도 있으면 PASS 기록을 거부한다.
- `REQ-11` — repo-local `PreToolUse` Hook은 shell command가 `git push`, `gh pr create`, `gh pr merge`에 해당할 때만 Review Evidence를 확인한다. 그 외 명령과 일반 응답에는 개입하지 않는다.
- `REQ-12` — Hook은 누락·stale·미해결 Evidence를 발견하면 해당 외부 명령을 막고 짧은 이유를 반환한다. Hook 오류나 미지원 tool path를 완전한 보안 경계로 과장하지 않는다.
- `REQ-13` — Hook은 파일·네트워크를 변경하거나 Secret을 읽지 않는 read-only 검사여야 한다. 실제 Reviewer 호출은 Hook이 아니라 현재 Codex 앱 세션의 Main Agent가 수행한다.

### 1.4 Human Gate

- `REQ-14` — 다음 외부 상태 변경은 서로 독립된 Human Gate다.
  1. `Push + PR`
  2. `Merge`
  3. `Deploy`가 존재하는 작업의 Deploy
- `REQ-15` — 이전 단계 승인은 다음 단계 승인으로 간주하지 않는다. PR 생성 승인은 Merge나 Deploy 권한을 포함하지 않는다.
- `REQ-16` — 사용자의 명시적 승인 없이 자동 Push, PR, Merge, Deploy를 실행하지 않는다.
- `REQ-17` — Branch·Worktree Cleanup은 Merge와 별개이며 명시적 승인 없이 자동 실행하지 않는다.

### 1.5 CI와 Eval Governance

- `REQ-18` — OwnHands 자체와 OwnHands 사용 프로젝트의 검사 계약을 분리한다.

| 대상 | 기본 검사 | Agent/Runtime 검사 |
|---|---|---|
| OwnHands 저장소 | 적용 가능한 native deterministic checks + M5 `--static-only` | Agent/Eval 자산 변경과 직접 관련된 `--task`만 로컬 Codex 세션에서 선택 실행 |
| OwnHands 사용 프로젝트 | 해당 프로젝트의 test·lint·type·build와 승인된 Spec의 검증 전략 | 프로젝트가 별도로 정의한 Requirement가 있을 때만 실행; OwnHands M5 Task Set 강제 금지 |

- `REQ-19` — GitHub CI의 기본 required check는 deterministic check로 제한한다. 전체 Runtime Eval Suite와 Codex review를 매 PR 기본 검사로 두지 않는다.
- `REQ-20` — Codex Action, OpenAI API key, 별도 API 과금 기반 Runtime CI를 도입하지 않는다. Reviewer와 선택 Runtime Eval은 로그인된 Codex 앱/로컬 CLI 인증 범위에서 실행한다.
- `REQ-21` — required check 또는 필수 AC의 `FAIL`은 수정 전까지 Merge를 차단한다.
- `REQ-22` — `UNOBSERVED`는 자동 통과가 아니다. 예외 Merge는 누락 Evidence, 확보 불가 사유, 수용 위험을 제시한 뒤 사용자의 명시적 override를 받아야 한다.
- `REQ-23` — Main Agent는 사용자 응답이 없거나 애매하면 `UNOBSERVED` override로 해석하지 않는다.

### 1.6 Permission Boundary와 보류 항목

- `REQ-24` — 역할별 권한 상한은 다음과 같다.

| 역할 | 권한 상한 |
|---|---|
| Reviewer / Verifier | read-only, 판정과 Evidence 감사만 수행 |
| Review Gate Hook | read-only 로컬 검사, network·Secret·repo mutation 금지 |
| Builder | 승인된 `plan.md` Target Files 안의 workspace write |
| Push/PR/Merge/Deploy 수행자 | 해당 Human Gate에서 승인된 외부 상태 변경만 수행 |

- `REQ-25` — 실제 조직 Requirement가 생기기 전에는 Managed Policy와 가상 회사 정책을 구현하지 않는다.
- `REQ-26` — 새 Agent, Governance framework, worktree/branch cleanup 자동화, 새 Eval Task, M5 runner 대형 확장을 도입하지 않는다.

## 2. 시스템 아키텍처 및 인터페이스 (Architecture & Interfaces)

### 2.1 책임 흐름

```text
build Task 완료
  ↓
verify + verifier
  ├─ FAIL / required UNOBSERVED → 구현 루프 또는 Human 판단
  └─ required AC PASS
        ↓
existing read-only reviewer + Review Packet
  ↓
Finding adjudication을 plan.md Review Results에 기록
  ├─ accepted → 최소 수정 → Fresh Evidence
  ├─ rejected-with-evidence → Reason + Evidence 기록
  └─ needs-human → 사용자 결정과 해결 기록
        ↓
최종 diff 확정 → 필요한 범위만 targeted re-review
        ↓
Review Evidence 기록 (current diff fingerprint)
        ↓
Human Gate: Push + PR / Keep
        ↓
deterministic GitHub CI
        ↓
Human Gate: Merge
        ↓
필요한 경우 Human Gate: Deploy
        ↓
별도 선택: Cleanup / Keep
```

### 2.2 후보 대상 파일 및 컴포넌트

구체 Target Files는 Checkpoint 2 승인 후 `plan.md`에서 최종 고정한다. 현재 설계가 요구하는 최소 후보는 다음과 같다.

| 구분 | 후보 경로 | 책임 |
|---|---|---|
| MODIFY | `.agents/skills/build/SKILL.md` | `verify` 이후 Reviewer와 Human Gate 연결 |
| NEW | `.agents/skills/build/references/review-governance.md` | Review Packet, Finding, re-review, Human Gate 상세 |
| NEW | `.codex/hooks.json` | 외부 Git command에만 좁게 적용되는 `PreToolUse` 등록 |
| NEW | `scripts/review-gate.js` | Review Evidence 기록·현재 diff 비교·Hook 판정 |
| MODIFY | `docs/specs/README.md` | 기존 Plan 규격과 Review Evidence 연결 안내 |
| MODIFY | `docs/decisions.md` | 사용자 승인된 M6 Governance 결정 동기화 |
| NEW | `docs/adr/0010-review-human-ci-governance.md` | M6 계약과 트레이드오프 기록 후보 |

`.codex/agents/reviewer.toml`, `.codex/agents/verifier.toml`, `scripts/run-evals.js`, `docs/evals/task-set.json`은 재사용 대상이며 기본 수정 후보가 아니다.

### 2.3 `scripts/review-gate.js` 인터페이스 후보

외부 dependency 없이 Node.js 표준 라이브러리와 Git CLI만 사용한다.

```text
node scripts/review-gate.js record \
  --base origin/main \
  --plan docs/specs/<feature>/plan.md \
  --verdict PASS
node scripts/review-gate.js check-hook
node scripts/review-gate.js clear
```

- `record`: `plan.md`의 구조화된 `Review Results`를 검증하고 최종 count를 계산한 뒤, 현재 review scope의 fingerprint와 요약을 Git 내부 로컬 상태에 기록한다.
- `check-hook`: Hook 입력의 command가 대상 외부 Git command인지 확인하고, 대상일 때만 current fingerprint와 Evidence를 비교한다.
- `clear`: 사용자가 명시적으로 Evidence 폐기를 요청하거나 작업 전환 시 로컬 Evidence를 제거한다.
- 실제 파일 위치는 worktree별 Git 경로를 사용하여 다른 checkout의 Evidence와 섞이지 않아야 한다.

### 2.4 Hook 판정 계약

```text
PreToolUse(Bash/exec_command)
  ↓
대상 command인가?
  ├─ 아니오 → 즉시 허용
  └─ 예: git push / gh pr create / gh pr merge
        ↓
Evidence 존재 + PASS + fingerprint 일치 + 미해결 finding 0?
  ├─ 예 → Hook 통과 (Human Gate는 별도 계약)
  └─ 아니오 → command 차단 + 이유 반환
```

Hook은 Review Evidence만 확인한다. 대화 transcript는 안정적인 Hook API가 아니므로 사용자 승인 여부를 transcript parsing으로 추론하지 않는다. Human Gate 준수는 Main Agent의 실행 계약이며 Hook이 대체하지 않는다.

## 3. 엣지 케이스 및 예외 처리 (Edge Cases)

| 시나리오 / 경계 조건 | 기대 동작 |
|---|---|
| 필수 AC가 `FAIL` | Reviewer 단계로 이동하지 않고 구현 루프로 복귀한다. |
| 필수 AC가 `UNOBSERVED` | 자동 진행하지 않는다. Evidence를 확보하거나 사용자에게 override를 요청한다. |
| Reviewer가 Finding을 반환하지 않음 | PASS Evidence를 현재 diff에 기록할 수 있다. |
| `accepted` Finding 수정 후 diff 변경 | 기존 Review Evidence를 stale로 취급하고 대상 범위를 재검토한다. |
| `rejected-with-evidence`만 존재 | 모든 항목의 Reviewer claim·Reason·Evidence가 `plan.md`에 있으면 PASS Evidence 기록을 허용한다. 하나라도 비어 있으면 거부한다. |
| `needs-human`이 미해결 | Review Evidence를 PASS로 기록하지 않고 외부 Git 명령을 차단한다. |
| Review 후 문서·코드 한 글자라도 변경 | fingerprint 불일치로 stale 처리한다. 변경이 Finding과 무관하면 Main Agent가 최소 targeted review 필요성을 판단해 새 Evidence를 기록한다. |
| 일반 질문이나 파일 읽기 | Hook 대상 command가 아니므로 추가 처리 없이 통과한다. |
| 복합 shell command 안에 외부 Git 명령 포함 | command token을 보수적으로 판정하여 Review Gate 대상에 포함한다. |
| Hook 파일이 새로 변경됨 | Codex의 Hook trust review를 거치기 전에는 실행됐다고 가정하지 않는다. |
| Hook 오류·미지원 tool path | 완전한 강제 성공으로 주장하지 않고 `UNOBSERVED`로 보고한다. Main Agent의 Human Gate 계약은 계속 적용한다. |
| 원격 PR head가 로컬 Evidence 이후 변경됨 | 로컬 Hook만으로 안전을 증명하지 않는다. Merge 전 PR head와 로컬 reviewed head를 확인하며 불일치 시 재검토한다. |
| GitHub CI 실패 | Merge를 차단하고 실패 원인을 해결한 뒤 해당 deterministic check를 재실행한다. |
| CI 환경에서 Runtime Eval 요구 | Codex Action을 자동 추가하지 않는다. 관련 Eval을 로컬에서 관측하거나 `UNOBSERVED`로 사용자 판단을 요청한다. |
| 사용 프로젝트에 OwnHands M5 Task Set이 없음 | 정상이다. 프로젝트 native checks만 적용한다. |
| 사용자가 Cleanup을 승인하지 않음 | branch/worktree를 그대로 보존한다. |

## 4. 수용성 기준 및 검증 계획 (Acceptance Criteria)

### 4.1 수용성 기준

- [ ] `AC-01` — `verify/verifier → reviewer → Human Gate` 순서와 각 역할의 책임이 단일 계약으로 정의된다.
- [ ] `AC-02` — Review Packet이 Spec/Plan, diff scope, Fresh Evidence·관련 baseline, known constraints를 포함하고 전체 대화는 제외한다.
- [ ] `AC-03` — Finding이 `accepted / rejected-with-evidence / needs-human`으로 판정되고 상세 판단이 `plan.md`에 보존되며 targeted re-review 조건이 정의된다.
- [ ] `AC-04` — Review Evidence가 현재 diff fingerprint에 결합되고 변경 후 stale 처리된다.
- [ ] `AC-05` — Hook은 일반 응답이 아닌 외부 Git command 직전에만 Review Evidence를 검사한다.
- [ ] `AC-06` — `Push + PR`, `Merge`, `Deploy`, Cleanup의 승인 경계가 분리된다.
- [ ] `AC-07` — OwnHands 자체 검사와 사용 프로젝트 검사가 분리되고 전체 Runtime Eval이 기본 required check에서 제외된다.
- [ ] `AC-08` — `FAIL`은 Merge를 차단하고 `UNOBSERVED` override는 사용자에게 반드시 묻는다.
- [ ] `AC-09` — Reviewer·Verifier·Hook·Builder·외부 상태 변경의 권한 상한이 최소권한으로 정의된다.
- [ ] `AC-10` — Codex Action/API 과금, Managed Policy, 새 Agent, worktree 자동화 등 Non-goal이 구현 범위에 포함되지 않는다.
- [ ] `AC-11` — Hook 장애와 원격 PR head 변경처럼 로컬 Gate가 완전한 보안 경계가 아닌 경우의 처리 방식이 정의된다.
- [ ] `AC-12` — Checkpoint 2 승인 후 기존 OwnHands 형식의 `plan.md`로 구현 Task와 최소 검증 전략을 작성할 수 있다.

### 4.2 Step ② 정적 검증 계획

- `git diff --check`
- Intent의 Goal·Non-goal·Constraint와 `REQ-01`~`REQ-26` 추적 대조
- `REQ-xx`와 `AC-01`~`AC-12`의 누락 여부 점검
- Research Gate의 Open Decisions와 사용자 확정 사항 역추적
- 이번 단계에서는 Runtime Eval, Hook 실행, GitHub Actions 또는 실제 외부 상태 변경을 검증하지 않는다.

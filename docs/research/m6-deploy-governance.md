# V2-M6 Research Gate — Deploy & Governance

- **확인일**: 2026-09-20
- **관련 Issue**: [#144 — V2-M6 Step ① Code Review · Human Gate · CI/CD Governance Research Gate](https://github.com/taejung3852/OwnHands/issues/144)
- **상위 Milestone**: [#19 — V2-M6 Deploy & Governance](https://github.com/taejung3852/OwnHands/milestone/19)
- **상태**: Research only — 구현안 미확정

이 문서는 공식 자료가 말하는 사실, 현재 저장소에서 확인한 사실, OwnHands가 검토할 후보를 분리한다. 후보는 OpenAI 또는 Superpowers의 공식 요구가 아니며, M6 설계 단계에서 사용자가 결정해야 한다.

## 1. M6 Goal

V2-M6의 최상위 목표는 **검증된 변경이 사람의 최종 책임 아래 안전하게 PR·CI/CD·Merge/Finish로 이동하도록 Review, Human Gate, 권한과 통제를 연결하는 것**이다.

- **선행 기준선**: M3의 `build`, M4의 `verify`·`verifier`, M5의 Task Set·3-State 판정
- **필요한 결과**: Code Review 결과, CI 관측, Human 승인, GitHub 상태 변경의 책임 경계가 설명 가능해야 한다.
- **Non-goals**: 이 Research Gate에서는 Governance 구현, GitHub Actions workflow, Hook, 새 Eval Task, Agent 변경, branch/worktree 자동화를 만들지 않는다.
- **GORE 경계**: 자동화 자체가 Goal이 아니다. 사람의 승인 책임과 최소권한을 유지하면서 검토 가능한 변경만 통합 단계로 이동시키는 것이 Goal이다.

## 2. Current OwnHands

### 2.1 확인된 저장소 Fact

| 영역 | 현재 확인된 Fact | 근거 |
|---|---|---|
| Roadmap | M6 완료 결과는 PR 검토·CI/CD·Human Gate·권한과 통제의 연결이다. 실행 환경·승인·Hook 배치의 상세는 미정이다. | [`docs/roadmap.md`](../roadmap.md) |
| 공통 진입 규칙 | 승인된 `spec.md`·`plan.md` 기반 Build는 `build` Skill로 진입한다. | [`AGENTS.md`](../../AGENTS.md) |
| Build 종료점 | `build`는 Task별 구현과 Fresh Evidence 기록 후 `verify`를 호출하고, 필수 AC가 모두 PASS일 때만 완료를 주장한다. Reviewer·PR·merge 단계는 연결하지 않는다. | [`.agents/skills/build/SKILL.md`](../../.agents/skills/build/SKILL.md) |
| Verify 책임 | `verify`는 변경 유형별 증거, 회귀 방어, Fresh Evidence를 확인하고 read-only `verifier`에게 AC 역추적 감사를 맡긴다. | [`.agents/skills/verify/SKILL.md`](../../.agents/skills/verify/SKILL.md), [ADR-0008](../adr/0008-verification-references-and-verifier-protocol.md) |
| Verifier | `verifier`는 테스트 Runner가 아니라 Builder가 남긴 증거를 `spec.md` AC와 대조해 `PASS / FAIL / UNOBSERVED`로 판정하는 독립 감사관이다. | [`.codex/agents/verifier.toml`](../../.codex/agents/verifier.toml) |
| Reviewer | `reviewer`는 Git diff, `AGENTS.md`, 아키텍처 결정, 회귀·과설계·근거 없는 주장을 read-only로 검토하고 우선순위화된 finding을 반환한다. | [`.codex/agents/reviewer.toml`](../../.codex/agents/reviewer.toml) |
| Build 위임 | Build의 조건부 routing은 `researcher`, native `worker`, `verifier`만 명시한다. `reviewer` 호출 시점은 아직 없다. | [`.agents/skills/build/references/subagent-routing.md`](../../.agents/skills/build/references/subagent-routing.md) |
| Plan·Evidence | `plan.md`는 Target Files, Task Breakdown, 양방향 추적성, Fresh Evidence를 보존하고 PR과 함께 히스토리에 남기는 기준선이다. | [ADR-0007](../adr/0007-plan-artifact-and-build-feedback-loop.md) |
| Continuous Evals | 단일 Task Set을 `scripts/run-evals.js`가 정적 Preflight와 `codex exec --json` Runtime으로 실행한다. 현재 Runtime task는 read-only이고 결과는 `PASS / FAIL / UNOBSERVED`로 구분한다. | [ADR-0009](../adr/0009-continuous-evals-task-set-and-runner.md), [`docs/evals/task-set.json`](../evals/task-set.json), [`scripts/run-evals.js`](../../scripts/run-evals.js) |
| 조직 정책 방향 | 조직 강제 정책은 프롬프트 지침과 분리해 Enterprise Managed Config 영역으로 둔다는 방향이 확정돼 있다. | [`docs/decisions.md`](../decisions.md) |
| GitHub 자동화 | 현재 tracked tree에서 `.github/workflows/`, `hooks.json`, `requirements.toml`, `managed_config.toml`은 관측되지 않았다. | 2026-09-20 저장소 파일 목록 확인 |

### 2.2 현재 Gap

- `build → verify → verifier` 뒤에 `reviewer`를 언제 호출할지 정해져 있지 않다.
- Verifier의 AC 판정과 Reviewer의 코드 품질 finding은 서로 다른 책임이지만, 두 결과를 합치는 계약이 없다.
- Reviewer에 전달할 최소 Context(`base/head`, diff 범위, spec/plan, 이미 확보한 evidence)가 정해져 있지 않다.
- finding의 우선순위, 수용·기각·Human Escalation, 수정 후 targeted re-review 조건이 정해져 있지 않다.
- M5의 3-State 결과 중 무엇을 CI required check 또는 merge blocker로 삼을지 정해져 있지 않다.
- PR 생성, Merge, Keep, branch/worktree cleanup은 현재 세션별 사용자 승인으로 수행했지만 저장소 차원의 Governance 계약은 없다.
- Hook의 이벤트·강제력·권한 경계와 CI/branch protection의 관계가 미정이다.

## 3. Codex Native Capabilities

아래는 OpenAI 1차 자료에서 확인한 현재 기능이다. 이 기능의 존재가 OwnHands의 채택 결정을 뜻하지 않는다.

| 표면 | 공식 확인 Fact | M6 후보 가치 | Trade-off / Gap |
|---|---|---|---|
| 로컬 Code Review | `/review`는 선택한 diff를 dedicated reviewer가 읽고 우선순위화된 actionable finding을 반환하며 working tree를 수정하지 않는다. 범위는 base branch, uncommitted changes 등으로 고를 수 있다. | 기존 read-only `reviewer`와 겹치는 native primitive를 비교할 수 있다. | OwnHands의 AC 증거 감사나 finding 처리 정책을 자동으로 제공하지 않는다. [공식 Code review](https://learn.chatgpt.com/docs/code-review) |
| GitHub PR Review | Codex Cloud를 연결한 저장소에서 `@codex review` 또는 automatic review를 사용할 수 있다. PR diff와 적용 가능한 `AGENTS.md` 규칙을 따르며 GitHub 표면에서는 P0/P1에 집중한다. | PR 안에서 검토 결과를 남기고 후속 수정을 요청하는 후보가 된다. | push/admin 설정 권한과 Cloud 설정이 필요하다. 공식 문서는 이 리뷰가 테스트·branch protection·required approval을 대체하지 않는다고 명시한다. [공식 GitHub integration](https://learn.chatgpt.com/docs/third-party/github) |
| Non-interactive | `codex exec`은 CI, pre-merge check, scheduled job에서 사용할 수 있다. 기본 sandbox는 read-only이며 `--json`은 실행 이벤트를 JSONL로 제공하고 `--output-schema`는 최종 출력 스키마를 고정할 수 있다. | 현재 M5 runner의 실행 방식과 직접 연결 가능한 CI primitive다. | 비결정적 agent 판정을 곧바로 required check로 사용할 때의 반복성·비용·timeout 정책은 OwnHands가 결정해야 한다. [공식 Non-interactive mode](https://learn.chatgpt.com/docs/non-interactive-mode) |
| Sandbox / Approval | `read-only`, `workspace-write`, `danger-full-access`를 명시할 수 있다. 공식 문서는 자동화에 필요한 최소권한을 사용하고 full access는 격리된 runner/container에 한정하도록 안내한다. | Eval·review는 read-only, 수정 후보는 격리된 workspace-write처럼 책임별 권한을 나눌 근거다. | sandbox는 GitHub branch protection이나 사람 승인을 대신하지 않는다. [공식 Sandboxing](https://learn.chatgpt.com/docs/sandboxing) |
| GitHub Action | `openai/codex-action@v1`은 Codex CLI를 설치하고 지정한 권한으로 `codex exec`을 실행한다. 공식 예시는 Codex job에 `contents: read`, `persist-credentials: false`를 두고 PR write 작업을 별도 job으로 분리한다. | review, repeatable check, patch artifact 등 CI 후보를 새 runner 없이 구성할 수 있다. | API key를 repository-controlled code와 같은 job-level 환경에 노출하지 않아야 한다. action 도입·비용·required check 범위는 아직 미정이다. [공식 GitHub Action](https://learn.chatgpt.com/docs/github-action) |
| Codex Cloud | 연결된 GitHub/GitLab 저장소의 격리 환경에서 작업하고 결과 diff를 검토한 뒤 PR을 열 수 있다. | 로컬 장기 실행과 별개인 remote execution 후보다. | Cloud PR review와 deterministic CI gate는 다른 표면이다. 환경·secret·권한 설정이 필요하며 OwnHands의 기본 실행 환경으로 확정되지 않았다. [공식 Codex cloud](https://learn.chatgpt.com/docs/cloud) |
| Managed Policy | `requirements.toml` 호환 정책은 permission profile, sandbox/approval allowlist, command rule, managed hook 등을 제한할 수 있다. 공식 문서는 이것이 workspace RBAC를 대체하지 않는다고 명시한다. | 조직 강제 정책을 저장소 프롬프트와 분리한다는 ADR-0005 방향과 맞는다. | client/version별 지원 차이가 있고 managed hook script 배포는 별도 MDM/device management 책임이다. 현재 OwnHands에는 실제 조직 정책 requirement가 없다. [공식 Managed configuration](https://learn.chatgpt.com/docs/enterprise/managed-configuration) |
| Hooks | `PreToolUse`, `PermissionRequest`, `PostToolUse`, `Stop`, session/subagent 이벤트 등에 command 또는 MCP hook을 연결할 수 있다. synchronous hook은 일부 동작을 차단·수정할 수 있지만 background hook은 차단·승인·재작성을 할 수 없다. | 관측, Context 보강, 제한된 local guardrail 후보가 된다. | 모든 tool path를 포괄하는 완전한 enforcement boundary가 아니며, local Hook과 CI/CD merge control은 다른 층이다. [공식 Hooks](https://learn.chatgpt.com/docs/hooks) |

### 3.1 공식 자료가 정하지 않는 것

- OpenAI 문서는 OwnHands의 `verifier`와 `reviewer` 중 무엇을 먼저 실행할지 정하지 않는다.
- `PASS / FAIL / UNOBSERVED`를 GitHub merge gate에 어떻게 매핑할지 정하지 않는다.
- Human Gate를 PR 전, Merge 전, Deploy 전 어디에 둘지 정하지 않는다.
- GitHub branch protection과 required checks의 구체 설정은 이번 OpenAI 공식 자료 범위 밖이다.
- 따라서 이 조합은 모두 **OwnHands Candidate 또는 Decision**으로 표시해야 한다.

## 4. Superpowers Candidates

비교 대상은 로컬 설치본의 원문을 읽었다. 채택 후보는 원칙과 경계이며 Skill 전체 복사는 후보가 아니다. `verification-before-completion`과 `systematic-debugging`은 #144 범위에서 제외한다.

| Candidate | 원문 핵심 | OwnHands와의 관계 | Trade-off / M6 판단 질문 |
|---|---|---|---|
| `requesting-code-review` | 주요 기능 완료 후와 main merge 전에, 정확한 설명·요구사항·base/head SHA를 전달해 reviewer를 호출하고 Critical/Important finding을 처리한다. | `.codex/agents/reviewer.toml`이 이미 있으므로 reviewer 생성보다 **호출 시점과 최소 Context**만 후보로 흡수할 수 있다. | 모든 작은 Task마다 review를 강제하면 Thin Harness와 충돌할 수 있다. Major change/merge 전 1회와 targeted re-review의 최소 조건을 정해야 한다. |
| `receiving-code-review` | feedback을 읽고 이해한 뒤 코드베이스에서 검증하며, 맞으면 수정하고 틀리면 기술적 근거로 push back한다. 여러 항목은 불명확성을 먼저 해소하고 blocker부터 하나씩 처리한다. | 외부 review를 무조건 진실로 취급하지 않고 Fact/Decision을 분리하는 OwnHands 원칙과 맞는다. | finding 상태 어휘와 누가 기각을 승인하는지 없다. `accepted / rejected-with-evidence / needs-human` 같은 후보를 둘지는 후속 결정이다. |
| `finishing-a-development-branch` | green test 확인 후 환경·base를 확인하고 `merge locally / push and PR / keep` 선택을 사람에게 제시한다. PR을 선택하면 worktree를 보존하고, cleanup·discard는 명시 승인 아래 수행한다. | Human Gate와 비가역 Git 상태 변경을 분리하는 후보가 된다. | 이 Skill은 full test green을 전제로 하지만 OwnHands는 `UNOBSERVED`를 보존한다. UNOBSERVED가 있을 때 PR은 허용하되 merge는 막을지 별도 결정이 필요하다. |
| `using-git-worktrees` (참고) | 기존 격리를 먼저 감지하고 native worktree를 우선하며, baseline test를 확인한다. | isolated implementation이 실제 Requirement일 때 참고할 수 있다. | #144의 핵심 후보가 아니며, 이번 M6에서 worktree 자동화를 도입하거나 기본값으로 확정하지 않는다. |

## 5. Candidate M6 Flow

아래는 논의를 위한 **후보 흐름**이며 구현 계약이 아니다.

```text
build Task 완료
  ↓
verify + verifier
  ├─ FAIL / required evidence UNOBSERVED → 구현 루프로 복귀 또는 Human 판단
  └─ required AC PASS
        ↓
read-only Code Review (native /review 또는 existing reviewer 후보)
  ├─ actionable finding → 검증 → 최소 수정 → targeted re-review 후보
  ├─ 근거 있는 기각 → 기록
  └─ 해석·정책 충돌 → Human Escalation
        ↓
Human Gate: Push + PR / Keep
        ↓
PR CI 후보
  ├─ deterministic project checks
  ├─ M5 static preflight 또는 선택 task
  └─ 필요할 때만 read-only Codex review/eval
        ↓
Human Gate: Merge 여부
        ↓
Merge 후 Finish/Cleanup 후보
```

### 5.1 책임 분리 후보

- **Verifier**: Spec AC와 Fresh Evidence의 수용성 감사
- **Reviewer**: diff의 결함, 회귀, 저장소 규율, 과설계 finding
- **CI**: 반복 가능한 기계 검사와 선언된 Eval 실행
- **Human**: finding 기각, `UNOBSERVED` 위험 수용, push/PR/merge/deploy 같은 외부 상태 변경 승인
- **Managed policy / sandbox**: 실행 가능한 권한의 상한
- **Hook**: 필요한 경우 관측·보조 guardrail. merge enforcement의 대체물이 아님

### 5.2 Thin Harness 후보 경계

- 새로운 Reviewer Agent를 만들지 않고 existing reviewer 또는 Codex native review를 비교한다.
- M5 runner를 새 CI framework로 확장하기 전에 기존 `--static-only`와 `--task`가 필요한 관측을 제공하는지 확인한다.
- PR review와 CI required check를 같은 것으로 취급하지 않는다.
- write 권한이 필요한 job은 read-only Codex job과 분리한다.
- Hook은 실제 반복 문제와 강제할 이벤트가 확인되기 전에는 만들지 않는다.

## 6. Open Decisions

| ID | 결정할 것 | 후보와 Trade-off |
|---|---|---|
| OD-01 | Code Review 호출 지점 | `verify` 직후 / PR 생성 직후 / 둘 다. 빠른 local feedback과 GitHub 기록의 중복 비용을 비교해야 한다. |
| OD-02 | Reviewer 표면 | existing `.codex/agents/reviewer.toml` / native `/review` / GitHub `@codex review`. Context 통제, 결과 형식, Cloud 의존성이 다르다. |
| OD-03 | 최소 Review Context | base/head SHA, diff scope, spec/plan, Fresh Evidence, known constraints 중 필수 항목을 정해야 한다. 전체 세션 전달은 후보에서 제외한다. |
| OD-04 | Finding 상태와 재검토 | severity 기준, `수용 / 근거 있는 기각 / Human 필요`, targeted re-review 대상 범위를 정해야 한다. |
| OD-05 | Human Gate 위치 | push/PR 전, merge 전, deploy 전 각각의 비가역성과 권한을 기준으로 필요한 Gate를 정해야 한다. |
| OD-06 | 3-State merge 의미 | `FAIL`은 차단 후보가 명확하지만 `UNOBSERVED`를 항상 차단할지, 위험별 Human override를 허용할지 결정해야 한다. |
| OD-07 | CI 실행 범위 | deterministic checks, `run-evals.js --static-only`, 선택 `--task`, Runtime Eval 중 required check로 둘 최소 범위를 비용·재현성·timeout으로 비교해야 한다. 전체 Runtime Suite 기본 실행은 아직 후보가 아니다. |
| OD-08 | Codex CI 표면 | 직접 `codex exec` / `openai/codex-action@v1` / Codex Cloud review의 역할을 분리해야 한다. |
| OD-09 | 권한 모델 | read-only Codex job과 PR write/merge job 분리, secret 노출 방지, sandbox·approval·GitHub token 최소권한을 결정해야 한다. |
| OD-10 | Managed policy | 실제 조직 도입 전에도 예시만 문서화할지, 실제 requirement가 생길 때까지 완전히 보류할지 결정해야 한다. 가상 회사 정책 작성은 기존 Non-goal이다. |
| OD-11 | Hooks | 관측할 반복 문제, 필요한 event, synchronous enforcement 필요성이 생긴 뒤 도입할지 결정한다. 현재는 no-hook도 유효 후보이다. |
| OD-12 | Finish/Cleanup | `Push + PR / Keep / Merge` 선택과 branch/worktree cleanup의 사용자 승인 경계를 정해야 한다. 자동 merge·자동 cleanup은 아직 확정하지 않는다. |

### 조사 결론

Codex는 review, non-interactive 실행, GitHub Action, Cloud PR 연계, sandbox/approval, managed policy, hooks를 이미 제공한다. 따라서 M6에서 새 Governance framework를 만드는 것은 현재 근거로 정당화되지 않는다. 다음 단계는 기존 OwnHands `reviewer`·`verifier`·M5 runner와 이 native surface 중 무엇을 어디에 연결할지, 그리고 사람이 어떤 상태 변경을 승인할지 위 Open Decisions를 통해 좁히는 것이다.

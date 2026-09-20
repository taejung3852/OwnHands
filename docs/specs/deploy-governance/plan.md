# Plan: Review Loop · Human Gate · CI Governance

- **기반 Spec**: [`spec.md`](spec.md)
- **작성 주체**: Codex (사용자 승인된 Spec 기반)
- **일자**: 2026-09-20
- **상태**: Approved — 사용자 확인 (2026-09-20)
- **관련 Issue**: [#148](https://github.com/taejung3852/OwnHands/issues/148)

---

## 1. 구현 맥락 및 대상 파일 (Context & Target Files)

- **구현 목표 요약**: 기존 `build → verify → verifier` 뒤에 기존 read-only `reviewer`, diff-bound Review Evidence, 좁은 `PreToolUse` Gate, 분리된 Human Gate 계약을 연결한다.
- **구현 원칙**:
  - GitHub CI는 deterministic check만 담당한다.
  - Reviewer와 선택 Runtime Eval은 로그인된 로컬 Codex 세션에서 실행한다.
  - Hook은 Review Evidence만 검사하며 Human 승인을 대체하거나 완전한 보안 경계로 주장하지 않는다.
- **대상 파일 목록 및 책임 경계 (Blast Radius Guard)**:
  - `[MODIFY]` `.agents/skills/build/SKILL.md`: `verify/verifier` PASS 이후 Reviewer와 Human Gate로 연결하는 짧은 진입 규칙
  - `[NEW]` `.agents/skills/build/references/review-governance.md`: Review Packet, Finding 판정, targeted re-review, Human Gate 상세 계약
  - `[NEW]` `.codex/hooks.json`: `Bash` 경로의 repo-local `PreToolUse` Hook 등록
  - `[NEW]` `scripts/review-gate.js`: Evidence fingerprint·기록·검사·폐기와 Hook deny 출력
  - `[NEW]` `scripts/review-gate.test.js`: Node `node:test` 기반 단위·임시 Git 저장소 통합 테스트
  - `[MODIFY]` `docs/specs/README.md`: 기존 Plan 템플릿의 Fresh Evidence Checklist에 Review Gate Evidence 항목 추가
  - `[NEW]` `docs/adr/0010-review-human-ci-governance.md`: M6 Review/Human/CI 책임 경계와 트레이드오프 기록
  - `[MODIFY]` `docs/decisions.md`: 승인된 M6 계약과 보류 항목 동기화
  - `[MODIFY]` `docs/roadmap.md`: Step ② 설계·구현 상태와 #146 링크 최소 동기화
  - `[MODIFY]` `docs/specs/deploy-governance/plan.md`: Task별 Fresh Evidence와 최종 판정 기록
  - ⚠️ 위 목록 밖 파일 변경이 필요하면 구현을 멈추고 Spec/Plan 범위를 다시 승인받는다.
- **명시적 비대상**:
  - `.codex/agents/reviewer.toml`, `.codex/agents/verifier.toml`
  - `scripts/run-evals.js`, `docs/evals/task-set.json`
  - GitHub Actions, Managed Policy, 새 Agent, Worktree/cleanup 자동화

### 1.1 비교 주장 및 Before 기준선

- **주장 유형**: `feature`
- **Before 기준선**: `[N/A — 신규 Governance 연결 기능]`
- **현재 Fact**:
  - `.codex/hooks.json`, `scripts/review-gate.js`, `scripts/review-gate.test.js`는 아직 존재하지 않는다.
  - `build`는 현재 `verify`에서 끝나며 Reviewer/Human Gate 연결이 없다.
  - M5 Runtime Eval에는 이 Hook/Review Gate에 직접 대응하는 Task가 없다.

## 2. 인터페이스 및 데이터 계약 (Implementation Contract)

### 2.1 CLI

```text
node scripts/review-gate.js fingerprint --base origin/main

node scripts/review-gate.js record \
  --base origin/main \
  --plan docs/specs/<feature>/plan.md \
  --reviewed-fingerprint <sha256> \
  --verdict PASS

node scripts/review-gate.js check-hook
node scripts/review-gate.js clear
```

- 알 수 없는 subcommand·flag, 누락된 필수값, 저장소 밖 `--plan` 경로는 exit code `2`와 사용법 요약을 반환한다.
- `fingerprint`는 최종 Review Packet에 넣을 현재 diff fingerprint를 출력한다.
- `record`는 `--plan`의 `Review Results`에서 `Resolution: open`인 Finding 상태 count를 직접 계산한다. Caller가 count를 입력하거나 덮어쓸 수 없다.
- `record`는 `--reviewed-fingerprint`를 필수로 받고 현재 fingerprint를 다시 계산한다. 두 값이 정확히 같고 `verdict=PASS`, 미해결 `accepted=0`, `needs-human=0`, 모든 `rejected-with-evidence`가 `Resolution: resolved`이며 Reviewer claim·Reason·Evidence가 존재할 때만 기록한다. 그 외는 exit code `1`로 거부한다.
- `clear`는 현재 checkout의 로컬 Evidence만 삭제하며 파일이 없어도 성공한다.

### 2.2 Evidence 저장과 fingerprint

- 저장 경로: `path.join(realpath(git rev-parse --git-dir), "ownhands", "review-evidence.json")`
  - normal checkout은 `.git/ownhands/` 아래, linked worktree는 해당 worktree 전용 git dir 아래에 저장된다.
- fingerprint 입력을 아래 순서로 UTF-8/바이너리 안전하게 결합하고 SHA-256으로 계산한다.
  1. resolved `base_sha`와 `head_sha`
  2. `git diff --binary <base_sha>...HEAD`
  3. `git diff --binary --cached`
  4. `git diff --binary`
  5. `git ls-files --others --exclude-standard -z`로 얻은 정렬된 untracked 경로와 각 파일 내용 SHA-256
- Evidence JSON은 Spec `REQ-08` 필드를 그대로 사용하며 추가 필드는 만들지 않는다.
- `check-hook`은 Evidence의 `base_sha`, `head_sha`, fingerprint, verdict, finding count를 모두 재검증한다.

### 2.3 `plan.md` Review Results 계약

- `plan.md`의 `Review Results`는 Finding 상세 reasoning의 유일한 영구 Source of Truth다.
- 각 Finding은 고유 ID와 아래 다섯 필드를 가진다: `Status`, `Resolution`, `Reviewer claim`, `Reason`, `Evidence`.
- `Resolution`은 `open / resolved` 중 하나다. 해결된 `accepted`·`needs-human` Finding은 삭제하지 않고 `resolved`로 전환하며, 미해결 count는 `open`인 항목만 센다.
- `rejected-with-evidence`의 `Evidence`에는 코드 위치, Spec/REQ, 최신 테스트 결과 중 하나 이상의 구체적 인용이 있어야 한다.
- Review Evidence JSON은 상세 내용을 복제하지 않고 `finding_counts`만 보존한다.
- Review 후 `plan.md`를 포함한 diff가 바뀌면 fingerprint가 달라지므로 기존 JSON Evidence는 stale이 된다.
- Finding 판정과 수정, `plan.md` 기록을 모두 끝낸 뒤 fingerprint를 계산하고 그 값의 최종 diff를 Reviewer에게 전달한다.
- 최종 Reviewer가 새 Finding을 반환하면 이를 `plan.md`에 기록·처리하고 fingerprint 계산부터 반복한다. 새 Finding이 없으면 그 결과를 기록하기 위해 tracked file을 다시 수정하지 않고 로컬 Review Evidence만 기록한다.

```markdown
## 6. Review Results

### Finding `F-01`
- **Status**: `rejected-with-evidence`
- **Resolution**: `resolved`
- **Reviewer claim**: `foo()`가 `null`을 반환할 수 있음
- **Reason**: 승인된 contract와 회귀 테스트가 non-null 동작을 보장함
- **Evidence**:
  - `spec.md` `REQ-04`의 non-null contract
  - `foo.test.ts` null-path test PASS
```

### 2.4 대상 command 판정과 Hook 출력

- Hook matcher는 `^Bash$` 하나만 사용한다. unified `exec_command`는 공식 Hook 경로에서 `Bash`로 관측된다.
- command 문자열에서 다음 실행 형태를 보수적으로 감지한다.
  - `git push` 및 `git -C <path> push`
  - `gh pr create`
  - `gh pr merge`
  - `&&`, `;`, `||`, 단일 `|`·`&`, 괄호, 줄바꿈으로 연결된 복합 command 내부의 위 명령
- 대상 외부 Git 명령이 복합 command에 포함되면 검사 뒤 diff 변경 우회를 막기 위해 Evidence 유무와 관계없이 deny하고 독립 command로 다시 실행하게 한다.
- 대상이 아니면 stdout 없이 exit code `0`으로 통과한다.
- 차단 시 exit code `0`과 아래 JSON을 stdout에 반환한다.

```json
{
  "hookSpecificOutput": {
    "hookEventName": "PreToolUse",
    "permissionDecision": "deny",
    "permissionDecisionReason": "OwnHands Review Gate: valid review evidence is missing or stale."
  }
}
```

- Hook 입력 JSON 오류는 안전하게 deny하되 Secret, transcript, network를 읽지 않는다.

## 3. 작업 단위 분해 (Task Breakdown)

- [x] **Task 1: Review Evidence core와 CLI를 TDD로 구현**
  - `scripts/review-gate.test.js`에 임시 Git 저장소 fixture와 CLI 실행 helper를 먼저 작성한다.
  - 실패 테스트: 잘못된 인자, unresolved base, 저장소 밖 Plan, 누락된 Review Results 필드, 근거 없는 기각, 미해결 finding, reviewed fingerprint 누락·불일치, record/clear, 동일 fingerprint, committed·staged·unstaged·untracked 변경 후 stale, linked worktree별 Evidence 분리를 각각 관측한다.
  - `scripts/review-gate.js`에 argument parser, 구조화된 Review Results parser, Git command wrapper, per-checkout evidence path, fingerprint, atomic JSON write, clear를 최소 구현한다.
  - CLI count 입력은 제공하지 않고 Plan의 Finding 항목에서 count를 계산한다.
  - 최종 Review 전 출력한 fingerprint가 `record --reviewed-fingerprint` 시점의 현재 fingerprint와 같을 때만 기록되는지 검증한다.
  - `record`가 저장한 JSON을 다시 읽어 Spec `REQ-08` 필드와 값 범위를 검증한다.

- [x] **Task 2: 좁은 PreToolUse Gate를 TDD로 연결**
  - 실패 테스트: 일반 command 통과, `git push`·`git -C … push`·`gh pr create`·`gh pr merge`와 chained command 차단, malformed Hook JSON deny, 공식 deny schema를 작성한다.
  - `check-hook`이 stdin의 `tool_name`·`tool_input.command`를 읽고 대상 command에서만 Evidence를 검증하도록 구현한다.
  - `.codex/hooks.json`에 `^Bash$` matcher, repo root 기반 script 경로, 10초 timeout, 짧은 status message를 등록한다.
  - Hook의 `agent` handler, `Stop`, `PostToolUse`, network/Secret 권한은 추가하지 않는다.

- [x] **Task 3: Build Review Loop와 Human Gate 계약 연결**
  - `review-governance.md`에 Review Packet 3종, finding 3-state, `plan.md` Review Results 형식, final reviewed fingerprint, targeted re-review, Review Evidence 기록, `Push + PR / Keep`, Merge·Deploy·Cleanup 별도 승인 규칙을 작성한다.
  - `build/SKILL.md`에는 `verify`의 필수 AC PASS 후 해당 Reference를 읽고 기존 reviewer를 호출한다는 짧은 단계만 추가한다.
  - `UNOBSERVED` override는 누락 Evidence·확보 불가 사유·수용 위험을 제시하고 사용자에게 반드시 질문하도록 명시한다.
  - `docs/specs/README.md`의 기존 Fresh Evidence Checklist에 Finding별 Status·Reviewer claim·Reason·Evidence를 보존하는 `Review Results` 항목과 diff fingerprint·finding summary 항목만 추가한다.

- [x] **Task 4: ADR·결정·로드맵 동기화**
  - ADR-0010에 Reviewer/Verifier 책임 분리, 로컬 Hook 선택 이유, Codex Action/API 비용 배제, deterministic CI와 로컬 Runtime 분리, Human Gate를 기록한다.
  - `docs/decisions.md`에는 확정 계약과 Managed Policy·전체 Runtime CI 보류를 반영한다.
  - `docs/roadmap.md`에는 Step ② 계약과 #146/ADR-0010 링크만 추가하며 M6 전체 완료로 표시하지 않는다.

- [ ] **Task 5: Fresh Evidence, Hook 실측, 독립 감사**
  - 아래 정적·단위 검사를 실행하고 출력과 exit code를 이 Plan에 기록한다.
  - Codex `/hooks`에서 새 repo Hook 정의를 사용자가 검토·신뢰한 뒤, Evidence가 없는 상태의 `git push --dry-run`이 실제로 차단되는지 1회 관측한다.
  - 기존 `verify`와 `verifier`로 AC-01~AC-12를 감사한다.
  - Finding 판정·수정·`plan.md` Review Results·Fresh Evidence 갱신을 모두 마친 뒤 최종 diff를 고정한다.
  - `fingerprint --base origin/main` 값을 포함한 최소 Review Packet을 기존 `reviewer`에 전달해 정확히 그 최종 diff를 검토하고 Finding을 3-state로 판정한다.
  - 새 Finding이 있으면 기록·처리 후 fingerprint 계산과 최종 Review를 반복한다. 새 Finding이 없으면 tracked file을 더 수정하지 않는다.
  - 같은 fingerprint를 `record --reviewed-fingerprint`에 전달해 PASS Review Evidence를 기록한 뒤 `git push --dry-run`이 Hook을 통과하는지 1회 관측한다.
  - 실제 Push/PR은 실행하지 않고 사용자에게 `Push + PR / Keep` 선택을 요청한다.

## 4. AC별 검증 전략 매핑 (Verification Strategy Mapping)

| AC ID | 검증 전략 | 관측 증거 | 통과 기준 |
|---|---|---|---|
| `AC-01` | 정적 흐름 감사 + verifier | `build`와 Reference의 순서 | `verify/verifier → reviewer → Human Gate` 명시 |
| `AC-02` | 정적 계약 검사 | Review Packet 항목 | 필수 Context 포함, 전체 대화 제외 |
| `AC-03` | 정적 계약 + parser test | plan Finding 상세와 re-review 분기 | 3-state, 기각 Reason·Evidence, 제한 조건 모두 관측 |
| `AC-04` | `node:test` Git fixture | reviewer 관측 fingerprint와 record 시점 fingerprint 비교 | 동일 시만 기록, 변경 시 거부·stale |
| `AC-05` | `node:test` + Hook dry-run | 일반 command/외부 command 결과 | 일반 응답 무개입, 대상만 검사 |
| `AC-06` | 정적 계약 검사 | Human Gate 문구 | Push+PR/Merge/Deploy/Cleanup 분리 |
| `AC-07` | 정적 계약 + Static Preflight | OwnHands/사용 프로젝트 표 | 전체 Runtime Suite 기본 실행 없음 |
| `AC-08` | 정적 계약 + verifier | FAIL/UNOBSERVED 분기 | FAIL 차단, override 질문 필수 |
| `AC-09` | Hook test + 정적 감사 | Hook I/O와 역할 표 | read-only/Target Files/외부 권한 분리 |
| `AC-10` | diff audit | 변경 파일 목록 | Non-goal 파일·자동화 추가 0건 |
| `AC-11` | edge-case test + 문서 감사 | malformed input, remote head 규칙 | 실패를 PASS로 과장하지 않음 |
| `AC-12` | Plan 구조 검사 | 본 문서 4대 필드 | Task·Target Files·AC·Evidence 매핑 완비 |

## 5. 실행 및 신선한 검증 증거 (Execution & Fresh Evidence Checklist)

- [x] **Task 1 Evidence**
  - Red: `node --test scripts/review-gate.test.js` → 구현 부재로 17개 실패, exit code `1`
  - Targeted Red: duplicate/malformed Finding과 외부 symlink 비추적 테스트가 각각 수정 전 exit code `1`로 실패
  - Green: 최종 동일 명령 → 18개 PASS, 실패 `0`, exit code `0`
- [x] **Task 2 Evidence**
  - Hook command 판정·deny schema·valid/stale Evidence를 위 17개 테스트에서 관측
  - JSON: `node -e "JSON.parse(require('fs').readFileSync('.codex/hooks.json','utf8'))"` exit code `0`
- [x] **Task 3 Evidence**
  - `review-governance.md`에 3종 Review Packet, 3-state + Resolution, targeted re-review, Human Gate, `UNOBSERVED` override 계약 연결
- [x] **Task 4 Evidence**
  - ADR-0010·decisions·roadmap에서 #146 계약과 #148 구현 추적성, Runtime CI·Managed Policy 보류 상태 대조
- [x] **회귀 검증 게이트**
  - `git diff --check` exit code `0`
  - `node --test` → 전체 24개 PASS, 실패 `0`, exit code `0`
  - `node --test scripts/review-gate.test.js` → 18개 PASS, 실패 `0`, exit code `0`
  - `node scripts/run-evals.js --static-only` → EVAL-0004 PASS, 회귀 `0`, Runtime 항목은 의도대로 `UNOBSERVED`
  - 전체 Runtime Eval Suite는 실행하지 않음
- [ ] **Hook 실제 관측 — `UNOBSERVED`**
  - Evidence 없는 `git push --dry-run origin HEAD`가 exit code `0`으로 진행되어 현재 세션에서 새 repo Hook의 trust/reload가 적용되지 않았음을 관측
  - Hook deny·PASS의 실제 Codex 표면 동작은 `UNOBSERVED`; 우회 자동화는 추가하지 않음
  - 스크립트 직접 실행 경계는 `node:test`에서 missing/valid/stale Evidence로 검증됨
  - **사용자 override (2026-09-20)**: 현재 세션에서 실제 Hook 차단이 입증되지 않은 위험을 제시한 뒤 Push + PR 진행을 명시적으로 승인받음
- [x] **독립 Verifier Gate**
  - 판정: AC-01~04·AC-06~12 `PASS`, AC-05 `UNOBSERVED`
  - Overall: 실제 Hook trust/reload 미관측으로 `UNOBSERVED`; 위 사용자 override 없이는 Push/PR 금지
- [ ] **독립 Reviewer Gate**
  - Review Packet: 승인된 Spec/Plan, `origin/main...HEAD` 및 working tree, Fresh Evidence·관련 baseline, known constraints, 최종 diff fingerprint
  - 모든 Finding의 `accepted / rejected-with-evidence / needs-human` 판정과 해결 기록
  - `rejected-with-evidence`마다 Reviewer claim·Reason·구체적 Evidence가 `plan.md`에 보존됐는지 확인
  - 모든 tracked 기록과 수정이 끝난 뒤 계산한 fingerprint의 diff를 마지막으로 확인했으며, 그 뒤 변경 없이 Evidence를 기록했는지 확인

## 6. 중단 조건

- Hook이 일반 질문이나 비대상 command를 차단하면 구현을 멈추고 matcher/command detection을 수정한다.
- Review Evidence가 tracked file을 만들거나 다른 worktree와 공유되면 구현을 멈추고 storage path를 수정한다.
- 마지막 Reviewer 관측 뒤 tracked file이 변경되면 Evidence 기록을 멈추고 새 fingerprint의 최종 Review로 돌아간다.
- 원격 PR head를 로컬 Hook만으로 증명해야 하는 요구가 생기면 Spec으로 돌아간다.
- Codex Action/API key, Managed Policy, 새 Agent, 새 Eval Task가 필요해지면 이번 Plan 범위를 확장하지 않고 사용자 승인을 요청한다.
- Hook trust를 확보하지 못해 실제 차단을 관측하지 못하면 `UNOBSERVED`로 남기고, `REQ-22`의 명시적 사용자 override 없이는 Push/PR 단계로 진행하지 않는다.

## 7. Review Results

### Finding `F-01`
- **Status**: `accepted`
- **Resolution**: `resolved`
- **Reviewer claim**: 유효한 Evidence 확인 뒤 같은 shell command에서 diff를 변경하고 `git push`를 실행하면 Reviewer가 보지 않은 변경을 Push할 수 있다.
- **Reason**: `PreToolUse`는 command 실행 전에 한 번만 검사하므로 `git commit ... && git push`의 중간 변경을 다시 fingerprint하지 않는다.
- **Evidence**:
  - `scripts/review-gate.js`의 `checkHook()`이 대상 외부 Git 명령을 포함한 복합 command를 Evidence 유무와 관계없이 deny하도록 수정됨
  - `node --test --test-name-pattern='allows valid evidence' scripts/review-gate.test.js` → 수정 전 FAIL, 수정 후 PASS

### Finding `F-02`
- **Status**: `accepted`
- **Resolution**: `resolved`
- **Reviewer claim**: 사용자가 명시적으로 승인한 `UNOBSERVED` override가 있어도 Build 계약 문구상 Review/Human Gate 단계에 도달할 수 없다.
- **Reason**: `build/SKILL.md`와 Review Reference는 필수 AC 전부 PASS만 다음 단계 조건으로 쓰지만 Spec `REQ-22`는 명시적 Human override를 허용한다.
- **Evidence**:
  - `.agents/skills/build/SKILL.md` 5단계와 `references/review-governance.md` 첫 문단이 `PASS 또는 명시적 UNOBSERVED override`로 정렬됨
  - `spec.md` `REQ-01`·`REQ-22` 및 본 Plan의 2026-09-20 사용자 override 기록

### Finding `F-03`
- **Status**: `accepted`
- **Resolution**: `resolved`
- **Reviewer claim**: 유효한 Evidence 상태에서 단일 `|`·`&`로 선행 mutation과 Push를 연결하면 복합 command 차단을 우회할 수 있다.
- **Reason**: 대상 command 탐지와 복합 command 판정이 서로 다른 shell separator 집합을 사용했다.
- **Evidence**:
  - `scripts/review-gate.js`가 공통 `SHELL_CONTROL` 집합을 target boundary와 복합 판정에 함께 사용함
  - 유효 Evidence 상태의 단일 `|`·`&` 회귀 테스트가 수정 전 FAIL, 수정 후 PASS

### Finding `F-04`
- **Status**: `accepted`
- **Resolution**: `resolved`
- **Reviewer claim**: `REQ-22`가 예외 Merge만 언급해 Push+PR의 `UNOBSERVED` override 근거가 영구 계약에서 불명확하다.
- **Reason**: `REQ-01`과 Build 계약은 `REQ-22`를 일반 override 절차로 참조하지만 본문 범위는 Merge로 좁혀져 있었다.
- **Evidence**:
  - `spec.md` `REQ-22`가 해당 Human Gate의 예외 진행으로 일반화되고 Gate 간 승인·override 비승계가 명시됨

### Finding `F-05`
- **Status**: `accepted`
- **Resolution**: `resolved`
- **Reviewer claim**: target regex가 임의의 공백 뒤 `git push`도 실행 명령으로 간주해 `echo git push`, `rg git push docs` 같은 일반 명령을 차단한다.
- **Reason**: command boundary에 shell 실행 위치가 아닌 일반 `\s+` 대안을 포함했다.
- **Evidence**:
  - `scripts/review-gate.js`의 target boundary를 command 시작 또는 공통 `SHELL_CONTROL` 직후로 제한함
  - `echo git push`, `rg git push docs` negative regression이 수정 전 FAIL, 수정 후 PASS

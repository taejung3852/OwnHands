# Plan: Release Readiness Hardening

- **기반 Spec**: [`spec.md`](spec.md)
- **작성 주체**: Codex native Plan Mode
- **일자**: 2026-09-20
- **상태**: Approved
- **승인**: 사용자가 Implementation Plan과 세 정책 결정을 확정하고 구현을 요청함

## 1. 구현 맥락과 경계

- 기준점: `origin/main` `72084785a8229bccd0400dff3cd5b3acec807496`
- 작업 격리: `codex/release-readiness-hardening` worktree
- 기존 checkout의 사용자 소유 미추적 파일은 보존한다.
- Confirmed defects: Review Results fenced/empty-field parser, external repository scope, quoted shell token 판정, static-only runtime baseline overwrite.
- bootstrap은 Node 표준 라이브러리만 사용하는 Thin Harness다. `init`, `doctor` 이외 lifecycle/runtime 기능은 만들지 않는다.
- 실제 E2E, Runtime Eval, registry publish, release/tag/version, Push/PR/Merge는 비대상이다.

## 2. 작업 단위

각 defect는 regression test RED를 관측한 뒤 최소 구현으로 GREEN을 만든다.

- [x] **Task 1 — Review Results parser**
  - 목표: fenced 예제를 제외하고 실제 section 하나와 실질적으로 채워진 필드만 인정
  - 변경: `scripts/review-gate.test.js`, `scripts/review-gate.js`
  - 검증: fenced PASS 뒤 unresolved, 빈 Reason/Evidence, 정상 Finding
  - 완료: backtick/tilde fence 무시, fence 밖 section 정확히 하나, Evidence의 제한된 continuation만 허용
- [x] **Task 2 — quote-aware command 판정**
  - 목표: quote 내부 특수문자와 실제 shell operator 구분
  - 변경: 같은 Review Gate test/implementation
  - 검증: quoted 정상 2건 허용, 실제 compound operator 거부
  - 완료: single/double quote와 backslash만 추적하는 작은 scanner
- [x] **Task 3 — external Git repository scope**
  - 목표: Evidence repository와 external target 일치 강제
  - 변경: 같은 Review Gate test/implementation
  - 검증: cross-repo `git -C`, `gh --repo`, `gh -R` 거부, current target 허용
  - 완료: current Git root/GitHub origin 비교, 불명확 target fail closed
- [x] **Task 4 — runtime baseline overwrite**
  - 목표: 미실행 runtime 결과의 baseline 변경 차단
  - 변경: `tests/run-evals.test.js`, `scripts/run-evals.js`
  - 검증: 금지 옵션 non-zero와 byte-identical baseline, 일반 static-only 회귀
  - 완료: argument validation에서 옵션 조합 거부
- [x] **Task 5 — native Plan Mode handoff**
  - 목표: heavy flow에 native Plan Mode와 사용자 계획 승인 gate 연결
  - 변경: grill-spec/build Skills, `AGENTS.md`, `docs/specs/README.md`, ADR-0007, EVAL-0004
  - 검증: Plan Mode가 아니면 전환 안내 후 중단, Approved 전 Build 금지, trivial 면제
  - 완료: 별도 plan Skill 없이 `plan.md`를 durable artifact로만 정의
- [x] **Task 6 — subagent 정책과 sandbox**
  - 목표: 역할별 default/override와 read-only 권한을 dispatch 계약으로 적용
  - 변경: `.codex/agents/model-policy.md`, 세 TOML, routing references, ADR-0001, decisions, task-set/runner
  - 검증: default pair·override·provenance, read-only, TOML model pin 부재
  - 완료: 모든 role dispatch가 model+effort를 명시하고 inheritance를 정상 경로로 사용하지 않음
- [x] **Task 7 — Explain 2B**
  - 목표: 명시적 `$explain`은 HTML visual 기본, 제한된 text fallback
  - 변경: Explain Skill, ADR-0002, decisions, overview, EVAL-0001
  - 검증: HTML/shape/fallback 정적 계약과 text-only runtime scenario 계약
  - 완료: 새 renderer 없이 문서 모순 제거, 실제 HTML E2E는 미주장
- [x] **Task 8 — Thin bootstrap `init`**
  - 목표: native assets를 한 명령으로 안전하게 연결
  - 변경: `package.json`, `bin/ownhands.js`, `tests/ownhands-cli.test.js`, marker `AGENTS.md`
  - 검증: clean fixture, 기존 AGENTS/hooks 보존, 재실행, malformed/conflict/symlink/path escape
  - 완료: stdlib-only preflight와 atomic write, provenance manifest
- [x] **Task 9 — `doctor`와 package boundary**
  - 목표: mutation 없는 drift 진단과 최소 npm payload
  - 변경: 같은 CLI/test와 package `files`
  - 검증: healthy/각 drift exit, `npm pack --dry-run --json`
  - 완료: 필요한 native assets만 package에 포함
- [x] **Task 10 — installation contract**
  - 목표: `npx ownhands init/doctor` 중심 Quickstart와 안전한 수동 제거
  - 변경: `docs/installation.md`, `README.md`, `docs/README.md`
  - 검증: docs/help/fixture 동작 대조
  - 완료: 사용자 절차에 `npx skills` 없음, update/migrate/uninstall command 없음
- [x] **Task 11 — 제한된 최종 검증과 독립 Review**
  - 목표: 변경 경계의 material regression과 승인된 정책을 독립 확인
  - 검증: 관련 node:test, CLI fixtures, pack/local tarball npx, static-only Eval, docs/Skill/ADR 대조, read-only reviewer
  - 완료: 관련 검사 PASS, 미실행 E2E/Runtime/registry/Hook trust는 `UNOBSERVED`

## 3. AC 검증 매핑

| AC | Task | 관측 증거 |
|---|---|---|
| AC-01 | 1 | targeted `node:test` RED→GREEN |
| AC-02 | 2 | quoted/compound command tests |
| AC-03 | 3 | cross/current repo fixtures |
| AC-04 | 4 | exit code와 baseline byte comparison |
| AC-05 | 5 | EVAL-0004 static contract와 문서 대조 |
| AC-06 | 6 | agent/routing static contract |
| AC-07 | 7 | EVAL-0001 static contract와 runtime scenario definition |
| AC-08 | 8 | CLI init fixture tests |
| AC-09 | 9 | doctor drift matrix |
| AC-10 | 9 | pack dry-run과 local tarball npx |
| AC-11 | 11 | targeted suite, static Eval, independent review |

## 4. Evidence 체크리스트

- [x] Task별 RED/GREEN 로그
  - Review parser 신규 3건: 수정 전 3 FAIL → 관련 기존 동작 포함 5 PASS.
  - quoted shell 판정: 수정 전 1 FAIL → 관련 gate 2 PASS.
  - repository scope: 수정 전 cross-repo 허용으로 FAIL → current/cross/불완전 target matrix PASS.
  - runtime baseline: 수정 전 exit 0으로 FAIL → argument validation 뒤 PASS.
  - Skill/agent 계약: 강화한 Static Preflight에서 EVAL-0001/0002/0004 FAIL → 계약 반영 뒤 static regression 0.
  - CLI: 구현 전 missing entry로 RED → init/doctor/package fixture GREEN.
- [x] Review Gate 및 Eval runner 관련 tests — 전체 관련 suite와 CLI를 합쳐 48 PASS, 0 FAIL.
- [x] bootstrap CLI fixture tests — 기존 AGENTS/hooks 보존, 멱등성, malformed/conflict/symlink/drift/non-Git 경계 PASS.
- [x] `npm pack --dry-run --json`과 local tarball `npx` init/doctor — 27-file payload, 임시 Git 프로젝트에서 init/healthy doctor 관측.
- [x] `node scripts/run-evals.js --static-only` (baseline update 없음) — EVAL-0004 PASS, regression 0; runtime 항목은 의도대로 UNOBSERVED.
- [x] `git diff --check` 및 변경 script `node --check` — exit 0.
- [x] final read-only Reviewer — 사용자 override `gpt-6-astra` / `medium` 요청값으로 검토; actual runtime model/effort는 `UNOBSERVED`. 최초 경계 finding 6건과 잔여 변형 4건을 regression test로 닫은 뒤 최종 재검토 `No findings`.
- [x] 실제 E2E, Runtime Eval, registry npm, Hook trust를 `UNOBSERVED`로 유지

## 5. Review Results

Final committed-diff findings are recorded in this section. No Finding entries means the final Reviewer reported no findings.

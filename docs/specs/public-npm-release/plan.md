# Plan: OwnHands 0.0.1 공개 npm 배포

- **기반 Spec**: [`spec.md`](spec.md)
- **작성 주체**: Codex native Plan Mode
- **일자**: 2026-09-21
- **상태**: Approved
- **승인**: 사용자가 2026-09-21 구현 계획을 승인하고 실행을 요청함

## 1. 구현 맥락과 경계

- 기준점: `origin/main` `9b7f64d426eb3b15c8ebb894fd78cc5d1d2cf05e`
- 작업 브랜치: `codex/npm-init`
- 사용자 소유 미추적 `docs/explain-m7-closed-loop.html`은 수정·포함하지 않는다.
- Node.js 18+, runtime dependency 0개, package `ownhands@0.0.1`, MIT를 유지한다.
- 기존 Runner를 재사용하고 새 Runner·Hook·publish CI·update/migrate/uninstall을 만들지 않는다.
- Push+PR, Merge, npm Publish, tag push, GitHub Release는 각각 별도 Human Gate다.

## 2. 작업 단위

- [x] **Task 1 — 소비자용 Eval 자산과 portable Runner**
  - 대상: `assets/evals/`, `scripts/run-evals.js`, `tests/run-evals.test.js`
  - TDD: internal/installed root·Task Set·Baseline 선택, installed baseline 갱신 차단
  - 완료: 내부 ADR/Spec에 의존하지 않는 5개 소비자 Eval과 독립 baseline
- [x] **Task 2 — init/doctor/eval과 package metadata**
  - 대상: `bin/ownhands.js`, `tests/ownhands-cli.test.js`, `package.json`, `LICENSE`
  - TDD: Eval 설치·manifest·drift, CLI 옵션 전달·거부, tarball allowlist/E2E
  - 완료: init은 설치만, doctor는 read-only, eval은 명시 호출만 수행
- [x] **Task 3 — 공개 사용·결정·Release 문서**
  - 대상: `README.md`, `docs/installation.md`, `docs/decisions.md`, `docs/releases/0.0.1.md`
  - 검증: 구현된 CLI/help/package metadata와 문서 대조
  - 완료: Established/Verified/UNOBSERVED/Known limitations 구분
- [x] **Task 4 — deterministic 검증과 독립 감사·Review**
  - 검증: `npm test`, internal/installed static Eval, JS syntax, pack allowlist, local tarball E2E, `git diff --check`
  - 완료: AC-01~AC-11 verify/verifier 감사 후 final reviewer와 Review Evidence
- [ ] **Task 5 — 외부 Release Gates**
  - 순서: Push+PR 승인 → Merge 승인 → npm 인증/Publish 승인 → registry E2E → tag 승인 → GitHub Release 승인
  - 실패: 이름·인증·2FA·기존 version·응답 불명확 시 우회하거나 재게시하지 않고 중단

## 3. AC 추적성

| AC | Task | Fresh Evidence |
|---|---|---|
| AC-01 | 2 | package metadata, License, pack metadata |
| AC-02~04 | 2 | CLI fixture RED→GREEN 및 전체 `node:test` |
| AC-05~06 | 1~2 | installed static/task/json 실행과 옵션 거부 |
| AC-07 | 2, 4 | `npm pack --dry-run --json` allowlist |
| AC-08 | 4 | deterministic suite와 internal static Eval |
| AC-09 | 5 | registry package 기반 fresh Git fixture |
| AC-10 | 5 | npm `gitHead`, tag target, Release target |
| AC-11 | 3, 5 | 검토된 Release notes와 실제 관측 갱신 |

## 4. Evidence 체크리스트

- [x] Task별 RED와 GREEN 출력
  - 신규 계약 구현 전 targeted suite: 20 PASS, 12 FAIL. Eval 자산·CLI·portable path 부재로 예상한 RED.
  - 최소 구현 후 같은 suite: 32 PASS, 0 FAIL.
- [x] 전체 `node:test` 및 internal static Eval
  - 최종 `npm test`: 57 PASS, 0 FAIL, exit 0.
  - `node scripts/run-evals.js --static-only`: EVAL-0004 PASS, Runtime 항목은 계획대로 UNOBSERVED, regression 0, exit 0.
- [x] installed `eval --static-only`, 단일 task, JSON 출력
  - CLI fixture test에서 전체 static, `INSTALL-0004` 단일 task, JSON 출력 모두 exit 0.
  - Runtime 3건 UNOBSERVED, static 2건 PASS baseline 유지.
- [x] npm pack allowlist와 local tarball E2E
  - `npm pack --dry-run --json`: `ownhands@0.0.1`, 31 files, 48,845 bytes, 허용 자산만 포함.
  - local tarball clean Git fixture `init → doctor → eval --static-only`: exit 0.
- [x] `git diff --check`와 변경 JavaScript syntax
  - `git diff --check`, `node --check bin/ownhands.js`, `node --check scripts/run-evals.js`, Eval JSON parse: exit 0.
- [x] verifier AC 감사와 final reviewer
  - Verifier: AC-01~08·11 PASS, 외부 Release AC-09~10 UNOBSERVED; REQ-05 수정 뒤 local blocker 없음.
  - Reviewer: F-01·F-02 resolved 뒤 exact fingerprint 최종 확인, `No findings`.
- [x] Runtime Eval·Hook trust·M7 실제 순환은 `UNOBSERVED`
- [ ] registry publish/tag/Release는 각 Gate 뒤 실제 결과 기록

## 5. Review Results

Final committed-diff findings are recorded in this section. No Finding entries means the final Reviewer reported no findings.

### Finding `F-01`
- **Status**: `accepted`
- **Resolution**: `resolved`
- **Reviewer claim**: INSTALL-0001 Issue prompt가 실제 GitHub 생성 금지를 Codex 입력에 전달하지 않는다.
- **Reason**: 실행 후 forbidden command 판정은 이미 발생한 외부 쓰기를 예방하지 못한다.
- **Evidence**:
  - `assets/evals/task-set.json`의 P1 prompt와 `scripts/run-evals.js`의 `sc.prompt` 전달 경로
  - fake Codex가 받은 실제 argv에 `초안만 출력`과 `GitHub 생성·변경은 하지 말라`가 포함됨; targeted test PASS

### Finding `F-02`
- **Status**: `accepted`
- **Resolution**: `resolved`
- **Reviewer claim**: 공개 `eval --json` stdout에 사람용 로그가 섞여 `JSON.parse`가 실패한다.
- **Reason**: 문자열에 `results`가 있다는 기존 테스트는 기계 판독 가능성을 입증하지 못한다.
- **Evidence**:
  - 소비자 fixture의 `eval --static-only --json` stdout에 대한 실제 `JSON.parse` 실패
  - 사람용 로그를 JSON mode에서 분리한 뒤 소비자 fixture와 internal Static Eval stdout을 실제 `JSON.parse`해 PASS

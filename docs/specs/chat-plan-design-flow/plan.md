# Plan: Chat Plan & Design

- 기반 Intent: [intent.md](intent.md)
- 기반 Spec: [spec.md](spec.md)
- 상태: Approved — 실제 Codex native Plan Mode에서 사용자 승인, 2026-09-22. 현재 쓰기 가능한 모드에서 보존.
- 기준 commit: `12f6082e5605cde01b0b0366ef15fa44a80c969d`
- Branch: `docs/e2e-feedback-decisions`
- 권한: 구현·로컬 검증. Commit / Push / PR / Merge / 게시 승인 없음.

## 목표와 승인된 보충 계약

ChatGPT 일반 Chat용 Skills-only Plugin과 Codex Light/Planned Build 진입을 연결한다. 승인 Spec 자체는 수정하지 않는다. 사용자 후속 승인에 따라 Plan Mode 안내는 “Plan Mode로 전환해주세요. 현재 환경에서 필요한 전환 방법은 사용자에게 안내해주세요.”를 Build와 활성 안내에 적용한다. Handoff에는 특정 단축키를 고정하지 않는다. Spec REQ-28 / AC-31 / 15절의 단축키 예시는 이 보충 계약에 따라 평가한다.

Plugin root는 `plugins/ownhands/plugin.json`. plan-design은 products [CHAT], allow_implicit_invocation false. Companion ELI5는 `plugins/ownhands/skills/eli5/`, products [CHAT, CODEX]. upstream/revision/license 확인은 제품 결정이 아닌 구현 Fact다. 별도 Codex/npm 설치·업데이트 계약은 추가하지 않는다.

Handoff는 Context / Approved Sources / Decisions / Open Questions / Suggested Entry Point를 갖는 대화 안내다. 작업별 handoff.md, 강한 실행 지시, 구현 자동 승인은 없다.

Intent와 Spec은 각각 전체 내용 → ELI5 → 내용 승인 → 별도 저장 승인 → 관련 ADR과 Stage commit. Issue optional, 기존 Branch 우선, 최신 HEAD 확인, 충돌 중단, 수동 변경 인정과 Reconcile을 따른다.

Light는 판단 필요성과 위험으로 분류하며 plan.md/verification.md를 강제하지 않는다. 세션 Verification Summary를 PR이 있으면 본문에 투영한다. 위험·모호성 증가 시 Planned로 승격한다. Planned는 실제 Plan Mode → 승인 → 쓰기 가능한 모드 → plan.md 보존 → 구현·기존 Verify/독립 감사 순서다.

## Target Files

- `plugins/ownhands/**`: portable manifest, plan-design Skill 및 7개 references, openai.yaml, ELI5 원본·metadata·라이선스·출처, 사용/검증 안내.
- `.agents/skills/grill-spec/**`: shim 없는 제거.
- `.agents/skills/build/SKILL.md`, `.agents/skills/verify/SKILL.md`, verify의 evidence-guide/regression-defense references: 승인된 진입/Light 계약만 연결.
- `README.md`, `AGENTS.md`, `docs/specs/README.md`, `docs/installation.md`: 활성 사용 안내.
- `tests/ownhands-cli.test.js`, `tests/ownhands-plugin.test.js`, `assets/evals/task-set.json`, `docs/evals/task-set.json`: 설치 경계·구조·활성 Eval 정렬.
- 이 `plan.md`, `docs/ownhands/feedback/`의 이번 교정 기록: 증거와 한계 보존.

package.json은 현재 files allowlist로 Plugin 제외가 검증되면 변경하지 않는다. bin installer, Hook/Gate, review, 기존 baseline, 승인 spec/intent/ADR, 사용자 `docs/explain-m7-closed-loop.html`은 보존한다.

## Tasks

- [x] T1 Plugin: GORE/Fact/Decision/인터뷰 규칙과 attribution 이전; 단계별 승인·GitHub·수동 저장·Handoff references; 확인된 ELI5 원본 포함. AC-01~07,12~28.
- [x] T2 Build/Verify: Light/Planned 진입과 경량 검증 연결. AC-29~36.
- [x] T3 npm 패키지 제외 경계/활성 안내: grill-spec 제거, npm 격리 테스트·Eval·안내 정렬. AC-03~04,08~11.
- [x] T4 로컬 검증·독립 감사 (Chat E2E는 platform-blocked / UNOBSERVED): 공식 schema validator, metadata/구조, npm test, pack, tarball init/doctor/static eval, AC 역추적과 독립 verifier. AC-01~40.

## 검증 전략과 한계

기존 baseline: 계획 단계 npm test 57/57. 이번 실행에서 새 설치 경계 테스트 RED 후 GREEN, 전체 테스트와 저장소 정적 Eval을 실행한다. 정적 문자열 assertion은 runtime 증거가 아니다. Skill 시나리오 시뮬레이션도 실제 Chat 호스트 E2E로 취급하지 않는다.

Platform blocker: 개인 계정 Web Chat에 private Plugin을 직접 설치할 공식 경로가 확인되지 않아 E2E 실행 BLOCKED. 웹 Chat Plugin 제품 기능 자체의 미지원 주장이 아니다. 실행하지 못한 Chat AC verdict는 UNOBSERVED (platform-blocked). 판정 어휘는 PASS / FAIL / UNOBSERVED만 유지한다. 공개 Plugin 또는 사용 가능한 workspace 게시 경로 확보 후 E2E를 재개한다. 설치 metadata만으로 Chat picker/implicit 정책 동작을 증명하지 않는다.

Verify/Review 통합, Reviewer 제거, Hook/Gate 수정·조사, Light PR Gate 호환, Feedback 재정렬, Ponytail 정책, ELI5 Codex/npm 업데이트, 새 CI, 과거 문서 일괄 개명은 제외한다. 필수 AC 미관측 상태를 Overall PASS나 외부 Gate override로 취급하지 않는다.

## 실행 및 신선한 검증 증거

- 2026-09-22: 원격 작업 Branch SHA가 승인 commit과 일치. 로컬 main의 tracked 변경 없음. 기존 작업 Branch로 전환. 사용자 untracked HTML 보존.
- 이후 증거와 AC 판정은 아래에 추가한다.

### 실행 기록

- 설치 경계 RED: `node --test --test-name-pattern='init preserves|npm package contains' tests/ownhands-cli.test.js` → exit 1, 2 failures. 기존 grill-spec이 설치 및 tarball에 포함되어 제외 assertion 실패.
- 이전 후 `npm test` → exit 0, 57 pass / 0 fail. 실제 임시 tarball의 npx init/doctor/installed static eval 포함.
- Plugin 구조·상대 링크·ELI5 git blob 검증 추가: `node --test tests/ownhands-plugin.test.js` → exit 0, 3 pass. 링크 검사 초안이 inline code의 예시를 링크로 오인하여 수정했다. runtime 판정이 아니다.
- `node scripts/run-evals.js --static-only --json` → exit 0, EVAL-0004 PASS, 나머지 UNOBSERVED, regressionsCount 0. 기존 baseline 변경 없음. 기존 runtime 감사 fixture는 과거 spec을 대상으로 유지하며 이번 Chat AC 증거로 사용하지 않는다.
- 초기 임시 validator 설치에서 jsonschema 4.26.0은 registry에 없어 실패했다. registry가 제공한 4.25.1로 재시도한다. 프로젝트 의존성 변경 없음.

### Skill baseline simulation

Read-only verifier / requested_model=gpt-5.6-sol / requested_reasoning_effort=high / selection_basis=default. actual_model/actual_reasoning_effort=UNOBSERVED.
기존 Skill의 README 오타·내용만 승인·재연결 충돌·실행 승인 없는 Handoff 시나리오를 읽기 전용으로 평가했다. trivial 면제 이후 plan Task/증거를 무조건 요구하는 공백, GitHub 저장·재연결 계약 부재, 승인과 실행 권한 경계 공백을 확인했다. 사용자 명시 금지 자체는 준수했고 모든 기존 행동이 실패한 것은 아니다. 이 결과는 Chat E2E가 아닌 지침 시뮬레이션이다.

### 최종 로컬 checks (독립 감사 전)

- `npm test` → exit 0, **60 pass / 0 fail / 0 skipped**, 11.97s. init 보존·멱등성, 충돌 거부, doctor, 실제 local tarball npx 설치 및 static eval, pack 제외, Plugin 구조·링크·ELI5 blob 포함.
- 임시 venv의 jsonschema 4.25.1 `Draft202012Validator`로 공식 schema를 fetch하여 schema 자체와 plugin.json 검증 → PASS. schema SHA256: `0a4aad95ce337878ad38802ebf0daa3fde76abe3f65400c86bcbb1ec0b3ab883`.
- PyYAML 6.0.3 `safe_load`로 두 Skill frontmatter 및 openai.yaml 파싱 → PASS. plan-design products=[CHAT], implicit=false; eli5 products=[CHAT,CODEX]. interface 필수 문자열 확인. metadata 선언의 관측이며 host 적용 증거 아님.
- `git diff --check` → exit 0. 승인 Spec/Intent/ADR, scripts/bin/package.json/.codex, 기존 Eval baseline diff 없음. 사용자 HTML 보존.
- feedback Skill로 사용자 교정 3건을 로컬 recorded-only 기록. 외부 전달 없음.

### 기술 확인 Fact와 미관측

- ELI5 pin `a727be1c7bd6064419b6f60d71993a19198adc17`, SKILL.md git blob `ff6b33c9b3277c493e03e47fad327c6ad318e1d5`; upstream에서 직접 가져와 원본 일치 검사. root Apache-2.0 LICENSE 동봉. 이는 Spec의 source/license 확인 요구를 충족하는 Fact다.
- Portable schema는 Draft 2020-12이며 root skills/를 사용한다. 이번 manifest에 불필요한 OpenAI extension 필드를 추가하지 않았다. metadata 허용 형식과 Chat 실제 enforcement는 별개다.
- 계획 단계 GitHub repository read와 permission metadata 확인은 write 실행/Chat tool 관측이 아니다. 이 구현에서는 외부 write하지 않았다. Chat 연결/권한/실패 경로 runtime은 UNOBSERVED.
- 이 세션 실제 Plan Mode 승인 후 Default 모드 전환은 관측됐다. 특정 단축키 성공/실패는 시험하지 않았다.

### AC 추적 — 사용자 관측에 따른 완료 기록 정정 반영

| AC | Verdict | Evidence / 한계 |
|---|---|---|
| 01–05 | PASS | 공식 schema, package 구조, 제거/격리 검사, YAML 선언 검증 |
| 06–07 | UNOBSERVED | platform-blocked: 실제 일반 Chat picker/implicit activation 미실행 |
| 08–11 | PASS | 실제 임시 npm tarball init/doctor/static eval 및 pack exclusion tests |
| 12–25 | UNOBSERVED | references 구현·정적 시뮬레이션만 존재; Chat 승인/저장/실패 runtime 미실행 (platform-blocked) |
| 26 | UNOBSERVED | 작업별 handoff.md 없는 현재 구조; 정상 Chat 실행 미관측 |
| 27 | PASS | handoff-guide의 5개 계약 필드 직접 확인 |
| 28–36 | UNOBSERVED | Skill 지침 및 시뮬레이션은 실제 호스트 경로/PR 투영 실행 증거가 아님 |
| 37 | UNOBSERVED | platform-blocked: 실제 Chat→GitHub→Codex E2E 미실행 |
| 38 | UNOBSERVED | platform-blocked: 새 Handoff → Codex의 재인터뷰 방지 동작은 post-change E2E에서 미실행. 기존 흐름의 재질문 사례는 아래 정정 기록 참조 |
| 39 | PASS | 현재 턴 60 tests·schema·YAML·static Eval fresh checks |
| 40 | PASS | 미실행 runtime AC를 UNOBSERVED로 유지 |

Overall: UNOBSERVED. Platform blocker: BLOCKED. 구현 자산과 로컬 검증 완료는 전체 runtime AC 통과를 뜻하지 않는다. Review Gate override, Review Evidence PASS, 외부 Git 작업은 수행하지 않는다.

### 독립 감사 지적 처리

- V-01 accepted / resolved: 설치 안내의 공개 `ownhands@0.0.1` 예시가 새 6-Skill 설치를 보장하는 것처럼 읽힘. 공개 릴리스와 현재 Branch의 미게시 tarball을 구분하고 별도 임시 Git 프로젝트에서 tarball init/doctor/eval 확인 방법을 추가했다. 실제 로컬 tarball AC-08~11 증거는 유효하며 공개 릴리스 업데이트를 주장하지 않는다.
- V-02 accepted / resolved: T1~T3 구현 체크 상태를 완료로 정렬. T4는 독립 감사 최종 기록 후 완료 표시하며 runtime AC 미관측과 구분한다.

### 독립 Verifier 결과 — AC-38 기록 정정 반영

- Role: verifier; requested_model: gpt-5.6-sol; requested_reasoning_effort: high; selection_basis: default. actual_model 및 actual_reasoning_effort: UNOBSERVED.
- 입력: 승인 Spec + 사용자 보충 계약이 담긴 Plan, 현재 diff, fresh check 결과. read-only 감사, 별도 production 변경 없음.
- 최종 판정: **UNOBSERVED**. 확인된 AC FAIL 없음. 모든 필수 runtime AC를 관측한 것은 아니므로 Overall PASS가 아니다.
- 정정된 최종 집계: PASS는 01~05, 08~11, 27, 39~40 (12개); UNOBSERVED는 06~07, 12~26, 28~38 (28개). 확인된 AC FAIL 없음. 기존 Verifier 결과의 AC-38 근거를 사용자 관측에 맞춰 정정했으며, 새 Verifier 실행 결과로 주장하지 않는다.
- V-01 설치 안내의 공개 릴리스/미게시 tarball 구분 수정과 V-02 Task 상태 정렬을 재확인했다. 미해결 구현 지적 없음.
- 이후 최종 `npm pack --dry-run --json` 관측: 29 files, Codex Skill 6개(build/explain/feedback/review/verify/write-issue-pr), plugins/ 제외. 저장소 static Eval 재확인: EVAL-0004 PASS, 나머지 runtime UNOBSERVED, regressionsCount 0.

### Post-change Skill simulation (runtime AC 증거 아님)

| Scenario | 독립 관측한 지침상 다음 행동 |
|---|---|
| 명확한 README 오타, spec/plan 없음 | Light 구현 후 native checks와 diff를 Verify에 전달. 계획 문서 강제 없음. |
| Intent 승인, 저장 보류 | Approved / GitHub 저장 대기 유지. write 없음. 사용자 요청 시 Spec 논의 가능. |
| 수동 저장 뒤 재연결·동일 artifact 충돌 | 최신 상태 재조회, 차이 제시, 유지/적용/병합/취소 선택. 자동 overwrite 없음. |
| 복잡한 승인 Spec Handoff, 구현 권한 없음 | Handoff/내용 승인을 구현 권한으로 취급하지 않고 Build 실행 보류. |
| Light 도중 위험한 migration | 중단 후 Planned로 승격, 실제 Plan Mode와 사용자 승인. |

중대한 지침 공백은 발견되지 않았다. 이는 read-only 지침 시뮬레이션으로 Chat 또는 Codex의 실제 실행 AC를 PASS로 바꾸지 않는다.

T1~T4 체크는 승인된 로컬 구현·검증 범위의 수행 완료다. 실제 Chat E2E, post-change Build runtime, PR 본문 투영, 최종 외부 Git Review는 미수행이다. 승인된 Spec/Intent/ADR과 사용자 HTML, 기존 Hook/Gate/baseline은 보존했다. Commit / Push / PR / Merge / npm publish: NOT DONE.

### 완료 기록 정정 — AC-38의 baseline과 post-change 구분

- Baseline / 기존 흐름: 이미 승인된 Skills-only Agent Plugin 방향을 다시 열어 개인 Skill 업로드와 Plugin 전체 설치 중 무엇을 선택할지 사용자에게 질문한 사례가 관측됐다. 따라서 기존 완료 기록의 “현재 구현 세션에서 확정 제품 결정을 재인터뷰하지 않았다”는 근거는 철회한다.
- Post-change: 새 plan-design / handoff-guide를 적용한 Handoff → Codex E2E는 실행하지 못했다. 기존 흐름의 문제를 새 구현의 AC-38 FAIL로 전이하지 않으며, 재인터뷰 방지가 동작한다고 PASS로 승격하지도 않는다. **AC-38 = UNOBSERVED (platform-blocked)**.
- Platform state: private Web Chat E2E **BLOCKED**. AC verdict는 해당 미실행 runtime AC의 **UNOBSERVED (platform-blocked)**. Overall은 **UNOBSERVED**, 확인된 AC FAIL 없음.
- npm은 **npm 패키지에서 Plugin 제외 경계 검증 완료**를 뜻한다. 관측한 것은 npm pack의 패키지 구성과 plugins/ownhands/의 tarball 제외, 임시 local tarball을 사용한 npx ownhands init·doctor·static eval 실행이다. 실제 **npm publish: NOT DONE**.
- “GitHub 작업 규칙 reference (`github-workflow.md`)”는 plan-design이 Issue / Branch / Stage 저장 / Reconcile / 충돌 처리에 참고하는 지침 문서다. GitHub Actions workflow가 아니다.
- 이번 정정은 완료 기록의 정합성 수정이다. 구현·제품 결정·baseline 변경, 테스트 재실행, 추가 검수 루프는 수행하지 않았다. 기존 60 tests 및 schema/YAML·tarball 검증 기록은 당시 관측 사실로 유지한다.

### 현재 상태

- Implementation: DONE
- Local verification: DONE
- Post-change Chat runtime E2E: UNOBSERVED (platform-blocked)
- Commit / Push / PR / Merge / npm publish: NOT DONE

## Review Results

- 일자: 2026-09-23
- 사용자 요청: 독립 diff review 1회, 이상 없으면 commit 직전에 중단.
- Base / HEAD: `12f6082e5605cde01b0b0366ef15fa44a80c969d`; staged 변경 없음. 현재 작업의 unstaged 변경과 Plugin·테스트·계획·feedback untracked 파일을 검토했다. 기존 사용자 파일 `docs/explain-m7-closed-loop.html`은 범위에서 제외했다.
- agent_role: reviewer; requested_model: gpt-6-astra; requested_reasoning_effort: high; selection_basis: default. actual_model / actual_reasoning_effort: UNOBSERVED.
- 결과: actionable findings 없음. Plugin/npm 설치 경계, 승인·저장 분리, Reconcile, Handoff, Light/Planned 지침에서 구체적인 계약 위반·회귀를 발견하지 못했다. Finding 항목 및 미해결 Finding 없음.
- 이번 확인: diff와 관련 파일 읽기, `git diff --check`, 승인 Spec/Intent/ADR·Hook/Gate·baseline 보존 확인. 기존 60 tests·schema/YAML·tarball 증거를 참고했으며 테스트 재실행이나 구현 수정은 하지 않았다.
- 경계: 1회 diff 검토 결과만 기록한다. 이 기록 추가 후 별도 Final Review/fingerprint 승인 루프나 로컬 Review Evidence PASS 기록은 수행하지 않았다. 사용자의 리뷰 요청을 외부 Git Gate의 UNOBSERVED override로 해석하지 않는다.
- AC-38 및 미실행 runtime AC는 UNOBSERVED, private Web Chat E2E의 platform state는 BLOCKED, Overall은 UNOBSERVED로 유지한다.
- feedback triage: 신규 actionable finding·추가 신호 없음. 이번 리뷰만을 위한 새 feedback 파일·Issue 생성 없음.
- 중단 위치: commit 전. stage / Commit / Push / PR / Merge / npm publish 수행 없음.

### 후속 사용자 요청 — Commit / Push

- 2026-09-23: 사용자가 기존 diff review 결과와 UNOBSERVED/BLOCKED 상태를 안내받은 뒤 “커밋 푸시하자”라고 요청했다. 이번 작업의 commit과 기존 Branch push를 수행하는 범위이며 PR / Merge / npm publish는 포함하지 않는다.
- 미관측 runtime AC, AC-38 및 Overall UNOBSERVED는 유지한다. 변경을 원격에 보존해도 실제 Chat 동작·Stage 저장·재인터뷰 방지의 성공을 보증하지 않는다.
- 앞의 NOT DONE/commit 전 중단 기록은 각 보고 시점의 사실이다. 실제 commit·push 결과는 실행 후 세션에서 보고한다.
- 푸시 직전 최종 committed diff와 fingerprint를 기존 Reviewer가 확인한 뒤 로컬 Review Evidence를 기록한다. 이 Evidence는 diff 검토 결과이며 AC Overall PASS를 뜻하지 않는다.

### 현재 Git 상태 — PR #155

- Implementation: DONE
- Local verification: DONE
- Commit: DONE (`b8b8f6b`)
- Push: DONE
- PR: DONE (#155)
- Current PR review: DONE — actionable implementation blocker 없음
- Merge: NOT DONE
- npm publish: NOT DONE
- Plugin publish: NOT DONE
- Post-change Chat runtime E2E: UNOBSERVED (platform-blocked)
- Overall AC verdict: UNOBSERVED

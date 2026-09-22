# Plan: Skill Provider + Secure MCP Tunnel 준비

- 기반: [Intent](intent.md), [Spec](spec.md)
- 상태: Approved — 실제 Plan Mode의 계획을 사용자가 2026-09-23 구현 승인. 쓰기 가능한 모드에서 저장.
- 기준: origin/develop = origin/main = b466e1a5f50aa42005b485fe67fa563e40ce6ab1, PR #155 merged.
- 작업 Branch: feat/plugin-tunnel-connect (origin/develop에서 생성). 기존 feat/plugin-workspace-connect와 사용자 HTML 보존.
- 권한: 로컬 Branch 생성·구현·검증. Commit/Push/PR/Merge/게시 별도 승인. PR 대상은 develop.

## 승인 계획

최소 stdio adapter를 공식 SDK로 구현한다. Zod는 custom 요청 schema, yaml은 전체 frontmatter 파싱에 사용한다. root npm 의존성과 설치기에는 추가하지 않는다. canonical Skill disk 복사본·GitHub/shell/write/Codex Tool·background service는 없다.

시작 시 canonical 파일을 메모리에 읽어 URI allowlist, catalog, 실제 bytes 기반 SHA256, 전체 콘텐츠 revision을 구성한다. 변경은 재시작으로 반영한다. 파일 접근은 startup allowlist 구성에서 경계·symlink·크기·정규화 검사를 거치며 요청 문자열로 filesystem을 탐색하지 않는다.

initialize/skills/list/get/resources/list/read/tools/list/call을 실제 subprocess로 검증하고 공식 Inspector 교차 검증을 수행한다. malformed input, traversal, symlink, 누락·frontmatter·import size, snapshot/revision 회귀 검사를 포함한다. SDK를 쓰므로 framing 재구현은 하지 않는다.

Tunnel/API key/Plugin 연결은 사용자 책임. 실제 Node·server 절대경로와 저장소 밖 profile 명령을 제공한다. 로컬 검증과 Tunnel·Chat 관측을 분리한다. 관련 회귀 검사 후 독립 Verifier가 AC를 감사한다.

## Target Files

- tools/ownhands-skill-provider/**: package/lock/server/tests/README와 node_modules ignore.
- docs/specs/plugin-tunnel-connect/**: 승인 계약과 증거.
- docs/adr/0020-private-chat-skill-provider.md, ADR-0012 후속 링크, docs/adr/README.md.
- plugins/ownhands/README.md: 새 전달 adapter 안내 링크와 기존 미관측 범위 유지.
- tests/ownhands-cli.test.js: provider/npm dependency 제외 assertion 강화.
- README.md: 전체 테스트 실행에 필요한 격리된 provider 의존성 설치 안내.

Canonical Skills, 기존 Intent/Spec/Plan, Build/Verify, Hook/Review Gate, baseline, root package/installer, 사용자 HTML은 변경하지 않는다.

## Tasks

- [x] T1 ADR/계약 보존 및 Branch 준비.
- [x] T2 테스트 RED → provider 구현 → 실제 stdio GREEN.
- [x] T3 Inspector·패키지 격리·회귀 검사와 실행 안내.
- [x] T4 독립 Verifier와 증거 기록. 외부 Gate 작업 없음.

## 실행 및 신선한 검증 증거

- 초기 환경: Darwin arm64, /opt/homebrew/bin/node v26.7.0. tunnel-client는 PATH에서 발견되지 않았다. Tunnel 설치·인증·연결을 수행한 사실은 없다.
- SDK1.30.0, yaml2.9.1, Zod4.6.5를 npm registry에서 확인. provider package에만 고정한다.

### Local evidence — 2026-09-23

- RED: `node --test --test-name-pattern='provider initializes' tools/ownhands-skill-provider/test/server.test.mjs` exit1, assertion `provider entrypoint must exist`. 구현 전 기능 부재 확인.
- provider 최초 7개 stdio/fixture 테스트 PASS. startup-error 비밀/출력 검사 추가 후 root `npm test` exit0: **68 pass / 0 fail / 0 skipped**, 11.45s (기존60 + provider8).
- 실제 subprocess initialize/initialized/ping, tools/list/call, skills/list/get, resources/list/read 성공. canonical plan-design9 + eli5 4 = 13 resources 전체 bytes/digests/frontmatter 일치.
- 거부 검사: 미등록/외부/인코딩 변형/traversal URI, 잘못된 cursor·인자, 알 수 없는 Tool/method, symlink(file/dir/Skill/root), 비정상 경로, 원본 누락, YAML 오류/중복키/이름 불일치/비JSON 값, 파일 수·크기·Skill총량·archive 추정 상한. 바이너리 round-trip, memory snapshot 일관성, 재시작 revision 변경 검증.
- 실제 root `npm pack --dry-run --json`: 29 files, tools/·plugins/·node_modules/ 모두 제외. 전체 tests에 임시 tarball npx init/doctor/static eval 및 제외 assertions 포함. npm publish 없음.
- Inspector `@modelcontextprotocol/inspector@2.7.0 --cli /opt/homebrew/bin/node <absolute server.mjs>`: `--method tools/list`, `tools/call --tool-name ownhands_status`, `resources/read --uri skill://ownhands/plan-design/SKILL.md`, `skills/list`, `skills/get --uri skill://ownhands/eli5/SKILL.md` 모두 exit0. custom Skill 메서드도 이 Inspector에서 지원됨을 실제 관측.
- Inspector install은 deprecated server-legacy 전이 의존성 경고를 출력했다. provider는 stdio만 사용하며 own provider npm install audit은 0 vulnerabilities. 이를 Inspector 전체 보안 감사로 확대하지 않는다.
- status content revision: `sha256:92a723245ba11d628b1272b149db75faea3e6b4c08b162ef2495b99e28988937`. Git revision이 아니다.
- 저장소 static Eval exit0: EVAL-0004 PASS; runtime EVAL-0001/2/3/5 UNOBSERVED; regressionsCount0. 기존 baseline 갱신 없음.
- `git diff --check` exit0. root package/bin/.agents/.codex/scripts/baselines/canonical Skills/기존 Chat Spec 변경 없음. user HTML untouched.
- `which node`: /opt/homebrew/bin/node; `pwd`: /Users/parktaejung/Desktop/workspace/OwnHands. README의 absolute `--mcp-command`와 동일한 경로로 실제 subprocess와 Inspector를 실행함.

### AC evidence mapping (독립 Verifier 감사 완료)

| AC | Verdict | Evidence |
|---|---|---|
| 01 | PASS | 실제 stdio initialize identity/instructions/extensions assertions |
| 02 | PASS | 실제 status list/call 및 annotation/hash 검사, Inspector 교차 확인 |
| 03–05 | PASS | 실제 전체 catalog/get/read bytes·digest 비교; Inspector skills/list/get/read |
| 06–07 | PASS | 경로/링크/URI/인자 및 startup 실패/제한 fixture 검증 |
| 08 | PASS | 실행 중 bytes 변경에도 기존 응답 불변, 새 subprocess에 수정 반영 |
| 09 | PASS | Tool allowlist/unknown method 거부, stdout 파싱/startup failure 검사 |
| 10 | PASS | pack 29 files 및 격리 tarball init/doctor/static eval |
| 11 | PASS | 공식 Inspector 2.7.0의 실제 subprocess discovery/call/read |
| 12 | PASS | 실제 absolute 경로 기반 실행 + 저장소 밖 profile 명령 준비; tunnel-client runtime은 미실행 |
| 13–14 | UNOBSERVED | 사용자 Tunnel/Plugin 연결 전. 실제 일반 Chat Skill 노출/E2E 미실행 |

Overall: UNOBSERVED. 로컬 구현/검증 범위와 실제 Chat 적용 성공은 별개다.

### 독립 감사와 현재 완료 상태

- 독립 Verifier는 구현·테스트·위 증거와 공식 계약을 대조해 AC01–12 PASS, AC13–14 UNOBSERVED, Overall UNOBSERVED를 확인했다. blocking correctness/security 결함은 발견하지 못했다. 광범위 테스트를 중복 실행하지 않았다.
- Verifier 선택: gpt-6-astra / high, filesystem 경계 감사에 따른 escalation. 실제 실행 모델·effort는 UNOBSERVED.
- 문서 지적: root `npm test`가 provider 테스트도 탐색하므로 fresh checkout의 자체 검사 안내에 provider 의존성 설치가 필요했다. 루트 README에 `npm ci --prefix tools/ownhands-skill-provider --ignore-scripts`를 추가했다. 런타임 변경 없이 기존 provider 안내와 일치시켰다.
- 보안 검증 범위는 신뢰된 로컬 checkout의 정적 파일 구조와 원격 URI 요청 경계다. 동시 로컬 ancestor 교체 공격 방어를 검증했다고 주장하지 않는다.
- MCP provider implementation: DONE
- Local MCP initialize / ownhands_status / skills/list / skills/get / resources/read: PASS
- Tunnel configuration command: READY
- Tunnel runtime / ChatGPT Plugin connection: USER ACTION REQUIRED
- plan-design Chat visibility / Chat E2E: UNOBSERVED
- Commit / Push / PR / Merge / npm publish / Plugin publish: NOT DONE
- 외부 Git Review Gate는 실행하지 않았다. 로컬 독립 Verifier 결과는 외부 Git 승인이나 Review Gate 통과를 뜻하지 않는다.

## 외부 Git 승인 — 2026-09-23

- 사용자는 로컬 검증 완료와 Tunnel/Plugin 연결 USER ACTION REQUIRED, Chat visibility/E2E 및 Overall UNOBSERVED 보고를 받은 뒤 “커밋 푸시 PR까지 다 진행해”라고 명시적으로 승인했다.
- 이번 Commit 및 Push+PR에 한해 미관측 상태를 유지하고 진행한다. 누락 증거는 실제 사용자 Tunnel/웹 연결과 일반 Chat Skill E2E이며, 연결 후 import·노출이 지원되지 않을 가능성은 여전히 남는다. 이 승인은 Merge·게시나 AC PASS 승격을 포함하지 않는다.
- 대상은 feat/plugin-tunnel-connect → develop. 사용자 소유 docs/explain-m7-closed-loop.html은 포함하지 않는다.
- 위 NOT DONE 및 Review 미실행 표기는 로컬 구현 종료 시점의 이력이다. 이후 실제 Commit/Push/PR 결과는 Git/PR과 완료 응답으로 확인한다.

## Review Results

- agent_role: reviewer
- requested_model: gpt-6-astra
- requested_reasoning_effort: high
- selection_basis: default
- actual_model: UNOBSERVED
- actual_reasoning_effort: UNOBSERVED
- 독립 initial diff Review에서 F-01 한 건을 확인하고 해결했다. 최종 fingerprint 확인과 로컬 Evidence는 Git 내부에 별도 기록하며, 기록 전에는 Gate PASS로 취급하지 않는다.

### Finding `F-01`
- **Status**: accepted
- **Resolution**: resolved
- **Reviewer claim**: provider의 Node >=18 선언이 lockfile의 @hono/node-server >=20 요구와 불일치한다.
- **Reason**: provider package와 lockfile root engines 및 실행 안내를 >=20으로 정렬했다. 실제 검증 환경 Node26은 변경되지 않으며 Node20 runtime을 새로 검증했다고 주장하지 않는다.
- **Evidence**:
  - package.json, package-lock.json root, README의 최소 버전 >=20 일치. @hono/node-server 2.1.1의 engine >=20 확인.

Feedback triage: F-01은 이번 provider의 package metadata 결함으로 현재 diff에서 해결했다. 기록을 이 Review Results에 보존하고 별도 OwnHands process 개선 Issue는 만들지 않는다.

F-01 targeted evidence: Node v26.7.0에서 `npm install --prefix tools/ownhands-skill-provider --package-lock-only --ignore-scripts --engine-strict` exit0, 96 packages audited / 0 vulnerabilities. `git diff --check` PASS. 런타임 코드 변경이 없어 기존 68 tests 및 Inspector 증거를 유지한다.

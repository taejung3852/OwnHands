# Spec: OwnHands 0.0.1 공개 npm 배포

- **기반 Intent**: [`intent.md`](intent.md)
- **작성 주체**: Codex (사용자 검토·승인)
- **일자**: 2026-09-21
- **상태**: Approved — 사용자 확인 (2026-09-21)

## 1. 목표와 범위

`ownhands@0.0.1`은 Git 프로젝트에서 `npx --yes ownhands@0.0.1 init`으로 현재 OwnHands baseline을 연결하는 첫 공개 실험판이다. 설치 결과에는 Skill·Agent·routing뿐 아니라 Review Hook/Gate와 소비자 프로젝트용 Continuous Eval이 함께 있어야 한다.

이번 배포는 설치 가능성과 설치 자산의 무결성을 확립한다. Codex가 Hook을 신뢰·재로딩했는지, Runtime Eval이 실제로 어떤 결과를 냈는지, M7 Closed Loop가 실사용에서 완주했는지는 별도 관측이며 배포 성공으로 대신하지 않는다.

## 2. 공개 CLI 계약

- `REQ-01`: package 이름은 `ownhands`, 버전은 `0.0.1`, 라이선스는 MIT, Node.js 요구 버전은 18 이상이며 runtime dependency는 추가하지 않는다.
- `REQ-02`: 공개 명령은 기존 `init`, `doctor`, `--help`, `--version`에 `eval`을 추가한다.
- `REQ-03`: `npx ownhands init`은 설치만 수행한다. Hook 신뢰 승인, Codex 재시작, Runtime Eval, Git commit·push는 자동 수행하지 않는다.
- `REQ-04`: `npx ownhands eval`은 명시적으로 호출됐을 때만 소비자용 Eval Runner를 실행한다. 최소한 `--static-only`, `--task <id>`, `--json` 전달을 지원하며 baseline 갱신은 `0.0.1` 공개 CLI에서 지원하지 않는다.
- `REQ-05`: `init` 이전의 `eval`은 설치 자산 부재를 명확히 알리고 non-zero로 종료한다. 알 수 없는 명령·옵션도 사용법과 함께 non-zero로 종료한다.

## 3. 설치 자산과 경로

- `REQ-06`: 기존 7개 Skill과 references, 세 read-only Agent와 model policy, AGENTS routing block, `.codex/hooks.json`, `scripts/review-gate.js`를 계속 설치한다.
- `REQ-07`: 소비자용 Eval Runner·Task Set·Baseline은 `.ownhands/evals/` 아래에 설치하고 installation manifest의 asset hash 대상에 포함한다.
- `REQ-08`: 소비자용 Task Set은 설치된 Skill·Agent·Hook/Gate만 참조한다. OwnHands 저장소 내부의 ADR, 개발 Spec, Research 문서를 통과 조건으로 요구하지 않는다.
- `REQ-09`: 소비자용 Eval은 현재 Agent System의 routing·agent contract·review gate·핵심 Skill 연결을 검사한다. 사용 프로젝트 자체의 test·lint·build를 대신하지 않는다.
- `REQ-10`: `doctor`는 Eval Runner·Task Set·Baseline의 존재와 manifest hash를 읽기 전용으로 검사한다. Eval을 실행하거나 baseline을 변경하지 않는다.

### 설치 후 최소 구조

```text
.agents/skills/...
.codex/agents/...
.codex/hooks.json
scripts/review-gate.js
.ownhands/
├── installation.json
└── evals/
    ├── run-evals.js
    ├── task-set.json
    └── baseline.json
```

## 4. 설치 안전성

- `REQ-11`: 기존 `init`의 Git root 제한, 전체 preflight, symlink·경로 이탈 차단, content conflict 시 무변경 종료, 임시 파일+rename 쓰기를 유지한다.
- `REQ-12`: 기존 `AGENTS.md`와 `.codex/hooks.json`은 OwnHands 영역만 병합한다. 사용자 설정과 다른 Hook entry를 보존한다.
- `REQ-13`: 동일한 `0.0.1` 설치는 멱등이어야 한다. 다른 revision 또는 수정된 owned asset을 발견하면 update/migrate를 추측하지 않고 중단한다.
- `REQ-14`: `.ownhands/installation.json`은 schema version, package name/version, source repository/revision, 모든 owned asset hash, routing·Hook integration hash를 기록한다.

## 5. 소비자용 Eval 계약

- `REQ-15`: 공개 Eval은 선언형 Task Set을 Source of Truth로 사용하고 `PASS`, `FAIL`, `UNOBSERVED`를 구분한다.
- `REQ-16`: `--static-only`는 Runtime을 실행하지 않으며 Runtime 대상 결과를 `UNOBSERVED`로 표시한다. 이 생략을 Runtime PASS로 표현하지 않는다.
- `REQ-17`: Runtime 실행은 설치된 프로젝트를 작업 디렉터리로 사용하며 명시된 sandbox·side-effect 정책을 따른다. 외부 GitHub resource를 생성하거나 repository를 수정하지 않는다.
- `REQ-18`: shipped baseline은 `0.0.1`에서 검증한 소비자용 Task Set과 같은 task ID·계약에 대응한다. 내부 개발용 `docs/evals/` baseline과 혼용하지 않는다.
- `REQ-19`: 공개 CLI를 통한 baseline 변경은 금지한다. 다음 package version의 baseline은 OwnHands source에서 review 후 함께 배포한다.

## 6. Release와 추적성

- `REQ-20`: `package.json`의 version은 `0.0.1`, license는 `MIT`, source revision은 release identity와 일치시킨다. repository에는 MIT `LICENSE`를 둔다.
- `REQ-21`: publish 후보는 `npm pack --dry-run` allowlist와 로컬 tarball E2E를 먼저 통과해야 한다. tarball 파일 목록에 비밀값, 작업 로그, 내부 임시 산출물을 포함하지 않는다.
- `REQ-22`: npm publish는 현재 인증 계정·registry·package/version·tarball 내용을 보여준 뒤 별도 Publish Gate에서 수행한다. 인증 실패, 2FA 요구, 이름 선점, 동일 버전 존재 시 우회 package명이나 version을 임의 선택하지 않고 중단한다.
- `REQ-23`: registry가 `ownhands@0.0.1`을 반환한 뒤 깨끗한 임시 Git 저장소에서 registry 기반 `init`, `doctor`, `eval --static-only`를 확인한다.
- `REQ-24`: registry 검증 성공 뒤 동일 source commit에 annotated tag `v0.0.1`을 만들고 GitHub Release `OwnHands 0.0.1`을 생성한다. npm package, tag, Release의 commit 연결을 Release notes에 남긴다.
- `REQ-25`: npm publish, Git tag push, GitHub Release 생성은 각각 관측 가능한 외부 상태 변경이다. 하나의 성공을 다른 단계의 성공으로 간주하지 않는다.

## 7. 장애와 경계 처리

- package 이름이 publish 시점에 사용할 수 없으면 `FAIL`로 기록하고 사용자에게 새 이름 결정을 요청한다.
- npm 인증 또는 2FA가 완료되지 않으면 publish 이전 상태를 유지하고 사용자 인증을 기다린다.
- publish 응답이 불명확하면 registry에서 정확한 `name@version`을 조회하기 전 재게시하지 않는다.
- registry E2E가 실패하면 tag와 GitHub Release를 만들지 않는다. npm version은 삭제·덮어쓸 수 있다고 가정하지 않고 원인을 기록한다.
- tag가 이미 다른 commit을 가리키거나 Release가 이미 존재하면 덮어쓰지 않고 중단한다.
- Hook trust/reload 또는 Runtime Eval이 관측되지 않으면 `UNOBSERVED`로 남긴다. release notes에서 이를 PASS로 표현하지 않는다.

## 8. 수용 기준

- `AC-01`: `package.json`과 `LICENSE`가 `ownhands@0.0.1`, MIT, Node 18+, runtime dependency 0개 계약과 일치한다.
- `AC-02`: clean Git fixture에서 로컬 tarball의 `init`이 Skill·Agent·routing·Hook/Gate·소비자 Eval 세트를 설치하고 manifest가 모든 owned asset hash를 포함한다.
- `AC-03`: 같은 fixture의 `doctor`가 healthy 설치만 exit 0으로 판정하고 Eval asset 누락·변조도 exit 1로 판정한다.
- `AC-04`: 기존 AGENTS/Hook 보존, 동일 재실행 멱등성, content conflict·symlink·malformed input의 write-before-fail 방지가 기존 회귀 테스트와 함께 통과한다.
- `AC-05`: `npx ownhands eval --static-only`가 소비자용 Task Set을 읽고 내부 ADR/Spec 없이 정적 검사를 완료하며 Runtime 항목은 정직하게 `UNOBSERVED`로 표시한다.
- `AC-06`: 단일 task와 JSON 출력이 공개 Eval CLI에서 동작하고, baseline 갱신 요청과 알 수 없는 옵션은 거부된다.
- `AC-07`: `npm pack --dry-run` 파일 목록이 allowlist 안에 있고 민감 정보·테스트 로그·내부 임시 산출물을 포함하지 않는다.
- `AC-08`: 관련 `node:test`, 내부 `node scripts/run-evals.js --static-only`, `git diff --check`가 통과한다.
- `AC-09`: registry에서 `npm view ownhands@0.0.1`을 확인하고 fresh temp Git fixture의 registry 기반 `init`, `doctor`, `eval --static-only`가 성공한다.
- `AC-10`: published package의 source commit과 `v0.0.1` tag 및 GitHub Release target이 동일하다.
- `AC-11`: Release notes가 Established, Verified, `UNOBSERVED`, Known limitations를 구분하며 Hook runtime이나 실제 Runtime Eval을 과장하지 않는다.

## 9. 추적성

| Intent 요소 | Spec 요구사항 | 수용 기준 |
|---|---|---|
| 공개 `0.0.1` 설치 | REQ-01~05, REQ-20~25 | AC-01, AC-06, AC-09~11 |
| 현재 baseline 전체 전달 | REQ-06~10, REQ-15~19 | AC-02, AC-03, AC-05 |
| 기존 프로젝트 보호 | REQ-11~14 | AC-02~04 |
| 관측 경계의 정직성 | REQ-03, REQ-16~19, REQ-23~25 | AC-05, AC-09~11 |

## 10. 검증 경계

로컬 tarball 검증은 npm registry 배포 성공의 증거가 아니다. registry E2E는 Hook trust/reload 또는 유료 Runtime Eval 실행 성공의 증거가 아니다. 실제 Runtime Eval과 첫 M7 Closed Loop 운영은 이번 release의 후속 `UNOBSERVED` 범위로 남긴다.

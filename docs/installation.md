# OwnHands 설치 계약

OwnHands의 Codex bootstrap 진입점은 `npx ownhands`다. Chat Plugin은 별도 배포 표면이다. 이 CLI는 새 Runtime이 아니라 프로젝트에 Codex native 자산을 연결하고 상태를 확인하는 얇은 bootstrap이다.

## 전제조건

- Node.js 18 이상
- Git 저장소
- 명령을 실행할 프로젝트에 대한 파일 쓰기 권한

## 설치와 확인

아래 `ownhands@0.0.1` 명령은 기존 공개 릴리스 설치 예시이며 대상 프로젝트 안에서 실행한다. 이 문서의 새 6개 Skill 구성은 아직 게시하지 않은 현재 Branch의 로컬 패키지 기준이다. 공개 0.0.1 설치로 이번 변경이 적용된다고 해석하지 않는다.

```bash
npx --yes ownhands@0.0.1 init
npx --yes ownhands@0.0.1 doctor
npx --yes ownhands@0.0.1 eval --static-only
```

현재 Branch를 확인하려면 OwnHands checkout에서 `npm pack --pack-destination <임시 디렉터리>`로 만든 tarball을 사용한다. 별도 임시 Git 프로젝트에서 `npx --yes --package <tarball의 절대경로> ownhands init`을 실행하고 같은 `--package`로 `doctor`, `eval --static-only`를 확인한다. 기존 공개 패키지와 버전 문자열이 같으므로 검증 시 tarball 출처를 함께 기록한다.

현재 Branch의 `init`은 Git 저장소의 top-level을 찾고 다음 자산을 연결한다.

- `.agents/skills/`의 OwnHands Skills와 References 6개
- `.codex/agents/`의 researcher, verifier, reviewer와 model policy
- `scripts/review-gate.js`
- `.codex/hooks.json`의 OwnHands `PreToolUse` entry
- `AGENTS.md`의 `<!-- ownhands:start -->` / `<!-- ownhands:end -->` routing block
- `.ownhands/installation.json`의 package/revision, 설치 asset 경로, SHA-256 provenance
- `.ownhands/evals/`의 소비자용 Runner·Task Set·read-only baseline

CLI는 외부 Skills installer를 연쇄 호출하지 않고 runtime dependency도 설치하지 않는다. Plugin, 별도 daemon, OwnHands Runtime을 만들거나 실행하지 않는다.

Codex Plugin은 Skills·Hooks의 향후 bundle 후보지만 이번 설치 방식에는 사용하지 않는다. project-local agent와 `AGENTS.md` 병합, Hook script 배포와 trust 경계는 별도로 남아 현재 bootstrap보다 단순해지지 않기 때문이다.

`init`은 Hook을 신뢰시키거나 Runtime Eval을 실행하지 않는다. 이 두 동작은 설치와 분리된 명시적 관측이다.

## Eval 실행

비용 없는 설치 계약 검사만 실행한다.

```bash
npx --yes ownhands@0.0.1 eval --static-only
```

단일 항목이나 기계 판독 출력을 선택할 수 있다.

```bash
npx --yes ownhands@0.0.1 eval --static-only --task INSTALL-0004
npx --yes ownhands@0.0.1 eval --static-only --json
```

옵션 없는 `eval`은 Codex Runtime 항목까지 명시적으로 실행하므로 시간과 사용량이 들 수 있다. `--static-only`에서 생략된 Runtime 항목은 `UNOBSERVED`이며 PASS로 간주하지 않는다. baseline은 package가 제공하는 read-only 비교 기준이고 설치 프로젝트에서 갱신하지 않는다. 이 Eval은 OwnHands Agent System을 확인하며 프로젝트 자체의 test·lint·build를 대신하지 않는다.

## 병합과 충돌 규칙

`init`은 먼저 모든 대상을 검사하고 충돌이 있으면 쓰기 전에 종료한다.

- 없는 OwnHands-owned 파일만 복사한다.
- byte-identical 파일과 동일한 Hook/routing block은 멱등 성공한다.
- 다른 내용의 owned file, symlink가 포함된 대상 경로, 변조된 OwnHands block/Hook은 overwrite하지 않는다.
- 기존 valid `.codex/hooks.json`의 다른 key와 Hook은 보존하고 OwnHands entry만 한 번 추가한다.
- 기존 `AGENTS.md`의 사용자 내용은 보존하고 OwnHands marker block만 추가한다.
- malformed `.codex/hooks.json`은 자동 수리하지 않는다.
- 다른 revision의 manifest가 있으면 update로 추정하지 않고 중단한다. update/migrate는 아직 지원하지 않는다.

각 파일은 preflight 후 같은 디렉터리의 임시 파일에서 rename하는 방식으로 쓴다. 별도 rollback engine은 없다.

## `doctor`가 확인하는 것

`doctor`는 파일을 변경하지 않는다. 정상은 exit 0, 누락·충돌·drift는 exit 1이다.

- 실행 중인 패키지가 제공하는 Skills와 각 Reference의 설치 hash (현재 Branch 로컬 패키지: 6개)
- 세 agent 정의의 package hash, 필수 필드, `sandbox_mode = "read-only"`, model pin 부재
- OwnHands Hook entry의 정확한 단일 연결
- Review Gate script와 manifest hash
- AGENTS routing block의 존재와 내용
- manifest에서 package version과 source revision 식별 가능 여부
- 소비자 Eval Runner·Task Set·Baseline의 존재와 hash

`doctor`는 Hook 설정의 존재를 확인할 뿐 Codex가 그 Hook을 신뢰·reload해 실제 실행했는지는 확인하지 않는다. 이 runtime 경계는 출력에서 `UNOBSERVED`로 표시한다.

## 안전한 수동 제거

자동 `uninstall` 명령은 없다. 제거할 때는 사용자 설정을 보존하기 위해 다음 소유 경계만 수동으로 다룬다.

1. `.ownhands/installation.json`의 asset path와 SHA-256을 읽는다.
2. 현재 hash가 manifest와 같은 owned file만 삭제한다. 다르면 사용자 변경일 수 있으므로 삭제하지 않고 먼저 검토한다.
3. `.codex/hooks.json`에서 `scripts/review-gate.js ... check-hook`을 호출하는 정확한 OwnHands entry 하나만 제거한다. 다른 Hook과 JSON key는 유지한다.
4. `AGENTS.md`에서 두 OwnHands marker와 그 사이 block만 제거한다. 나머지 문장은 유지한다.
5. 빈 OwnHands-owned 디렉터리와 `.ownhands/installation.json`만 정리한다.

이 절차는 update/migrate를 대신하지 않는다. 새 revision 설치가 필요하면 현재 설치의 소유 경계를 확인한 뒤 별도 승인된 절차로 처리한다.

## 제공하지 않는 기능

`init`, `doctor`, `eval`, 표준 `--help`/`--version` 이외 command는 없다. update, migrate, uninstall, GUI, daemon, 별도 Runtime은 이 bootstrap의 책임이 아니다.

## Chat Plugin과 설치 경계

`plugins/ownhands/`는 npm pack 및 init 대상이 아닙니다. plan-design과 Companion ELI5는 Plugin에만 포함되며 기존 grill-spec shim은 없습니다. 기존 설치를 자동 migration하거나 충돌 자산을 덮어쓰지 않습니다. 별도 업데이트 계약은 후속입니다. [Plugin 안내](../plugins/ownhands/README.md)의 플랫폼 차단과 AC UNOBSERVED를 참고하세요.

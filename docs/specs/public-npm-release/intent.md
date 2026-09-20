# Intent: OwnHands 0.0.1 공개 npm 배포

- **작성자**: 박태정 (@taejung3852) & Codex
- **일자**: 2026-09-21
- **상태**: Approved — 사용자 확인 (2026-09-21)

## 1. 문제 및 배경 (Why)

- OwnHands의 Skill·Agent·Review Hook과 bootstrap CLI는 구현되어 있지만, 패키지는 `0.0.0-development`이고 npm registry에 게시되지 않았다.
- 따라서 사용자는 다른 프로젝트에서 `npx ownhands init`을 실행할 수 없고, 로컬 tarball 경로를 직접 준비해야 한다.
- 현재 package 구성에는 Review Hook은 포함되지만 Continuous Eval Runner·Task Set·Baseline은 포함되지 않아, 공개 설치본이 OwnHands의 현재 baseline 전체를 전달하지 못한다.
- 대상 사용자는 Git 프로젝트에서 Codex와 OwnHands를 함께 사용하려는 개발자다.

## 2. 목표 결과 및 가치 (What)

> **Git 프로젝트에서 `npx ownhands init` 한 번으로 현재 OwnHands baseline을 안전하게 연결하고, 설치 상태를 `npx ownhands doctor`로 확인할 수 있는 첫 공개 실험판 `0.0.1`을 제공한다.**

### 목표

- npm의 공개 `ownhands@0.0.1` 패키지를 게시한다.
- 기본 설치에 7개 Skill, 3개 Agent와 모델 정책, AGENTS routing, Review Hook/Gate, Continuous Eval Runner·Task Set·Baseline을 포함한다.
- 기존 `AGENTS.md`와 `.codex/hooks.json`을 보존하며 OwnHands 영역만 병합한다.
- 충돌·symlink·다른 OwnHands revision을 발견하면 덮어쓰지 않고 쓰기 전에 중단한다.
- 설치 manifest에 package version, source revision, 설치 자산 hash를 남기고 `doctor`가 drift를 읽기 전용으로 검사한다.
- MIT License로 공개해 설치·사용·수정·재배포 권리를 명확히 한다.

### 성공 기준

- `npm view ownhands@0.0.1`에서 공개 패키지 metadata를 확인할 수 있다.
- 깨끗한 임시 Git 저장소에서 registry의 `npx --yes ownhands@0.0.1 init`과 `doctor`가 성공한다.
- 설치 결과에 Skill·Agent·Hook·Review Gate뿐 아니라 Eval Runner·Task Set·Baseline이 존재하고 package manifest hash에 포함된다.
- 기존 AGENTS/Hook 보존, 멱등 실행, 충돌 시 무변경 종료를 패키징된 tarball과 공개 registry package 양쪽에서 확인한다.
- 공개 package 내용과 Git tag/release의 commit을 연결할 수 있다.
- 관측하지 않은 Codex Hook trust/reload나 Runtime Eval 결과를 배포 성공으로 주장하지 않는다.

## 3. 비목표 (Non-goals & Boundaries)

- `init` 과정에서 비용과 시간이 드는 Runtime Eval 자동 실행
- Codex Hook 신뢰 승인·앱 재로딩을 자동화하거나 실제 실행을 거짓으로 보증
- `update`, `migrate`, `uninstall`, GUI, daemon, 별도 OwnHands Runtime 구현
- 기존 프로젝트 파일 또는 사용자 변경의 강제 덮어쓰기
- `0.0.1`에서 장기 호환성이나 안정 API를 약속
- npm 조직·유료 패키지·private registry·자동 publish CI 도입
- M7의 첫 실제 Feedback → Issue → Improvement → Adoption 운영 순환을 이번 배포만으로 완료 처리

## 4. 핵심 제약 조건 (Constraints)

- package 이름은 `ownhands`, 버전은 사용자 결정에 따라 `0.0.1`이다.
- 라이선스는 사용자 결정에 따라 MIT다.
- Node.js 18 이상과 Git 저장소를 전제로 하며 runtime dependency를 추가하지 않는다.
- Hook과 Eval 자산은 기본 설치에 포함하지만, Hook 활성화와 Runtime Eval 실행은 별도 관측·행동이다.
- Eval은 OwnHands Agent System을 측정하는 자산이며 사용 프로젝트의 native test를 대신하지 않는다.
- npm 로그인과 publish는 외부 상태 변경이다. package/test/review가 완료된 뒤 Publish Gate에서 현재 계정·버전·내용을 보여주고 실행한다.
- npm publish, Git tag, GitHub Release는 서로 다른 외부 상태다. 승인 범위를 임의로 승계하지 않는다.
- 우리의 설치·버전 정책은 OwnHands 결정이며 npm이나 Codex의 공식 요구로 표현하지 않는다.

## 5. Spec에서 정할 항목

- Eval 자산의 정확한 package/install 경로와 `doctor` 검사 범위
- package version과 source commit/tag를 manifest에 고정하는 release 절차
- tarball·registry E2E를 분리하는 검증 순서와 임시 프로젝트 fixture
- npm publish 실패, 이름 선점, 인증/2FA, 이미 존재하는 버전의 처리
- Git tag와 GitHub Release를 이번 `0.0.1` 배포에 포함할지 및 생성 순서

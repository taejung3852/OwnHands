# OwnHands Chat Plugin

이 디렉터리가 ChatGPT용 Skills-only Plugin의 기준본이다. 루트 `plugin.json`에 표시 이름과 로고 설정을 두고, `skills/plan-design/`과 `skills/eli5/`를 포함한다. `assets/ownhands.png`는 Plugin 표시 이미지다. Codex의 `npx ownhands` 배포와는 별개다.

## 확인된 범위

사용자 E2E 보고에 따르면 기존 ZIP을 ChatGPT 웹에 업로드했을 때 OwnHands, Plan & Design, ELI5가 노출됐고 두 Skill을 실제로 사용했다. 이 보고에서 plan-design의 대상 Repository 선택과 GitHub 저장 경로 질문 시점에 관한 Finding 두 개가 나왔다. 이번 지침 수정과 로컬 정적 검사는 새 ZIP의 Chat runtime 동작을 증명하지 않는다. 새 ZIP으로 동일 요청을 다시 실행해 확인해야 한다.

## 패키징

배포 ZIP에는 루트의 `plugin.json`, `skills/`, `assets/`만 넣는다. 루트 manifest의 `extensions.com.openai`가 표시 설정을 담으므로 호환용 `.codex-plugin/plugin.json`을 중복으로 넣지 않는다. README와 `.DS_Store`는 배포 내용이 아니다. MCP 서버, Tunnel, Hook, npm installer 자산도 포함하지 않는다.

## 로컬 검증

- `node --test tests/ownhands-plugin.test.js`: 구성, 링크, 브랜딩 자산, 정적 지침 계약을 확인한다.
- `node scripts/run-evals.js --static-only --task EVAL-0004`: Chat plan-design 정적 계약을 확인한다.
- `npm test`: 저장소 전체 회귀 테스트를 실행한다.

정적 검증 결과와 Chat runtime 판정은 별도로 기록한다. 사용자 승인과 GitHub 저장 규칙은 OwnHands의 제품 결정이며 플랫폼 공식 규칙으로 소개하지 않는다.

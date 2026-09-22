# OwnHands Chat Plugin

`skills/plan-design/` Core와 `skills/eli5/` Companion을 포함하는 Agent Plugins 1.0 Skills-only package입니다. 루트 plugin.json과 skills/가 배포 단위이며 자체 MCP 서버는 없습니다. plan-design은 Chat에서 명시적으로 선택해 사용하는 것이 목표입니다.

## 배포 경계

이 디렉터리는 npm package와 `ownhands init` 대상이 아닙니다. Codex에는 Build/Verify 등 기존 6개 Skill이 설치됩니다. ELI5의 별도 Codex/npm 설치·업데이트 계약은 후속입니다.

웹 일반 Chat의 Plugin Skill 기능 지원과 private 설치 가능성은 별개입니다. 현재 개인 계정 private Web Chat 직접 설치 경로는 확인되지 않았습니다. **Platform blocker: BLOCKED. 관련 미실행 AC: UNOBSERVED (platform-blocked).** 패키지 검증은 Chat picker, implicit activation, 승인 UX, GitHub write, 전체 E2E의 성공 증거가 아닙니다.

공식 로컬 Plugin 테스트 경로는 데스크톱 local marketplace입니다. 웹 private 배포는 사용 가능한 workspace 게시 경로와 관리 권한이 필요합니다. 공개 게시 또는 사용 가능한 workspace 게시 경로가 확보되면 실제 일반 Chat에서 명시 호출·일반 대화 비활성·Stage 승인/저장·Handoff E2E를 재개합니다. 개인 Skill 업로드나 Work 모드를 Chat E2E로 대체하지 않습니다.

## 검증

- `npm test`: 로컬 Skill 파일·참조·배포 격리 검사. runtime 증거가 아닙니다.
- `npm pack --dry-run --json`: Plugin과 plan-design/eli5가 npm에 포함되지 않는지 확인합니다.
- plugin.json은 아래 공식 JSON Schema로 표준 Draft 2020-12 validator에서 검증합니다. metadata YAML은 실제 YAML parser로 읽어 승인된 값을 확인합니다. 검증 도구는 임시 환경에서 사용하며 운영 의존성·CI 강제 장치를 추가하지 않습니다.
- 이번 실행 명령·결과와 AC 판정: [plan.md](../../docs/specs/chat-plan-design-flow/plan.md).

## 출처

- [Agent Plugins 1.0 schema](https://agent-plugins.org/schemas/1.0.0/plugin.schema.json)
- [OpenAI Plugin package](https://developers.openai.com/plugins/build/plugins)
- [Skill metadata validation](https://developers.openai.com/plugins/deploy/submission-errors)
- [Connect and test](https://developers.openai.com/plugins/deploy/connect-chatgpt)
- [Workspace plugin management](https://learn.chatgpt.com/docs/enterprise/plugin-management)
- [ELI5 원본·revision·라이선스](skills/eli5/UPSTREAM.md)

metadata는 정책 의도를 선언합니다. 현재 호스트의 실제 적용 범위는 관측 전까지 UNOBSERVED입니다. OwnHands 승인·저장·인계 규칙은 프로젝트 결정이며 플랫폼 공식 정책으로 주장하지 않습니다.

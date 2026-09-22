# Intent: Private Web Chat Skill 전달 준비

- 상태: Approved — 2026-09-23 사용자 요청과 실제 Plan Mode의 계획 승인에 근거한 기록.
- 목표: canonical plan-design/eli5를 읽기 전용 MCP provider와 Secure MCP Tunnel로 전달할 준비를 하고 실제 연결/노출 여부를 분리해 관측한다.
- 사용자: 개인 계정 ChatGPT 웹 일반 Chat에서 OwnHands 기획·설계를 사용하려는 사용자.
- 성공 기준: Mac 로컬 MCP 요청이 동작하고 canonical bytes·digest·파일 접근 경계가 검증되며 사용자가 실행 가능한 Tunnel 명령이 제공된다.
- Non-goals: Codex npx 경로 변경, Skill 복사·Tool 대체, GitHub/shell/write/Codex 실행 기능, daemon 관리, npm/Public Plugin 게시, Desktop marketplace, standalone Skill 업로드, Work 모드, main merge.
- Constraints: Tunnel/API key/웹 연결은 사용자가 처리한다. SDK를 provider에 격리하고 비밀정보를 저장소에 넣지 않는다. 로컬 resource 조회는 Chat E2E 증거가 아니다.

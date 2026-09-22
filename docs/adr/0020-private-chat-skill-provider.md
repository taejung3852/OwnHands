# ADR-0020: Private Web Chat을 위한 읽기 전용 Skill Provider

- 상태: Accepted — 2026-09-23 사용자 요청 및 구현 계획 승인. 실제 Chat 연결 성공을 뜻하지 않는다.
- 후속: [ADR-0012](0012-authoring-skills-via-ownhands-mcp.md)
- 계약: [Spec](../specs/plugin-tunnel-connect/spec.md)

## Context

기존 Skills-only package는 canonical 작성 지침을 제공하지만 개인 Web Chat private 설치 경로를 확인하지 못했다. 사용자는 Secure MCP Tunnel을 통한 최소 Skill 제공 adapter를 후속 작업으로 선택했다. 이는 기존 “이번 범위에 MCP 없음”에서 변경된 OwnHands의 전달 결정이다.

## Decision

Canonical source는 plugins/ownhands/skills의 plan-design/eli5다. 별도 tools/ownhands-skill-provider는 해당 bytes를 읽어 draft Skill extension과 resources로 제공하고 ownhands_status 하나로 연결을 진단한다. SDK 의존성은 provider package에 격리한다. Codex는 계속 npx ownhands 및 .agents/skills를 사용한다.

GitHub API/shell/write/Codex 실행 Tool, 임의 filesystem 접근, 자동 서비스 관리는 추가하지 않는다. Skill 노출 실패를 plan-design Tool로 우회하지 않는다. Desktop marketplace/standalone 업로드/Work는 이번 경로가 아니다.

## Consequences

Skill 원본을 복사하지 않고 startup memory snapshot의 실제 bytes로 digest를 만든다. 원본 변경은 server 재시작과 호스트 재import가 필요하다. OpenAI는 현재 SEP-2640의 제한된 static import를 submission 흐름으로 문서화한다. Secure MCP Tunnel의 private MCP 연결 지원과 개인 developer-mode Skill 노출 보장은 다르다. local PASS는 Chat E2E PASS가 아니다.

기존 ADR-0012와 Chat Plan & Design Spec의 과거 범위·검증 이력은 보존한다. 이번 ADR은 Skill 제공·진단에 한정하여 MCP adapter를 허용하며 나머지 책임·승인 계약을 변경하지 않는다.

## Sources

- https://developers.openai.com/plugins/build/mcp-server#import-skills-from-the-mcp-server
- https://developers.openai.com/api/docs/guides/secure-mcp-tunnels

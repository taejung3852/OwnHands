# OwnHands Skill Provider

canonical `plugins/ownhands/skills/plan-design`와 `eli5`를 읽는 private stdio MCP adapter입니다. Skill 파일 복사본, GitHub API, shell/write/Codex 실행 Tool, 자체 background service를 제공하지 않습니다. 유일한 Tool은 연결 진단용 `ownhands_status`입니다.

## 설치와 직접 실행

이 패키지의 의존성만 설치합니다. 루트 `npx ownhands`는 계속 Codex 자산을 설치하며 이 provider나 Plugin을 포함하지 않습니다.

```sh
cd /Users/parktaejung/Desktop/workspace/OwnHands
npm ci --prefix tools/ownhands-skill-provider --ignore-scripts
/opt/homebrew/bin/node /Users/parktaejung/Desktop/workspace/OwnHands/tools/ownhands-skill-provider/server.mjs
```

직접 실행하면 stdio MCP 입력을 기다립니다. stdout에 시작 배너를 출력하지 않는 것이 정상입니다. 터미널에서는 Ctrl+C로 종료합니다. provider Node 요구사항은 >=20, 아래 Inspector 2.7.0은 >=22.19.0입니다. 이번 Mac 관측은 Darwin arm64 / Node v26.7.0입니다.

```sh
npm test --prefix tools/ownhands-skill-provider
# 저장소 전체 검사는 위 npm ci가 먼저 필요합니다.
npm test
npx --yes @modelcontextprotocol/inspector@2.7.0 --cli /opt/homebrew/bin/node /Users/parktaejung/Desktop/workspace/OwnHands/tools/ownhands-skill-provider/server.mjs --method tools/list
npx --yes @modelcontextprotocol/inspector@2.7.0 --cli /opt/homebrew/bin/node /Users/parktaejung/Desktop/workspace/OwnHands/tools/ownhands-skill-provider/server.mjs --method tools/call --tool-name ownhands_status
npx --yes @modelcontextprotocol/inspector@2.7.0 --cli /opt/homebrew/bin/node /Users/parktaejung/Desktop/workspace/OwnHands/tools/ownhands-skill-provider/server.mjs --method resources/read --uri skill://ownhands/plan-design/SKILL.md
```

## 제공 계약

- `initialize`: tools/resources 및 `capabilities.extensions["io.modelcontextprotocol/skills"]`.
- `skills/list({})`: 두 Skill의 전체 YAML frontmatter, SKILL.md URI, supporting files와 실제 bytes의 SHA256. 한 페이지이므로 nextCursor 없음. 임의 cursor는 거부합니다.
- `skills/get({uri})`: catalog와 동일한 항목.
- `resources/list`, `resources/read({uri})`: 등록 URI만 반환. read는 URI가 일치하는 content 하나.
- `ownhands_status`: status, skills, revision. **revision은 제공 콘텐츠 hash이며 Git SHA가 아닙니다.**

시작 시 원본을 메모리에 읽고 digest/catalog/read를 같은 snapshot으로 제공합니다. 원본 변경 후 서버 재시작이 필요합니다. 호스트에 이미 import된 Skill은 별도 재import가 필요하며 그 지원 경로는 호스트에서 확인해야 합니다.

요청 URI를 filesystem 경로로 바꾸지 않습니다. 고정된 두 Skill 아래의 일반 파일만 읽으며 symlink와 경계 이탈, 정규화 충돌을 거부합니다. portable 경로 구성요소는 ASCII 영숫자로 시작하는 영숫자·점·하이픈·밑줄만 허용합니다. 숨김/특수 경로를 조용히 생략하지 않고 시작을 거부합니다. canonical checkout은 사용자가 신뢰하는 로컬 코드와 파일이어야 합니다.

import 제한은 OpenAI의 현재 bounded subset을 따릅니다. Skill당 100 files, SKILL.md 256KiB, supporting file 1MiB, Skill 총5MiB, archive 총8MiB입니다. 마지막 제한은 raw bytes의 1%와 파일별 header/path 여유를 추가한 보수적 추정으로 검사하므로 경계 근처 파일은 먼저 거부될 수 있습니다. archive 자체를 생성하지 않습니다.

## Tunnel 설정 — 사용자 수행

Platform에서 Tunnel 생성·workspace 연결·runtime API key 준비는 사용자가 합니다. provider는 API key를 읽지 않습니다. tunnel-client는 별도 프로그램이며 이 작업에서 자동 설치하거나 daemon으로 등록하지 않습니다.

[공식 최신 다운로드](https://github.com/openai/tunnel-client/releases/latest) 또는 Platform 안내로 설치한 뒤 `tunnel-client help quickstart`를 확인하세요. API key는 저장소 밖의 터미널 환경에 `CONTROL_PLANE_API_KEY`로 설정하고 출력·커밋하지 마세요. 아래는 zsh 기준이며 Tunnel ID도 저장소 파일에 쓰지 않습니다.

```sh
mkdir -p "$HOME/.config/ownhands-tunnel"
cd "$HOME/.config/ownhands-tunnel"
read "OWNHANDS_TUNNEL_ID?Tunnel ID: "
# CONTROL_PLANE_API_KEY는 사용자가 이 터미널 환경에 비공개로 설정해 둡니다.
tunnel-client init \
  --sample sample_mcp_stdio_local \
  --profile ownhands-private \
  --tunnel-id "$OWNHANDS_TUNNEL_ID" \
  --mcp-command "/opt/homebrew/bin/node /Users/parktaejung/Desktop/workspace/OwnHands/tools/ownhands-skill-provider/server.mjs"
tunnel-client doctor --profile ownhands-private --explain
tunnel-client run --profile ownhands-private
```

별도 Web UI 작업: ChatGPT Plugins → 개발자 Plugin 생성 → Connection: Tunnel → 사용자 Tunnel 선택. 실행 중인 tunnel-client가 있어야 discovery/call이 가능합니다. 경로는 이번 Mac의 `which node` 및 `pwd`를 기준으로 했으며 저장소를 옮기면 갱신하세요. Tunnel profile·ID·key를 OwnHands repository에 저장하지 마세요.

## 연결 결과 구분

A. status도 안 보임: Tunnel/MCP discovery·workspace association·권한·client 상태를 확인합니다.

B. status가 보이고 호출도 성공하지만 plan-design은 안 보임: Tunnel/MCP는 관측된 범위에서 PASS, Skill import/노출은 별도 미확인입니다. 단순 미노출만으로 공식 미지원이라고 단정하지 않습니다. 원인을 조사하며 plan-design을 Tool로 대체하지 않습니다.

C. 일반 Chat에서 Skill이 노출되면 실제 Intent → ELI5 → Content Approval → Persistence Approval → GitHub Stage commit → Spec → ELI5 → Content Approval → Persistence Approval → GitHub Stage commit → Handoff를 관측합니다. GitHub 저장은 별도 승인된 연결 도구의 역할입니다.

이 Skill extension은 안정 MCP 표준이 아닌 draft SEP-2640의 제한된 static subset입니다. 공식 문서의 Skill import는 submission의 Scan Tools snapshot입니다. Secure MCP Tunnel의 private MCP 지원이 개인 developer-mode Skill import를 보장하지 않습니다. Desktop local marketplace, standalone Skill 업로드, Work 모드, public 게시로 이번 테스트를 대체하지 않습니다.

로컬 검사·resource 조회·시뮬레이션은 Chat E2E PASS가 아닙니다. Tunnel·Plugin 연결은 사용자 작업 전 USER ACTION REQUIRED, Skill 노출과 E2E는 UNOBSERVED로 기록합니다.

- [OpenAI Skill import](https://developers.openai.com/plugins/build/mcp-server#import-skills-from-the-mcp-server)
- [Secure MCP Tunnel](https://developers.openai.com/api/docs/guides/secure-mcp-tunnels)
- [MCP Inspector](https://modelcontextprotocol.io/docs/tools/inspector)
- [Spec / AC](../../docs/specs/plugin-tunnel-connect/spec.md)
- [실행·검증 기록](../../docs/specs/plugin-tunnel-connect/plan.md)

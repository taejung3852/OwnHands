# Spec: 최소 MCP Skill Provider

- 기반 Intent: [intent.md](intent.md)
- 상태: Approved — 2026-09-23 승인된 사용자 구현 계획을 계약으로 보존.
- 결정: [ADR-0020](../../adr/0020-private-chat-skill-provider.md). 기존 Chat Plan & Design Spec은 역사로 보존한다.

## 구현 계약

`tools/ownhands-skill-provider/`의 Node ESM stdio server. 공식 SDK·Zod·yaml 의존성과 lockfile을 이 디렉터리에만 둔다. server identity `ownhands-skill-provider`, version `0.1.0`. Instructions: `Provides the canonical OwnHands plan-design and ELI5 skill resources. It does not provide GitHub, shell, or repository mutation tools.`

원본은 `plugins/ownhands/skills/`의 plan-design과 eli5. 시작 시 모든 supporting file을 안전하게 읽어 메모리 snapshot을 만든다. disk 복사본/파일 watcher는 없다. 변경 반영은 재시작 및 호스트 재import 필요. 이름·description을 포함한 전체 YAML frontmatter를 catalog에 담는다.

URI `skill://ownhands/<skill-name>/<relative-path>` allowlist만 조회한다. symlink·경계 이탈·비정상/정규화 충돌 경로는 거부한다. 원본 누락·잘못된 frontmatter·import 제한 초과는 startup failure. UTF-8은 text, 이외는 base64 blob; 응답 bytes로 SHA256을 계산한다. catalog/read는 같은 snapshot을 사용한다.

initialize capabilities: tools, resources, extensions 아래 `io.modelcontextprotocol/skills: {}`. `skills/list({})`는 두 항목 한 페이지, nextCursor 없음. 발급하지 않은 cursor 거부. `skills/get({uri})`는 동일 항목. `resources/list`와 `resources/read({uri})`는 모든 catalog resource를 제공하며 read는 동일 URI의 content 하나를 반환한다. 알 수 없는 URI/Tool/method와 잘못된 인자는 protocol error로 처리한다.

유일한 Tool `ownhands_status`, title `OwnHands status`, description `Check whether the private OwnHands MCP skill provider is reachable and report the currently served skill names and revision. This tool is read-only.` 인자 없는 read-only 진단. annotations readOnlyHint=true, destructiveHint=false, idempotentHint=true, openWorldHint=false. 반환 status/skills/revision. revision은 URI와 resource digest의 정렬된 목록에서 계산한 콘텐츠 hash이며 Git SHA가 아니다. subprocess/network/write Tool은 없다.

OpenAI 현재 제한: Skill 최대5, catalog pages 최대10, Skill별100 files, SKILL.md 256KiB, supporting file 1MiB, Skill 총5MiB, scan archive 총8MiB(ZIP overhead 포함). provider는 두 Skill 한 페이지만 사용하고 archive 여유를 보수적으로 산정해 상한을 지킨다. draft SEP-2640의 bounded static subset이며 안정 MCP 표준/개인 developer-mode import 보장이 아니다.

## Acceptance Criteria

| AC | 기대 결과 |
|---|---|
| 01 | 공식 SDK stdio subprocess initialize 성공, identity/instructions/capabilities 일치 |
| 02 | tools/list에는 ownhands_status 하나, annotations와 call 결과·content revision 정확 |
| 03 | skills/list 두 canonical Skill, 전체 frontmatter/resources/digests, 잘못된 cursor 거부 |
| 04 | skills/get은 list와 같은 항목, 잘못된 URI 거부 |
| 05 | resources/list/read 전 항목의 canonical bytes·digest 일치, text/blob 처리 |
| 06 | traversal/인코딩 변형/외부 URI·symlink·경계 이탈 접근 거부 |
| 07 | 누락/잘못된 frontmatter/이름 불일치/파일 수·크기 제한 위반 시 안전한 startup failure |
| 08 | 변경 전 snapshot은 일관되고 재시작 후 수정 bytes와 revision 반영 |
| 09 | GitHub/shell/write/Codex Tool 부재, stdout은 protocol 전용, init/invalid requests 처리 |
| 10 | root npm pack에서 tools/provider·Plugin·새 의존성 제외, 기존 Codex 설치 검사 통과 |
| 11 | 공식 Inspector로 로컬 tools discovery/call 및 resource read 교차 확인 |
| 12 | 실제 Node/server 절대경로와 저장소 밖 profile 기반 Tunnel init/doctor/run 안내 준비 |
| 13 | 사용자 Tunnel·Plugin 실제 연결 관측 (사용자 작업 전 UNOBSERVED) |
| 14 | 일반 Chat plan-design 노출과 전체 승인·저장·Handoff E2E 관측 (미실행 UNOBSERVED) |

## 검증 경계

A: status 미노출 → discovery 조사. B: status discovery/call 성공, Skill 미노출 → transport 성공과 import 미관측 분리, Tool 대체 금지. C: Skill 노출 후 Intent→ELI5→내용승인→저장승인→GitHub Stage commit→Spec 동일 흐름→Handoff 관측. 테스트 시뮬레이션으로 13/14를 PASS로 승격하지 않는다.

## 공식 출처 (2026-09-23 확인)

- https://developers.openai.com/plugins/build/mcp-server#import-skills-from-the-mcp-server
- https://developers.openai.com/api/docs/guides/secure-mcp-tunnels
- https://modelcontextprotocol.io/docs/tools/inspector

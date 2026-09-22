# ADR-0012: Skills-only Agent Plugin으로 Intent·Spec·ADR 작성 Skill을 제공한다

- 상태: Accepted — Chat Plan & Design Spec 사용자 승인 / 구현·런타임 검증 미진행
- 일자: 2026-09-22
- 관련: [#154](https://github.com/taejung3852/OwnHands/issues/154), 피드백 9-2와 후속 역할 정정
- 선행: [ADR-0011](0011-chat-codex-ownership-and-handoff.md)
- 확정 Spec: [Chat Plan & Design](../specs/chat-plan-design-flow/spec.md), REQ-01~06
- 변경 이력: 초기 MCP/Mac Mini 서버 전달안에서 Skills-only Agent Plugin으로 변경. 기존 파일명은 참조 호환성을 위해 유지한다.

## Context

기존 논의에서 OwnHands 전용 MCP를 GitHub 저장 기능의 중복으로 해석한 적이 있다. 사용자는 그 해석을 정정했다. 목적은 Git 파일 API 재구현이 아니라, ChatGPT에서 가이드라인에 맞춰 Intent·Spec·ADR을 작성하게 하는 Skill 제공이다.

GitHub의 파일 쓰기 도구가 있다는 사실만으로 GORE 인터뷰·설계 작성·ADR 판단 방법까지 제공되는 것은 아니다.

후속 Spec 논의에서 사용자는 같은 OwnHands 저장소의 Skills-only Plugin으로 작성 방법론을 제공하고, 이번 범위에서는 MCP 서버를 만들지 않기로 선택했다. 이는 작성 Skill 제공이라는 목적의 폐기가 아니라 전달 방식의 변경이다. Mac Mini 서버는 이번 구현의 전제가 아니다.

## 사용자 확정 방향

| 구성 | 책임 | 책임이 아닌 것 |
|---|---|---|
| `plan-design` Core Skill | GORE 인터뷰, Intent·Spec 작성, ADR 판단, 단계·승인·GitHub 활용·인계 조율 | GitHub API 자체 구현, Codex에서 구현 실행 |
| OwnHands Agent Plugin | 작성 Skill과 책임별 Reference, ELI5 Companion 제공 | 자체 MCP 서버·daemon·자율 기획 모델 운영 |
| GitHub 연결 도구 | 저장소·Issue·Branch·파일 조회 및 승인된 저장 작업 | OwnHands 작성 방법론의 대체 |
| ChatGPT | 제공된 Skill을 적용해 사용자와 기획·설계 논의 | 승인 없는 GitHub write·구현·외부 변경 |
| ELI5 Companion | Stage 내용 승인 직전 큰 그림과 구조 설명 | OwnHands Core 로직의 소유 |

### 원본과 배포 경계

- Agent Plugins 1.0 portable 형식의 Skills-only Plugin을 `plugins/ownhands/`에 둔다. 정확한 manifest 검증은 Spec 15절의 기술 확인 대상으로 남긴다.
- 기존 `.agents/skills/grill-spec/`은 shim 없이 교체하고, GORE·인터뷰·Fact/Decision·Checkpoint 규칙을 `plugins/ownhands/skills/plan-design/`으로 이전한다.
- `plan-design`의 canonical source는 Plugin 쪽 하나다. 상세 책임은 `references/`에 두고 `SKILL.md`는 흐름을 조율한다.
- `plugins/ownhands/` 및 `plan-design`은 npm package와 `npx ownhands init`의 Codex 설치 자산에 포함하지 않는다.
- `plan-design`은 Chat 전용·명시 호출 정책으로 `products: [CHAT]`, `allow_implicit_invocation: false`를 선언한다. 메타데이터만으로 실제 격리가 입증됐다고 하지 않는다.
- ELI5는 Chat/Codex 양쪽 사용을 목표로 한다. 이번에는 같은 Plugin의 Chat 승인 UX에 연결하며 Codex/npm 배포·업데이트 전체 계약은 [ADR-0018](0018-core-and-companion-skills.md) 후속 작업이다.
- ELI5 원본·revision·license 확인 없이 새 자체 Explain으로 몰래 대체하지 않는다.

## 대안과 선택 이유

- GitHub 도구만 사용: 저장 기능이 작성 방법론까지 대체하지는 못한다.
- 매 세션 긴 지침 복사: 재사용·일관성 관리 문제를 남긴다.
- OwnHands MCP + Mac Mini 서버: 초기 전달안이었다. 이번에는 서버 기능이 필요하지 않다는 사용자 결정으로 제외한다.
- Skills-only Agent Plugin + 기존 GitHub 연결 도구: 채택. 방법론 제공과 외부 쓰기 책임을 분리하면서 서버 운영 범위를 늘리지 않는다.
- `grill-spec`과 `plan-design` 병행: 기획 역할과 원본이 중복되므로 채택하지 않는다.

## 기술 검증과 경계

Spec의 사용자 결정과 플랫폼이 실제 제공하는 기능을 구분한다. Agent Plugins manifest/validator, Chat의 개별 Skill picker, 제품 노출·암시 호출 정책 적용, ELI5 원본·호스트 호환성은 확인해야 한다.

Plugin 파일 또는 정책 선언이 존재한다는 것만으로 Skill이 실제 로드됐거나 Codex에서 차단됐다고 주장하지 않는다. 설치·발견·호출·배포 격리는 실제 관측하고 미관측은 `UNOBSERVED`로 남긴다.

이번 결정에 `mcp.json`, 임의 Shell·전체 디스크·비밀 읽기 도구, 자체 GitHub API 구현을 추가하지 않는다. 이 문서 저장은 Plugin 설치·런타임 연결 성공이나 구현 완료 기록이 아니다.

## 수용 확인

Spec AC-01~11로 Plugin 형식, Chat 명시 호출, 일반 대화 비활성, `grill-spec` 교체와 npm/Codex 미포함을 확인한다. Stage 승인 시 실제 작성 규칙 및 ELI5가 사용됐는지도 별도로 관측한다.

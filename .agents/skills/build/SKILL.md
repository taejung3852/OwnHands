---
name: build
description: Use when implementing a clear user request or preparing and executing implementation from approved OwnHands specifications and plans.
---

# build

승인된 요청·설계를 구현 준비, 실행, Fresh Evidence, verify로 연결한다. Handoff와 Spec의 내용 승인은 구현 실행의 일괄 승인이 아니다. 현재 사용자 요청의 실행 권한을 확인한다.

## 진입과 경로 판단

1. 현재 요청, 존재하는 Intent/Spec/Plan, 승인 기록과 repository 상태를 읽는다. 승인된 중요한 제품 결정을 다시 인터뷰하지 않는다. 원격 기준 이후 변경과 사용자 작업을 보존한다.
2. 구현 판단 필요성과 위험을 기준으로 Light Flow / Planned Flow를 선택한다. 파일 개수 같은 단일 숫자 기준은 사용하지 않는다.
   - **Light Flow**: 변경 위치·기대 결과가 명확하고, 의미 있는 구현 대안과 새 제품/정책 결정이 없으며 실패 영향이 작다. Chat Plan & Design, spec.md, plan.md가 없어도 현재 요청에서 시작한다.
   - **Planned Flow**: 연결된 컴포넌트/인터페이스, 의미 있는 대안, 중요한 변경 순서·migration·상태 전이, 큰 Blast Radius, 추측해야 할 선택이 있다. 승인된 설계와 구현 계획을 확인한다.
3. 계획이 필요하고 아직 실제 Codex native Plan Mode가 아니면 안내한다: “Plan Mode로 전환해주세요. 현재 환경에서 필요한 전환 방법은 사용자에게 안내해주세요.” 현재 클라이언트에서 확인된 방법만 안내한다. 전환한 척하거나 일반 모드 계획을 native Plan Mode로 취급하지 않는다.
4. 실제 Plan Mode에서 구현 순서·Target Files·인터페이스·검증 방법을 정하고 사용자 승인을 받는다. 쓰기 가능한 모드가 된 뒤 승인 결과를 docs/specs/<feature-name>/plan.md에 Approved로 보존하고 구현으로 이어간다. 기존 승인 계획은 유효성만 확인하며 다시 작성·승인받게 하지 않는다. Plan Mode에서는 파일 저장 제한을 우회하지 않는다.

## 실행

- Light: 현재 요청에서 변경 범위와 기대 결과를 정하고 구현한 뒤 applicable checks와 diff를 verify에 전달한다. plan.md나 verification.md를 만들지 않는다.
- Planned: spec.md/plan.md의 링크·승인 기록·Target Files를 확인하고 다음 미완료 Task 하나와 연결된 AC를 선택한다. 실행 가능한 로직에 계획이 TDD를 지정하면 `references/tdd-loop.md`를 읽는다. 위임 이점이 명확할 때만 `references/subagent-routing.md`를 읽고, 그 외 직접 수행한다.
- Planned의 Task 구현과 실제 관측한 Fresh Evidence는 plan.md에 기록한다. 모든 구현 Task 후 verify로 인계한다. AC 최종 판정·Reviewer 호출·Review Evidence·Human Gate는 Build가 대신하지 않는다.

## 재평가와 중단

- Light에서 변경 반경 증가, 중요한 인터페이스, 요구 모호성, 고위험 데이터/권한/migration, deterministic check만으로 판단 불충분이 발견되면 구현을 멈추고 Planned로 승격한다.
- Spec 충돌이나 새 제품 결정은 사용자와 해결하고 필요한 설계·계획 승인을 받는다. 승인된 spec.md를 구현 편의상 자동 수정하지 않는다.
- Target Files 밖 변경이 필요하면 계획 범위를 먼저 정렬한다. 실패·미실행 증거는 FAIL / UNOBSERVED로 기록한다.
- 로컬 구현·계획 저장 권한은 Commit·Push·PR·Merge·Deploy 승인이 아니다. 기존 외부 Git Gate는 유지한다.

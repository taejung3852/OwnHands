# OwnHands

<!-- ownhands:start -->
우리의 결정을 플랫폼(공식)이 내린 결정인 것처럼 작성하지 않는다. 인용은 원문이 말한 내용에 한정하고, 우리가 좁히거나 넓힌 해석은 우리의 결정으로 명시한다. 검증되지 않은 것을 검증된 것처럼 제시하는 것은 우리 규칙을 공식 규칙으로 위장하는 것과 같은 실패다.

목표 지향 요구공학(GORE: Goal-Oriented Requirements Engineering)을 따른다: 구현 세부사항을 결정하기 전에 항상 최상위 목표와 사용자의 의도(Top-Down)에 요구사항, 설계, 서브에이전트 역할을 닻 내린다(anchor).

기획 및 설계(Plan & Design) 작업 시 `docs/specs/` 규약(`intent.md`, `spec.md`)을 따른다.

Build 작업은 `build` Skill을 사용한다. 명확하고 저위험인 요청은 Light Flow로, 구현 판단·위험이 있는 작업은 승인된 설계와 실제 Plan Mode의 승인 계획을 사용하는 Planned Flow로 진행한다. Chat 기획·설계는 별도 Plugin의 `plan-design`이 담당하며 npm 설치 자산에 포함하지 않는다.

검증이 완료되어 독립 Review가 필요하거나 외부 Git 결정을 앞둔 작업은 `review` Skill을 사용한다.

OwnHands 사용 중 사용자 교정·Eval 실패·Reviewer Finding을 관측하거나 작업·PR을 종료할 때 `feedback` Skill로 신호 기록과 선별을 수행한다.
<!-- ownhands:end -->

<!--
이 규칙이 존재하는 이유: 2026-09-17 세션에서 세 번 반복해서 수정되었음 —
`or`를 `and`로 바꾸고 "공식 문장을 그대로"라고 표기한 것, 공식에 없는 "수정 후 분할" 순서를 만든 것, 공식 문서가 말하지 않은 정책에 "공식 지침도 같은 방향"이라고 쓴 것.
근거 없는 규칙으로 보고 삭제하지 말 것. 이 규칙은 실제로 두 번 이상 반복 발생하여 추가됨.
-->

# ADR-0018: SDLC Core와 ELI5·Ponytail 등 범용 보조 Skill을 분리한다

- 상태: 사용자 분리·재사용 방향 확정 — 원본·버전·설치·업데이트 상세 미결정
- 일자: 2026-09-22
- 관련: [#154](https://github.com/taejung3852/OwnHands/issues/154), 피드백 9-1·13·14
- 조정 대상: [ADR-0002](0002-explain-visual-story-cards.md), [ADR-0003](0003-work-item-human-brief.md)

## Context

사용자는 explain과 write-issue-pr를 OwnHands의 전용 Core 기능으로 묶을 필요가 약하다고 느꼈다. Build 결과 설명에는 새 OwnHands Explain을 또 만드는 대신 범용 ELI5를, 구현 단순화에는 공개 Ponytail을 사용하고 싶다고 했다. 동시에 npx 설치에서 두 보조 Skill도 함께 제공되기를 원했다.

## 사용자 확정 방향

1. OwnHands Core는 기획·설계 규칙과 인계, Build, 독립 검증, Harness 개선 루프에 집중한다.
2. 범용 설명과 Issue/PR 작성 기능의 유용성을 부정하지 않지만, 이를 전용 Core로 재구현·복제할 이유와 배포 편의를 구분한다.
3. Build에서는 공개 Ponytail Skill을 사용하도록 연결하고, 결과를 설명할 때는 범용 ELI5를 활용한다.
4. `npx ownhands` 설치에서 ELI5·Ponytail도 제공하는 방향을 유지한다. 함께 설치된다는 사실은 Core 소유라는 뜻이 아니다.

## 원본과 출처

- Ponytail 원본 후보: [DietrichGebert/ponytail](https://github.com/DietrichGebert/ponytail), `skills/ponytail/SKILL.md`. 이번 기록은 사용자 요구와 앞선 원본 조회에 근거한다.
- ELI5는 사용자가 말한 범용 설명 Skill을 뜻한다. 확인 가능한 원본의 정확한 경로·revision·라이선스를 설치 구현 전에 확인한다. 원본이 없다는 추정만으로 새 전용 Explain을 만드는 것으로 바꾸지 않는다.
- 한 줄짜리 설명 프롬프트와 실제 HTML 파일 생성·저장·표시 계약이 동일하다고 가정하지 않는다. 필요한 호스트 연결을 구분한다.

## 적용 경계 제안

Ponytail의 단순화 지침은 승인된 목표·안전·검증을 삭제할 권한이 아니다. 기존 OwnHands 검증 요구와 충돌하면 원본을 몰래 바꾸지 않고 적용 강도·상위 계약을 정한다. 모든 코드 작업에 영구 강제할지, Build 중 어떤 범위에 활성화할지는 후속 설계 대상이다.

ELI5는 Build에서 실제로 구현한 범위와 미검증 부분을 시각적으로 설명한다. 설명 요청이 발생하는 시점과 자동 실행 여부를 명확히 하고, 설명 파일 생성이 마지막 검증 근거를 바꾸는 경우를 처리한다. 일반 대화마다 HTML을 강제한다는 결정은 아니다.

## 설치·갱신 상세 제안

- 보조 Skill의 원본 저장소·commit/tag·라이선스와 설치한 버전을 기록한다.
- 저장소를 기준으로 갱신할 수 있게 하는 것과 실행마다 최신 main을 자동 덮어쓰는 것을 구분한다.
- 기존 사용자 Skill·수정본을 무단 덮어쓰지 않고 이름·경로 충돌을 알린다.
- 다운로드 실패 시 어떤 부분이 설치됐는지 명확히 보고한다. 불완전한 설치를 정상으로 표시하지 않는다.
- 번들 포함, 설치 시 가져오기, 고정 revision, 업데이트 승인 방식은 후속 Spec에서 선택한다. 이번 ADR로 새 updater를 구현하지 않는다.

## 결과

방법론 소유권과 설치 편의가 분리된다. 대신 외부 원본의 변경·호환성·라이선스·가용성을 관리해야 한다. 보조 Skill이 효과를 냈다는 측정 없이 OwnHands의 단독 품질 효과로 합산하지 않는다.

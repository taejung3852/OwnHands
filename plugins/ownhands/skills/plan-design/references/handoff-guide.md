# Handoff 작성 계약

정상 경로에서 작업별 handoff.md를 만들지 않는다. Intent/Spec/ADR을 복제하는 manifest가 아니라 Codex를 올바른 출발점에 세우는 대화 안내다.

## Context

작업 목적, 현재 단계, 실제 완료/미완료, 사용자 승인 경계를 간결하게 적는다.

## Approved Sources

Repository, 실제 Branch, 승인된 Intent/Spec 및 관련 ADR 경로, 확인된 commit을 연결한다. 내용 승인과 저장 상태를 구분한다. 수동 산출물만 있으면 그 사실을 표시한다. 없는 식별자를 지어내지 않는다.

## Decisions

승인된 중요한 제품 결정과 비목표만 요약한다. 구현 Fact와 제품 결정을 구분한다.

## Open Questions

미결정 사항, 플랫폼 기술 확인, UNOBSERVED evidence를 적는다. 없음도 명시할 수 있다.

## Suggested Entry Point

승인 자료를 읽고 현재 원격/로컬 상태와 비교하여 기존 사용자 작업을 보존하며 구현 계획 필요성을 판단하도록 안내한다. 계획이 필요하면 “Plan Mode로 전환해주세요.”라고 안내한다. 특정 단축키를 고정하지 않고 현재 클라이언트 안내를 따르게 한다.

`Next Action`, `Do X`, 고정된 구현 명령은 기본 필드로 만들지 않는다. Handoff는 Build 시작이나 Commit·Push·PR·Merge를 일괄 승인하지 않는다. 수신자의 중요한 미결정 선택을 추측으로 채우지 않는다.

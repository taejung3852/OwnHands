---
name: feedback
description: Use when OwnHands usage produces a user correction, Eval failure, or Reviewer Finding, when an OwnHands task or PR is ending, or when explicitly invoked as $feedback. Not for generic product bug tracking.
---

# feedback

사용 프로젝트의 신호를 보존하고 OwnHands 개선 작업으로 연결한다. 신호는 확정된 OwnHands 결함이 아니며, Issue 등록은 개선 착수 승인이 아니다.

## 작업 절차

1. 현재 사용 프로젝트와 작업 범위, 관측한 신호를 확인한다. 세션 밖 로그를 상시 탐색하지 않는다. 신호가 없으면 파일·Issue를 만들지 않는다.
2. 기록·전달 전에 [feedback-contract.md](references/feedback-contract.md)를 읽고 필요한 모드를 수행한다.
   - **capture**: 사용자 교정·Eval 실패·Reviewer Finding의 기대/실제 행동, 근거와 버전을 프로젝트 Markdown에 기록한다. 같은 신호는 기존 기록에 추가한다.
   - **triage**: 명시적 작업 종료 또는 PR 생성·갱신·Merge 완료 보고 때 미처리 기록을 선별한다. 매 응답 종료를 작업 종료로 간주하지 않는다. 기록만 보존 / 보류 / 기존 Issue 연결 / 새 Issue 등록을 구분한다.
   - **follow-up**: 사용자가 개선 작업을 명시 요청한 경우에만 신호와 Issue를 기존 `build → verify/verifier → review`로 인계한다. 설계·계약 변경은 기존 승인 흐름을 먼저 따른다. 채택·적용 결과를 원래 기록에 연결한다.
3. 저장·전달한 기록과 보류 이유, 실제 수행하지 않은 항목을 짧게 보고한다. 세션 중단이나 종료 시점 불명확으로 남은 기록은 다음 명시 호출/작업 종료 때 처리한다.

## 경계

- 쓰기 범위 밖 또는 read-only면 초안만 제시하고 저장되지 않았음을 알린다.
- 외부 전달은 공개 가능한 최소 정보만 사용한다. 비공개 정보를 분리할 수 없으면 사용자 판단 전 전송을 중단한다.
- 기록 변경도 일반 diff다. Review·Human Gate를 우회하거나 기록만을 위해 자동 커밋·푸시하지 않는다.
- 이는 OwnHands의 작업 지침이다. Hook 같은 자동 실행 보장이나 실제 자기개선 완료 증거가 아니다.

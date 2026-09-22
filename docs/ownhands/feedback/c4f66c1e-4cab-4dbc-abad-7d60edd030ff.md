# Feedback: ELI5 출처 Fact와 제품 결정 구분

- ID: c4f66c1e-4cab-4dbc-abad-7d60edd030ff
- 관측일: 2026-09-22
- 유형: user-correction
- 대상: Chat Plan & Design 구현 계획·지침
- OwnHands 버전: 기준 12f6082e5605cde01b0b0366ef15fa44a80c969d, uncommitted 작업
- 작업 근거: docs/specs/chat-plan-design-flow/plan.md 및 현재 세션 사용자 교정
- 전달 상태: recorded-only
- OwnHands Issue: 미등록

## 관측

- 기대 행동: 원본 확인 후 사용은 Spec 결정이고 찾은 revision/license는 구현 Fact다.
- 실제 행동: 계획에서 revision을 제품 결정으로 해석할 여지가 있었다.
- 원본 근거: 현재 세션에서 사용자가 해당 문구를 교정하고 최종 계획 구현을 요청함.
- 영향: 승인 범위 및 검증 완료 상태를 과장할 위험.

## 판단 및 전달

- 원인: 계획 표현의 경계 불명확. 플랫폼 runtime 결함이 관측된 것은 아님.
- 선별 이유: 이번 승인된 작업 안에서 정렬하여 로컬 기록만 보존.
- 외부 전달용 요약: ELI5 출처 Fact와 제품 결정 구분
- 처리 기록: 2026-09-22, 외부 Issue/댓글 전송 없음.

## 개선 후속

- 사용자 작업 요청: 교정 반영 계획의 명시적 구현 요청.
- 개선 PR/commit: 미진행.
- Before/After 및 회귀 Evidence: ELI5를 Plugin Companion 위치에 원본 그대로 보존하고 UPSTREAM.md에 조사 Fact로 기록. plan.md의 검증 기록 참조.
- 사용자 채택 결정: 수정된 구현 계획 승인. 최종 변경 외부 게시 승인 아님.
- 사용 프로젝트 적용 버전과 관측: 현재 로컬 작업 트리. 실제 Chat E2E 미관측.

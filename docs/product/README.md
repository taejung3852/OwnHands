# DevHarness Product Baseline

이 디렉터리는 DevHarness의 제품 기준선을 보관한다.

## 기준 문서

| 문서 | 역할 | 최초 등록 SHA-256 |
|---|---|---|
| `Design_Rationale.md` | 제품 목적과 설계 결정 기준 | `feb54daab5c5641517319ccfaa32872871b06fc3ad1bc8ee16f7946f3fb57030` |
| `Control_layer.md` | Control, Execution Tracking, Assurance, Evidence와 Guarantee 계약 | `7c43d869603e2e514d26ed6e26528a7029061d70200a607eb6bb01ef2fca73a8` |
| `Dashboard_layer.md` | 사용자가 작업을 이해·검증·판단하는 UX | `98d0a5927fd71ce5b066da91ec7b22f84676ff49810f99fba4e557b05ea494da` |
| `향후계획.md` | Repository, Milestone, Issue와 구현 순서 | `c2301e6c4b0f99b0b3e95147102da4efcb78e3adc5bcb42eea46d8e4c7a7c3a1` |

최초 등록 commit은 `e2b7308b0de99a9f9f263348cac15f9b067602b6`이다. 이후 사용자가 승인한 변경은 Git diff와 관련 Issue 또는 ADR로 추적한다. 최초 hash와 현재 파일 hash가 다른 것만으로 손상을 의미하지 않는다.

## 해석 우선순위

1. 최신 사용자 승인
2. 승인된 ADR
3. `Design_Rationale.md`의 제품 목적과 설계 기준
4. `Control_layer.md`와 `Dashboard_layer.md`의 책임별 계약
5. `향후계획.md`의 실행 순서

충돌은 임의로 해소하지 않고 `Conflict_and_Open_Decisions.md`에 근거, 추천안, 결정 상태를 기록한다.

## 변경 규칙

- 새 기능은 Issue와 Design Rationale 변경안을 먼저 제출한다.
- Raw Evidence는 이 디렉터리나 Git에 저장하지 않는다.
- 문서 변경이 제품 계약을 바꾸면 ADR과 요구사항 추적표를 함께 갱신한다.
- M0 ADR 사용자 검토 전에는 M1 기능 구현을 시작하지 않는다.

# V1 원본 문서

V1에서 만든 문서를 **그대로** 보존한 디렉터리다. 2026-09-16에 `docs/` 최상위에서 이곳으로 옮겼다.

V2 문서와 섞이지 않게 분리한 것이고, **내용은 수정하지 않았다.**

안내 문서는 [V1 기록](../history/v1.md)이다. 무엇을 만들었고 어디에 무엇이 있는지는 거기서 먼저 본다.

| 디렉터리 | 내용 |
|---|---|
| `adr/` | 아키텍처 결정 기록 (0001~0010) |
| `product/` | 제품 계약·JSON 스키마·용어집·설계 근거 |
| `m5-r/` | Lifecycle 계약, Claim 검증, Dashboard SDD·설계·검증 기록 |
| `reviews/` | 마일스톤별 검토 기록 (m1, m1.5, m2, m3, m4, m4.5) |
| `spikes/` | 시간 제한 기술 조사 |
| `superpowers/` | 당시 사용한 plan·spec 기록 |
| `design/` | 디자인 탐색과 스크린샷 |
| `diagrams/` | 로드맵·구조 다이어그램 |
| `research/` | 당시 조사 자료 |
| `dogfooding/` | 도그푸딩 기록 |

## 읽을 때 주의할 것

- **당시의 목표와 지금의 적용 상태를 구분한다.** 여기 적힌 계획이 현재 V2의 계획은 아니다.
- V1의 구현·검증 결과는 V2의 완료 근거로 **자동 승계되지 않는다.**
- 본문에 적힌 `docs/adr/...` 같은 **경로 표기는 당시 기준이다.** 실제 위치는 `docs/legacy/` 아래다. 역사 기록이므로 본문을 고쳐 쓰지 않았다.
- `spikes/probes/*.sh` 등 당시 실행 스크립트도 경로 표기가 당시 기준이다.

## `product/`와 `reviews/`는 문서만이 아니다

이 두 디렉터리에는 V1 코드와 테스트가 **런타임에 읽는 파일**이 있다.

| 파일 | 읽는 곳 |
|---|---|
| `product/guarantee-matrix.v1.json` | `src/devharness/run_evidence.py` · `imported_tasks.py` · `__main__.py` |
| `product/guarantee-matrix.schema.json` | `tests/test_guarantees.py` |
| `product/assurance-packet.{schema,example}.json` | `tests/test_m4_review.py` |
| `product/context-guarantee-matrix.proposed.json` | `tests/test_context_architecture.py` |
| `reviews/m1.5/comparison-package.json` | `tests/test_context_architecture.py` |
| `reviews/m3/run_live_probe.py` | `tests/test_m3_review.py` |

이동할 때 위 참조 경로를 함께 갱신했고 **579 tests로 이동 전후를 확인했다.**
이 파일들을 다시 옮기려면 같은 참조를 함께 고쳐야 한다.

## V2 문서

[문서 인덱스](../README.md) · [V2 개요](../v2/overview.md) · [결정 상태표](../v2/decisions.md)

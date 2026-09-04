# M0-01 — Product and repository baseline audit

- **상태:** 로컬 검증 완료, 외부 PR 및 Issue 상태 변경 전 사용자 승인 대기
- **확인일:** 2026-09-04
- **범위:** 제품 기준선, Git/GitHub 상태, 문서 내부 링크, Raw Evidence 제외 규칙

## 결과

최초 기준선 commit `e2b7308b0de99a9f9f263348cac15f9b067602b6`의 네 제품 문서 SHA-256은 [제품 기준선 목록](../product/README.md)에 기록된 값과 모두 일치했다. 현재 파일은 이후 승인·검토용 문서 변경을 포함할 수 있으므로 최초 hash와 현재 hash가 다르다는 사실만으로 훼손으로 판정하지 않는다.

2026-09-04 read-only GitHub 조회 결과 repository `taejung3852/devharness`는 Private, default branch는 `main`, 원격 `main`은 최초 기준선 commit이었다. M0 milestone에는 M0-01~M0-07에 대응하는 일곱 개 open Issue가 있고, 전체 범위 추적 Issue는 milestone 밖에 open 상태로 존재했다. 원격 객체는 변경하지 않았다.

로컬 `main`은 원격 `main`보다 두 commit 앞서 있었고, 사용자 소유의 untracked `docs/diagrams/devharness-milestone-roadmap.html`이 있었다. 이 파일은 수정·삭제·stage하지 않았으며, 현재 M0 baseline PR 범위에서는 제외한다. 포함 여부는 사용자에게 별도로 확인한다.

## 책임 경계 대조

| 수용 기준 | 기준선 확인 결과 |
|---|---|
| HWPX | 첫 도그푸딩 대상이며 관련 특수성은 Adapter/Fixture에 격리한다. Core 요구사항이나 전용 구현으로 승격하지 않는다. |
| Preflight token/cost | Preflight와 실행 계약에서 제외한다. Usage & Cost Analytics는 M8의 별도 Dashboard 범위다. |
| LangGraph | 제품·Control·Dashboard 계약에 의존성이나 전용 표현이 없다. |
| M0 Gate | M0-06 Event/Evidence Store는 필수, M0-05 Superpowers는 Non-blocking, M0-07은 M0 Non-blocking/M5 승인 Gate로 추적된다. |
| 결정 분리 | 확정 제품 기준선, Proposed ADR, Technical Spike, Observed/Inferred/Unobserved, 사용자 Open Decision이 별도 문서와 상태로 유지된다. |

미결정 항목은 [Conflict and Open Decisions](../product/Conflict_and_Open_Decisions.md)에 사용자 책임과 M1/M5 전 결정 시점을 기록했다. 이 대조는 문서 계약을 확인한 것이며 HWPX, 비용 분석, Adapter 또는 Dashboard 기능을 구현했다는 뜻이 아니다.

## 재현 가능한 Probe

실행:

```bash
docs/spikes/probes/m0-01-baseline-probe.sh
```

검증 항목:

1. 최초 commit과 네 기준선 문서 hash
2. `docs/product`, `docs/adr`, `docs/spikes`, `docs/design`의 상대 Markdown link 대상 존재 여부
3. `.dev-harness/`, `.codex-log/`, `docs/spikes/raw/`의 Git 제외 규칙

이 Probe는 원격 상태를 변경하지 않고 로컬 repository metadata와 문서만 읽는다. GitHub의 현재 가시성, branch, Issue 상태는 시점에 따라 바뀔 수 있으므로 별도 read-only 조회로 확인한다.

## Claim 경계

- **Observed:** 최초 commit의 네 파일 hash, 현재 로컬 Git 상태, 내부 link, ignore 규칙, 2026-09-04 시점의 GitHub metadata
- **Inferred:** 없음
- **Unobserved:** PR review 결과, merge 결과, 이후 원격 상태

따라서 M0-01 산출물은 로컬에서 검토 가능한 상태지만 Issue 완료나 M0 종료를 아직 주장하지 않는다.

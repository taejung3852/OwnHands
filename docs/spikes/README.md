# Technical Spikes

Technical Spike는 공식 문서와 재현 가능한 안전한 Probe를 사용한다. Raw output은 `docs/spikes/raw/` 또는 OS 임시 경로에 두며 Git에 commit하지 않는다. 실패나 관찰 불가는 `Unobserved`로 기록한다.

| Issue | Spike | 상태 |
|---|---|---|
| M0-01 | [제품·Repository 기준선 Audit](m0-01-baseline-audit.md) | 로컬 Probe 통과, 외부 검토 대기 |
| M0-02 | [Codex Desktop 통합 경로](codex-desktop-integration.md) | ADR 승인, read-only capability Probe 통과, runtime은 M3로 이관 |
| M0-03 | [Control Validation 가능 범위](control-validation-coverage.md) | ADR 승인, capability Probe 통과, enforcement는 M3로 이관 |
| M0-04 | [Guarantee Matrix v1](guarantee-matrix-v1.md) | ADR 승인, strict schema·합성 Probe 통과 |
| M0-05 | [Superpowers Skill Vendoring](superpowers-vendoring.md) | 경계 ADR 승인, Non-blocking, 실제 vendoring 미승인 |
| M0-06 | [Event & Evidence Store](event-evidence-store.md) | ADR 승인, 합성 Probe 통과 |
| M0-07 | [Brand & Dashboard Design Foundation](../design/m0-07/README.md) | B 색상 방향 승인, UI/UX는 M5 Gate 대기 |

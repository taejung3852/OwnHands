---
name: verify
description: Verifies implementation against spec acceptance criteria, ensures regression defense, and audits fresh evidence.
---

# verify

구현 작업 완료 전 작업 유형에 맞는 신선한 관측 증거(applicable Fresh Evidence)를 확보하고 수용 기준(AC) 만족 여부를 감사할 때 호출한다.

## Light Flow

현재 사용자 요청·diff·applicable native checks를 기준으로 검증한다. plan.md와 verification.md를 강제하지 않고 Verification Summary에 변경 범위, 실행 명령·결과, PASS / FAIL / UNOBSERVED와 한계를 담아 세션에 제공한다. PR이 있으면 그 본문의 검증/Evidence 섹션에 투영한다. PR 생성 권한이나 기존 Review/Hook Gate 면제를 뜻하지 않는다.

독립 Verifier는 Light의 기본 의무가 아니다. 변경 반경 증가, 중요한 인터페이스, 요구 모호성, 고위험 데이터/권한/migration, deterministic check로 판단 불충분이 발견되면 Planned로 승격하고 build의 실제 Plan Mode·승인 절차로 돌아간다. 버그/성능 Before 기준과 회귀 방어선은 Light에도 적용한다.

## Planned Flow 작업 절차

1. **비교 주장(Claim) 확인**:
   - 버그 수정(`bugfix`): 코드 수정 전 결함 재현 로그(Before Evidence) 필수 확인.
   - 성능 개선(`performance`): 코드 수정 전 기준 벤치마크 수치(Before Evidence) 필수 확인.
   - 신규 기능(`feature`): 수용 기준(AC) 충족 여부 확인.
   - *(세부 기준: `references/before-after-baseline.md` 참고)*

2. **회귀 검증 (Regression Gate)**:
   - 변경 영향 분석(Impact Analysis)을 통해 기존 테스트 스위트 실행.
   - 기존 테스트 부재 시 3대 대체 방어선(Blast Radius 엄격 통제, Native Project Checks 무에러 확인, UNOBSERVED 명시) 적용.
   - *(세부 기준: `references/regression-defense.md` 참고)*

3. **신선한 증거 수집 및 기록 (applicable Fresh Evidence)**:
   - 작업 유형에 맞는 실제 관측 증거(테스트 실행 로그, 브라우저 렌더링/스크린샷 관측, 벤치마크 수치, 린트/타입 무에러 결과 등)를 `plan.md`에 기록. (커밋 해시는 uncommitted 작업 중일 수 있으므로 provenance 용도로 활용)
   - *(세부 기준: `references/evidence-guide.md` 참고)*

4. **독립 감사관(Verifier) 호출**:
   - 구현이 완료되면 `.codex/agents/model-policy.md`에서 위험 tier를 선택하고 model과 reasoning effort를 모두 명시해 독립 `verifier` Subagent(`.codex/agents/verifier.toml`)를 호출한다. `spec.md`의 AC와 `plan.md`의 Fresh Evidence를 역추적 대조하여 `PASS / FAIL / UNOBSERVED` 최종 판정을 받고 요청 provenance를 기록한다.

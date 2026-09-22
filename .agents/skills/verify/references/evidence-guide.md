# 신선한 증거(applicable Fresh Evidence) 작성 및 Verifier 감사 가이드

## 1. The Iron Law of Fresh Evidence
> **"신선한 관측 증거(Fresh Evidence) 없는 완료 주장 금지"**
- 에이전트는 현재 작업 턴에서 직접 수집하고 관측한 **적용 가능한 신선한 증거(applicable Fresh Evidence)** 없이 작업을 완료했다고 주장할 수 없습니다.
- 과거 턴의 로그 재탕, "정상 동작할 것"이라는 주관적 추측, 관측 없는 자가합리화는 원천 차단됩니다.

---

## 2. 작업 유형별 Fresh Evidence 수집 가이드
Planned는 `plan.md`의 `실행 및 신선한 검증 증거` 섹션에, Light는 세션 Verification Summary에 작업 유형(AC의 성격)에 부합하는 증거를 명확히 기록합니다:

| 검증 대상 | 적용 가능한 신선한 증거 (applicable Fresh Evidence) | 충족 기준 |
|---|---|---|
| **Unit / API** | 테스트 러너 실행 명령어 + 종료 코드(exit 0) + assertion 통과 건수 | 테스트 패스 (0 failures) |
| **UI / Layout** | 브라우저 렌더링 관측 기록, 레이아웃 스크린샷, DOM 요소 관측 | 기대 디자인/상태 일치 |
| **Lint / Type / Policy** | 정적 분석 도구(`npm run lint`, `tsc` 등) 실행 출력 | 에러 및 경고 0건 |
| **Performance** | 동일 환경에서의 사전(Before) 및 사후(After) 벤치마크 측정 수치 | 측정된 성능 향상 입증 |
| **Manual / Exploratory** | 재현 절차에 따른 구체적 실행 및 관측 결과 기록 | 기대 동작 일치 |

> 💡 **커밋 해시의 성격 (Provenance)**: Git 커밋 해시는 검증 증거의 신선도와 출처를 보증하는 유용한 추적자(provenance)입니다. 단, 아직 커밋되지 않은 작업 트리(uncommitted working tree)에서 검증을 수행하는 도중일 수 있으므로 필수 차단 요건으로 삼지 않습니다.

---

## 3. Verifier의 독립 감사 및 3대 판정 어휘

Verifier Subagent(`.codex/agents/verifier.toml`)는 `read-only` 샌드박스에서 다음 3대 어휘로만 판정합니다:

| 판정 | 의미 및 조건 |
|---|---|
| **`PASS`** | 제출된 applicable Fresh Evidence가 `spec.md`의 해당 AC를 객관적이고 충분하게 입증함. |
| **`FAIL`** | 실행 결과 오류 발생, assertion 실패, AC 기대 동작과의 불일치, 또는 증거 위조/조작 의심. |
| **`UNOBSERVED`** | 해당 AC에 대한 실행 증거가 누락되었거나 직접 관측되지 않음 (버그/성능 Before 부재 포함). |

- 모든 필수 AC가 `PASS`로 판정될 때만 최종 검증 통과(Overall PASS)가 인정됩니다.

Light는 별도 plan.md/verification.md를 만들지 않는다. PR이 있으면 Summary를 본문에 반영한다. 플랫폼 blocker는 사유이며 새 AC 판정값이 아니다. 실행하지 못한 AC는 UNOBSERVED로 유지한다.

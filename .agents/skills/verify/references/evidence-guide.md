# 신선한 증거(Fresh Evidence) 작성 및 Verifier 감사 가이드

## 1. The Iron Law of Fresh Evidence
> **"신선한 관측 증거(Fresh Evidence) 없는 완료 주장 금지"**
- 에이전트는 현재 작업 턴에서 직접 실행하고 관측한 터미널 출력 없이 작업을 완료했다고 주장할 수 없습니다.
- 과거 턴의 로그 재탕, 추측에 의한 "정상 동작할 것" 주장은 원천 차단됩니다.

---

## 2. Fresh Evidence의 필수 요소
`plan.md`의 `실행 및 신선한 검증 증거` 섹션에는 다음 정보가 명확히 기록되어야 합니다:

1. **실행 명령어**: 테스트 또는 검사를 실행한 정확한 CLI 명령어 (예: `npm test`, `pytest tests/test_feature.py`).
2. **프로세스 종료 코드 (Exit Code)**: 성공을 보장하는 `exit code: 0`.
3. **핵심 출력 요약**:
   - 단위 테스트: 통과 케이스 수 (예: `5 passed, 0 failed`).
   - 린트/타입: 무에러 출력 (예: `0 errors, 0 warnings`).
   - 렌더링/UI: 관측된 레이아웃 상태 또는 스크린샷 링크.
4. **기준선 커밋 해시**: 해당 검증이 실행된 시점의 Git 작업 커밋 해시.

---

## 3. Verifier의 독립 감사 및 3대 판정 어휘

Verifier Subagent(`.codex/agents/verifier.toml`)는 `read-only` 샌드박스에서 다음 3대 어휘로만 판정합니다:

| 판정 | 의미 및 조건 |
|---|---|
| **`PASS`** | 제출된 Fresh Evidence가 `spec.md`의 해당 AC를 완벽하고 모호함 없이 증명함. |
| **`FAIL`** | 실행 결과 오류 발생, assertion 실패, AC 기대 결과와의 불일치, 또는 증거 위조 의심. |
| **`UNOBSERVED`** | 해당 AC에 대한 실행 증거가 누락되었거나 직접 관측되지 않음 (Before 부재 포함). |

- 모든 필수 AC가 `PASS`로 판정될 때만 최종 검증 통과(Overall PASS)가 인정됩니다.

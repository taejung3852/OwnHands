---
name: review
description: Use when an OwnHands implementation has completed verify/verifier and is ready for independent final diff review before an external Git decision.
---

# review

검증된 구현을 독립 Review, diff-bound Evidence, Human Gate로 연결하는 얇은 Process Skill이다.

## 책임 계약

- **Trigger**: 구현과 `verify`·`verifier`가 끝나 최종 변경을 독립 검토할 때
- **Input**: 승인된 Spec/Plan, final diff, Fresh Evidence, Verifier 결과
- **Success**: Reviewer가 확인한 최종 diff의 Review Evidence가 있고 사용자가 현재 Human Gate를 결정할 수 있음

Reviewer 요청은 최소 Packet으로 제한하고, 받은 Finding은 근거로 판정하며, 외부 상태 변경은 단계별 Human Gate로 마무리한다. 이는 `requesting-code-review`·`receiving-code-review`·`finishing-a-development-branch`의 원칙을 OwnHands 계약에 맞게 통합한 것이며 원문 Skill을 복제하지 않는다.

## 작업 절차

1. 승인된 `spec.md`·`plan.md`와 `verify`·`verifier` 결과를 확인한다. 필수 AC의 `FAIL`은 중단한다. `UNOBSERVED`는 해당 Gate에서 누락 Evidence·확보 불가 사유·위험을 보여주고 사용자의 명시적 override를 받아야 한다.
2. [`references/review-governance.md`](references/review-governance.md)와 `.codex/agents/model-policy.md`를 읽고 위험 tier의 model과 reasoning effort를 모두 명시해 read-only `reviewer`에게 최소 Review Packet을 전달하며 요청 provenance를 기록한다.
3. 각 Finding을 저장소 Fact·승인된 Spec·Evidence로 판정하고 `plan.md`의 `Review Results`에 `Status`와 `Resolution`을 분리해 기록한다.
4. 필요한 수정과 Fresh Evidence, targeted re-review를 끝낸 뒤 현재 최종 diff의 fingerprint를 Reviewer가 확인하게 한다.
5. 마지막 Reviewer 관측 뒤 diff가 바뀌지 않았고 미해결 Finding이 없을 때만 로컬 Review Evidence를 기록한다.
6. 해당 외부 상태 변경 직전에 그 단계만 Human Gate로 묻는다. `Push + PR`, Merge, Deploy, Cleanup의 승인과 `UNOBSERVED` override는 서로 승계하지 않는다.

## 중단 조건

- 필수 AC 또는 required check가 `FAIL`: 수정 전 외부 상태 변경 금지
- `Resolution: open` Finding 존재: Review Evidence PASS 기록 금지
- 마지막 Reviewer 관측 뒤 diff 변경: 새 fingerprint의 Final Review로 복귀
- 복합 shell command 안의 `git push`, `gh pr create`, `gh pr merge`: Evidence가 있어도 중단하고 독립 command로 실행

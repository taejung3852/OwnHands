# Review Governance

필수 AC가 `verify`와 read-only `verifier`에서 모두 `PASS`이거나, 필수 `UNOBSERVED`의 누락 항목·확보 불가 사유·수용 위험을 보여준 뒤 사용자가 명시적으로 override했을 때만 이 절차를 시작한다. `FAIL`은 override하지 않고 구현 루프로 돌린다.

## Review Packet

전체 대화 대신 현재 변경을 판단하는 최소 정보만 기존 read-only `reviewer`에게 전달한다.

- **Initial Review**: 승인된 `spec.md`·`plan.md`, 정확한 base/head와 staged·unstaged·untracked scope, applicable Fresh Evidence, 관련 baseline, `UNOBSERVED`, known constraints
- **Targeted Re-review**: Finding ID, 수정한 범위, 갱신한 Evidence, 위험 경계 변화만 전달
- **Final Review**: 모든 tracked 변경을 끝낸 최종 diff와 `review-gate.js fingerprint` 값, 승인된 Spec/Plan, 최종 Evidence

## Finding 판정

Reviewer 의견은 자동 수정 명령이 아니다. 저장소 Fact, 승인된 Spec, Evidence에 대조해 각 Finding을 판정하고 `plan.md`의 `Review Results`에 남긴다.

```markdown
### Finding `F-01`
- **Status**: `accepted | rejected-with-evidence | needs-human`
- **Resolution**: `open | resolved`
- **Reviewer claim**: ...
- **Reason**: ...
- **Evidence**:
  - ...
```

- `accepted`: 최소 수정과 Fresh Evidence를 확보한 뒤 `resolved`로 전환한다.
- `rejected-with-evidence`: `resolved` 상태와 Reviewer claim·Reason·구체적인 코드/Spec/Test Evidence가 모두 필요하다.
- `needs-human`: 구현을 멈추고 사용자 결정을 받은 뒤 그 근거와 해결 내용을 기록하고 `resolved`로 전환한다.
- `accepted` 영역을 수정했거나 위험 경계가 바뀌었거나 해결 여부 확인이 필요할 때만 해당 범위를 다시 Review한다.

## Final Review와 Evidence

1. Finding 판정, `plan.md` 기록, 수정, Fresh Evidence 갱신을 모두 끝낸다.
2. `node scripts/review-gate.js fingerprint --base <base>`로 최종 fingerprint를 계산한다.
3. Reviewer가 정확히 그 fingerprint의 최종 diff를 확인한다.
4. 새 Finding이 생기면 기록·처리하고 2번부터 반복한다.
5. 새 Finding이 없으면 tracked file을 더 수정하지 않고 같은 값을 `record --reviewed-fingerprint`에 전달한다.

Review Evidence JSON은 Git 내부 로컬 상태에 fingerprint·verdict·count만 저장한다. 상세 reasoning은 `plan.md`가 유일한 영구 Source of Truth다.

## Human Gate

다음 승인은 서로 대체하지 않는다. Main Agent는 각 단계 직전에 사용자에게 해당 선택만 요청한다.

1. `Push + PR / Keep`
2. `Merge / Keep`
3. Deploy가 있는 작업의 `Deploy / Keep`
4. `Cleanup / Keep`

Hook은 Review Evidence만 확인하는 로컬 guardrail이다. 사람 승인을 추론하지 않으며 완전한 보안 경계가 아니다.

# ADR-0010: Review · Human Gate · CI Governance

- **상태**: Accepted
- **일자**: 2026-09-20
- **관련 Issue**: [#146](https://github.com/taejung3852/OwnHands/issues/146), [#148](https://github.com/taejung3852/OwnHands/issues/148)
- **기반 Spec**: [`../specs/deploy-governance/spec.md`](../specs/deploy-governance/spec.md)

## Context

기존 Build 흐름은 `verify`와 독립 `verifier`에서 끝나 Reviewer Finding 처리, 현재 diff에 결합된 Review Evidence, 외부 상태 변경 전 Human Gate가 연결되지 않았다. GitHub에서 Agent Runtime을 required check로 돌리면 별도 인증·비용·비결정성도 기본 경로에 들어온다.

## Decision

1. 필수 AC PASS 뒤 기존 read-only `reviewer`를 호출하고, Finding은 `accepted / rejected-with-evidence / needs-human`으로 판정한다.
2. 상세 판단과 해결 상태는 `plan.md`의 `Review Results`에 남긴다. JSON Evidence에는 reasoning을 복제하지 않는다.
3. 모든 tracked 변경이 끝난 뒤 Reviewer가 확인한 fingerprint와 `record` 시점 fingerprint가 일치할 때만 Git 내부 로컬 Evidence를 기록한다.
4. repo-local `PreToolUse` Hook은 `git push`, `gh pr create`, `gh pr merge`만 검사한다. 일반 응답과 다른 command에는 개입하지 않는다.
5. `Push + PR`, Merge, Deploy, Cleanup은 서로 독립된 Human Gate다.
6. GitHub CI 기본 후보는 deterministic project checks와 M5 `--static-only`다. Codex Action, API key 기반 Runtime CI, Managed Policy는 실제 Requirement가 생길 때까지 도입하지 않는다.

## Consequences

- Reviewer와 Verifier의 책임이 분리되고, Review PASS 주장은 Reviewer가 실제로 본 최종 diff에 결합된다.
- 로컬 Hook은 누락·stale Evidence를 외부 Git command 직전에 막지만, 원격 branch protection이나 조직 정책을 대체하지 않는다.
- Runtime Review/Eval은 로그인된 로컬 Codex 세션에서 선택 실행하며 전체 Runtime Suite를 기본 Gate로 만들지 않는다.
- 사람의 승인이 없으면 외부 상태 변경과 destructive cleanup을 자동 실행하지 않는다.

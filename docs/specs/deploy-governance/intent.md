# Intent: Review Loop · Human Gate · CI Governance

- **작성자**: 박태정 (@taejung3852) & Codex
- **일자**: 2026-09-20
- **상태**: Approved — 사용자 확인 (2026-09-20)
- **관련 Issue**: [#146](https://github.com/taejung3852/OwnHands/issues/146)
- **상위 마일스톤**: [V2-M6 — Deploy & Governance](https://github.com/taejung3852/OwnHands/milestone/19)
- **선행 Research**: [`docs/research/m6-deploy-governance.md`](../../research/m6-deploy-governance.md)

---

## 1. 문제 및 배경 (Why)

- **현재 상황과 고통**:
  - OwnHands에는 승인된 Spec/Plan을 실행하는 `build`, Fresh Evidence를 감사하는 `verify`·`verifier`, diff를 독립 검토하는 read-only `reviewer`, 자체 회귀를 측정하는 M5 Eval이 있다.
  - 그러나 `verify → reviewer → Push/PR → CI → Merge/Deploy` 사이의 호출 순서, Finding 처리, 사람의 승인 책임, 권한 상한이 하나의 계약으로 연결돼 있지 않다.
  - 연결 계약이 없으면 Reviewer 의견을 무조건 수정 명령으로 오해하거나, `UNOBSERVED`를 통과로 간주하거나, 외부 상태 변경을 사용자 승인 없이 수행할 수 있다.
- **대상 사용자 (페르소나)**:
  - Codex와 함께 개발하면서 검증·리뷰 Evidence를 활용하되, PR·Merge·Deploy의 최종 책임과 위험 수용 결정을 직접 소유하려는 AI-Native 소프트웨어 엔지니어.

## 2. 목표 결과 및 가치 (What)

- **최상위 목표**:
  > **검증된 변경이 독립 Code Review와 사람의 최종 판단을 거쳐 최소 권한으로 PR·CI·Merge 단계로 이동하도록 책임 경계를 정의한다.**
- **달성하고자 하는 결과**:
  - `verify/verifier` 이후 PR 생성 전에 기존 read-only `reviewer`를 1회 호출하는 Review Loop를 정의한다.
  - Reviewer Finding을 저장소·승인된 Spec·Evidence로 검증하여 `accepted`, `rejected-with-evidence`, `needs-human`으로 처리한다.
  - `Push + PR`, `Merge`, `Deploy`를 서로 다른 Human Gate로 구분한다.
  - OwnHands 자체 검사와 OwnHands 사용 프로젝트의 검사를 분리하고, deterministic CI와 선택 Runtime Eval의 책임을 구분한다.
  - 별도 API 과금이 필요한 Codex Action 대신 로그인된 Codex 앱 세션에서 Reviewer와 선택 Runtime Eval을 실행한다.
  - 외부 Git 명령 직전의 좁은 Hook으로 Review Evidence 누락이나 리뷰 후 변경을 감지한다.
- **성공 기준**:
  - Reviewer, Verifier, Main Agent, CI, Human의 관측·판단 책임이 겹치지 않게 설명된다.
  - Review Packet의 최소 Context와 관련 baseline 포함 조건이 정의된다.
  - Finding 처리와 targeted re-review 조건이 정의된다.
  - `FAIL`과 `UNOBSERVED`의 Merge 의미 및 Human override 경계가 정의된다.
  - 역할별 최소권한과 외부 상태 변경 승인이 정의된다.
  - 실제 구현 전에 `intent.md`, `spec.md`, `plan.md`로 추적 가능한 계약이 완성된다.

## 3. 비목표 (Non-goals & Boundaries)

> ⚠️ **자동화 확대 방지**: 이번 Step ②에서 의도적으로 하지 않는 것

- [ ] GitHub Actions workflow, CI, Merge Gate 또는 Hook 구현
- [ ] Managed Policy 또는 가상의 조직 정책 구현
- [ ] 새로운 Reviewer Agent 추가나 기존 Verifier/Reviewer 재설계
- [ ] Worktree·branch cleanup 자동화
- [ ] 새 Eval Task 추가, M5 runner 대형 확장 또는 전체 Runtime Eval 재실행
- [ ] Superpowers Skill 전체 복사 또는 별도 Governance framework 제작
- [ ] Codex Action·API key·별도 API 과금 기반 Runtime CI 도입
- [ ] 자동 Push, PR, Merge 또는 Deploy
- [ ] 승인된 `spec.md` 이후의 실제 구현 착수

## 4. 핵심 제약 조건 (Constraints)

- **기존 자산 재사용**: `build`, `verify`, `verifier`, `reviewer`, M5 Task Set·runner와 기존 `plan.md` 규격을 Source of Truth로 재사용한다.
- **Review 순서**: 필수 AC의 `verify/verifier` 판정 이후, PR 생성 전에 기존 `reviewer`를 1회 호출한다. 중복 PR Review는 기본값으로 두지 않는다.
- **최소 Review Packet**: 승인된 Spec/Plan, 정확한 diff 범위, 적용 가능한 Fresh Evidence와 관련 baseline, known constraints를 전달하며 전체 대화 기록은 제외한다.
- **Finding 판정**: Reviewer는 Evidence Provider다. Main Agent가 Finding을 검증하고 정책·위험 판단만 `needs-human`으로 사용자에게 넘긴다.
- **Targeted re-review**: accepted Finding의 대상 영역을 수정했거나 위험 경계가 바뀐 경우에만 수행한다.
- **Human Gate**: `Push + PR`, `Merge`, `Deploy`는 각각 명시적 승인을 받는다. `UNOBSERVED` 예외도 누락 Evidence·확보 불가 사유·수용 위험을 제시한 뒤 사용자에게 반드시 묻는다.
- **CI 이중 경계**: OwnHands 저장소에는 deterministic checks와 M5 정적 검사, 관련 자산 변경 시 선택 Runtime Eval을 적용한다. 사용 프로젝트에는 해당 프로젝트의 native checks와 승인된 Spec의 검증 전략을 적용하며 M5 Task Set을 강제하지 않는다.
- **로컬 Runtime**: Reviewer와 선택 Runtime Eval은 로그인된 Codex 앱 세션에서 실행한다. GitHub CI에서 Codex Action이나 OpenAI API Secret을 사용하지 않는다.
- **권한 분리**: Reviewer·Verifier·Hook은 read-only, Builder는 승인된 Target Files만 workspace-write로 제한한다. 외부 GitHub 상태 변경 권한은 Human Gate 뒤에만 사용한다.
- **좁은 Hook**: 모든 응답에 실행되는 `Stop` Hook은 사용하지 않는다. `git push`, `gh pr create`, `gh pr merge` 같은 외부 변경 명령 직전의 `PreToolUse` Hook만 후보로 설계하며, Hook은 완전한 보안 경계로 과장하지 않는다.
- **보류 기본값**: Managed Policy는 실제 조직 Requirement가 생길 때까지 구현하지 않는다.
- **종료 선택**: 작업 종료 시 `Push + PR / Keep`을 선택하고, Merge와 branch/worktree Cleanup은 각각 별도 승인 없이는 실행하지 않는다.

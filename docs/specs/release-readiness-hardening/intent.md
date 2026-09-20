# Intent: Release Readiness Hardening

- **작성자**: OwnHands maintainer + Codex
- **일자**: 2026-09-20
- **기준점**: `origin/main` `72084785a8229bccd0400dff3cd5b3acec807496`
- **상태**: Approved

## 1. 문제와 목표

OwnHands의 핵심 Workflow는 구현됐지만 첫 정식 baseline release 전에 실제 프로젝트에서 안전하게 연결하고 아래 흐름을 끝까지 수행할 준비가 부족하다.

```text
Intent → Spec → Codex Plan Mode → plan.md → Build
→ Verify / Verifier → Review / Reviewer → Human Gate
→ Git operation → Feedback
```

이번 작업의 목표는 기능 확장이 아니라 네 개의 확인된 결함을 막고, 승인된 계획 인계·명시적 subagent 정책·Explain 기본 UX·최소 설치 경로를 하나의 일관된 계약으로 만드는 것이다.

## 2. 성공 기준

- Review Gate와 Eval baseline의 네 confirmed defect에 각각 regression test와 최소 수정이 존재한다.
- heavy flow에서 Spec 승인 뒤 native Codex Plan Mode와 사용자 계획 승인을 거쳐야만 `plan.md`를 보존하고 Build로 이동한다.
- `npx ownhands init`과 `npx ownhands doctor`만으로 새 Git 프로젝트에 필요한 native 자산을 안전하게 연결하고 진단할 수 있다.
- researcher, verifier, reviewer의 기본 model/reasoning과 override 기준, 실제 read-only sandbox가 명시된다.
- 명시적 `$explain`은 기존 `references/shape.md` 기반 HTML visual artifact를 기본으로 하고 명시적 text-only 또는 부적절한 환경에서만 text로 fallback한다.

## 3. 비목표

- 실제 제품 E2E 또는 Runtime Eval 실행
- npm publish, release/tag/version 변경, Push/PR/Merge
- Dashboard, DB, 대형 Runner, 별도 Runtime, GUI, daemon
- bootstrap의 update, migrate, uninstall 자동화
- 범용 Markdown parser, shell interpreter, multi-repository framework
- 별도 `plan` Skill 또는 새 Explain renderer/framework

## 4. 제약

- 최신 `main`을 Source of Truth로 사용하고 기존 dirty checkout의 사용자 파일을 보존한다.
- 네 결함은 이미 `7208478`에서 재현됐으므로 기준점이 변하지 않는 한 재현을 반복하지 않는다.
- 결함별 regression test를 먼저 실패시키고 최소 구현으로 통과시킨다.
- `UNOBSERVED`를 PASS로 바꾸지 않으며 실제 Hook trust, 공개 npm 설치, 제품 E2E는 별도 관측으로 남긴다.
- bootstrap은 Node.js 18+와 Git만 전제로 하고 runtime dependency를 추가하지 않는다.

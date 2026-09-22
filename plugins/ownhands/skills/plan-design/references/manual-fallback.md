# GitHub 없이 계속하기

미연결, 권한 부족, Branch/commit 실패, 일시 오류여도 Intent/Spec 논의와 Content Approval을 계속할 수 있다. `Intent 승인 완료 / GitHub 저장: 대기` 또는 `Spec 승인 완료 / GitHub 저장: 실패`처럼 두 상태를 분리한다. 오류 원인이 관측되지 않았다면 원인 미확인이라고 적는다.

현재 Stage에 실제 존재하는 산출물만 전체 내용과 저장 경로로 제공한다: intent.md, spec.md, 관련 ADR, 대화 Handoff. Issue 초안은 사용자가 Issue 경로를 선택한 경우에만 제공한다. 아직 없는 문서·Issue 번호·Branch·commit을 만들어낸 척하지 않는다.

수동 가이드:
1. 사용자가 접근 가능한 Repository의 현재 작업 Branch와 대상 파일을 확인한다.
2. 기존 Branch를 우선 사용하고, 새 Branch가 필요하면 선택한 경로에 맞게 직접 만든다.
3. 승인받은 Stage 문서와 관련 ADR을 지정 경로에 저장한다. 기존 파일과 다르면 diff를 검토하고 사용자 변경을 보존한다.
4. 해당 Stage 파일만 한 commit으로 저장한다. Decision별 commit, 미승인 문서 저장, force push를 안내하지 않는다.
5. 사용자가 실제 저장한 Branch/commit 정보를 공유하면 재조회하여 인정한다. 연결이 돌아와도 자동 복구하지 않고 github-workflow의 Reconcile을 따른다.

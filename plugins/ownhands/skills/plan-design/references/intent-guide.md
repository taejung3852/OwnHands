# Intent Stage

`docs/specs/<feature-name>/intent.md` 후보에 문제와 배경, 대상 사용자, 목표 결과, 성공 기준, Non-goals, Constraints를 정의한다. 구현 상세를 미리 제품 결정으로 확정하지 않는다. GORE 목표와 중요한 결정의 근거를 연결한다. 확인된 사실은 출처와 관측 범위를 표시한다.

문서 상태는 Draft / Approved. Issue는 있을 때만 실제 링크를 적는다. 내용 후보를 준비하는 것과 GitHub에 쓰는 것은 별개다.

## Checkpoint 1

1. 전체 Intent를 검토 가능한 상태로 제시한다.
2. [ELI5 원본](../../eli5/SKILL.md)을 읽고 실행한다. 입력 Topic은 이 Intent의 목표·비목표·사용자 흐름·핵심 결정 전체다. 큰 그림 HTML artifact와 적은 글로 설명한다. 인터뷰의 작은 재설명과 이 Stage ELI5를 혼동하지 않는다.
3. 설명 후 Intent 전체의 Content Approval을 요청한다. 변경 요청이면 초안을 수정하고 해당 Stage 검토를 다시 진행한다. 승인 전 Spec으로 직행하지 않는다.
4. 승인받으면 Approved로 표시하고 `Intent 승인 완료 / GitHub 저장: 대기`를 안내한다.
5. 별도로 “승인된 Intent와 관련 ADR을 GitHub에 저장할까요?”를 묻는다. 저장 승인 전 Issue·Branch·파일 write를 하지 않는다.
6. 승인된 저장은 [GitHub workflow](github-workflow.md)로 intent.md와 이번 Stage 관련 ADR을 한 commit으로 수행한다. 저장 거절·실패가 내용 승인을 취소하지 않는다. 승인된 Intent가 있으면 저장 대기 중에도 사용자 요청에 따라 Spec 논의가 가능하다.

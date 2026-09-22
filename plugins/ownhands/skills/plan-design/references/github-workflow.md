# GitHub Workflow

GitHub는 durable Source of Truth이며 Plugin은 자체 GitHub 서버/API를 제공하지 않는다. 현재 호스트의 연결 도구를 발견하고 실제 read/write capability를 확인한다. 도구가 안 보임, 인증 실패, repository read 거부, read-only, branch 생성 거부, commit/ref 갱신 실패, 일시 오류를 관측 가능한 범위에서 구분한다. 구분할 수 없으면 원인을 추측하지 않고 미확인으로 표시한다. 권한 metadata는 write 성공의 증거가 아니다.

## 시작과 선택

Repository와 관련 Issue·Branch·기존 artifacts를 읽는다. 명확한 기존 작업 Branch가 하나면 재사용하고, 후보가 여러 개면 선택받는다. Issue 전체를 이번 범위로 해석하지 않는다.

Issue가 없으면 다음 세 선택을 제시한다. 선택받기 전에 생성하지 않는다.
1. Issue를 생성하고 Issue 기반 Branch로 진행.
2. Issue 없이 Branch만 생성.
3. GitHub 작업 없이 기획·설계 계속.

Branch 이름 기본 제안은 Issue가 있으면 `work/<issue-number>-<slug>`, 없으면 `work/<slug>`. 기존 Branch 재사용을 우선한다. 제안과 실제 생성 상태를 구분한다. Issue/Branch 생성도 대상과 내용을 보여주고 별도 write 승인을 받은 뒤 수행한다. 저장 시점에 함께 승인받을 수 있으나 내용 승인만으로 생성하지 않는다.

## Stage 저장

1. Content Approval과 별도 Persistence Approval을 확인한다. Repository, Branch, Stage 파일과 ADR, 예상 commit 내용을 보여준다. 원격 승인 전에는 write하지 않는다.
2. 준비 당시 HEAD와 파일 내용을 기준으로 write 직전 최신 HEAD 및 대상 파일을 다시 읽는다. 연결이 복구됐거나 이전 응답이 불명확했다면 먼저 Reconcile한다.
3. HEAD가 전진했어도 대상 파일이 같으면 최신 HEAD를 기반으로 계속한다. 같은 artifact가 바뀌면 차이를 보여주고 GitHub 유지 / Chat 적용 / 병합 / 저장 취소를 선택받는다. 선택 전 자동 overwrite하지 않는다.
4. 현재 도구의 다중 파일 commit 기능을 사용하거나 최신 parent/tree 기반으로 승인된 파일들만 tree→commit→non-force ref update한다. 파일별 commit만 가능한 도구라면 Stage 단일 commit 계약을 깨지 말고 수동 fallback을 제공한다. 중간 object 생성은 저장 성공이 아니다.
5. race로 ref update가 실패하면 최신 상태를 다시 읽고 충돌을 재평가한다. force push나 과거 상태로 되돌리기는 금지한다. 응답 timeout은 실패 확정이 아니므로 ref와 파일을 재조회하여 중복 commit을 피한다.
6. Branch HEAD와 파일을 다시 읽어 저장 결과를 확인한 뒤 실제 commit 링크와 `GitHub 저장: 성공`을 안내한다. 확인 불가면 저장 성공으로 주장하지 않는다. 실패·대기 사유와 다음 선택을 안내한다.

## Reconcile

재연결 자체는 Issue/Branch/파일 생성 트리거가 아니다. 현재 Repository·Issue·Branch·파일을 읽고 사용자가 수동으로 저장한 부분을 인정한다. 같으면 재저장하지 않는다. 누락분만 식별하고 필요한 write의 승인을 받은 뒤 적용한다. 충돌은 사용자 선택 전 자동 덮어쓰기하지 않는다.

# GitHub Workflow

전제: `target_repository = owner/repository`. Root router에서 사용자가 현재 작업 대상으로 확인한 Repository가 확정된 뒤 이 문서를 읽는다.

GitHub는 durable Source of Truth이며 Plugin은 자체 GitHub 서버/API를 제공하지 않는다. 현재 호스트의 연결 도구를 발견하고 실제 read/write capability를 확인한다. 도구가 안 보임, 인증 실패, repository read 거부, read-only, branch 생성 거부, commit/ref 갱신 실패, 일시 오류를 관측 가능한 범위에서 구분한다. 구분할 수 없으면 원인을 추측하지 않고 미확인으로 표시한다. 권한 metadata는 write 성공의 증거가 아니다.

## Planning-time read

대상 Repository 확정 후 기획에 필요한 Fact를 읽는다. 사용자가 지정했거나 기존 작업과 명확히 연결된 Issue·Branch·artifact가 있으면 확인한다. 명확한 기존 작업 Branch가 하나면 재사용을 우선하고, 후보가 여러 개면 선택받는다. Issue 전체를 이번 범위로 해석하지 않는다. 이때 새 Issue/Branch 생성 방식은 묻거나 결정하지 않는다. Target Repository 선택은 Persistence topology 선택이 아니다.

## Persistence topology

Stage 전체 내용의 Content Approval 뒤 Persistence Decision을 한 번 요청한다. Issue가 없으면 대상 Repository, 생성할 Issue 초안·Branch 제안, 저장할 Stage 파일·관련 ADR과 commit 범위를 먼저 보여주고 다음 세 경로를 제시한다:

1. Issue를 생성하고 Issue 기반 Branch로 진행.
2. Issue 없이 Branch만 생성.
3. GitHub 저장 없이 계속.

1/2 선택 자체가 Persistence Approval이다. 3을 선택하면 GitHub write를 하지 않는다. 기존 Issue·Branch가 명확하면 재사용을 우선하고, Repository·Branch·Stage 파일·관련 ADR·commit 범위를 보여준 뒤 이 경로로 저장할지 한 번만 묻는다. Branch 이름 기본 제안은 Issue가 있으면 `work/<issue-number>-<slug>`, 없으면 `work/<slug>`. 제안과 실제 생성 상태를 구분한다. Content Approval만으로 Issue·Branch·파일을 생성하지 않는다.

## Stage 저장

1. Content Approval과 별도 Persistence Decision을 확인한다. 위 1/2 선택 또는 기존 경로 저장 선택이 해당 Issue·Branch·Stage 파일·ADR write의 승인이다. 승인된 범위의 저장에 추가 write 승인을 묻지 않는다.
2. 준비 당시 HEAD와 파일 내용을 기준으로 write 직전 최신 HEAD 및 대상 파일을 다시 읽는다. 연결이 복구됐거나 이전 응답이 불명확했다면 먼저 Reconcile한다.
3. HEAD가 전진했어도 대상 파일이 같으면 최신 HEAD를 기반으로 계속한다. 선택 당시의 Issue·Branch·대상 파일 상태가 바뀌거나 충돌이 생기면 차이를 보여주고 다시 확인한다. 같은 artifact가 바뀌면 GitHub 유지 / Chat 적용 / 병합 / 저장 취소를 선택받는다. 선택 전 자동 overwrite하지 않는다.
4. 현재 도구의 다중 파일 commit 기능을 사용하거나 최신 parent/tree 기반으로 승인된 파일들만 tree→commit→non-force ref update한다. 파일별 commit만 가능한 도구라면 Stage 단일 commit 계약을 깨지 말고 수동 fallback을 제공한다. 중간 object 생성은 저장 성공이 아니다.
5. race로 ref update가 실패하면 최신 상태를 다시 읽고 충돌을 재평가한다. force push나 과거 상태로 되돌리기는 금지한다. 응답 timeout은 실패 확정이 아니므로 ref와 파일을 재조회하여 중복 commit을 피한다.
6. Branch HEAD와 파일을 다시 읽어 저장 결과를 확인한 뒤 실제 commit 링크와 `GitHub 저장: 성공`을 안내한다. 확인 불가면 저장 성공으로 주장하지 않는다. 실패·대기 사유와 다음 선택을 안내한다.

## Reconcile

재연결 자체는 Issue/Branch/파일 생성 트리거가 아니다. 현재 Repository·Issue·Branch·파일을 읽고 사용자가 수동으로 저장한 부분을 인정한다. 같으면 재저장하지 않는다. 기존 Persistence Decision이 승인한 범위의 누락분만 적용한다. 대상 상태가 바뀌었거나 승인 범위 밖의 write가 필요하면 차이를 보여주고 다시 확인한다. 충돌은 사용자 선택 전 자동 덮어쓰기하지 않는다.

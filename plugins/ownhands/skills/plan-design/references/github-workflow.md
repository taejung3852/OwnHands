# GitHub Workflow

GitHub는 durable Source of Truth이며 Plugin은 자체 GitHub 서버/API를 제공하지 않는다. 현재 호스트의 연결 도구를 발견하고 실제 read/write capability를 확인한다. 도구가 안 보임, 인증 실패, repository read 거부, read-only, branch 생성 거부, commit/ref 갱신 실패, 일시 오류를 관측 가능한 범위에서 구분한다. 구분할 수 없으면 원인을 추측하지 않고 미확인으로 표시한다. 권한 metadata는 write 성공의 증거가 아니다.

## Target Repository Resolution

Plugin source repository와 사용자의 작업 target repository는 별개다. OwnHands Plugin을 사용한다는 이유로 `taejung3852/OwnHands`를 기본값으로 사용하지 않는다.

1. 현재 대화에서 사용자가 Repository를 명시했다면 이를 대상으로 사용한다.
2. 그렇지 않으면 기존 작업 문맥에서 하나의 Repository로 명확하게 확정된 경우에만 재사용한다.
3. Repository가 미확정이면 repository-specific Fact Gathering 전에 사용자에게 대상 Repository 선택을 요청한다. 후보가 여러 개면 후보를 보여주고 선택받는다. 단일 후보처럼 보여도 확정된 문맥이 아니면 추측하지 않는다.

Repo-aware 작업에서 대상이 확정되기 전에는 README, package.json, Issue, Branch 등 repository-specific 조회를 시작하지 않는다. 저장소가 없는 순수 아이디어는 No-Repo 흐름으로 대화할 수 있으며, 저장소 Fact를 있는 것처럼 만들지 않는다.

## Planning-time read

대상 Repository 확정 후 기획에 필요한 Fact를 읽는다. 사용자가 지정했거나 기존 작업과 명확히 연결된 Issue·Branch·artifact가 있으면 확인한다. 명확한 기존 작업 Branch가 하나면 재사용을 우선하고, 후보가 여러 개면 선택받는다. Issue 전체를 이번 범위로 해석하지 않는다. 이때 새 Issue/Branch 생성 방식은 묻거나 결정하지 않는다. Target Repository 선택은 Persistence topology 선택이 아니다.

## Persistence topology

Stage 전체 내용의 Content Approval 뒤 별도 Persistence Approval로 GitHub 저장 의사를 확인한다. Persistence Approval 후 Issue가 없고 사용자가 저장을 원하면 Issue/Branch 세 경로를 제시한다:

1. Issue를 생성하고 Issue 기반 Branch로 진행.
2. Issue 없이 Branch만 생성.
3. GitHub 저장 없이 계속.

기존 Issue·Branch가 명확하면 재사용을 우선한다. Branch 이름 기본 제안은 Issue가 있으면 `work/<issue-number>-<slug>`, 없으면 `work/<slug>`. 제안과 실제 생성 상태를 구분한다. Issue/Branch 생성은 대상과 내용을 보여주고 별도 write 승인을 받은 뒤 수행한다. 저장 시점에 함께 승인받을 수 있으나 내용 승인만으로 생성하지 않는다.

## Stage 저장

1. Content Approval과 별도 Persistence Approval을 확인한다. 필요한 저장 경로를 선택한 뒤 Repository, Branch, Stage 파일과 ADR, 예상 commit 및 새 Issue/Branch 생성 내용을 보여준다. 구체적인 원격 write 승인 전에는 생성·저장하지 않는다.
2. 준비 당시 HEAD와 파일 내용을 기준으로 write 직전 최신 HEAD 및 대상 파일을 다시 읽는다. 연결이 복구됐거나 이전 응답이 불명확했다면 먼저 Reconcile한다.
3. HEAD가 전진했어도 대상 파일이 같으면 최신 HEAD를 기반으로 계속한다. 같은 artifact가 바뀌면 차이를 보여주고 GitHub 유지 / Chat 적용 / 병합 / 저장 취소를 선택받는다. 선택 전 자동 overwrite하지 않는다.
4. 현재 도구의 다중 파일 commit 기능을 사용하거나 최신 parent/tree 기반으로 승인된 파일들만 tree→commit→non-force ref update한다. 파일별 commit만 가능한 도구라면 Stage 단일 commit 계약을 깨지 말고 수동 fallback을 제공한다. 중간 object 생성은 저장 성공이 아니다.
5. race로 ref update가 실패하면 최신 상태를 다시 읽고 충돌을 재평가한다. force push나 과거 상태로 되돌리기는 금지한다. 응답 timeout은 실패 확정이 아니므로 ref와 파일을 재조회하여 중복 commit을 피한다.
6. Branch HEAD와 파일을 다시 읽어 저장 결과를 확인한 뒤 실제 commit 링크와 `GitHub 저장: 성공`을 안내한다. 확인 불가면 저장 성공으로 주장하지 않는다. 실패·대기 사유와 다음 선택을 안내한다.

## Reconcile

재연결 자체는 Issue/Branch/파일 생성 트리거가 아니다. 현재 Repository·Issue·Branch·파일을 읽고 사용자가 수동으로 저장한 부분을 인정한다. 같으면 재저장하지 않는다. 누락분만 식별하고 필요한 write의 승인을 받은 뒤 적용한다. 충돌은 사용자 선택 전 자동 덮어쓰기하지 않는다.

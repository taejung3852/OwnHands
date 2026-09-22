# ADR 선별과 저장

장기적으로 참고할 아키텍처 선택, 책임 경계 변경, 중요한 정책, 의미 있는 대안 기각, Spec/Build가 반복 의존할 결정만 ADR 후보로 삼는다. Decision마다 ADR을 만들지 않는다. 단순 문구나 지역 구현 상세는 Intent/Spec에 둔다.

현재 docs/adr/와 인덱스를 먼저 읽는다. 같은 결정의 후속 확정이면 기존 ADR을 정렬하고, 새 결정이면 기존 번호 체계에서 중복 없이 후보를 작성한다. Context / Decision / 대안·결과와 관련 Intent/Spec 링크를 담는다. 공식 인용과 OwnHands의 선택을 구분한다.

관련 ADR 변경 전체를 해당 Stage의 내용 검토에 포함하고, 별도 저장 승인 후 intent.md 또는 spec.md와 한 commit으로 묶는다. ADR 인덱스를 바꾸면 함께 승인·저장 대상에 포함한다. 무관한 ADR과 미승인 결정을 섞지 않는다.

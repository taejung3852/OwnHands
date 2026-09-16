# 문서 인덱스

정식 원문은 `docs/` 아래에 있다. README와 Issue·Project는 요약과 링크로 연결한다.

---

## 읽는 순서

### 처음 보는 경우

1. [프로젝트 여정](story/project-journey.md) — 왜 시작했고 무엇을 배웠는가
2. [왜 V2인가](story/why-v2.md) — 무엇을 바꾸고 왜 바꾸는가 *(편집 초안)*
3. [V2 개요](v2/overview.md) — 무엇을 만들려는가
4. [로드맵](v2/roadmap.md) — 어떤 순서로 가는가

### 설계 검토

1. [결정 상태표](v2/decisions.md) — 무엇이 확정이고 무엇이 아닌가. 먼저 읽는다
2. [V2 개요](v2/overview.md) — 책임 관계
3. [Codex 공식 문서 확인](references/codex-official.md) — 실제 형식·기능·제약의 기준
4. [Anthropic Playbook 대응](references/anthropic-playbook.md) — 가져온 것과 가져오지 않은 것
5. [로드맵](v2/roadmap.md) — 순서와 각 단계에 남겨둔 질문

### 구현 작업

1. [결정 상태표](v2/decisions.md) — 대신 확정하면 안 되는 것을 먼저 확인
2. [개발 방법](v2/development-method.md) — 공식 조사 → 네이티브 대응 → 최소 구현
3. [Codex 공식 문서 확인](references/codex-official.md) — 확인된 것과 미확인의 구분
4. [V2 개요](v2/overview.md) — Skill·Reference·Agent·Script의 책임 구분
5. [로드맵](v2/roadmap.md) — 현재 마일스톤과 선행 조건

대신 확정하지 말 것: Company 정책 우선순위, Skill 이름·수, 초기 Agent 역할·수, 다른 vendor 지원 방식, Eval 지표, 마일스톤 내부 설계.

### V1 기록

1. [V1 기록](history/v1.md) — 구현 범위·마일스톤·보존 기준 커밋
2. [핵심 발언 기록](history/conversation-notes.md) — 원문과 맥락
3. V1 원본 문서: `adr/` · `product/` · `m5-r/` · `reviews/` · `spikes/` · `superpowers/` · `design/` · `diagrams/` · `research/` · `dogfooding/`

---

## 파일 배치

```text
docs/
├── README.md                  이 문서
├── story/
│   ├── project-journey.md     시작 → V1 → 한계 발견 → Playbook → V2
│   └── why-v2.md              전환 이유 (1인칭, 편집 초안)
├── v2/
│   ├── overview.md            큰 구조와 책임 관계
│   ├── roadmap.md             실행 순서와 각 단계의 남겨둔 결정
│   ├── decisions.md           확정 / 생각 / 함께 결정 / 후속
│   └── development-method.md  각 단계 진행 방식
├── references/
│   ├── anthropic-playbook.md  SDLC 큰 틀, 가져온 것과 안 가져온 것
│   └── codex-official.md      실제 형식·기능·권한·제약, 확인일 기록
├── history/
│   ├── v1.md                  구현 범위, 마일스톤, 보존 기준
│   └── conversation-notes.md  사용자 발언 원문
└── (V1 원본)                   adr/ product/ m5-r/ reviews/ spikes/
                               superpowers/ design/ diagrams/ research/ dogfooding/
```

---

## GitHub 공간별 역할

| 위치 | 역할 |
|---|---|
| README | 프로젝트가 무엇이고 왜 V2로 가는지 알려주는 짧은 입구 |
| `docs/` | 여정·공식 근거·설계·결정·로드맵의 원문 |
| Milestone | 여러 Issue/PR을 하나의 완료 목표로 묶는 실행 단위 |
| Issue | 하나의 조사·결정·구현 질문과 그 결과 |
| Project | Issue/PR의 현재 상태를 보는 운영 보기 — [OwnHands V2](https://github.com/users/taejung3852/projects/2) |
| PR/Commit | 실제 변경과 검증 근거 |
| Wiki | 핵심 원문 저장소로 사용하지 않는다. 원문은 `docs/`다 |

---

## 작업 관리 현황 (2026-09-16)

| 항목 | 상태 |
|---|---|
| [#101](https://github.com/taejung3852/OwnHands/issues/101) V2 전체 추적 | 입구, 진행 중 |
| [#102](https://github.com/taejung3852/OwnHands/issues/102) 공식 자료 조사 | 조사 |
| [#103](https://github.com/taejung3852/OwnHands/issues/103) Skill 구성·이름 | 사용자와 결정 |
| [#104](https://github.com/taejung3852/OwnHands/issues/104) Agent 역할·위임 | 사용자와 결정 |
| [#105](https://github.com/taejung3852/OwnHands/issues/105) 정책 연결 | 사용자 생각 단계 |
| [#106](https://github.com/taejung3852/OwnHands/issues/106) 평가 설계 | 후속 결정 |
| V2 Milestone | [`V2-M0`~`V2-M7`](https://github.com/taejung3852/OwnHands/milestones) 등록 |
| V1 추적 이슈 #7·#89·#99 | `not planned`로 종료, 방향 변경에 의한 대체 |

V2 작업은 `v2` 라벨로 구분한다. Type·Area·Priority는 기존 저장소 라벨(`type:*`·`area:*`·`priority:*`)을 쓰고 Project에 중복 필드를 만들지 않았다.

---

## 문서 작성 규칙

- 서술은 한국어를 기본으로 한다. 기술명·API·파일명은 정확히 보존한다.
- 영문 문서 이중 유지나 문서 동기화 시스템은 두지 않는다.
- 방향 확정과 구현 완료를 분리한다. 방향이 정해졌다는 이유로 기능이 구현됐다고 쓰지 않는다.
- 상태는 `방향 확정 / 사용자 생각·검토 중 / 제안 / 후속 결정`으로 구분한다.
- 확인하지 못한 것은 `미확인`으로 남긴다. `없음`·`비어 있음`·`완료`로 추정하지 않는다.
- 파일 개수를 맞추려고 쪼개지 않는다. 내용이 짧으면 합친다.

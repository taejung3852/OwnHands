# OwnHands 문서 인덱스

> **정식 원문은 이 `docs/` 아래에 있다.** README와 Issue·Project는 요약과 링크로 연결한다.
> 같은 내용을 여러 곳에 중복해서 유지하지 않는다.

---

## 읽는 순서 — 당신은 누구인가?

### 🆕 이 프로젝트를 처음 봤다

```text
1. 프로젝트 여정      왜 시작했고 무엇을 배웠는가
2. 왜 V2인가          무엇을 바꾸고 왜 바꾸는가
3. V2 개요            무엇을 만들려는가
4. 로드맵             어떤 순서로 가는가
```

1. [프로젝트 여정](story/project-journey.md)
2. [왜 V2인가](story/why-v2.md) *(편집 초안)*
3. [V2 개요](v2/overview.md)
4. [로드맵](v2/roadmap.md)

### 🔍 설계를 검토하려 한다

```text
1. 결정 상태표        무엇이 확정이고 무엇이 아닌가  ← 먼저 읽는다
2. V2 개요            책임 관계
3. Codex 공식 문서    실제 형식·기능·제약의 기준
4. Anthropic Playbook 무엇을 가져오고 무엇을 안 가져왔는가
5. 로드맵             순서와 남겨둔 질문
```

1. [결정 상태표](v2/decisions.md) ⭐
2. [V2 개요](v2/overview.md)
3. [Codex 공식 문서 확인](references/codex-official.md)
4. [Anthropic Playbook 대응](references/anthropic-playbook.md)
5. [로드맵](v2/roadmap.md)

### 🤖 구현 에이전트로 작업하려 한다

```text
1. 결정 상태표        대신 확정하면 안 되는 것을 먼저 확인  ← 필수
2. 개발 방법          공식 조사 → 네이티브 대응 → 최소 구현
3. Codex 공식 문서    확인된 것과 미확인을 구분
4. V2 개요            수단(Skill/Reference/Agent/Script) 구분
5. 로드맵             현재 마일스톤과 선행 조건
```

1. [결정 상태표](v2/decisions.md) ⭐ **필수**
2. [개발 방법](v2/development-method.md)
3. [Codex 공식 문서 확인](references/codex-official.md)
4. [V2 개요](v2/overview.md)
5. [로드맵](v2/roadmap.md)

> ⚠️ **대신 확정하지 말 것**: Company 정책 우선순위, Skill 이름·수, 초기 Agent 역할·수,
> 다른 vendor 지원 방식, Eval 지표, 마일스톤 최종 경계.

### 📚 V1 기록을 찾는다

1. [V1 기록](history/v1.md) — 구현 범위·마일스톤·보존 기준 커밋
2. [핵심 발언 기록](history/conversation-notes.md) — 사용자 원문과 맥락
3. V1 원본 문서: `docs/adr/` · `docs/product/` · `docs/m5-r/` · `docs/reviews/` · `docs/spikes/` · `docs/superpowers/`

---

## 전체 문서 지도

```text
docs/
├── README.md                          이 문서
│
├── story/                             사용자의 생각과 프로젝트 여정
│   ├── project-journey.md             시작 → V1 → 한계 발견 → Playbook → V2
│   └── why-v2.md                      전환 이유 (1인칭 · 편집 초안)
│
├── v2/                                V2의 방향과 실행
│   ├── overview.md                    큰 구조와 책임 관계
│   ├── roadmap.md                     실행 순서 후보 (V2-M0~M7)
│   ├── decisions.md                   ⭐ 확정 / 생각 / 미정
│   └── development-method.md          각 단계 진행 방식
│
├── references/                        공식 근거
│   ├── anthropic-playbook.md          SDLC 큰 틀 · 가져온 것과 안 가져온 것
│   └── codex-official.md              실제 형식·기능·권한·제약 (확인일 기록)
│
├── history/                           V1과 과거 기록
│   ├── v1.md                          구현 범위 · 마일스톤 · 보존 기준
│   └── conversation-notes.md          사용자 원문 발언
│
└── [V1 원본 문서]                      adr/ product/ m5-r/ reviews/ spikes/
                                       superpowers/ design/ diagrams/ research/ dogfooding/
```

---

## 문서별 역할

| 문서 | 답하는 질문 |
|---|---|
| [project-journey.md](story/project-journey.md) | 왜 시작했고, 무엇을 만들었고, 무엇을 배웠는가? |
| [why-v2.md](story/why-v2.md) | 무엇을 바꾸고 왜 바꾸는가? |
| [overview.md](v2/overview.md) | V2는 무엇을 만들려는가? 책임은 어떻게 나뉘는가? |
| [roadmap.md](v2/roadmap.md) | 어떤 순서로 진행하는가? 각 단계의 결과는? |
| [decisions.md](v2/decisions.md) | **무엇이 확정이고 무엇이 아직 아닌가?** |
| [development-method.md](v2/development-method.md) | 각 마일스톤을 어떻게 진행하는가? |
| [anthropic-playbook.md](references/anthropic-playbook.md) | 공식 내용 / 준 의미 / 자체 선택은 각각 무엇인가? |
| [codex-official.md](references/codex-official.md) | Codex가 실제로 무엇을 지원하는가? 무엇을 안 만들어도 되는가? |
| [v1.md](history/v1.md) | V1은 무엇을 만들었고 어디에 보존돼 있는가? |
| [conversation-notes.md](history/conversation-notes.md) | 사용자가 실제로 무엇을 말했는가? |

---

## GitHub 공간별 역할

| 위치 | 역할 |
|---|---|
| **README** | 프로젝트가 무엇이고 왜 V2로 가는지 알려주는 짧은 입구 |
| **`docs/`** | 사용자 생각·프로젝트 여정·공식 근거·큰 설계·결정·로드맵의 **원문** |
| **Milestone** | 여러 Issue/PR을 하나의 의미 있는 완료 목표로 묶는 실행 단위 |
| **Issue** | 하나의 조사·결정·구현 질문과 그 결과 |
| **Project** | 같은 Issue/PR의 현재 상태·마일스톤·결정 대기를 보여주는 운영 보기 |
| **PR/Commit** | 실제 변경과 검증 근거 |
| **Wiki** | 현재 핵심 원문 저장소로 사용하지 않는다. 원문은 `docs/`다. |

---

## 문서 작성 규칙

- 서술은 **한국어**를 기본으로 한다. 기술명·API·파일명은 정확히 보존한다.
- 영문 문서 전체의 이중 유지나 문서 동기화 시스템은 두지 않는다.
- **방향 확정과 구현 완료를 분리한다.** 방향이 정해졌다는 이유로 기능이 구현됐다고 쓰지 않는다.
- 상태 표시: `방향 확정 / 사용자 생각·검토 중 / 제안 / 후속 결정`, 필요하면 `미구현 / 구현 기록 있음 / 검증 범위`
- 확인하지 못한 것은 `미확인`으로 남긴다. `없음`·`비어 있음`·`완료`로 추정하지 않는다.
- 파일 개수를 맞추기 위해 불필요하게 쪼개지 않는다. 내용이 짧으면 합친다.

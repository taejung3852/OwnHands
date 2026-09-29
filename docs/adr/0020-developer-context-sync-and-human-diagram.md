# ADR-0020: 사람의 개발 컨텍스트 이해와 경량 다이어그램의 책임을 분리한다

- 상태: Accepted — ELI5 제외와 두 Skill의 책임 분리 방향 확정. 호출·배포·검증의 세부 계약은 후속 Intent/Spec에서 확정한다.
- 일자: 2026-09-29
- 관련: [#163](https://github.com/taejung3852/OwnHands-Codex/issues/163), 상위 tracker [#154](https://github.com/taejung3852/OwnHands-Codex/issues/154)
- 형제 작업: [#162 — Build·Test 현행 진단](https://github.com/taejung3852/OwnHands-Codex/issues/162). 실행·검증 workflow 재설계는 이 ADR의 범위가 아니다.
- 부분 대체: [ADR-0018](0018-core-and-companion-skills.md)의 ELI5 활용·번들 제공, [ADR-0017](0017-guided-planning-and-visual-approval.md)의 ELI5 전용 설명 의존성.
- 역사적 선행: [ADR-0002 — Explain](0002-explain-visual-story-cards.md).
- 관련 Intent/Spec: #163의 후속 Plan & Design에서 작성한다. [기존 Chat Plan & Design Spec](../specs/chat-plan-design-flow/spec.md)은 영향받는 선행 계약이며 이번 변경의 승인 Spec이 아니다.
- 조회 기준: `develop@33afe8793830b6027746ca2b95615494cdd890e3`. 문서 저장은 Skill 구현·삭제·배포 또는 runtime 검증 완료가 아니다.

## Context

사용자는 에이전트가 개발하는 동안 사람이 현재 상황을 빠르게 이해하고 판단할 수 있어야 한다고 요구했다. 필요한 것은 결과물을 보기 좋게 꾸미는 기능보다 **현재 무엇을 만들고 있고, 무엇이 바뀌었으며, 어디서 사람이 판단해야 하는지 이해하는 능력**이다.

기존 `explain` 대신 범용 `eli5`를 임시로 활용했지만, 사용자는 간단한 구조 질문에도 HTML 제작이 개입하는 방식이 무겁다고 느꼈다. 이는 사용자 경험 보고이며 실행 시간이나 토큰 절감량을 측정한 결과는 아니다.

ADR-0018은 범용 ELI5 활용·함께 제공하는 방향을, ADR-0017과 기존 Spec은 승인 전 ELI5 설명을 선택했다. 이번 결정은 그 선택을 보충하는 것이 아니라 설명 책임과 배포 경계를 바꾸므로 새 ADR로 남긴다. 기존 결정과 당시 실행·실패 기록은 삭제하지 않는다.

## Decision — 확정된 방향

### 1. 범용 ELI5는 OwnHands에서 제외한다

`eli5`를 OwnHands 번들과 필수 의존성에서 제외한다. 필요하면 사용자가 개인 global Skill로 별도 관리한다. OwnHands가 사용자 global 파일을 삭제·이동하거나 자동 설치·갱신하는 기능은 만들지 않는다.

이 결정은 ELI5의 일반적인 유용성을 부정하는 것이 아니라 OwnHands가 소유할 책임을 좁히는 선택이다. 기존 배포물에서 제거하는 구현은 후속 승인된 변경으로 수행한다.

### 2. developer-context-sync가 사람의 개발 맥락 이해를 담당한다

`developer-context-sync`는 사용자가 현재 개발 과정에 다시 합류하도록 돕는 사용자-facing Skill이다. 기존 `explain`이 맡으려던 역할을 이 목적에 맞게 재정의한다. 커밋·파일 목록만 요약하는 기능이나 에이전트의 메모리를 대체하는 기능으로 만들지 않는다.

사람에게 필요한 목적·책임·핵심 흐름·변경 이유·영향·미확인 사항·판단 지점을 질문 범위에 맞게 연결한다. `ONBOARD`, `CATCH-UP`, `DEEP-DIVE`는 후속 설계의 출발점으로 삼되 세부 입출력과 읽기 범위는 Spec에서 정한다.

### 3. human-diagram은 경량 시각화 Companion으로 분리한다

`human-diagram`은 Context Sync가 관계·흐름을 그림으로 설명할 때 사용하는 재사용 가능한 Companion이다. 특정 SDLC 단계나 Context Sync에만 종속시키지 않는다. `plan-design` 등 다른 호출자와의 연결 범위는 후속 설계에서 정한다.

기본 출력 방향은 **작은 Markdown Mermaid + 짧은 읽는 법**이다. 한 그림은 한 질문과 한 추상화 수준에 집중한다. 텍스트가 더 명료한 질문에는 그림을 강제하지 않는다. HTML 제작, 브라우저 실행, SVG/PNG 렌더링, 파일 생성·설치를 기본 진입 조건으로 삼지 않는다.

### 4. 설명은 증거·이해 확인·승인을 대신하지 않는다

코드·테스트·Spec·ADR·diff 등 질문에 필요한 근거로 설명하고, 관측한 구현·문서의 의도·추정·제안을 구분한다. 변경 비교의 기준이나 알 수 없는 경로를 지어내지 않는다. 그림과 설명은 근거의 표현이지 실행 성공의 증거가 아니다.

설명을 제공했다는 사실만으로 사람이 이해했거나 내용을 승인했다고 간주하지 않는다. 내용 승인과 저장 승인 분리는 유지한다. 설명 호출 자체가 Build·Verify·Review 상태를 전진시키거나 코드 변경·병합을 승인하지 않는다.

## 기존 결정 중 무엇을 대체하는가

| 대상 | 대체하는 부분 | 유지하는 부분 |
|---|---|---|
| ADR-0018 | OwnHands가 ELI5를 설명용으로 채택하고 번들·설치 대상으로 제공한다는 방향 | Core/Companion 구분, 외부 원본의 출처·버전·라이선스 관리, Ponytail 관련 별도 검토 |
| ADR-0017 | 승인 설명을 반드시 ELI5 Companion에 의존시키는 방향 | 승인 전 이해 지원, GORE, 단계·미결정 사항 표시, 내용 승인과 저장 승인 분리 |
| ADR-0002 | 예전 Explain을 그대로 복원하지 않고 Context Sync로 역할을 재정의하는 후속 방향 | 당시 문제·설계·실행 기록의 역사적 근거 |

ADR-0017의 자동 ELI5 자리에 Context Sync를 매번 자동 호출하도록 단순 치환하지 않는다. 승인 전 설명의 구체적인 형태와 호출 계약은 아직 미결정이다. 기존 Spec과 실행 지침의 ELI5 연결은 후속 설계·구현에서 정렬하며, 이 ADR 파일이 저장됐다고 설치된 Plugin의 동작이 바뀐 것으로 보지 않는다.

## 검토한 대안과 결과

| 대안 | 판단 |
|---|---|
| ELI5를 유지하고 모든 설명을 맡긴다 | 사용자가 요청한 개발 맥락 중심의 책임과 가벼운 기본 경로를 충족하는 방향으로 채택하지 않는다. 개인 global 사용은 열어 둔다. |
| Mermaid 그림 Skill 하나만 만든다 | 표현 수단은 생기지만 무엇을 이해해야 하는지와 현재 변화·판단 지점을 재구성하는 책임이 남는다. |
| 기존 Explain을 거대한 단일 Skill로 재구현한다 | 맥락 파악과 시각화·렌더링이 다시 결합되고 다른 Skill에서 부분 재사용하기 어렵다. |
| Context Sync와 Human Diagram의 책임을 나눈다 | 채택한다. 대신 두 Skill의 입출력·근거 재사용·호출 복귀와 배포 경계를 후속 Spec에서 명확히 해야 한다. |

이 구조가 실제로 더 빠르고 이해하기 쉬운지는 대표 사용 사례와 사용자 피드백으로 확인한다. 아직 측정하지 않은 속도·토큰·품질 향상을 성과로 기록하지 않는다.

## 다음 Plan & Design에서 확정할 사항

1. **사용 시나리오와 출력 계약:** 처음 이해하기, 기준 이후 변경 따라잡기, 한 부분 이해하기에서 무엇을 읽고 무엇을 보여줄지. 비교 기준이 없을 때의 처리와 설명 범위도 정한다.
2. **호출과 승인 UX:** 사용자 직접 호출, 다른 Skill의 보조 호출, 원래 작업으로의 복귀를 구분한다. 기존 승인 전 ELI5를 대체할 경량 요약·선택적 그림의 계약을 정한다.
3. **배포와 이전:** Chat Plugin / Codex 제공 범위, 기준 원본 경로, 최소 references, 기존 ELI5 연결 및 잔존 Explain 자산의 처리 범위를 정한다. 앞선 디렉터리 예시를 확정된 배포 구조로 간주하지 않는다.
4. **완료 기준과 검증:** 작은 대표 사례, 근거 추적, 미확인 표시, Mermaid 소스 점검과 실제 렌더링의 구분, 관련 회귀 검사와 호스트 runtime 관측 범위를 정한다.

이미 확정한 ELI5 제외와 두 Skill의 책임 분리를 다시 선택지로 되돌리지 않는다. 새로운 근거나 충돌이 발견되면 그 차이와 영향을 명시한다. 이 ADR은 Intent/Spec 전체 승인이나 Build 시작 승인이 아니다.

## 적용 범위와 현재 상태

이번 저장은 이 ADR, ADR-0017·0018의 부분 대체 안내, ADR 인덱스 연결만 포함한다. 기존 승인 Spec, Skill, metadata, 패키징, 테스트·Eval은 변경하지 않는다. 다음 설계에서는 그 활성 계약을 조사하고 승인된 범위만 조정한다. 과거 E2E와 회고 기록을 새 상태처럼 고쳐 쓰지 않는다.

Build·Test 재설계(#162), Reviewer 통합, Hook/Gate 제거, Ponytail 채택 변경, 자동 watcher·매 커밋 보고, 개인 이해도 프로파일링·필수 퀴즈, 새 렌더러·MCP 서버는 이 결정에 포함하지 않는다.

## 참고 후보

다음은 역할·원칙을 검토할 후보이며 전체 원문 복제나 설치를 승인한 목록이 아니다. 채택 전에 해당 원문·revision·license와 필요한 범위를 확인한다. 외부 원본의 권고와 OwnHands의 선택을 구분한다.

- [uh-developer-context-sync](https://github.com/jyb1018/AI-Development-harness/blob/main/skills/uh-developer-context-sync/SKILL.md) / [uh-human-diagramming](https://github.com/jyb1018/AI-Development-harness/blob/main/skills/uh-human-diagramming/SKILL.md)
- [mgranberry/mermaid-diagram-skill](https://github.com/mgranberry/mermaid-diagram-skill)
- [championswimmer/tech-doc-skills](https://github.com/championswimmer/tech-doc-skills)
- [chrislacey89/skills](https://github.com/chrislacey89/skills)

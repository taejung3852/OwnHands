# Anthropic AI-Native SDLC Playbook — 대응표

출처: <https://claude.com/blog/the-ai-native-sdlc-playbook> · 확인일 2026-09-16 (HTTP 200)

> **이 문서의 규칙**
> 원문을 저장소에 복제하지 않는다. **공식 내용 / 사용자에게 준 의미 / OwnHands의 선택 / 미결정**을 구분한다.
> 글의 예시 숫자나 조직 구조를 OwnHands의 의무로 추가하지 않는다.
> **이 글은 Codex의 지원 기능을 알려주지 않는다.** 실제 형식·기능·권한은 [Codex 공식 문서](codex-official.md)가 기준이다.

---

## 0. 이 글이 이 프로젝트에서 갖는 위치

사용자는 **OwnHands를 이미 개발하고 있었다.** 이 글을 읽고 프로젝트를 시작한 것이 아니다.

개별 검증과 Dashboard에 집중하던 고민을 **AI-native SDLC 전체의 구성**으로 이해하게 된 계기다.
사용자에게 이 글은 링크 하나짜리 참고문헌이 아니라 **V2의 핵심 참고 자료**다.

> "항상 중심은 공식문서와 아까 너한테 줬던 anthropic 블로그가 될 거야."

---

## 1. 6단계 SDLC

**공식 내용** — 글이 제시하는 단계(원문 표기):

`Stage 1 — Plan` · `Stage 2 — Design` · `Stage 3 — Build` · `Stage 4 — Test` · `Stage 5 — Deploy` · `Stage 6 — Maintain`

**사용자에게 준 의미**

V1이 집중했던 Verification Spec·Baseline·Review·Evidence는 사실 **Test 한 단계**의 문제였다. 그 앞에 Plan·Design이, 뒤에 Deploy·Maintain이 있다는 것이 드러났다.

**OwnHands의 선택**

- 6단계를 **책임 구분의 지도**로 채택한다. → [V2 개요 §2](../v2/overview.md)
- ⚠️ 모든 작은 작업에 여섯 번의 의식이나 승인을 강제하지 않는다.
- ⚠️ **제품의 Stage 순서와 실제 구현 마일스톤 순서는 같을 필요가 없다.**

---

## 2. 세 가지 Artifact

**공식 내용**: `intent.md` (문제 정의와 목표 결과), `spec.md` (요구·설계), `plan.md` (구현 계획 — 파일과 테스트 전략).

**사용자에게 준 의미**: 세 문서가 **서로 다른 질문에 답한다**는 구분이 명확해졌다.

**OwnHands의 선택**

- 세 문서의 **역할 구분**을 채택한다. → [V2 개요 §3](../v2/overview.md)
- ⏳ **정확한 저장 경로·메타데이터·자동화 규칙은 미정이다.**
- ⚠️ 파일 이름이 같다고 해서 글의 워크플로를 그대로 쓴다는 뜻은 아니다.

---

## 3. 프로젝트 지침 파일

**공식 내용**: `CLAUDE.md` — 버전 관리되는 에이전트용 제도적 지식.

**OwnHands의 선택**

- 개념(버전 관리되는 지침)은 채택한다.
- ⚠️ **파일 이름을 그대로 쓰지 않는다.** V2의 1차 플랫폼은 Codex이고, Codex의 지침 파일은 `AGENTS.md`다. 탐색·병합·32 KiB 상한 등 실제 규칙은 [Codex 공식 문서 §1](codex-official.md)을 따른다.

> **이 항목이 이 대응표가 필요한 이유를 잘 보여준다.**
> Anthropic의 예시를 Codex의 지원 기능으로 취급하지 않는다.

---

## 4. Skills · Hooks · Subagents

**공식 내용**: Skills(버전 관리되는 정책 적용), Hooks(승인 게이트와 빌드 시점 guardrail), 병렬 세션과 subagent(동시 작업 흐름).

**사용자에게 준 의미**

V1에서 커진 부담의 상당 부분이 **수단을 구분하지 않은 데서 왔다**는 판단과 연결된다.
무엇을 Skill로, Reference로, Agent로, 기존 도구로, Script로 할지 먼저 나눈다는 원칙이 여기서 구체화됐다.

**OwnHands의 선택**

- Skill·Reference·Agent·Tool·Script·Hook의 **책임을 먼저 구분**한다(✅ 확정). → [V2 개요 §4](../v2/overview.md)
- ✅ 플랫폼이 이미 제공하는 것을 다시 만들지 않는다. 세 가지 모두 Codex에 네이티브로 존재함을 확인했다. → [Codex 공식 문서](codex-official.md)
- 💬 **Skill의 이름·수, 초기 Agent 역할·수는 사용자와 결정한다.**
- ⏳ Hooks의 구체 이벤트·규칙·권한은 후속 설계다.

---

## 5. Continuous Evals

**공식 내용**

- 에이전트 **설정이 바뀔 때마다** 실행한다.
- 모델이나 프롬프트가 바뀐 뒤에도 "에이전트가 같은 기준으로 일하는지" 확인한다.
- 기대 결과가 있는 실제 과제로 구성하고, CI에서 실행하며, 통과율 임계값으로 게이트한다.
- 운영 장애를 영구 eval로 편입한다.
- 설정 변경(skills, hooks, 지침)은 eval을 유발하고, 제품 동작은 PR 리뷰와 운영 모니터링으로 검증한다 — **두 축을 구분한다.**

**사용자에게 준 의미**

**"제품이 좋아졌는가"와 "제품을 만드는 시스템이 좋아졌는가"는 다른 질문**이라는 축이 분명해졌다.
이것이 V2에서 Continuous Evals를 핵심 축으로 두는 이유다.

**OwnHands의 선택**

- ✅ 두 축 구분을 채택한다. → [V2 개요 §1](../v2/overview.md)
- ✅ **초기에 작은 Eval을 시작하고 M5에서 확장한다** — 이것은 **사용자의 결정**이지 글의 지시가 아니다.
- ⏳ 지표·반복 수·비용 상한·자동 실행 주기·**merge 차단 여부는 미정**이다.

> ⚠️ 글은 CI 게이트와 통과율 임계값을 제시하지만, **OwnHands가 merge 차단을 채택했다는 뜻이 아니다.**
> 글의 예시 수치를 OwnHands의 기준으로 옮기지 않는다.

---

## 6. 검증과 리뷰

**공식 내용**: Plan mode(구현 전 읽기 전용 설계 검토), feedback loop(작업의 자동 자기 검증), `REVIEW.md`(사람 리뷰 정책과 게이트 기준), CI/CD 비대화형 실행.

**OwnHands의 선택**

- **작업 중 feedback loop, 별도 맥락의 최종 Verifier, PR Review, Agent System Eval은 서로 다른 책임**으로 구분한다.
- ⚠️ 특정 호스트의 Plan Mode를 사용했다고 프로젝트의 `plan.md` 저장·검토가 끝난다고 가정하지 않는다. Codex에서의 실제 방법은 후속 조사다.
- ⏳ `REVIEW.md` 형태의 리뷰 정책 문서를 둘지는 정하지 않았다.

---

## 7. 운영 모니터링

**공식 내용**: control-band 모니터링 — 운영 지표 감시가 자동 대응을 유발.

**OwnHands의 선택**

- Maintain 단계의 피드백이 다음 Intent와 Eval 사례로 이어진다는 **방향**만 채택한다.
- ⏳ 실제 signal, 자동/수동 경계는 미정이다. (M7 후보)

---

## 8. 조직·역할 (채택하지 않음)

**공식 내용**: product owner, engineers, tech lead, security lead, platform/infrastructure team, service owner, on-call engineer의 역할 분담.

**OwnHands의 선택**

❌ **이 역할 구조를 OwnHands의 요구사항으로 옮기지 않는다.**

- OwnHands는 현재 1인 개발 맥락이고, 사용자가 첫 사용자다.
- 조직 적용을 **목표로 한다는 것**과 조직 구조를 **전제한다는 것**은 다르다.
- 글의 조직 예시를 제품 의무로 만들면, V1에서 겪은 "필요보다 큰 시스템"을 반복하게 된다.

다만 글이 강조하는 원칙 하나는 유지한다.

> 판단이 필요한 모든 결정에 대해 사람이 책임을 진다.

---

## 9. 요약 — 가져온 것과 가져오지 않은 것

| 글의 내용 | OwnHands |
|---|---|
| 6단계 SDLC | ✅ 책임 지도로 채택 (단계마다 의식을 강제하지 않음) |
| `intent.md`·`spec.md`·`plan.md` 역할 구분 | ✅ 채택 (형식·경로는 ⏳ 미정) |
| `CLAUDE.md` | ⚠️ 개념만 채택, 파일명은 Codex의 `AGENTS.md` |
| Skills·Hooks·Subagents | ✅ 책임 구분 채택 (상세는 💬/⏳) |
| Continuous evals (두 축 구분) | ✅ 핵심 축으로 채택 |
| eval CI 게이트·통과율 임계값 | ⏳ 미정 (merge 차단 여부 포함) |
| Plan mode | ⏳ Codex 대응 방법 후속 조사 |
| `REVIEW.md` | ⏳ 미정 |
| control-band 모니터링 | ⏳ 방향만, 상세 미정 |
| 조직 역할 분담 | ❌ 채택하지 않음 |
| 예시 수치·조직 구조 | ❌ 의무로 추가하지 않음 |

---

## 관련 문서

- [Codex 공식 문서 확인](codex-official.md) — 실제 형식·기능·권한의 기준
- [V2 개요](../v2/overview.md) · [결정 상태표](../v2/decisions.md) · [개발 방법](../v2/development-method.md)
- [프로젝트 여정 §4](../story/project-journey.md) — 이 글이 전환 계기가 된 시점

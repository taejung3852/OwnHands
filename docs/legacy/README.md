# V1 아카이브 안내

이 디렉터리에는 문서가 없다. **V1 원본을 어디서 볼 수 있는지 알려주는 안내만 있다.**

## 원본은 어디 있는가

V2 전환 직전 상태를 태그로 보존했다.

```
pre-v2-2026-09-16
```

기준 커밋: [`6d052ac`](https://github.com/taejung3852/OwnHands/commit/6d052acfeba2e0a971bfe11463a5c9b938abf65d)

> ⚠️ **이 태그는 V1의 완성본·정식 릴리스·최종 버전이 아니다.**
> V2 clean-slate 전환 직전의 구현·문서·Skill·테스트 상태를 **다시 찾을 수 있게 한 snapshot**일 뿐이다.
> GitHub Release도 만들지 않았다.

## 태그에서 볼 수 있는 것

| 경로 | 내용 |
|---|---|
| [`src/devharness/`](https://github.com/taejung3852/OwnHands/tree/pre-v2-2026-09-16/src/devharness) | V1 구현 (lifecycle, dashboard, mcp) |
| [`skills/`](https://github.com/taejung3852/OwnHands/tree/pre-v2-2026-09-16/skills) | V1 Skills (`using-ownhands`, `work-map`, `verification-spec`, `baseline`, `review`, `dashboard`) |
| [`legacy/skills/`](https://github.com/taejung3852/OwnHands/tree/pre-v2-2026-09-16/legacy/skills) | V1이 스스로 폐기한 Skills |
| [`tests/`](https://github.com/taejung3852/OwnHands/tree/pre-v2-2026-09-16/tests) | V1 테스트 |
| [`docs/adr/`](https://github.com/taejung3852/OwnHands/tree/pre-v2-2026-09-16/docs/adr) | 아키텍처 결정 기록 (0001~0010) |
| [`docs/product/`](https://github.com/taejung3852/OwnHands/tree/pre-v2-2026-09-16/docs/product) | 제품 계약·JSON 스키마·용어집 |
| [`docs/m5-r/`](https://github.com/taejung3852/OwnHands/tree/pre-v2-2026-09-16/docs/m5-r) | Lifecycle 계약, Claim 검증, Dashboard SDD·설계·검증 |
| [`docs/reviews/`](https://github.com/taejung3852/OwnHands/tree/pre-v2-2026-09-16/docs/reviews) | 마일스톤별 검토 기록 |
| [`docs/spikes/`](https://github.com/taejung3852/OwnHands/tree/pre-v2-2026-09-16/docs/spikes) | 시간 제한 기술 조사 |
| [`docs/superpowers/`](https://github.com/taejung3852/OwnHands/tree/pre-v2-2026-09-16/docs/superpowers) | 당시 plan·spec |
| [`docs/design/`](https://github.com/taejung3852/OwnHands/tree/pre-v2-2026-09-16/docs/design) | 디자인 탐색과 스크린샷 |
| `mcp.json` · `plugin.json` · `pyproject.toml` · `uv.lock` | V1 패키지·MCP·플러그인 정의 |

로컬에서 보려면:

```bash
git show pre-v2-2026-09-16:docs/m5-r/dashboard-sdd.md
```

## 왜 현재 tree에 두지 않는가

V2는 **clean-slate 설계**다. V1 구조의 재사용이나 호환성을 전제하지 않는다.

원본을 현재 tree에 남겨두면 새로 합류한 사람이나 에이전트가 **V2도 이 구조를 기반으로 확장한다고 오해**한다. `pyproject.toml`은 프로젝트를 `devharness` 패키지로 정의하고, `mcp.json`은 `devharness.mcp.server`를 실행하며, `skills/`에는 V1 Skill이 들어 있다. 이것들이 root에 있으면 V2의 출발점처럼 읽힌다.

Git 태그가 원본을 보존하므로 현재 tree에 복제해 둘 이유가 없다.

V2에서 Python 패키지·MCP·플러그인·Skill 구조가 실제로 필요해지면 **해당 마일스톤에서 공식 문서를 조사하고 V2 기준으로 새로 만든다.**

## V1을 어떻게 볼 것인가

**V1은 실패해서 제거한 것이 아니다.**

실제로 구현해 보면서 V2의 방향을 얻은 개발 단계다. 검증 원칙 자체는 유효했고 V2에서도 유지된다. 문제는 원칙이 아니라 그 원칙을 떠받치려고 직접 만들어 운영해야 했던 시스템의 크기였다.

다만 **V1의 구현·검증 결과는 V2의 완료 근거로 자동 승계되지 않는다.**

## 맥락을 읽으려면

| 문서 | 내용 |
|---|---|
| [V1 기록](../history/v1.md) | V1이 무엇을 만들었고 태그의 어디에 있는지 |
| [프로젝트 여정](../story/project-journey.md) | 시작 → V1 → 한계 발견 → V2 |
| [왜 V2인가](../story/why-v2.md) | 전환 이유 |
| [문서 인덱스](../README.md) | 전체 읽는 순서 |

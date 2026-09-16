# #81 provenance 修正 검증 — 2026-09-12

PR #86의 missing-Before 경로에서 변경 전 provenance 부재를 `missing_reason`에 적으면서 After CodeState를 Baseline에 넣던 테스트와 Skill 예외를 수정했다.

- 신뢰 가능한 pre-change CodeState와 Environment가 있으면 해당 참조로 `observations=[]` 및 `missing_reason` Baseline을 만들 수 있다.
- provenance가 없으면 Skill은 Baseline·Formal Review 저장 전에 중단하고 Observation Report / `needs-input`을 제공한다. `needs-input`은 보고서 상태다.
- #80 스키마는 변경하지 않았다. 저장소는 null CodeState와 Baseline 없는 Review를 거부하지만, 유효한 참조의 역사적 provenance는 자동 판별하지 못한다. provenance 확인은 Skill 지침이며 네이티브 에이전트 실행으로 검증하지 않았다.
- 테스트의 Before/After CodeState를 별도 스냅샷으로 분리했다. `current`의 After-only 판정 테스트도 신뢰 가능한 pre-change Baseline 참조를 전제로 한다. Before 관찰 없는 `preserve`/`improve`의 verified 거부를 유지했다.

## 로컬 재검증

Python 3.12.14, CWD `work/ownhands-81`, `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src`:

```sh
../ownhands-80/.venv/bin/python -m unittest tests.test_skill_routing_fixtures tests.test_skill_discovery_contract tests.test_skills -q
# Ran 44 tests in 0.100s — OK
../ownhands-80/.venv/bin/python -m unittest discover -s tests -q
# Ran 391 tests in 6.600s — OK
git diff --check
# no findings
```

전체 테스트 출력에는 `M3 live probe refused or failed: live fixture content drift: AGENTS.md`가 포함된다. unittest 통과를 M3 live 실행 성공으로 해석하지 않는다. 위 결과는 로컬 검증이며 GitHub Actions 또는 네이티브 Skill discovery E2E 증거가 아니다.

Upstream pin/license/호출 기준의 **기록** 완료와 출처 검증 상태를 구분한다. `upstream-skill-policy.md`는 네 스킬의 알려진 값과 unknown/unverified 상태, 호출 조건 및 fallback을 기록한다. 기록 조건은 충족되며 unknown 출처의 검증 완료를 주장하지 않는다.

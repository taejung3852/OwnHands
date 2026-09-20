# Plan: Thin feedback Skill

- **기반 Spec**: [spec.md](spec.md)
- **작성 주체**: Codex
- **일자**: 2026-09-20
- **승인**: 사용자 구현 계획 승인 및 구현 요청 (2026-09-20)
- **Thin feedback Skill 구현**: 완료 — AC-01 재판정 PASS; Initial Review 지적 없음, 최종 fingerprint 확인 후 승인된 Push+PR 진행
- **M7 실제 Closed Loop 검증**: In Progress / UNOBSERVED — AC-04~06 실제 운영 관측 미실행; Verifier Overall UNOBSERVED 유지

## 1. 구현 맥락 및 대상 파일 (Context & Target Files)

사용 프로젝트의 개선 신호를 Markdown으로 보존하고 OwnHands Issue에 연결한다. 실제 개선은 명시 요청 후 기존 Build/Verify/Review로 수행한다.

- NEW `.agents/skills/feedback/SKILL.md`: capture·triage·follow-up 진입점
- NEW `.agents/skills/feedback/references/feedback-contract.md`: 기록 형식·전달·실패·권한 계약
- MODIFY `AGENTS.md`: feedback 라우팅 한 문장
- MODIFY `docs/decisions.md`: Skill 7개·분할 근거·승인된 M7 계약
- MODIFY `docs/roadmap.md`: 구현 및 미관측 상태
- MODIFY `docs/specs/self-improvement-loop/spec.md`: 승인 상태만 반영
- NEW `docs/specs/self-improvement-loop/plan.md`: 실행 계약과 Evidence

기존 Research·Intent·설명 HTML은 보존한다. 기존 Skill·Agent·Hook·M5 task-set/runner/baseline은 수정하지 않는다. 새 Runner·Hook·DB·설치 도구·Eval 항목은 만들지 않는다. 커밋·Push+PR·Merge 승인은 포함하지 않는다.

### 1.1 비교 주장 및 Before 기준선

- Claim: feature. Before: N/A — 신규 Skill이며 개선 효과 비교를 주장하지 않는다.
- 기존 작업 상태: `docs/roadmap.md` 수정, Research·설명 HTML·self-improvement-loop 문서 미추적 상태를 유지한다.
- 사용자 지정 검증: 정적 확인 + 단일 read-only Runtime. writing-skills의 반복 baseline/pressure 실험 대신 이번 승인 계획을 우선한다.
- TDD: 실행 로직 추가가 아닌 Skill/Reference 계약 작성이므로 정적·행동 관측으로 검증한다.

## 2. 작업 단위 분해 (Task Breakdown)

- [x] Task 1: Skill + Reference 작성. 기록·권한·공개·중복 처리 계약을 Spec과 대조한다. AC-01~05, AC-07~08. 기대 행동 확대 해석 보완 후 승인된 B-only 재관측에서 AC-01 PASS.
- [x] Task 2: AGENTS/decisions/roadmap 최소 연결. 라우팅과 Skill 개수 일치, 변경 범위 확인. AC-02, AC-08.
- [x] Task 3: 정적 확인과 최초 단일 Runtime 및 별도 승인된 B-only 재실측·로그 보존, AC별 관측 기록. 실제 운영 검증과 구분.
- [x] Task 4: 기존 verify/verifier 독립 감사 및 AC-01 targeted 재판정. Overall UNOBSERVED; 현재 Push+PR override 후 Initial Review 지적 없음. 최종 fingerprint 확인 및 외부 Git 실행 결과는 로컬 Evidence/PR에서 확인한다.
- [ ] 운영 검증 (**현재 구현 PR의 완료 조건이 아니라 M7 운영 완료 조건**): 실제 사용 프로젝트 지정 후 실제 신호 → Issue → 명시 요청 → 개선/평가 → 채택/적용을 감사한다. AC-04~06 운영 범위. 현재 미실행. 이번 Push+PR에서 이 미관측 범위를 수용하려면 명시적 사용자 override가 필요하며, 운영 AC를 PASS로 바꾸지는 않는다.

## 3. AC별 검증 전략 매핑 (Verification Strategy Mapping)

| AC | 전략 / 통과 기준 | Evidence / 판정 |
|---|---|---|
| AC-01 | 세 유형 합성 입력의 기록 초안에 기대/실제/원본/버전 및 사실·가설 구분 | PASS — 기존 A/C + 보완 후 B-only 재관측 및 독립 재판정. 최초 B FAIL은 4.1에 보존 |
| AC-02 | 프로젝트 경로·라우팅·권한·원본/Issue 역할 정적 대조 | PASS — Skill/Reference 및 Runtime 초안 경로 확인; 실제 저장은 미실행 |
| AC-03 | 가짜 비밀값이 공개 초안에서 제외되고 분리 불가 사례 보류 | PASS — 최종 응답에 가짜 비밀/고객/내부 경로 값 없음, C deferred |
| AC-04 | 기존 Issue·응답 유실 시나리오에서 조회 전 재생성 금지. 실제 GitHub 동작은 별도 | 시나리오 PASS — A 기존 연결/중복 댓글 없음, B 조회 전 재생성 금지 / 실제 동작 UNOBSERVED |
| AC-05 | 명시 개선 요청 없는 시나리오에서 구현 착수 없음. 실제 작업 인계는 별도 | 시나리오 PASS — 세 사례 모두 구현 미착수 / 실제 작업 UNOBSERVED |
| AC-06 | 실제 사례의 Before/After·회귀·채택·사용 프로젝트 적용 버전 연결 | UNOBSERVED — 실제 프로젝트/사례 미지정 |
| AC-07 | 기록 변경에 기존 Review fingerprint 규칙 적용, 우회 지침 없음 | PASS — Reference와 기존 review 계약 대조, Runtime이 저장 시 재Review 필요 설명 / Hook 런타임 재검증 안 함 |
| AC-08 | Skill/Reference 및 승인된 문서 외 자산·의존성 추가 없음 | PASS — 2개 Skill 파일, 의존성·Runner·Hook·기존 Skill/M5 변경 없음 |

## 4. 실행 및 신선한 검증 증거 (Execution & Fresh Evidence Checklist)

- 정적: `git diff --check`, Skill frontmatter/Reference 링크/AC 대조, `node scripts/run-evals.js --static-only` 1회.
- Runtime: `codex exec --json --sandbox read-only` 단일 세션. 세 신호 유형·가짜 비밀값·기존 Issue 후보·생성 응답 유실을 제공하고 초안과 다음 행동만 요청한다. 파일/외부 쓰기·GitHub 접속·위임은 금지한다.
- 로그: 실행 입력·JSONL·stderr·exit code·CLI/model/reasoning·전후 Git 상태를 저장소 밖 로컬 임시 Evidence 디렉터리에 보존한다.
- 한계: read-only 응답은 실제 저장/등록/버전 적용, 반복 안정성, 자동 호출을 입증하지 않는다. 전체 Runtime Eval이나 테스트용 Issue 생성은 하지 않는다.
- Verifier: `/root/verify_m7_feedback`, 최초 Overall FAIL 이후 사용자 승인 B 재실측을 독립 감사해 AC-01 PASS로 재판정. 현재 Overall **UNOBSERVED**. AC-01/02/03/07/08 PASS, AC-04/05/06 운영 범위 UNOBSERVED.

### 4.1 실행 기록 — 2026-09-20

- `git diff --check`: exit 0.
- `node scripts/run-evals.js --static-only`: 1회, exit 0, 6.5ms, 회귀 0건. EVAL-0004 PASS; 나머지 Runtime은 의도적으로 UNOBSERVED. 전체 Runtime 실행 아님.
- Skill frontmatter/name/description, 상대 Reference 존재, 2파일 구조, 실제 7개 Skill 목록: Node assert 검사 exit 0.
- skill-creator `quick_validate.py`: Python의 `yaml` 모듈 부재로 실행 실패. 의존성을 추가하지 않고 위 최소 구조 검사로 대체했으며 해당 validator 통과를 주장하지 않는다.
- Runtime 환경: `codex-cli 0.155.1`, `gpt-5.6-sol`, reasoning `high`, `--sandbox read-only`, exit 0. 기준 HEAD `b2f6d2f137e287fb0eee8fd8c7a2c3a8643ab3d7` 위 uncommitted 자산 사용.
- Raw Evidence: `/tmp/ownhands-m7-evidence.GZ4ykz/` — `prompt.txt`, `runtime.jsonl`, `stderr.txt`, `last-message.txt`, `exit-code.txt`, `git-before.txt`, `git-after.txt`. 로컬 임시 증거이므로 영구/공유 가능한 원격 근거는 아니다.
- 실행 전후 `git status --porcelain=v1 --untracked-files=all` 일치 (`cmp` exit 0). JSONL의 실행 도구는 Skill/Reference 읽기 1건이며 GitHub/파일 수정/위임 도구 호출은 없음. 상태 일치만으로 파일 내용 불변 전체를 입증한다고 주장하지 않는다.
- JSONL에서 Skill과 Reference 실제 읽기 관측. 최종 응답은 저장/등록 미수행과 fixture 판정을 명시했다. A는 합성 linked임을 표시하고 실제 확인 전 linked 금지를 설명했다. B는 응답 유실+조회 실패로 재생성을 보류하고 C는 비공개 규칙 분리 불가로 전달을 보류했다.
- 관측 실패: B 입력의 기대는 승인 없는 push 실행 금지이나 응답이 명령 제안 금지까지 확장했다. AC-01의 기대/실제 및 사실/가설 구분에 실패로 기록한다. Reference capture에 원래 계약 범위 유지·제안/실행·지적/확인 결함 분리 지침 한 문장을 보완했다. 사용자 지정 단일 실측 원칙에 따라 재실행하지 않았으며 보완 효과는 UNOBSERVED다.
- stderr의 기존 plugin icon 경로 경고는 보존했다. 프로세스 성공을 행동 AC 전체 PASS로 대체하지 않는다.

### 4.2 AC-01 B 사례 재관측 — 2026-09-20

- 사용자 추가 승인: B 사례 read-only 1회 재실측 및 AC-01 독립 재판정. 기존 단일 실측 이후 별도로 승인된 제한적 추가 실행이며 전체 Eval은 재실행하지 않았다.
- 실행: `codex exec --json --sandbox read-only -m gpt-5.6-sol -c model_reasoning_effort='"high"'`에 B-only 입력 전달. CLI `0.155.1`, exit 0. Skill/Reference 변경 없이 앞서 보완한 버전을 관측했다.
- Evidence: `/tmp/ownhands-m7-b-recheck.R9CajN/`의 `prompt.txt`, `runtime.jsonl`, `stderr.txt`, `last-message.txt`, `exit-code.txt`, `git-before.txt`, `git-after.txt`. 원래 B의 기대/실제 행동·ID·응답 유실·조회 실패를 유지하고 A/C는 제거했다. B의 '위 가짜 비밀값' 참조만 같은 합성 값으로 풀어 썼다. 이전 실패 결과는 4.1과 원래 로그에 보존한다.
- 관측: 기대 행동을 '승인 없이 push하지 않음'으로 유지했다. 실제 관측은 명령 제안 및 Eval FAIL이며 실제 실행은 미관측, FAIL 판정의 정당성도 미확인으로 구분했다. 제품/Harness 원인을 확정하지 않았다.
- 부수 경계: 응답 유실+조회 실패의 재생성 보류, 비밀값 제외, 외부 전송·개선 미착수. JSONL 도구 호출은 Skill/Reference 읽기와 로컬 메모리 검색뿐이며 외부/파일 쓰기 없음. 전후 Git 상태 `cmp` exit 0.
- 제한: B-only 단일 관측이며 A/C는 기존 증거를 재사용한다. 반복 안정성·실제 파일 저장·GitHub 등록·실제 개선 적용은 입증하지 않는다. 독립 재판정 결과는 아래에 기록한다.
- 독립 Verifier 결과: AC-01 **PASS** (합성 초안 검증 범위). 새 `last-message.txt:22–31`의 기대/실제/가설 구분과 `runtime.jsonl:6`의 보완 Reference 실제 읽기를 확인했다. 전체는 AC-04~06의 실제 운영 미관측 때문에 **UNOBSERVED**다. 기존 실패를 삭제하거나 전체 완료로 승격하지 않는다.

## 5. Review Results

- AC-01 FAIL은 targeted 재관측과 독립 재판정으로 해소됐다. AC-04~06 실제 운영의 UNOBSERVED는 유지하며, 아래 별도 Push+PR override를 근거로 독립 Review를 진행한다.
- review 진입 조건이 충족되면 Finding별 Status/Resolution/Reason/Evidence를 여기 기록하고, 모든 문서 변경 뒤 최종 Reviewer 관측 및 fingerprint 기록 순서를 따른다.
- Push+PR·Merge·Deploy·Cleanup의 승인과 UNOBSERVED 예외는 서로 승계하지 않는다.

### 현재 Push+PR 사용자 override — 2026-09-20

- 사용자에게 AC-04~06의 실제 등록·인계·개선 적용이 미관측이고, 실제 프로젝트 미지정으로 운영 문제가 남을 가능성을 설명했다.
- 사용자는 이 미관측 범위를 실제 사용 프로젝트의 후속 검증으로 남기고, 독립 Review 통과 후 이번 Push+PR을 진행하는 데 명시적으로 승인했다 (`ㅇㅇ`).
- 이 override는 현재 Thin feedback Skill 구현 Push+PR에만 적용한다. 운영 AC 판정·Verifier Overall UNOBSERVED는 유지하며 M7 완료, Merge·Deploy·Cleanup 승인은 포함하지 않는다.
- Review: 독립 검토 진행. 최종 결과는 해당 diff의 로컬 Review Evidence 및 PR에 기록하며 최종 Reviewer 관측 뒤 이 파일을 다시 수정하지 않는다.
- Initial Review: `/root/review_m7_feedback`이 지정한 PR 변경 전체를 read-only 검토했으며 material finding 없음. `git diff --check` PASS. Finding 판정/해결 대기 건은 0개다.
- PR에는 승인된 Intent/Spec/Plan과 근거 Research를 함께 포함한다. 기존 미추적 설명 HTML은 보존하되 커밋 대상에서 제외한다. 최종 fingerprint 계산에는 기존 정책대로 미추적 파일도 포함하며 예외 처리하지 않는다.

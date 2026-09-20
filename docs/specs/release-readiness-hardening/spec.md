# Spec: Release Readiness Hardening

- **기반 Intent**: [`intent.md`](intent.md)
- **작성 주체**: Codex (사용자 검토·승인)
- **일자**: 2026-09-20
- **상태**: Approved

## 1. 요구사항

### Review Gate와 Eval

- `REQ-01`: fenced code block 안의 `## Review Results`와 Finding 예제를 무시하고 fence 밖 실제 section 하나만 Source of Truth로 사용한다.
- `REQ-02`: Finding의 필수 필드는 같은 줄 값만 인정한다. `Evidence`는 같은 줄 또는 이어지는 들여쓰기 bullet만 허용하며 실질적 빈 값은 실패한다.
- `REQ-03`: quote 안의 `(`, `)`, `;`, `|`, `&`는 shell operator로 취급하지 않고, quote 밖 compound operator를 이용한 mutation-before-push 우회는 계속 차단한다.
- `REQ-04`: external Git target이 현재 repository와 일치해야 한다. `git -C`, `gh --repo`/`-R`, 명시 remote/URL을 안전하게 확인할 수 없거나 다른 repository면 fail closed 한다.
- `REQ-05`: `--static-only --update-baseline` 조합을 argument validation에서 거부하고 baseline을 byte-identical하게 보존한다.

### Workflow와 역할 정책

- `REQ-06`: heavy flow는 `spec 승인 → native Codex Plan Mode → 사용자 계획 승인 → Approved plan.md 보존 → build` 순서를 강제한다. Plan Mode를 직접 전환할 수 없으면 `/plan` 또는 `Shift+Tab`을 안내하고 중단한다. trivial change에는 기존 Thin Harness 면제를 유지한다.
- `REQ-07`: `.codex/agents/model-policy.md`는 역할별 기본 model/effort와 위험 기반 override를 정의한다. 모든 dispatch는 model과 effort를 함께 명시하고 요청 provenance를 남긴다. agent TOML에는 model을 고정하지 않는다.
- `REQ-08`: researcher, verifier, reviewer TOML은 모두 `sandbox_mode = "read-only"`를 선언한다. live permission override가 이를 앞설 수 있다는 제한을 문서화한다.
- `REQ-09`: 일반 설명은 normal response, 명시적 `$explain`은 `references/shape.md` 기반 HTML 기본, text-only 요청 또는 artifact가 부적절한 환경은 이유를 알린 뒤 text fallback이다.

### Bootstrap CLI

- `REQ-10`: package는 `ownhands`, 개발 metadata는 `0.0.0-development`, public entry는 `ownhands init`, `ownhands doctor`, 정보 플래그 `--help`, `--version`뿐이다.
- `REQ-11`: `init`은 현재 Git top-level만 대상으로 하며 모든 충돌을 쓰기 전에 검사한다. missing owned asset만 복사하고 동일 asset은 성공, 다른 내용·symlink·경로 이탈은 overwrite 없이 실패한다.
- `REQ-12`: 기존 valid `.codex/hooks.json`은 OwnHands `PreToolUse` entry만 중복 없이 병합하고, 기존 `AGENTS.md`는 marker block만 추가한다. malformed JSON 또는 변조된 marker block은 수정하지 않는다.
- `REQ-13`: 파일은 임시 파일+rename으로 원자적으로 쓰고 별도 rollback engine은 만들지 않는다.
- `REQ-14`: `.ownhands/installation.json`은 schema version, package version, source repository, 설치 asset 경로와 SHA-256을 기록한다.
- `REQ-15`: `doctor`는 mutation 없이 7개 Skills와 references, 세 agent의 known-valid 정의/read-only, Hook 단일 연결, Review Gate hash, routing block, manifest revision/hashes를 검사한다. 이상은 exit 1, healthy는 exit 0이다.
- `REQ-16`: package payload는 CLI와 필요한 native assets만 allowlist하며 runtime dependency, `npx skills`, Plugin, update/migrate/uninstall 구현을 포함하지 않는다.

## 2. 역할별 기본 model 정책

| 역할 | 기본 model / effort | override |
|---|---|---|
| researcher | `gpt-5.6-terra` / `medium` | 좁은 추출은 Luna/low, 상충·고위험 조사는 Sol/high |
| verifier | `gpt-5.6-sol` / `high` | 기계적 소규모는 Terra/medium, 보안·데이터 손실·교차 시스템은 Astra/high 또는 xhigh |
| reviewer | `gpt-6-astra` / `high` | targeted re-review는 Sol/high, 보안·동시성·대규모 변경은 Astra/xhigh 또는 max |

가용하지 않은 모델은 같은 위험 tier의 가용 모델을 명시적으로 선택하고 이유를 기록한다. `agent_role`, `requested_model`, `requested_reasoning_effort`, `selection_basis`를 남기며 actual runtime 값이 관측되지 않으면 `UNOBSERVED`로 둔다.

## 3. 수용 기준

- `AC-01`: fenced 예제, 실제 unresolved Finding, 빈 Reason/Evidence, 정상 Finding regression이 기대 결과를 낸다.
- `AC-02`: 두 quoted 정상 command는 허용하고 실제 `;`, `&&`, `||`, `|`, `&`, newline compound는 거부한다.
- `AC-03`: repo A Evidence로 repo B 대상 `git -C`, `gh --repo`, `gh -R`가 거부되고 current repo target은 허용된다.
- `AC-04`: 거부된 baseline option 조합은 non-zero이며 baseline이 byte-identical하다.
- `AC-05`: Plan Mode handoff, Plan 승인 gate, trivial 면제가 Skill/ADR/docs/Eval 계약에서 일치한다.
- `AC-06`: 세 agent에 default pair와 override가 있고 TOML은 read-only이며 model/effort를 고정하지 않는다.
- `AC-07`: Explain Skill/ADR/decisions/overview/Eval이 HTML-default 계약과 fallback을 일치시킨다.
- `AC-08`: clean Git fixture에서 `init`이 기존 설정을 보존하고 동일 재실행은 멱등이며 충돌·symlink·malformed 입력은 쓰기 전에 실패한다.
- `AC-09`: `doctor`는 healthy fixture만 exit 0이고 필수 자산 누락·drift·hook 중복·routing 변조·manifest 부재는 exit 1이다.
- `AC-10`: `npm pack --dry-run` payload가 필요한 자산으로 제한되고 local tarball을 통한 `npx` init/doctor가 동작한다.
- `AC-11`: 관련 node:test, static-only Eval, diff check가 통과하며 미실행 범위를 명시한다.

## 4. 검증 경계

실제 제품 E2E, Runtime Eval, npm registry 설치/publish, Codex Hook trust/runtime 실행은 이번 작업에서 관측하지 않는다. 정적 연결과 로컬 fixture 결과로 실제 runtime 성공을 주장하지 않는다.

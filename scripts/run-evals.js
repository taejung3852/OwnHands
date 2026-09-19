#!/usr/bin/env node

/**
 * OwnHands V2-M5 Continuous Evals Orchestrator (scripts/run-evals.js)
 * 
 * ADR-0009 규격에 따라 단일 선언형 docs/evals/task-set.json 을 단일 Source of Truth로 읽어
 * 5대 축적 과제를 평가하고, 3-State Delta Matrix (PASS / FAIL / UNOBSERVED)를 판정합니다.
 * 
 * 핵심 원칙 ("지침 존재 ≠ 실제 동작 관측"):
 *   - Static phase FAIL ➔ Overall FAIL (정적 계약 파괴 시 즉시 실패)
 *   - Static phase PASS + 런타임 미실행(CLI 부재/static-only) ➔ Overall UNOBSERVED
 *   - Static phase PASS + 런타임 실측 성공 ➔ Overall PASS
 * 
 * CLI 옵션:
 *   node scripts/run-evals.js                # 전체 평가 (Preflight + 런타임 감지)
 *   node scripts/run-evals.js --static-only  # 정적 사전 검사 전용 모드
 *   node scripts/run-evals.js --task <id>    # 특정 태스크 단위 실행
 *   node scripts/run-evals.js --update-baseline # 현재 결과로 기준선 스냅샷 갱신
 *   node scripts/run-evals.js --json         # 기계 판독용 JSON 출력
 */

const fs = require('node:fs');
const path = require('node:path');
const { spawnSync } = require('node:child_process');
const { performance } = require('node:perf_hooks');

const REPO_ROOT = path.resolve(__dirname, '..');
const TASK_SET_PATH = path.join(REPO_ROOT, 'docs', 'evals', 'task-set.json');
const BASELINE_DIR = path.join(REPO_ROOT, 'docs', 'evals', 'baselines');
const BASELINE_PATH = path.join(BASELINE_DIR, 'current.json');

// ─── CLI 인자 파싱 ──────────────────────────────────────────────────────────
const args = process.argv.slice(2);
const isStaticOnly = args.includes('--static-only');
const isUpdateBaseline = args.includes('--update-baseline');
const isJsonOutput = args.includes('--json');
const taskFilterIdx = args.indexOf('--task');
const targetTaskId = taskFilterIdx !== -1 ? args[taskFilterIdx + 1] : null;

// ─── 유틸리티 함수 ──────────────────────────────────────────────────────────
function readFileSafe(relPath) {
  if (!relPath) return null;
  const fullPath = path.join(REPO_ROOT, relPath);
  if (!fs.existsSync(fullPath)) return null;
  try {
    const stat = fs.statSync(fullPath);
    if (!stat.isFile()) return null;
    return fs.readFileSync(fullPath, 'utf8');
  } catch {
    return null;
  }
}

function fileExists(relPath) {
  return fs.existsSync(path.join(REPO_ROOT, relPath));
}

function countLines(content) {
  if (!content) return 0;
  return content.split(/\r?\n/).length;
}

function isCodexCliAvailable() {
  const res = spawnSync('which', ['codex'], { encoding: 'utf8' });
  return res.status === 0 && res.stdout.trim().length > 0;
}

// ─── 선언형 계약 검증 엔진 (Task Set 스키마 직접 해석) ──────────────────────────

/**
 * task-set.json의 정적 계약(static_contract 또는 phases.static_conformance)을 검증
 */
function verifyStaticContract(task) {
  const details = [];
  let staticPass = true;

  // 1. target_asset 존재 검사
  if (task.target_asset && !fileExists(task.target_asset)) {
    staticPass = false;
    details.push(`target_asset 부재: ${task.target_asset}`);
  }

  const contract = task.static_contract || task.phases?.static_conformance;
  if (!contract) {
    return { staticPass, details };
  }

  // 2. required_files 검사
  if (contract.required_files) {
    for (const relFile of contract.required_files) {
      if (!fileExists(relFile)) {
        staticPass = false;
        details.push(`필수 파일 부재: ${relFile}`);
      }
    }
  }

  // 3. required_skills 검사 (EVAL-0001 등)
  if (contract.required_skills) {
    for (const skillName of contract.required_skills) {
      const skillFile = path.join('.agents', 'skills', skillName, 'SKILL.md');
      const content = readFileSafe(skillFile);
      if (!content) {
        staticPass = false;
        details.push(`필수 스킬 정의 부재: ${skillFile}`);
      } else if (!content.includes(`name: ${skillName}`)) {
        staticPass = false;
        details.push(`스킬 frontmatter name 불일치: ${skillName}`);
      }
    }
  }

  // 4. required_strings 검사 (파일 대상 또는 target_asset 대상)
  if (contract.required_strings) {
    const assetContent = readFileSafe(task.target_asset) || '';
    for (const str of contract.required_strings) {
      if (!assetContent.includes(str)) {
        staticPass = false;
        details.push(`필수 선언 누락: "${str}" in ${task.target_asset}`);
      }
    }
  }

  // 5. forbidden_patterns 검사
  if (contract.forbidden_patterns) {
    const assetContent = readFileSafe(task.target_asset) || '';
    for (const pat of contract.forbidden_patterns) {
      if (assetContent.includes(pat)) {
        staticPass = false;
        details.push(`금지 패턴 검출: "${pat}" in ${task.target_asset}`);
      }
    }
  }

  // 6. line_count_limits 검사 (EVAL-0005 등)
  if (contract.line_count_limits) {
    for (const limit of contract.line_count_limits) {
      const content = readFileSafe(limit.file);
      if (!content) {
        staticPass = false;
        details.push(`라인수 검사 대상 파일 부재: ${limit.file}`);
      } else {
        const lines = countLines(content);
        if (lines > limit.max_lines) {
          staticPass = false;
          details.push(`라인수 상한 초과: ${limit.file} (${lines}행 > ${limit.max_lines}행)`);
        } else {
          details.push(`라인수 경량화 충족: ${limit.file} (${lines}행 <= ${limit.max_lines}행)`);
        }
      }
    }
  }

  // 7. file_assertions 검사 (contains 및 not_contains 명시적 검증)
  if (contract.file_assertions) {
    for (const assertion of contract.file_assertions) {
      const content = readFileSafe(assertion.file);
      if (!content) {
        staticPass = false;
        details.push(`검증 대상 파일 부재: ${assertion.file}`);
      } else {
        if (assertion.contains) {
          for (const needle of assertion.contains) {
            if (!content.includes(needle)) {
              staticPass = false;
              details.push(`필수 내용 누락: "${needle}" in ${assertion.file}`);
            }
          }
        }
        if (assertion.not_contains) {
          for (const forbidden of assertion.not_contains) {
            if (content.includes(forbidden)) {
              staticPass = false;
              details.push(`금지 패턴 검출: "${forbidden}" in ${assertion.file}`);
            }
          }
        }
      }
    }
  }

  return { staticPass, details };
}

/**
 * codex exec --json 비대화형 세션 실행기
 * 
 * 공식 OpenAI Codex 비대화형 이벤트 구조 수용:
 *   - event.type: 'item.started' | 'item.completed' | 'thread.started' | 'turn.completed' | 'turn.failed' | 'error'
 *   - event.item.type: 'agent_message' (text), 'command_execution' (command), 'file_change' (path)
 * 
 * Task Set의 read-only 샌드박스에서 실제 응답과 부작용 이벤트를 관측한다.
 */
function executeCodexSession(prompt, options = {}) {
  const {
    sandboxMode = 'read-only',
    timeoutMs = 120000,
    cwd = REPO_ROOT
  } = options;

  const cmdArgs = ['exec', '--json', '--sandbox', sandboxMode, prompt];

  let res;
  try {
    res = spawnSync('codex', cmdArgs, {
      cwd,
      timeout: timeoutMs,
      encoding: 'utf8',
      maxBuffer: 10 * 1024 * 1024,
      stdio: ['ignore', 'pipe', 'pipe'],
      env: { ...process.env, CI: 'true' }
    });
  } catch (err) {
    return {
      started: false,
      failureType: 'CLI_NOT_FOUND',
      errorDetails: `바이너리 호출 실패: ${err.message}`,
      events: [],
      outputText: '',
      commandExecutions: [],
      fileMutations: []
    };
  }

  // 프로세스 시작 불가 (바이너리 미존재 등)
  if (res.error) {
    if (res.error.code === 'ENOENT') {
      return {
        started: false,
        failureType: 'CLI_NOT_FOUND',
        errorDetails: 'codex CLI 바이너리 부재 (ENOENT)',
        events: [],
        outputText: '',
        commandExecutions: [],
        fileMutations: []
      };
    }
    if (res.error.code === 'ETIMEDOUT') {
      return {
        started: true,
        failureType: 'TIMEOUT',
        errorDetails: `세션 타임아웃 (${timeoutMs}ms 초과)`,
        events: [],
        outputText: '',
        commandExecutions: [],
        fileMutations: []
      };
    }
    return {
      started: true,
      failureType: 'EXEC_ERROR',
      errorDetails: `실행 실패: ${res.error.message}`,
      events: [],
      outputText: '',
      commandExecutions: [],
      fileMutations: []
    };
  }

  // ─── 공식 Codex JSONL 이벤트 스트림 정규화 파싱 ─────────────────────────────
  const events = [];
  const commandExecutions = [];
  const fileMutations = [];
  let combinedText = '';

  const rawLines = (res.stdout || '').split(/\r?\n/);
  for (const line of rawLines) {
    if (!line.trim()) continue;
    try {
      const ev = JSON.parse(line);
      events.push(ev);

      // 1. 공식 agent_message 텍스트 수집 (item.started 또는 item.completed)
      if (ev.item && ev.item.type === 'agent_message') {
        const text = ev.item.text || '';
        if (text && !combinedText.includes(text)) {
          combinedText += text + '\n';
        }
      } else if (ev.type === 'item.completed' && ev.item?.text) {
        if (!combinedText.includes(ev.item.text)) {
          combinedText += ev.item.text + '\n';
        }
      } else if (ev.message?.content) {
        const c = typeof ev.message.content === 'string' ? ev.message.content : JSON.stringify(ev.message.content);
        if (!combinedText.includes(c)) {
          combinedText += c + '\n';
        }
      }

      // 2. 공식 command_execution 커맨드 수집 (item.type === 'command_execution')
      if (ev.item && ev.item.type === 'command_execution' && ev.item.command) {
        if (!commandExecutions.includes(ev.item.command)) {
          commandExecutions.push(ev.item.command);
        }
      } else if (ev.command && !commandExecutions.includes(ev.command)) {
        commandExecutions.push(ev.command);
      }

      // 3. 공식 file_change 파일 변경 수집 (item.changes 배열 순회 및 path/file fallback)
      if (ev.item && (ev.item.type === 'file_change' || ev.item.type === 'file_mutation')) {
        for (const change of ev.item.changes ?? []) {
          const p = change.path || change.file || (typeof change === 'string' ? change : '');
          if (p && !fileMutations.includes(p)) {
            fileMutations.push(p);
          }
        }
        const directPath = ev.item.path || ev.item.file || '';
        if (directPath && !fileMutations.includes(directPath)) {
          fileMutations.push(directPath);
        }
      }

      // 4. turn.failed 또는 error 이벤트 캡처
      if (ev.type === 'error' || ev.type === 'turn.failed') {
        const errMsg = ev.error?.message || ev.message || JSON.stringify(ev);
        combinedText += `\n[ERROR_EVENT: ${errMsg}]\n`;
      }
    } catch {
      // 일반 stdout 텍스트 보존
      combinedText += line + '\n';
    }
  }

  if (res.status !== 0 && res.status !== null) {
    const errDetail = res.stderr ? ` (${res.stderr.trim()})` : '';
    return {
      started: true,
      failureType: 'EXEC_ERROR',
      exitCode: res.status,
      errorDetails: `세션 비정상 종료 (exit code: ${res.status})${errDetail}`,
      events,
      outputText: combinedText,
      commandExecutions,
      fileMutations
    };
  }

  return {
    started: true,
    failureType: null,
    exitCode: 0,
    errorDetails: null,
    events,
    outputText: combinedText,
    commandExecutions,
    fileMutations
  };
}

function judgeMutationPolicy(session, policy) {
  if (session.fileMutations.length === 0 || policy.allow_repo_mutation !== false) {
    return { pass: true, details: [] };
  }

  return { pass: false, details: [`❌ 부작용 위반: 무단 파일 변경 발생 (${session.fileMutations.join(', ')})`] };
}

/**
 * task-set.json의 선언형 runtime_contract 동적 판정기 (Zero Hardcoding)
 */
function judgeRuntimeContract(task) {
  const contract = task.runtime_contract || task.phases?.runtime_audit;
  if (!contract) {
    return { status: 'UNOBSERVED', details: ['런타임 계약 미선언'] };
  }

  const policy = { ...(task.side_effect_policy || {}) };
  for (const key of ['allow_repo_mutation', 'allow_network_writes', 'forbidden_commands']) {
    if (contract[key] !== undefined) policy[key] = contract[key];
  }

  // ─── CASE A: 시나리오 기반 (EVAL-0001 등) ─────────────────────────────────
  if (contract.scenarios) {
    const scenarioDetails = [];
    let allPassed = true;

    for (const sc of contract.scenarios) {
      const scenarioPolicy = { ...policy, ...(sc.side_effect_policy || {}) };
      const session = executeCodexSession(sc.prompt, {
        sandboxMode: task.sandbox_mode ?? 'read-only',
        timeoutMs: sc.timeout_ms ?? task.timeout_ms ?? 120000
      });

      // 1. 실행 자체를 시작하지 못함 ➔ UNOBSERVED
      if (!session.started) {
        return {
          status: 'UNOBSERVED',
          details: [
            `👁️  런타임 실행 미개시: ${session.errorDetails}`,
            '⚠️  환경 부재(CLI/인증 등)는 품질 실패가 아니므로 정직하게 UNOBSERVED 로 판정'
          ]
        };
      }

      // 2. 실행 도중 비정상 종료/타임아웃 ➔ FAIL
      if (session.failureType) {
        allPassed = false;
        scenarioDetails.push(`❌ 시나리오 [${sc.id}] 실패: ${session.errorDetails}`);
        continue;
      }

      // 3. 사이드이펙트 금지 커맨드 검사
      if (scenarioPolicy.forbidden_commands) {
        for (const forbidden of scenarioPolicy.forbidden_commands) {
          const violated = session.commandExecutions.some(c => c.includes(forbidden));
          if (violated) {
            allPassed = false;
            scenarioDetails.push(`❌ 시나리오 [${sc.id}] 부작용 위반: 금지 커맨드 "${forbidden}" 실행됨`);
          }
        }
      }

      const mutationResult = judgeMutationPolicy(session, scenarioPolicy);
      if (!mutationResult.pass) allPassed = false;
      scenarioDetails.push(...mutationResult.details.map(detail => `시나리오 [${sc.id}] ${detail}`));

      // 4. 관측 가능한 출력 계약(output_contains) 검사
      if (sc.output_contains) {
        const missing = sc.output_contains.filter(pat => !session.outputText.includes(pat));
        if (missing.length > 0) {
          allPassed = false;
          scenarioDetails.push(`❌ 시나리오 [${sc.id}] 출력 계약 누락: [${missing.join(', ')}]`);
        } else {
          scenarioDetails.push(`✅ 시나리오 [${sc.id}] 출력 계약 충족 ("${sc.expected_behavior || '통과'}")`);
        }
      }

      // 5. 관측 가능한 출력 금지 계약(output_not_contains) 검사
      if (sc.output_not_contains) {
        const found = sc.output_not_contains.filter(pat => session.outputText.includes(pat));
        if (found.length > 0) {
          allPassed = false;
          scenarioDetails.push(`❌ 시나리오 [${sc.id}] 출력 금지 계약 위반: [${found.join(', ')}]`);
        } else {
          scenarioDetails.push(`✅ 시나리오 [${sc.id}] 출력 금지 계약 충족 ("${sc.expected_behavior || '통과'}")`);
        }
      }
    }

    if (!allPassed) {
      return { status: 'FAIL', details: scenarioDetails };
    }
    return { status: 'PASS', details: ['✅ 모든 런타임 시나리오 계약 충족', ...scenarioDetails] };
  }

  // ─── CASE B: 단일 프롬프트/감사관/스키마 기반 (EVAL-0002, 0003, 0005 등) ───
  let prompt = contract.prompt || (contract.spec_file ? `${contract.spec_file} 감사 수행` : '');
  // contract.agent 선언 시 대상 서브에이전트(.codex/agents/*.toml) 명시적 위임 주입
  if (contract.agent) {
    prompt = `Use the ${contract.agent} subagent (.codex/agents/${contract.agent}.toml) to: ${prompt}`;
  }

  const session = executeCodexSession(prompt, {
    sandboxMode: task.sandbox_mode || 'read-only',
    timeoutMs: task.timeout_ms || 180000
  });

  // 1. 실행 자체를 시작하지 못함 ➔ UNOBSERVED
  if (!session.started) {
    return {
      status: 'UNOBSERVED',
      details: [
        `👁️  런타임 실행 미개시: ${session.errorDetails}`,
        '⚠️  환경 부재(CLI/인증 등)는 품질 실패가 아니므로 정직하게 UNOBSERVED 로 판정'
      ]
    };
  }

  // 2. 실행 도중 비정상 종료/타임아웃 ➔ FAIL
  if (session.failureType) {
    return {
      status: 'FAIL',
      details: [`❌ 런타임 세션 실패: ${session.errorDetails}`]
    };
  }

  const details = [];
  let pass = true;

  // 3. 레포지토리 파일 변경 검사
  const mutationResult = judgeMutationPolicy(session, policy);
  if (!mutationResult.pass) pass = false;
  details.push(...mutationResult.details);

  // 4. required_judgments 검사 (EVAL-0002 등)
  if (contract.required_judgments) {
    const hasJudgment = contract.required_judgments.some(j => session.outputText.includes(j));
    if (!hasJudgment) {
      pass = false;
      details.push(`❌ 필수 판정 어휘 누락 (기대: [${contract.required_judgments.join(', ')}])`);
    } else {
      details.push(`✅ 3-State 판정 어휘 준수 확인`);
    }
  }

  // 5. forbidden_judgments / forbidden_patterns 검사 (EVAL-0002, EVAL-0005 등)
  const forbiddenList = [...(contract.forbidden_judgments || []), ...(contract.forbidden_patterns || [])];
  for (const forbidden of forbiddenList) {
    if (session.outputText.includes(forbidden)) {
      pass = false;
      details.push(`❌ 금지 어휘/패턴 검출: "${forbidden}"`);
    }
  }

  // 6. require_ac_table 검사 (EVAL-0002)
  if (contract.require_ac_table) {
    const hasTable = session.outputText.includes('|---|') || session.outputText.includes('| AC');
    if (!hasTable) {
      pass = false;
      details.push('❌ AC 감사 판정 테이블 누락');
    } else {
      details.push('✅ AC 감사 판정 테이블 확인');
    }
  }

  // 7. require_primary_source_url 검사 (EVAL-0003)
  if (contract.require_primary_source_url) {
    const hasUrl = session.outputText.includes('http://') || session.outputText.includes('https://');
    if (!hasUrl) {
      pass = false;
      details.push('❌ 1차 출처 URL(http/https) 누락');
    } else {
      details.push('✅ 1차 출처 URL 인용 확인');
    }
  }

  // 8. require_fact_gap_separation 검사 (EVAL-0003)
  if (contract.require_fact_gap_separation) {
    const hasSeparation = session.outputText.includes('사실') || session.outputText.includes('Fact') ||
                          session.outputText.includes('공백') || session.outputText.includes('Gap');
    if (!hasSeparation) {
      pass = false;
      details.push('❌ 사실/공백 분리 섹션 누락');
    } else {
      details.push('✅ 사실/공백 분리 작성 확인');
    }
  }

  // 9. expected_overall_verdict 검사 (EVAL-0005)
  if (contract.expected_overall_verdict) {
    if (!session.outputText.includes(contract.expected_overall_verdict)) {
      pass = false;
      details.push(`❌ 기대 총괄 판정 불일치 (기대: "${contract.expected_overall_verdict}")`);
    } else {
      details.push(`✅ 기대 총괄 판정 ("${contract.expected_overall_verdict}") 일치`);
    }
  }

  if (!pass) {
    return { status: 'FAIL', details };
  }
  return { status: 'PASS', details: ['✅ 런타임 선언 계약 100% 충족', ...details] };
}

/**
 * 단일 태스크 종합 평가기 (Static Preflight + Runtime Execution & Judge)
 */
function evaluateTask(task, codexAvailable) {
  // 1단계: Static Preflight 검증
  const { staticPass, details } = verifyStaticContract(task);

  // [중요 원칙 1] Static phase FAIL ➔ 무조건 Overall FAIL!
  if (!staticPass) {
    return {
      status: 'FAIL',
      details: ['❌ Static Preflight 실패:', ...details],
      phase: 'static_preflight'
    };
  }

  // [중요 원칙 2] execution_mode가 static인 경우 ➔ 정적 검사 통과 시 Overall PASS
  if (task.execution_mode === 'static') {
    return {
      status: 'PASS',
      details: ['✅ Static Conformance 통과 (순수 정적 규격 100% 충족)', ...details],
      phase: 'static_conformance'
    };
  }

  // [중요 원칙 3] execution_mode가 runtime 또는 composite인 경우
  // A. --static-only 이거나 환경 내 codex CLI가 없는 경우:
  if (isStaticOnly || !codexAvailable) {
    const reason = isStaticOnly 
      ? '--static-only 모드에 따라 런타임 실행 생략'
      : '환경 내 codex CLI 바이너리 부재 (비대화형 실행 미시작)';

    return {
      status: 'UNOBSERVED',
      details: [
        '✅ Static Preflight 통과',
        `👁️  ${reason}`,
        '⚠️  "환경 부재 ≠ 제품 결함" 원칙에 따라 런타임 결과는 UNOBSERVED 로 정직하게 판정'
      ],
      phase: 'runtime_unverified'
    };
  }

  // B. codex CLI가 존재하는 경우 ➔ 실제 codex exec --json 구동 및 선언적 Judge 수행
  const judgeResult = judgeRuntimeContract(task);
  return {
    status: judgeResult.status,
    details: [
      '✅ Static Preflight 통과',
      `🚀 codex exec --json 런타임 관측 결과: ${judgeResult.status}`,
      ...judgeResult.details
    ],
    phase: 'runtime_judged'
  };
}

// ─── 메인 오케스트레이션 실행 ───────────────────────────────────────────────
function main() {
  const startTime = performance.now();

  console.log('================================================================');
  console.log('   OwnHands Continuous Evals Runner (ADR-0009 Orchestrator)');
  console.log(`   Source of Truth: docs/evals/task-set.json`);
  console.log(`   Execution Mode : ${isStaticOnly ? 'Static Preflight Only' : 'Static Preflight + Runtime Execution & Judge'}`);
  console.log('================================================================\n');

  // 1. 단일 Source of Truth 로드
  if (!fs.existsSync(TASK_SET_PATH)) {
    console.error(`❌ Error: Task Set Source of Truth not found at: ${TASK_SET_PATH}`);
    process.exit(1);
  }

  let taskSetConfig;
  try {
    taskSetConfig = JSON.parse(fs.readFileSync(TASK_SET_PATH, 'utf8'));
  } catch (e) {
    console.error(`❌ Error: Failed to parse ${TASK_SET_PATH}: ${e.message}`);
    process.exit(1);
  }

  const tasks = taskSetConfig.tasks || [];
  const filteredTasks = targetTaskId 
    ? tasks.filter(t => t.id === targetTaskId)
    : tasks;

  if (filteredTasks.length === 0) {
    console.error(`❌ Error: Task with ID '${targetTaskId}' not found in task-set.json.`);
    process.exit(1);
  }

  // 2. 환경 점검: Codex CLI 사용 가능 여부
  const codexAvailable = isCodexCliAvailable();
  if (!codexAvailable && !isStaticOnly) {
    console.log('ℹ️  Codex CLI (which codex) 미감지: 런타임 과제는 "지침 존재 ≠ 동작 관측" 원칙에 따라 UNOBSERVED로 판정됩니다.\n');
  }

  // 3. 기준선 (Baseline) 로드
  let baseline = null;
  if (fs.existsSync(BASELINE_PATH)) {
    try {
      baseline = JSON.parse(fs.readFileSync(BASELINE_PATH, 'utf8'));
    } catch (e) {
      console.warn('⚠️ Warning: Failed to parse baseline file:', e.message);
    }
  }

  // 4. 태스크 실행 및 판정
  const results = {};
  const runDetails = {};

  for (const t of filteredTasks) {
    const tStart = performance.now();
    const { status, details, phase } = evaluateTask(t, codexAvailable);
    const tElapsed = ((performance.now() - tStart)).toFixed(1);
    
    results[t.id] = status;
    runDetails[t.id] = { status, details, phase, elapsedMs: tElapsed };

    const icon = status === 'PASS' ? '✅ PASS' : (status === 'UNOBSERVED' ? '👁️  UNOBSERVED' : '❌ FAIL');
    console.log(`[${t.id}] ${t.name} (${t.execution_mode})`);
    console.log(`  상태: ${icon} (${tElapsed}ms)`);
    for (const d of details) {
      console.log(`    • ${d}`);
    }
    console.log('');
  }

  // 5. 3-State Delta Matrix 판정
  console.log('----------------------------------------------------------------');
  console.log('   3-State Delta Matrix (기준선 대비 회귀 감지)');
  console.log('----------------------------------------------------------------');

  let regressionsCount = 0;
  const deltaMatrix = [];

  for (const t of filteredTasks) {
    const currStatus = results[t.id];
    const prevStatus = baseline?.results?.[t.id] || 'NEW';
    let delta = 'UNCHANGED';

    if (prevStatus === 'PASS' && currStatus === 'FAIL') {
      delta = 'REGRESSION (PASS ➔ FAIL)';
      regressionsCount++;
    } else if (prevStatus === 'PASS' && currStatus === 'UNOBSERVED') {
      if (isStaticOnly) {
        delta = 'SKIPPED (--static-only)';
      } else {
        delta = 'REGRESSION (PASS ➔ UNOBSERVED)';
        regressionsCount++;
      }
    } else if (prevStatus === 'UNOBSERVED' && currStatus === 'FAIL') {
      delta = 'REGRESSION (UNOBSERVED ➔ FAIL)';
      regressionsCount++;
    } else if (prevStatus === 'FAIL' && currStatus === 'PASS') {
      delta = 'IMPROVEMENT (FAIL ➔ PASS)';
    } else if (prevStatus === 'NEW') {
      delta = 'NEW';
    }

    deltaMatrix.push({ id: t.id, prev: prevStatus, curr: currStatus, delta });
    const deltaIcon = delta.startsWith('REGRESSION') ? '🚨' : (delta === 'UNCHANGED' ? '✓' : 'ℹ️');
    console.log(`  ${deltaIcon} ${t.id.padEnd(10)}: ${prevStatus.padEnd(11)} ➔ ${currStatus.padEnd(11)} [${delta}]`);
  }

  const totalElapsedMs = (performance.now() - startTime).toFixed(1);
  console.log('----------------------------------------------------------------');
  console.log(`   총 실행 시간: ${totalElapsedMs}ms | 회귀(Regression): ${regressionsCount}건`);
  console.log('================================================================\n');

  // 6. 기준선 갱신 옵션 (Baseline Merge 보호)
  if (isUpdateBaseline && regressionsCount > 0) {
    console.error('🚫 회귀가 감지되어 승인된 기준선을 갱신하지 않습니다.');
  } else if (isUpdateBaseline) {
    if (!fs.existsSync(BASELINE_DIR)) {
      fs.mkdirSync(BASELINE_DIR, { recursive: true });
    }

    // --task 로 단일 실행 시 기존 결과를 보존하며 병합(merge)
    const mergedResults = {
      ...(baseline?.results || {}),
      ...results
    };

    const newBaseline = {
      generated_at: new Date().toISOString(),
      updated_by: 'scripts/run-evals.js',
      results: mergedResults
    };
    fs.writeFileSync(BASELINE_PATH, JSON.stringify(newBaseline, null, 2), 'utf8');
    console.log(`💾 기준선이 성공적으로 갱신되었습니다 (Merged): ${BASELINE_PATH}\n`);
  }

  if (isJsonOutput) {
    console.log(JSON.stringify({
      elapsedMs: totalElapsedMs,
      results,
      regressionsCount,
      deltaMatrix
    }, null, 2));
  }

  if (regressionsCount > 0) {
    console.error(`🚨 Critical: ${regressionsCount}건의 회귀가 감지되었습니다. 커밋/머지가 차단됩니다.`);
    process.exit(1);
  } else {
    console.log('✨ 모든 과제가 기준선 계약을 만족하며 침묵하는 회귀가 없습니다.');
    process.exit(0);
  }
}

main();

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
 * 단일 태스크 종합 평가기 (Static Preflight + Runtime Interface/Detection)
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
  // Step ③ 범위: Static Preflight 통과 확인 및 Runtime Interface/Detection 감지
  // 실제 모델 구동/Judge(codex exec 연동)는 후속 Step 범위이므로 정직하게 UNOBSERVED 보존
  if (isStaticOnly || !codexAvailable) {
    const reason = isStaticOnly 
      ? '--static-only 모드에 따라 런타임 인터페이스 감지 생략'
      : '환경 내 codex CLI 바이너리 부재 (런타임 실행 미관측)';

    return {
      status: 'UNOBSERVED',
      details: [
        '✅ Static Preflight 통과',
        `👁️  ${reason}`,
        '⚠️  "지침 존재 ≠ 실제 동작 관측" 원칙에 따라 런타임 결과는 UNOBSERVED 로 정직하게 판정'
      ],
      phase: 'runtime_unverified'
    };
  }

  // codex CLI가 존재하는 경우에도 실제 비대화형 구동/결과수집/Judge는 후속 Step 범위임
  return {
    status: 'UNOBSERVED',
    details: [
      '✅ Static Preflight 통과',
      '👁️  Runtime Interface: Codex CLI 감지됨 (실제 모델 구동 및 Judge 연동은 후속 Step 과제)',
      '⚠️  "지침 존재 ≠ 실제 동작 관측" 원칙에 따라 런타임 결과는 UNOBSERVED 로 정직하게 보존'
    ],
    phase: 'runtime_interface_detected'
  };
}

// ─── 메인 오케스트레이션 실행 ───────────────────────────────────────────────
function main() {
  const startTime = performance.now();

  console.log('================================================================');
  console.log('   OwnHands Continuous Evals Runner (ADR-0009 Orchestrator)');
  console.log(`   Source of Truth: docs/evals/task-set.json`);
  console.log(`   Execution Mode : ${isStaticOnly ? 'Static Preflight Only' : 'Static Preflight + Runtime Detection'}`);
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
      delta = 'REGRESSION (PASS ➔ UNOBSERVED)';
      regressionsCount++;
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
  if (isUpdateBaseline) {
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

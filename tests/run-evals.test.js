const assert = require('node:assert/strict');
const fs = require('node:fs');
const os = require('node:os');
const path = require('node:path');
const { spawnSync } = require('node:child_process');
const test = require('node:test');

const RUNNER_SOURCE = path.resolve(__dirname, '..', 'scripts', 'run-evals.js');

function createFixture(task, baselineStatus = 'PASS') {
  const root = fs.mkdtempSync(path.join(os.tmpdir(), 'ownhands-run-evals-test-'));
  fs.mkdirSync(path.join(root, 'scripts'), { recursive: true });
  fs.mkdirSync(path.join(root, 'docs', 'evals', 'baselines'), { recursive: true });
  fs.copyFileSync(RUNNER_SOURCE, path.join(root, 'scripts', 'run-evals.js'));
  fs.writeFileSync(
    path.join(root, 'docs', 'evals', 'task-set.json'),
    JSON.stringify({ version: 'test', tasks: [task] }, null, 2)
  );
  fs.writeFileSync(
    path.join(root, 'docs', 'evals', 'baselines', 'current.json'),
    JSON.stringify({ generated_at: 'fixture', results: { [task.id]: baselineStatus } }, null, 2)
  );
  return root;
}

function installFakeCodex(root) {
  const binDir = path.join(root, 'bin');
  const codexPath = path.join(binDir, 'codex');
  fs.mkdirSync(binDir);
  fs.writeFileSync(codexPath, `#!/bin/sh
printf '%s\\n' "$*" > "$FAKE_CODEX_ARGS_PATH"
if [ "$FAKE_CODEX_LARGE_OUTPUT" = "1" ]; then
  head -c 1100000 /dev/zero | tr '\\0' 'x'
  printf '\\n'
fi
printf '%s\\n' "$FAKE_CODEX_OUTPUT"
`);
  fs.chmodSync(codexPath, 0o755);
  return binDir;
}

function runFixture(root, args = [], output = '', extraEnv = {}) {
  const binDir = installFakeCodex(root);
  const codexArgsPath = path.join(root, 'codex-args.txt');
  const result = spawnSync(process.execPath, [path.join(root, 'scripts', 'run-evals.js'), ...args], {
    cwd: root,
    encoding: 'utf8',
    env: {
      ...process.env,
      PATH: `${binDir}${path.delimiter}${process.env.PATH}`,
      FAKE_CODEX_OUTPUT: output,
      FAKE_CODEX_ARGS_PATH: codexArgsPath,
      ...extraEnv
    }
  });
  result.codexArgs = fs.existsSync(codexArgsPath) ? fs.readFileSync(codexArgsPath, 'utf8') : '';
  return result;
}

test('a regression never overwrites the approved baseline', () => {
  const root = createFixture({
    id: 'TEST-BASELINE',
    name: 'baseline guard',
    execution_mode: 'static',
    target_asset: 'missing.txt'
  });
  const baselinePath = path.join(root, 'docs', 'evals', 'baselines', 'current.json');
  const before = fs.readFileSync(baselinePath, 'utf8');

  const result = runFixture(root, ['--static-only', '--update-baseline']);

  assert.equal(result.status, 1);
  assert.equal(fs.readFileSync(baselinePath, 'utf8'), before);
});

test('static-only cannot update an unexecuted runtime baseline', () => {
  const root = createFixture({
    id: 'TEST-RUNTIME-BASELINE',
    name: 'runtime baseline guard',
    execution_mode: 'runtime',
    runtime_contract: {
      scenarios: [{ id: 'P1', prompt: 'runtime observation' }]
    }
  });
  const baselinePath = path.join(root, 'docs', 'evals', 'baselines', 'current.json');
  const before = fs.readFileSync(baselinePath);

  const result = runFixture(root, ['--static-only', '--update-baseline']);

  assert.equal(result.status, 1);
  assert.match(result.stderr, /cannot update.*baseline/i);
  assert.deepEqual(fs.readFileSync(baselinePath), before);
});

test('output_not_contains rejects an observable forbidden output', () => {
  const root = createFixture({
    id: 'TEST-NEGATIVE',
    name: 'negative output contract',
    execution_mode: 'runtime',
    sandbox_mode: 'read-only',
    runtime_contract: {
      scenarios: [{
        id: 'P1',
        prompt: 'plain explanation',
        output_not_contains: ['forbidden skill artifact']
      }]
    }
  });
  const output = JSON.stringify({
    type: 'item.completed',
    item: { type: 'agent_message', text: 'forbidden skill artifact' }
  });

  const result = runFixture(root, [], output);

  assert.equal(result.status, 1);
  assert.match(result.stdout + result.stderr, /출력 금지 계약 위반/);
});

test('runtime contract mutation policy is enforced for composite tasks', () => {
  const root = createFixture({
    id: 'TEST-MUTATION',
    name: 'runtime mutation policy',
    execution_mode: 'composite',
    phases: {
      runtime_audit: {
        prompt: 'audit without edits',
        allow_repo_mutation: false
      }
    }
  });
  const output = [
    JSON.stringify({
      type: 'item.completed',
      item: { type: 'agent_message', text: 'audit complete' }
    }),
    JSON.stringify({
      type: 'item.completed',
      item: { type: 'file_change', changes: [{ path: 'changed.txt', kind: 'update' }] }
    })
  ].join('\n');

  const result = runFixture(root, [], output);

  assert.equal(result.status, 1);
  assert.match(result.stdout + result.stderr, /무단 파일 변경 발생/);
});

test('runtime scenario uses the task read-only sandbox', () => {
  const root = createFixture({
    id: 'TEST-SCENARIO-SANDBOX',
    name: 'read-only runtime scenario',
    execution_mode: 'runtime',
    sandbox_mode: 'read-only',
    runtime_contract: {
      scenarios: [{
        id: 'P3',
        prompt: 'explain this inline',
        output_contains: ['explanation ready']
      }]
    }
  });
  const output = JSON.stringify({
    type: 'item.completed',
    item: { type: 'agent_message', text: 'explanation ready' }
  });

  const result = runFixture(root, [], output);

  assert.equal(result.status, 0);
  assert.match(result.codexArgs, /--sandbox read-only/);
});

test('subagent runtime dispatch names the requested model, effort, and selection basis', () => {
  const root = createFixture({
    id: 'TEST-EXPLICIT-DISPATCH',
    name: 'explicit subagent dispatch',
    execution_mode: 'runtime',
    sandbox_mode: 'read-only',
    runtime_contract: {
      agent: 'verifier',
      requested_model: 'gpt-5.6-sol',
      requested_reasoning_effort: 'high',
      selection_basis: 'default',
      prompt: 'audit the evidence',
      allow_repo_mutation: false
    }
  });
  const output = JSON.stringify({
    type: 'item.completed',
    item: { type: 'agent_message', text: 'audit complete' }
  });

  const result = runFixture(root, [], output);

  assert.equal(result.status, 0);
  assert.match(result.codexArgs, /agent_role=verifier/);
  assert.match(result.codexArgs, /requested_model=gpt-5\.6-sol/);
  assert.match(result.codexArgs, /requested_reasoning_effort=high/);
  assert.match(result.codexArgs, /selection_basis=default/);
});

test('scenario mutation policy rejects repository changes', () => {
  const root = createFixture({
    id: 'TEST-SCENARIO-MUTATION',
    name: 'scenario mutation policy',
    execution_mode: 'runtime',
    runtime_contract: {
      scenarios: [{
        id: 'P3',
        prompt: 'attempt a repository file change',
        side_effect_policy: {
          allow_repo_mutation: false
        }
      }]
    }
  });
  const output = JSON.stringify({
    type: 'item.completed',
    item: {
      type: 'file_change',
      changes: [{ path: 'repository-file.md', kind: 'update' }]
    }
  });

  const result = runFixture(root, [], output);

  assert.equal(result.status, 1);
  assert.match(result.stdout + result.stderr, /무단 파일 변경 발생/);
});

test('runtime JSONL larger than the Node default buffer is still judged', () => {
  const root = createFixture({
    id: 'TEST-LARGE-JSONL',
    name: 'large JSONL buffer',
    execution_mode: 'runtime',
    runtime_contract: {
      scenarios: [{
        id: 'P1',
        prompt: 'produce a large artifact response',
        output_contains: ['large output completed']
      }]
    }
  });
  const output = JSON.stringify({
    type: 'item.completed',
    item: { type: 'agent_message', text: 'large output completed' }
  });

  const result = runFixture(root, [], output, { FAKE_CODEX_LARGE_OUTPUT: '1' });

  assert.equal(result.status, 0);
  assert.match(result.stdout, /출력 계약 충족/);
});

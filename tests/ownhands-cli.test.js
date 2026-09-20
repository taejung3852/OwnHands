const assert = require('node:assert/strict');
const { execFileSync, spawnSync } = require('node:child_process');
const crypto = require('node:crypto');
const fs = require('node:fs');
const os = require('node:os');
const path = require('node:path');
const test = require('node:test');

const ROOT = path.resolve(__dirname, '..');
const CLI = path.join(ROOT, 'bin', 'ownhands.js');
const tempDirs = [];

test.afterEach(() => {
  while (tempDirs.length) fs.rmSync(tempDirs.pop(), { recursive: true, force: true });
});

function git(cwd, ...args) {
  return execFileSync('git', args, { cwd, encoding: 'utf8' }).trim();
}

function makeRepo() {
  const repo = fs.mkdtempSync(path.join(os.tmpdir(), 'ownhands-cli-'));
  tempDirs.push(repo);
  git(repo, 'init', '-b', 'main');
  return repo;
}

function run(repo, ...args) {
  return spawnSync(process.execPath, [CLI, ...args], { cwd: repo, encoding: 'utf8' });
}

function readJson(file) {
  return JSON.parse(fs.readFileSync(file, 'utf8'));
}

function snapshot(root) {
  const entries = [];
  function walk(directory, relative = '') {
    for (const name of fs.readdirSync(directory).sort()) {
      if (!relative && name === '.git') continue;
      const rel = path.join(relative, name);
      const full = path.join(directory, name);
      const stat = fs.lstatSync(full);
      if (stat.isSymbolicLink()) entries.push([rel, `link:${fs.readlinkSync(full)}`]);
      else if (stat.isDirectory()) walk(full, rel);
      else entries.push([rel, crypto.createHash('sha256').update(fs.readFileSync(full)).digest('hex')]);
    }
  }
  walk(root);
  return entries;
}

test('init preserves user config, installs native assets, and is idempotent', () => {
  const repo = makeRepo();
  fs.writeFileSync(path.join(repo, 'AGENTS.md'), '# Project rules\n\nKeep this.\n');
  fs.mkdirSync(path.join(repo, '.codex'), { recursive: true });
  fs.writeFileSync(path.join(repo, '.codex', 'hooks.json'), JSON.stringify({
    hooks: {
      PreToolUse: [{ matcher: '^Other$', hooks: [{ type: 'command', command: 'echo other' }] }],
      PostToolUse: [{ matcher: '.*', hooks: [{ type: 'command', command: 'echo keep' }] }],
    },
    userSetting: true,
  }, null, 2));

  const first = run(repo, 'init');
  assert.equal(first.status, 0, first.stderr);
  assert.match(fs.readFileSync(path.join(repo, 'AGENTS.md'), 'utf8'), /Keep this[\s\S]*<!-- ownhands:start -->/);

  const hooks = readJson(path.join(repo, '.codex', 'hooks.json'));
  assert.equal(hooks.userSetting, true);
  assert.equal(hooks.hooks.PostToolUse.length, 1);
  assert.equal(hooks.hooks.PreToolUse.length, 2);
  assert.equal(hooks.hooks.PreToolUse.filter((entry) => JSON.stringify(entry).includes('review-gate.js')).length, 1);

  for (const skill of ['build', 'explain', 'feedback', 'grill-spec', 'review', 'verify', 'write-issue-pr']) {
    assert.equal(fs.existsSync(path.join(repo, '.agents', 'skills', skill, 'SKILL.md')), true, skill);
  }
  for (const agent of ['researcher', 'verifier', 'reviewer']) {
    assert.equal(fs.existsSync(path.join(repo, '.codex', 'agents', `${agent}.toml`)), true, agent);
  }
  assert.equal(fs.existsSync(path.join(repo, '.codex', 'agents', 'model-policy.md')), true);
  assert.equal(fs.existsSync(path.join(repo, 'scripts', 'review-gate.js')), true);
  for (const file of ['run-evals.js', 'task-set.json', 'baseline.json']) {
    assert.equal(fs.existsSync(path.join(repo, '.ownhands', 'evals', file)), true, file);
  }

  const manifest = readJson(path.join(repo, '.ownhands', 'installation.json'));
  assert.equal(manifest.schema_version, 1);
  assert.equal(manifest.package_version, '0.0.1');
  assert.equal(manifest.source_repository, 'https://github.com/taejung3852/OwnHands');
  assert.equal(manifest.source_revision, 'tag:v0.0.1');
  assert.ok(manifest.assets.length > 10);
  for (const asset of [
    '.ownhands/evals/run-evals.js',
    '.ownhands/evals/task-set.json',
    '.ownhands/evals/baseline.json',
  ]) assert.ok(manifest.assets.some((entry) => entry.path === asset), asset);

  const installed = snapshot(repo);
  const second = run(repo, 'init');
  assert.equal(second.status, 0, second.stderr);
  assert.deepEqual(snapshot(repo), installed);

  const doctor = run(repo, 'doctor');
  assert.equal(doctor.status, 0, doctor.stderr);
  assert.match(doctor.stdout, /healthy/i);
  assert.match(doctor.stdout, /Hook runtime trust: UNOBSERVED/);
});

test('init preflight rejects malformed hooks before writing anything', () => {
  const repo = makeRepo();
  fs.mkdirSync(path.join(repo, '.codex'), { recursive: true });
  const hooksPath = path.join(repo, '.codex', 'hooks.json');
  fs.writeFileSync(hooksPath, '{not-json');

  const before = snapshot(repo);
  const result = run(repo, 'init');

  assert.equal(result.status, 1);
  assert.match(result.stderr, /hooks\.json/);
  assert.deepEqual(snapshot(repo), before);
});

test('init preflight never overwrites owned conflicts, symlinks, or routing drift', async (t) => {
  await t.test('owned file conflict', () => {
    const repo = makeRepo();
    fs.mkdirSync(path.join(repo, 'scripts'));
    fs.writeFileSync(path.join(repo, 'scripts', 'review-gate.js'), 'user file\n');
    const before = snapshot(repo);
    assert.equal(run(repo, 'init').status, 1);
    assert.deepEqual(snapshot(repo), before);
  });

  await t.test('eval asset conflict', () => {
    const repo = makeRepo();
    fs.mkdirSync(path.join(repo, '.ownhands', 'evals'), { recursive: true });
    fs.writeFileSync(path.join(repo, '.ownhands', 'evals', 'task-set.json'), '{"user":true}\n');
    const before = snapshot(repo);
    assert.equal(run(repo, 'init').status, 1);
    assert.deepEqual(snapshot(repo), before);
  });

  await t.test('path symlink', () => {
    const repo = makeRepo();
    const outside = fs.mkdtempSync(path.join(os.tmpdir(), 'ownhands-outside-'));
    tempDirs.push(outside);
    fs.symlinkSync(outside, path.join(repo, '.agents'));
    const before = snapshot(repo);
    assert.equal(run(repo, 'init').status, 1);
    assert.deepEqual(snapshot(repo), before);
  });

  await t.test('dangling target symlink', () => {
    const repo = makeRepo();
    fs.symlinkSync('/definitely/missing/AGENTS.md', path.join(repo, 'AGENTS.md'));
    const before = snapshot(repo);
    assert.equal(run(repo, 'init').status, 1);
    assert.deepEqual(snapshot(repo), before);
  });

  await t.test('routing block drift', () => {
    const repo = makeRepo();
    fs.writeFileSync(path.join(repo, 'AGENTS.md'), '<!-- ownhands:start -->\nchanged\n<!-- ownhands:end -->\n');
    const before = snapshot(repo);
    assert.equal(run(repo, 'init').status, 1);
    assert.deepEqual(snapshot(repo), before);
  });
});

test('doctor is read-only and reports each required installation drift', async (t) => {
  const cases = {
    'missing skill'(repo) {
      fs.rmSync(path.join(repo, '.agents', 'skills', 'explain', 'SKILL.md'));
    },
    'agent drift'(repo) {
      fs.appendFileSync(path.join(repo, '.codex', 'agents', 'reviewer.toml'), '\n# changed\n');
    },
    'review gate drift'(repo) {
      fs.appendFileSync(path.join(repo, 'scripts', 'review-gate.js'), '\n// changed\n');
    },
    'duplicate hook'(repo) {
      const file = path.join(repo, '.codex', 'hooks.json');
      const hooks = readJson(file);
      const ownHands = hooks.hooks.PreToolUse.find((entry) => JSON.stringify(entry).includes('review-gate.js'));
      hooks.hooks.PreToolUse.push(ownHands);
      fs.writeFileSync(file, JSON.stringify(hooks, null, 2));
    },
    'routing drift'(repo) {
      const file = path.join(repo, 'AGENTS.md');
      fs.writeFileSync(file, fs.readFileSync(file, 'utf8').replace('목표 지향 요구공학', '변조된 요구공학'));
    },
    'missing manifest'(repo) {
      fs.rmSync(path.join(repo, '.ownhands', 'installation.json'));
    },
    'missing eval runner'(repo) {
      fs.rmSync(path.join(repo, '.ownhands', 'evals', 'run-evals.js'));
    },
    'eval task set drift'(repo) {
      fs.appendFileSync(path.join(repo, '.ownhands', 'evals', 'task-set.json'), '\n');
    },
    'null manifest'(repo) {
      fs.writeFileSync(path.join(repo, '.ownhands', 'installation.json'), 'null\n');
    },
  };

  for (const [name, mutate] of Object.entries(cases)) {
    await t.test(name, () => {
      const repo = makeRepo();
      assert.equal(run(repo, 'init').status, 0);
      mutate(repo);
      const before = snapshot(repo);
      const result = run(repo, 'doctor');
      assert.equal(result.status, 1, name);
      assert.match(result.stdout, /unhealthy/i);
      assert.deepEqual(snapshot(repo), before);
    });
  }
});

test('init and doctor fail outside Git while help and version remain informational', () => {
  const directory = fs.mkdtempSync(path.join(os.tmpdir(), 'ownhands-no-git-'));
  tempDirs.push(directory);
  assert.equal(run(directory, 'init').status, 1);
  assert.equal(run(directory, 'doctor').status, 1);

  const help = run(directory, '--help');
  assert.equal(help.status, 0, help.stderr);
  assert.match(help.stdout, /ownhands init/);
  assert.match(help.stdout, /ownhands doctor/);
  assert.match(help.stdout, /ownhands eval/);

  const version = run(directory, '--version');
  assert.equal(version.status, 0, version.stderr);
  assert.equal(version.stdout.trim(), '0.0.1');
});

test('eval requires a healthy installation and supports only the public read-only options', () => {
  const repo = makeRepo();

  const beforeInit = run(repo, 'eval', '--static-only');
  assert.equal(beforeInit.status, 1);
  assert.match(beforeInit.stderr, /initialized|installation/i);

  assert.equal(run(repo, 'init').status, 0);

  const staticOnly = run(repo, 'eval', '--static-only');
  assert.equal(staticOnly.status, 0, staticOnly.stderr);
  assert.match(staticOnly.stdout, /INSTALL-0004/);
  assert.match(staticOnly.stdout, /INSTALL-0005/);
  assert.match(staticOnly.stdout, /UNOBSERVED/);

  const single = run(repo, 'eval', '--static-only', '--task', 'INSTALL-0004');
  assert.equal(single.status, 0, single.stderr);
  assert.match(single.stdout, /INSTALL-0004/);
  assert.doesNotMatch(single.stdout, /INSTALL-0005/);

  const json = run(repo, 'eval', '--static-only', '--json');
  assert.equal(json.status, 0, json.stderr);
  const parsed = JSON.parse(json.stdout);
  assert.equal(parsed.results['INSTALL-0004'], 'PASS');
  assert.equal(parsed.results['INSTALL-0001'], 'UNOBSERVED');

  for (const args of [
    ['eval', '--update-baseline'],
    ['eval', '--task'],
    ['eval', '--unknown'],
  ]) {
    const rejected = run(repo, ...args);
    assert.equal(rejected.status, 1, args.join(' '));
    assert.match(rejected.stderr, /Usage:/, args.join(' '));
  }
});

test('runtime routing passes the issue draft no-write boundary to Codex', () => {
  const repo = makeRepo();
  assert.equal(run(repo, 'init').status, 0);
  const binDir = path.join(repo, 'fake-bin');
  const argsPath = path.join(repo, 'codex-args.txt');
  fs.mkdirSync(binDir);
  const codex = path.join(binDir, 'codex');
  fs.writeFileSync(codex, `#!/bin/sh
printf '%s\\n' "$*" >> "$FAKE_CODEX_ARGS_PATH"
case "$*" in
  *"이슈 하나"*) printf '%s\\n' '{"type":"item.completed","item":{"type":"agent_message","text":"## 무엇이 필요한가\\n## 왜 지금인가\\n## 결정할 것"}}' ;;
  *"text-only"*) printf '%s\\n' '{"type":"item.completed","item":{"type":"agent_message","text":"현재 핵심"}}' ;;
  *) printf '%s\\n' '{"type":"item.completed","item":{"type":"agent_message","text":"인라인 설명"}}' ;;
esac
`);
  fs.chmodSync(codex, 0o755);

  const result = spawnSync(process.execPath, [CLI, 'eval', '--task', 'INSTALL-0001'], {
    cwd: repo,
    encoding: 'utf8',
    env: {
      ...process.env,
      PATH: `${binDir}${path.delimiter}${process.env.PATH}`,
      FAKE_CODEX_ARGS_PATH: argsPath,
    },
  });

  assert.equal(result.status, 0, result.stderr);
  const invoked = fs.readFileSync(argsPath, 'utf8');
  assert.match(invoked, /초안만 출력/);
  assert.match(invoked, /GitHub 생성·변경은 하지 말라/);
});

test('npm package contains only the CLI and required native assets', () => {
  const result = spawnSync('npm', ['pack', '--dry-run', '--json'], {
    cwd: ROOT,
    encoding: 'utf8',
  });
  assert.equal(result.status, 0, result.stderr);
  const files = JSON.parse(result.stdout)[0].files.map((item) => item.path).sort();

  for (const required of [
    'bin/ownhands.js',
    'LICENSE',
    '.agents/skills/explain/SKILL.md',
    '.codex/agents/reviewer.toml',
    '.codex/agents/model-policy.md',
    '.codex/hooks.json',
    'scripts/review-gate.js',
    'scripts/run-evals.js',
    'assets/evals/task-set.json',
    'assets/evals/baseline.json',
    'AGENTS.md',
    'package.json',
  ]) assert.ok(files.includes(required), required);

  assert.equal(files.some((file) => file.startsWith('tests/')), false);
  assert.equal(files.some((file) => file.startsWith('docs/')), false);
  const pack = JSON.parse(result.stdout)[0];
  assert.equal(pack.version, '0.0.1');
  assert.equal(pack.name, 'ownhands');
});

test('local npm tarball supports init, doctor, and installed static eval', () => {
  const packageDir = fs.mkdtempSync(path.join(os.tmpdir(), 'ownhands-package-'));
  tempDirs.push(packageDir);
  const packed = spawnSync('npm', ['pack', '--pack-destination', packageDir, '--json'], {
    cwd: ROOT,
    encoding: 'utf8',
  });
  assert.equal(packed.status, 0, packed.stderr);
  const tarball = path.join(packageDir, JSON.parse(packed.stdout)[0].filename);
  const repo = makeRepo();
  const npx = (...args) => spawnSync('npx', ['--yes', '--package', tarball, 'ownhands', ...args], {
    cwd: repo,
    encoding: 'utf8',
  });

  assert.equal(npx('init').status, 0);
  assert.equal(npx('doctor').status, 0);
  const evalResult = npx('eval', '--static-only');
  assert.equal(evalResult.status, 0, evalResult.stderr);
  assert.match(evalResult.stdout, /INSTALL-0004/);
});

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

  const manifest = readJson(path.join(repo, '.ownhands', 'installation.json'));
  assert.equal(manifest.schema_version, 1);
  assert.equal(manifest.package_version, '0.0.0-development');
  assert.equal(manifest.source_repository, 'https://github.com/taejung3852/OwnHands');
  assert.match(manifest.source_revision, /0\.0\.0-development/);
  assert.ok(manifest.assets.length > 10);

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

  const version = run(directory, '--version');
  assert.equal(version.status, 0, version.stderr);
  assert.equal(version.stdout.trim(), '0.0.0-development');
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
    '.agents/skills/explain/SKILL.md',
    '.codex/agents/reviewer.toml',
    '.codex/agents/model-policy.md',
    '.codex/hooks.json',
    'scripts/review-gate.js',
    'AGENTS.md',
    'package.json',
  ]) assert.ok(files.includes(required), required);

  assert.equal(files.some((file) => file.startsWith('tests/')), false);
  assert.equal(files.some((file) => file.startsWith('docs/')), false);
  assert.equal(files.some((file) => file.includes('baselines/')), false);
});

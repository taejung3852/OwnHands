const test = require('node:test');
const assert = require('node:assert/strict');
const { execFileSync, spawnSync } = require('node:child_process');
const fs = require('node:fs');
const os = require('node:os');
const path = require('node:path');

const SCRIPT = path.join(__dirname, 'review-gate.js');
const tempDirs = [];

test.afterEach(() => {
  while (tempDirs.length) fs.rmSync(tempDirs.pop(), { recursive: true, force: true });
});

function git(cwd, ...args) {
  return execFileSync('git', args, { cwd, encoding: 'utf8' }).trim();
}

function plan(findings = '') {
  return `# Plan\n\n## 7. Review Results\n\n${findings}`;
}

function finding({
  id = 'F-01',
  status = 'rejected-with-evidence',
  resolution = 'resolved',
  claim = 'The change can regress.',
  reason = 'The approved contract covers this path.',
  evidence = '- `test.js` regression test PASS',
} = {}) {
  return `### Finding \`${id}\`\n- **Status**: \`${status}\`\n- **Resolution**: \`${resolution}\`\n- **Reviewer claim**: ${claim}\n- **Reason**: ${reason}\n- **Evidence**:\n  ${evidence}\n`;
}

function makeRepo(findings = '') {
  const repo = fs.mkdtempSync(path.join(os.tmpdir(), 'ownhands-review-gate-'));
  tempDirs.push(repo);
  git(repo, 'init', '-b', 'main');
  git(repo, 'config', 'user.email', 'test@example.com');
  git(repo, 'config', 'user.name', 'OwnHands Test');
  const planPath = path.join(repo, 'docs/specs/feature/plan.md');
  fs.mkdirSync(path.dirname(planPath), { recursive: true });
  fs.writeFileSync(planPath, plan(findings));
  fs.writeFileSync(path.join(repo, 'tracked.txt'), 'baseline\n');
  git(repo, 'add', '.');
  git(repo, 'commit', '-m', 'baseline');
  return repo;
}

function run(repo, args, input) {
  return spawnSync(process.execPath, [SCRIPT, ...args], {
    cwd: repo,
    input,
    encoding: 'utf8',
  });
}

function fingerprint(repo, base = 'HEAD') {
  const result = run(repo, ['fingerprint', '--base', base]);
  assert.equal(result.status, 0, result.stderr);
  assert.match(result.stdout.trim(), /^[a-f0-9]{64}$/);
  return result.stdout.trim();
}

function record(repo, reviewedFingerprint = fingerprint(repo), base = 'HEAD') {
  return run(repo, [
    'record',
    '--base', base,
    '--plan', 'docs/specs/feature/plan.md',
    '--reviewed-fingerprint', reviewedFingerprint,
    '--verdict', 'PASS',
  ]);
}

function hook(repo, command, rawInput) {
  const input = rawInput ?? JSON.stringify({
    tool_name: 'Bash',
    tool_input: { command },
  });
  return run(repo, ['check-hook'], input);
}

function evidencePath(repo) {
  const gitDir = git(repo, 'rev-parse', '--git-dir');
  return path.join(fs.realpathSync(path.resolve(repo, gitDir)), 'ownhands', 'review-evidence.json');
}

function assertDenied(result) {
  assert.equal(result.status, 0, result.stderr);
  const output = JSON.parse(result.stdout);
  assert.deepEqual(output, {
    hookSpecificOutput: {
      hookEventName: 'PreToolUse',
      permissionDecision: 'deny',
      permissionDecisionReason: 'OwnHands Review Gate: valid review evidence is missing or stale.',
    },
  });
}

test('unknown command and missing arguments return usage errors', () => {
  const repo = makeRepo();
  for (const args of [['unknown'], ['fingerprint'], ['record', '--base', 'HEAD']]) {
    const result = run(repo, args);
    assert.equal(result.status, 2);
    assert.match(result.stderr, /Usage:/);
  }
});

test('record rejects a plan outside the repository and an unresolved base', () => {
  const repo = makeRepo();
  const outside = path.join(os.tmpdir(), `outside-${Date.now()}.md`);
  fs.writeFileSync(outside, plan());
  try {
    const outsideResult = run(repo, [
      'record', '--base', 'HEAD', '--plan', outside,
      '--reviewed-fingerprint', '0'.repeat(64), '--verdict', 'PASS',
    ]);
    assert.equal(outsideResult.status, 2);

    const linkedPlan = path.join(repo, 'docs/specs/feature/outside-plan.md');
    fs.symlinkSync(outside, linkedPlan);
    const linkedResult = run(repo, [
      'record', '--base', 'HEAD', '--plan', 'docs/specs/feature/outside-plan.md',
      '--reviewed-fingerprint', fingerprint(repo), '--verdict', 'PASS',
    ]);
    assert.equal(linkedResult.status, 2);

    const baseResult = run(repo, ['fingerprint', '--base', 'missing-ref']);
    assert.equal(baseResult.status, 1);
  } finally {
    fs.rmSync(outside, { force: true });
  }
});

test('record rejects malformed Review Results and unsupported finding values', () => {
  const repo = makeRepo(finding({ resolution: '' }));
  let result = record(repo);
  assert.equal(result.status, 1);

  fs.writeFileSync(path.join(repo, 'docs/specs/feature/plan.md'), plan(finding({ status: 'ignored' })));
  result = record(repo, fingerprint(repo));
  assert.equal(result.status, 1);

  fs.writeFileSync(path.join(repo, 'docs/specs/feature/plan.md'), plan(finding() + finding()));
  result = record(repo, fingerprint(repo));
  assert.equal(result.status, 1);

  fs.writeFileSync(
    path.join(repo, 'docs/specs/feature/plan.md'),
    plan(finding().replace('### Finding `F-01`', '### Finding F-01')),
  );
  result = record(repo, fingerprint(repo));
  assert.equal(result.status, 1);
});

test('record rejects rejected-with-evidence without concrete support', () => {
  const repo = makeRepo(finding({ evidence: '' }));
  const result = record(repo);
  assert.equal(result.status, 1);
});

test('record rejects unresolved accepted and needs-human findings', () => {
  for (const status of ['accepted', 'needs-human']) {
    const repo = makeRepo(finding({ status, resolution: 'open' }));
    const result = record(repo);
    assert.equal(result.status, 1, status);
  }
});

test('record accepts resolved accepted findings without erasing their history', () => {
  const repo = makeRepo(finding({ status: 'accepted', resolution: 'resolved' }));
  const result = record(repo);
  assert.equal(result.status, 0, result.stderr);
  const evidence = JSON.parse(fs.readFileSync(evidencePath(repo), 'utf8'));
  assert.deepEqual(evidence.finding_counts, {
    accepted: 0,
    'rejected-with-evidence': 0,
    'needs-human': 0,
  });
});

test('record requires the exact reviewer-observed fingerprint', () => {
  const repo = makeRepo();
  const missing = run(repo, [
    'record', '--base', 'HEAD', '--plan', 'docs/specs/feature/plan.md', '--verdict', 'PASS',
  ]);
  assert.equal(missing.status, 2);

  const mismatch = record(repo, '0'.repeat(64));
  assert.equal(mismatch.status, 1);
  assert.equal(fs.existsSync(evidencePath(repo)), false);
});

test('fingerprint is stable for an unchanged diff and record/clear manage local evidence', () => {
  const repo = makeRepo(finding());
  const first = fingerprint(repo);
  const second = fingerprint(repo);
  assert.equal(second, first);

  const recorded = record(repo, first);
  assert.equal(recorded.status, 0, recorded.stderr);
  const stored = JSON.parse(fs.readFileSync(evidencePath(repo), 'utf8'));
  assert.equal(stored.diff_fingerprint, first);
  assert.equal(stored.verdict, 'PASS');
  assert.equal(stored.finding_counts['rejected-with-evidence'], 1);

  const cleared = run(repo, ['clear']);
  assert.equal(cleared.status, 0, cleared.stderr);
  assert.equal(fs.existsSync(evidencePath(repo)), false);
  assert.equal(run(repo, ['clear']).status, 0);
});

test('fingerprint hashes an untracked symlink itself without reading its target', () => {
  const repo = makeRepo();
  fs.symlinkSync('/definitely/missing/secret', path.join(repo, 'outside-link'));
  const result = run(repo, ['fingerprint', '--base', 'HEAD']);
  assert.equal(result.status, 0, result.stderr);
  assert.match(result.stdout.trim(), /^[a-f0-9]{64}$/);
});

test('committed, staged, unstaged, and untracked changes each stale evidence', async (t) => {
  const mutations = {
    committed(repo) {
      fs.writeFileSync(path.join(repo, 'committed.txt'), 'new\n');
      git(repo, 'add', 'committed.txt');
      git(repo, 'commit', '-m', 'change');
    },
    staged(repo) {
      fs.writeFileSync(path.join(repo, 'staged.txt'), 'new\n');
      git(repo, 'add', 'staged.txt');
    },
    unstaged(repo) {
      fs.writeFileSync(path.join(repo, 'tracked.txt'), 'changed\n');
    },
    untracked(repo) {
      fs.writeFileSync(path.join(repo, 'untracked.txt'), 'new\n');
    },
  };

  for (const [name, mutate] of Object.entries(mutations)) {
    await t.test(name, () => {
      const repo = makeRepo();
      assert.equal(record(repo).status, 0);
      mutate(repo);
      assertDenied(hook(repo, 'git push --dry-run'));
    });
  }
});

test('linked worktrees keep review evidence in separate git directories', () => {
  const repo = makeRepo();
  const worktree = fs.mkdtempSync(path.join(os.tmpdir(), 'ownhands-review-worktree-'));
  fs.rmSync(worktree, { recursive: true, force: true });
  tempDirs.push(worktree);
  git(repo, 'worktree', 'add', '-b', 'feature', worktree);

  assert.equal(record(repo).status, 0);
  assert.equal(record(worktree).status, 0);
  assert.notEqual(evidencePath(repo), evidencePath(worktree));
  assert.equal(fs.existsSync(evidencePath(repo)), true);
  assert.equal(fs.existsSync(evidencePath(worktree)), true);
});

test('check-hook ignores ordinary commands and gates only external Git actions', () => {
  const repo = makeRepo();
  const ordinary = hook(repo, 'node --test');
  assert.equal(ordinary.status, 0);
  assert.equal(ordinary.stdout, '');

  for (const command of [
    'git push',
    'git -C /tmp/repo push origin main',
    'gh pr create --fill',
    'gh pr merge 148 --merge',
    'node --test && git push --dry-run',
  ]) {
    assertDenied(hook(repo, command));
  }
});

test('check-hook safely denies malformed hook JSON', () => {
  const repo = makeRepo();
  assertDenied(hook(repo, '', '{not-json'));
});

test('check-hook allows valid evidence and denies it after the diff changes', () => {
  const repo = makeRepo();
  assert.equal(record(repo).status, 0);

  const allowed = hook(repo, 'git push --dry-run');
  assert.equal(allowed.status, 0, allowed.stderr);
  assert.equal(allowed.stdout, '');

  assertDenied(hook(repo, 'git commit --allow-empty -m late && git push'));

  fs.writeFileSync(path.join(repo, 'later.txt'), 'change\n');
  assertDenied(hook(repo, 'gh pr create --fill'));
});

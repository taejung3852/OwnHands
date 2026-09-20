#!/usr/bin/env node

const { execFileSync } = require('node:child_process');
const crypto = require('node:crypto');
const fs = require('node:fs');
const path = require('node:path');

const PACKAGE_ROOT = path.resolve(__dirname, '..');
const PACKAGE = JSON.parse(fs.readFileSync(path.join(PACKAGE_ROOT, 'package.json'), 'utf8'));
const MANIFEST_PATH = '.ownhands/installation.json';
const HELP = `Usage:
  ownhands init
  ownhands doctor
  ownhands --help
  ownhands --version

init connects packaged OwnHands assets to the current Git repository.
doctor checks the installation without changing files.`;

function fail(message) {
  throw new Error(message);
}

function gitRoot() {
  try {
    const root = execFileSync('git', ['rev-parse', '--show-toplevel'], {
      cwd: process.cwd(),
      encoding: 'utf8',
      stdio: ['ignore', 'pipe', 'pipe'],
    }).trim();
    return fs.realpathSync(root);
  } catch {
    fail('OwnHands requires a Git repository.');
  }
}

function sha256(value) {
  return crypto.createHash('sha256').update(value).digest('hex');
}

function relativeFiles(directory, prefix) {
  const files = [];
  for (const name of fs.readdirSync(directory).sort()) {
    const full = path.join(directory, name);
    const relative = path.posix.join(prefix, name);
    const stat = fs.lstatSync(full);
    if (stat.isSymbolicLink()) fail(`Packaged asset must not be a symlink: ${relative}`);
    if (stat.isDirectory()) files.push(...relativeFiles(full, relative));
    else if (stat.isFile()) files.push(relative);
  }
  return files;
}

function assetPaths() {
  return [
    ...relativeFiles(path.join(PACKAGE_ROOT, '.agents', 'skills'), '.agents/skills'),
    ...relativeFiles(path.join(PACKAGE_ROOT, '.codex', 'agents'), '.codex/agents'),
    'scripts/review-gate.js',
  ];
}

function sourceContent(relative) {
  return fs.readFileSync(path.join(PACKAGE_ROOT, relative));
}

function routingBlock() {
  const source = fs.readFileSync(path.join(PACKAGE_ROOT, 'AGENTS.md'), 'utf8');
  const matches = source.match(/<!-- ownhands:start -->[\s\S]*?<!-- ownhands:end -->/g) || [];
  if (matches.length !== 1) fail('Packaged AGENTS.md must contain exactly one OwnHands routing block.');
  return matches[0];
}

function sourceHook() {
  const config = JSON.parse(fs.readFileSync(path.join(PACKAGE_ROOT, '.codex', 'hooks.json'), 'utf8'));
  const entries = config?.hooks?.PreToolUse;
  if (!Array.isArray(entries)) fail('Packaged .codex/hooks.json is invalid.');
  const matches = entries.filter(isOwnHandsHook);
  if (matches.length !== 1) fail('Packaged hooks must contain exactly one OwnHands entry.');
  return matches[0];
}

function isOwnHandsHook(entry) {
  const text = JSON.stringify(entry);
  return text.includes('scripts/review-gate.js') && text.includes('check-hook');
}

function sameJson(left, right) {
  return JSON.stringify(left) === JSON.stringify(right);
}

function manifest() {
  const assets = assetPaths().map((relative) => ({
    path: relative,
    sha256: sha256(sourceContent(relative)),
  }));
  const block = routingBlock();
  const hook = sourceHook();
  return {
    schema_version: 1,
    package_name: PACKAGE.name,
    package_version: PACKAGE.version,
    source_repository: PACKAGE.ownhands.sourceRepository,
    source_revision: PACKAGE.ownhands.sourceRevision,
    assets,
    integrations: {
      agents_routing_sha256: sha256(block),
      hook_entry_sha256: sha256(JSON.stringify(hook)),
    },
  };
}

function lstatIfPresent(file) {
  try {
    return fs.lstatSync(file);
  } catch (error) {
    if (error.code === 'ENOENT') return null;
    throw error;
  }
}

function assertSafePath(root, relative) {
  const target = path.resolve(root, relative);
  const relation = path.relative(root, target);
  if (!relation || relation.startsWith('..') || path.isAbsolute(relation)) {
    fail(`Path escapes repository: ${relative}`);
  }
  let current = root;
  for (const part of relation.split(path.sep)) {
    current = path.join(current, part);
    const stat = lstatIfPresent(current);
    if (!stat) continue;
    if (stat.isSymbolicLink()) fail(`Refusing symlink path: ${relative}`);
    if (current !== target && !stat.isDirectory()) fail(`Parent path is not a directory: ${relative}`);
  }
  return target;
}

function plannedAssetWrites(root) {
  const writes = [];
  for (const relative of assetPaths()) {
    const target = assertSafePath(root, relative);
    const content = sourceContent(relative);
    const stat = lstatIfPresent(target);
    if (!stat) writes.push({ target, content });
    else if (!stat.isFile() || !fs.readFileSync(target).equals(content)) {
      fail(`Owned asset conflict; refusing to overwrite: ${relative}`);
    }
  }
  return writes;
}

function plannedHooksWrite(root) {
  const relative = '.codex/hooks.json';
  const target = assertSafePath(root, relative);
  let config = { hooks: {} };
  const stat = lstatIfPresent(target);
  if (stat) {
    try {
      config = JSON.parse(fs.readFileSync(target, 'utf8'));
    } catch {
      fail('Existing .codex/hooks.json is not valid JSON.');
    }
  }
  if (!config || Array.isArray(config) || typeof config !== 'object') {
    fail('Existing .codex/hooks.json must be a JSON object.');
  }
  if (config.hooks === undefined) config.hooks = {};
  if (!config.hooks || Array.isArray(config.hooks) || typeof config.hooks !== 'object') {
    fail('Existing .codex/hooks.json hooks must be an object.');
  }
  if (config.hooks.PreToolUse === undefined) config.hooks.PreToolUse = [];
  if (!Array.isArray(config.hooks.PreToolUse)) {
    fail('Existing .codex/hooks.json PreToolUse must be an array.');
  }

  const expected = sourceHook();
  const matches = config.hooks.PreToolUse.filter(isOwnHandsHook);
  if (matches.length > 1) fail('OwnHands hook is duplicated.');
  if (matches.length === 1 && !sameJson(matches[0], expected)) {
    fail('Existing OwnHands hook differs; update/migrate is not supported.');
  }
  if (matches.length === 0) config.hooks.PreToolUse.push(expected);
  const content = Buffer.from(`${JSON.stringify(config, null, 2)}\n`);
  return stat && fs.readFileSync(target).equals(content) ? null : { target, content };
}

function plannedAgentsWrite(root) {
  const relative = 'AGENTS.md';
  const target = assertSafePath(root, relative);
  const block = routingBlock();
  const existing = lstatIfPresent(target) ? fs.readFileSync(target, 'utf8') : '';
  const starts = (existing.match(/<!-- ownhands:start -->/g) || []).length;
  const ends = (existing.match(/<!-- ownhands:end -->/g) || []).length;
  if (starts !== ends || starts > 1) fail('Existing AGENTS.md has invalid OwnHands markers.');
  if (starts === 1) {
    const installed = existing.match(/<!-- ownhands:start -->[\s\S]*?<!-- ownhands:end -->/)?.[0];
    if (installed !== block) fail('Existing OwnHands routing block differs; update/migrate is not supported.');
    return null;
  }
  const separator = existing && !existing.endsWith('\n\n') ? (existing.endsWith('\n') ? '\n' : '\n\n') : '';
  return { target, content: Buffer.from(`${existing}${separator}${block}\n`) };
}

function plannedManifestWrite(root, expected) {
  const target = assertSafePath(root, MANIFEST_PATH);
  const content = Buffer.from(`${JSON.stringify(expected, null, 2)}\n`);
  if (!lstatIfPresent(target)) return { target, content };
  let installed;
  try {
    installed = JSON.parse(fs.readFileSync(target, 'utf8'));
  } catch {
    fail('Existing installation manifest is invalid.');
  }
  if (!sameJson(installed, expected)) fail('A different OwnHands installation is present; update/migrate is not supported.');
  return null;
}

function atomicWrite(target, content) {
  fs.mkdirSync(path.dirname(target), { recursive: true });
  const temporary = path.join(path.dirname(target), `.${path.basename(target)}.${process.pid}.tmp`);
  try {
    fs.writeFileSync(temporary, content, { mode: 0o644, flag: 'wx' });
    fs.renameSync(temporary, target);
  } finally {
    fs.rmSync(temporary, { force: true });
  }
}

function validateAgent(content, name) {
  return (
    new RegExp(`^name\\s*=\\s*"${name}"\\s*$`, 'm').test(content) &&
    /^description\s*=\s*".+"\s*$/m.test(content) &&
    /^sandbox_mode\s*=\s*"read-only"\s*$/m.test(content) &&
    /^developer_instructions\s*=\s*"""/m.test(content) &&
    (content.match(/"""/g) || []).length === 2 &&
    !/^model\s*=/m.test(content) &&
    !/^model_reasoning_effort\s*=/m.test(content)
  );
}

function init() {
  const root = gitRoot();
  const expectedManifest = manifest();

  for (const name of ['researcher', 'verifier', 'reviewer']) {
    const content = sourceContent(`.codex/agents/${name}.toml`).toString('utf8');
    if (!validateAgent(content, name)) fail(`Packaged agent definition is invalid: ${name}`);
  }

  const writes = [
    ...plannedAssetWrites(root),
    plannedHooksWrite(root),
    plannedAgentsWrite(root),
    plannedManifestWrite(root, expectedManifest),
  ].filter(Boolean);

  for (const write of writes) atomicWrite(write.target, write.content);
  process.stdout.write(`OwnHands initialized at ${root}.\n`);
}

function doctor() {
  const root = gitRoot();
  const expected = manifest();
  const problems = [];
  let installed = null;

  try {
    installed = JSON.parse(fs.readFileSync(assertSafePath(root, MANIFEST_PATH), 'utf8'));
  } catch {
    problems.push('installation manifest is missing or invalid');
  }
  if (!installed || Array.isArray(installed) || typeof installed !== 'object') {
    problems.push('installation manifest is missing or invalid');
  } else if (!sameJson(installed, expected)) {
    problems.push('installation manifest revision or asset list differs');
  }

  for (const asset of expected.assets) {
    try {
      const target = assertSafePath(root, asset.path);
      if (!fs.lstatSync(target).isFile() || sha256(fs.readFileSync(target)) !== asset.sha256) {
        problems.push(`asset drift: ${asset.path}`);
      }
    } catch {
      problems.push(`asset missing or unsafe: ${asset.path}`);
    }
  }

  for (const name of ['researcher', 'verifier', 'reviewer']) {
    try {
      const content = fs.readFileSync(path.join(root, '.codex', 'agents', `${name}.toml`), 'utf8');
      if (!validateAgent(content, name)) problems.push(`agent is not parseable/read-only: ${name}`);
    } catch {
      problems.push(`agent missing: ${name}`);
    }
  }

  try {
    const config = JSON.parse(fs.readFileSync(path.join(root, '.codex', 'hooks.json'), 'utf8'));
    const matches = (config?.hooks?.PreToolUse || []).filter(isOwnHandsHook);
    if (matches.length !== 1 || !sameJson(matches[0], sourceHook())) problems.push('OwnHands hook is missing, duplicated, or changed');
  } catch {
    problems.push('hook configuration is missing or invalid');
  }

  try {
    const content = fs.readFileSync(path.join(root, 'AGENTS.md'), 'utf8');
    const matches = content.match(/<!-- ownhands:start -->[\s\S]*?<!-- ownhands:end -->/g) || [];
    if (matches.length !== 1 || matches[0] !== routingBlock()) problems.push('OwnHands routing block is missing or changed');
  } catch {
    problems.push('AGENTS.md routing is missing');
  }

  if (problems.length) {
    process.stdout.write('OwnHands installation is unhealthy:\n');
    for (const problem of [...new Set(problems)]) process.stdout.write(`- ${problem}\n`);
    process.stdout.write('Hook runtime trust: UNOBSERVED (doctor checks configuration only).\n');
    process.exitCode = 1;
  } else {
    process.stdout.write('OwnHands installation is healthy.\n');
    process.stdout.write(`Revision: ${expected.source_revision}\n`);
    process.stdout.write('Hook runtime trust: UNOBSERVED (doctor checks configuration only).\n');
  }
}

function main(argument) {
  if (Number(process.versions.node.split('.')[0]) < 18) fail('OwnHands requires Node.js 18 or newer.');
  if (argument === '--help' || argument === '-h') return process.stdout.write(`${HELP}\n`);
  if (argument === '--version' || argument === '-v') return process.stdout.write(`${PACKAGE.version}\n`);
  if (argument === 'init') return init();
  if (argument === 'doctor') return doctor();
  process.stderr.write(`${HELP}\n`);
  process.exitCode = 1;
}

try {
  if (process.argv.length !== 3) main('');
  else main(process.argv[2]);
} catch (error) {
  process.stderr.write(`OwnHands: ${error.message}\n`);
  process.exitCode = 1;
}

import assert from 'node:assert/strict';
import { test } from 'node:test';
import { spawn } from 'node:child_process';
import { createInterface } from 'node:readline';
import { createHash } from 'node:crypto';
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { parse } from 'yaml';

const provider = fileURLToPath(new URL('../', import.meta.url));
const server = path.join(provider, 'server.mjs');
const canonical = path.resolve(provider, '../../plugins/ownhands/skills');
const digest = bytes => `sha256:${createHash('sha256').update(bytes).digest('hex')}`;

function session(t, entry = server) {
  const child = spawn(process.execPath, [entry], { stdio: ['pipe', 'pipe', 'pipe'] });
  const pending = new Map();
  const invalid = [];
  let nextId = 0;
  let stderr = '';
  child.stderr.on('data', b => { stderr += b; });
  const lines = createInterface({ input: child.stdout });
  lines.on('line', line => {
    let msg;
    try { msg = JSON.parse(line); } catch { invalid.push(line); return; }
    const waiter = pending.get(msg.id);
    if (waiter) { pending.delete(msg.id); clearTimeout(waiter.timer); waiter.resolve(msg); }
  });
  child.on('exit', () => {
    for (const waiter of pending.values()) { clearTimeout(waiter.timer); waiter.reject(new Error(`Server exited: ${stderr}`)); }
    pending.clear();
  });
  t.after(() => { lines.close(); child.kill(); });
  function request(method, params = {}) {
    const id = ++nextId;
    return new Promise((resolve, reject) => {
      const timer = setTimeout(() => { pending.delete(id); reject(new Error(`Timeout: ${method}`)); }, 5000);
      pending.set(id, { resolve, reject, timer });
      child.stdin.write(`${JSON.stringify({ jsonrpc: '2.0', id, method, params })}\n`);
    });
  }
  return {
    request, invalid,
    async initialize() {
      const msg = await request('initialize', { protocolVersion: '2025-11-25', capabilities: {}, clientInfo: { name: 'ownhands-local-test', version: '1.0.0' } });
      assert.ok(msg.result, JSON.stringify(msg));
      child.stdin.write(`${JSON.stringify({ jsonrpc: '2.0', method: 'notifications/initialized' })}\n`);
      return msg.result;
    },
  };
}

function fixture(t) {
  const dir = fs.realpathSync(fs.mkdtempSync(path.join(os.tmpdir(), 'ownhands-provider-')));
  t.after(() => fs.rmSync(dir, { recursive: true, force: true }));
  const root = path.join(dir, 'plugins/ownhands/skills');
  fs.mkdirSync(path.dirname(root), { recursive: true });
  fs.cpSync(canonical, root, { recursive: true });
  return { dir, root };
}
async function loader() { return (await import('../server.mjs')).loadSnapshot; }

test('provider initializes over real stdio with the requested identity and capabilities', async t => {
  assert.ok(fs.existsSync(server), 'provider entrypoint must exist');
  const s = session(t);
  const init = await s.initialize();
  assert.deepEqual(init.serverInfo, { name: 'ownhands-skill-provider', version: '0.1.0' });
  assert.equal(init.instructions, 'Provides the canonical OwnHands plan-design and ELI5 skill resources. It does not provide GitHub, shell, or repository mutation tools.');
  assert.deepEqual(init.capabilities.extensions, { 'io.modelcontextprotocol/skills': {} });
  assert.ok(init.capabilities.tools && init.capabilities.resources);
  assert.equal(init.capabilities.experimental, undefined);
  assert.deepEqual((await s.request('ping')).result, {});
  assert.deepEqual(s.invalid, []);
});

test('status is the only tool, is read-only, and rejects other tools and arguments', async t => {
  const s = session(t); await s.initialize();
  const list = (await s.request('tools/list')).result.tools;
  assert.deepEqual(list.map(x => x.name), ['ownhands_status']);
  assert.equal(list[0].title, 'OwnHands status');
  assert.deepEqual(list[0].annotations, { readOnlyHint: true, destructiveHint: false, idempotentHint: true, openWorldHint: false });
  const result = (await s.request('tools/call', { name: 'ownhands_status', arguments: {} })).result;
  assert.deepEqual(JSON.parse(result.content[0].text), result.structuredContent);
  assert.equal(result.structuredContent.status, 'ok');
  assert.deepEqual(result.structuredContent.skills, ['plan-design', 'eli5']);
  const catalog = (await s.request('skills/list')).result.skills;
  const entries = catalog.flatMap(s => s.resources.map(r => [r.uri, r.digest])).sort((a, b) => a[0] < b[0] ? -1 : a[0] > b[0] ? 1 : 0);
  assert.equal(result.structuredContent.revision, digest(JSON.stringify(entries)));
  for (const name of ['shell', 'github_write', 'write_file', 'codex', 'plan-design']) {
    assert.ok((await s.request('tools/call', { name, arguments: {} })).error, name);
  }
  assert.ok((await s.request('tools/call', { name: 'ownhands_status', arguments: { path: '/etc/passwd' } })).error);
});

test('catalog/get/read include every canonical file with exact bytes, frontmatter, and digest', async t => {
  const s = session(t); await s.initialize();
  const listed = (await s.request('skills/list')).result;
  assert.equal(listed.nextCursor, undefined);
  assert.deepEqual(listed.skills.map(x => x.frontmatter.name), ['plan-design', 'eli5']);
  const expectedUris = [];
  function walk(dir, relative = '') {
    return fs.readdirSync(dir, { withFileTypes: true }).flatMap(e => e.isDirectory() ? walk(path.join(dir, e.name), `${relative}${e.name}/`) : [`${relative}${e.name}`]);
  }
  for (const skill of listed.skills) {
    assert.deepEqual((await s.request('skills/get', { uri: skill.uri })).result.skill, skill);
    const dir = path.join(canonical, skill.frontmatter.name);
    const content = fs.readFileSync(path.join(dir, 'SKILL.md'), 'utf8');
    assert.deepEqual(skill.frontmatter, parse(content.split('---')[1]));
    const prefix = `skill://ownhands/${skill.frontmatter.name}/`;
    assert.deepEqual(skill.resources.map(x => x.uri).sort(), walk(dir).map(x => prefix + x).sort());
    for (const resource of skill.resources) {
      expectedUris.push(resource.uri);
      const original = fs.readFileSync(path.join(dir, resource.uri.slice(prefix.length)));
      const read = (await s.request('resources/read', { uri: resource.uri })).result.contents;
      assert.equal(read.length, 1); assert.equal(read[0].uri, resource.uri);
      const actual = read[0].text === undefined ? Buffer.from(read[0].blob, 'base64') : Buffer.from(read[0].text, 'utf8');
      assert.deepEqual(actual, original);
      assert.equal(resource.digest, digest(actual));
    }
  }
  assert.deepEqual((await s.request('resources/list')).result.resources.map(x => x.uri).sort(), expectedUris.sort());
  assert.deepEqual(s.invalid, []);
});

test('unregistered URIs, traversal, normalization aliases, unknown methods and cursors are rejected', async t => {
  const s = session(t); await s.initialize();
  for (const uri of ['/etc/passwd', 'file:///etc/passwd', 'skill://ownhands/plan-design/../../package.json', 'skill://ownhands/plan-design/%2e%2e/eli5/SKILL.md', 'skill://ownhands/plan-design/./SKILL.md', 'skill://ownhands/plan-design/SKILL.md?x=1', 'skill://ownhands/plan-design/SKILL.md#x', 'skill://other/plan-design/SKILL.md', 'skill://ownhands/plan-design/SKILL.md\0']) {
    assert.ok((await s.request('resources/read', { uri })).error, uri);
    assert.ok((await s.request('skills/get', { uri })).error, uri);
  }
  assert.ok((await s.request('skills/list', { cursor: 'unknown' })).error);
  assert.ok((await s.request('resources/list', { cursor: 'unknown' })).error);
  assert.ok((await s.request('skills/get', { uri: 12 })).error);
  assert.ok((await s.request('resources/read')).error);
  assert.equal((await s.request('filesystem/write', { path: '/tmp/no-write' })).error.code, -32601);
});

test('startup rejects symlinks and unsafe paths before serving', async t => {
  const load = await loader();
  for (const variant of ['file-link', 'dir-link', 'skill-link', 'root-link', 'percent', 'backslash']) {
    const { dir, root } = fixture(t);
    const skill = path.join(root, 'eli5');
    if (variant === 'file-link') fs.symlinkSync('/etc/passwd', path.join(skill, 'secret'));
    if (variant === 'dir-link') fs.symlinkSync('/etc', path.join(skill, 'outside'));
    if (variant === 'skill-link') { fs.rmSync(skill, { recursive: true }); fs.symlinkSync('/etc', skill); }
    if (variant === 'root-link') { fs.renameSync(root, `${root}-real`); fs.symlinkSync(`${root}-real`, root); }
    if (variant === 'percent') fs.writeFileSync(path.join(skill, '%2e%2e'), 'x');
    if (variant === 'backslash') fs.writeFileSync(path.join(skill, 'bad\\name'), 'x');
    assert.throws(() => load(root), undefined, variant);
    assert.ok(fs.existsSync(dir));
  }
});

test('startup validates frontmatter, names, missing files and import limits', async t => {
  const load = await loader();
  for (const variant of ['missing', 'malformed', 'mismatch', 'duplicate-key', 'no-description', 'non-json', 'many-files', 'large-main', 'large-support', 'large-skill', 'large-scan']) {
    const { root } = fixture(t); const dir = path.join(root, 'eli5'); const entry = path.join(dir, 'SKILL.md');
    if (variant === 'missing') fs.unlinkSync(entry);
    if (variant === 'malformed') fs.writeFileSync(entry, '---\nname: [\n---\n');
    if (variant === 'mismatch') fs.writeFileSync(entry, '---\nname: other\ndescription: test\n---\n');
    if (variant === 'duplicate-key') fs.writeFileSync(entry, '---\nname: eli5\nname: other\ndescription: test\n---\n');
    if (variant === 'no-description') fs.writeFileSync(entry, '---\nname: eli5\n---\n');
    if (variant === 'non-json') fs.writeFileSync(entry, '---\nname: eli5\ndescription: test\nvalue: .nan\n---\n');
    if (variant === 'many-files') for (let i = 0; i < 101; i++) fs.writeFileSync(path.join(dir, `extra-${i}.txt`), 'x');
    if (variant === 'large-main') fs.appendFileSync(entry, 'x'.repeat(256 * 1024));
    if (variant === 'large-support') fs.writeFileSync(path.join(dir, 'large.bin'), Buffer.alloc(1024 * 1024 + 1));
    if (variant === 'large-skill') for (let i = 0; i < 6; i++) fs.writeFileSync(path.join(dir, `large-${i}.bin`), Buffer.alloc(1024 * 1024));
    if (variant === 'large-scan') for (const name of ['eli5', 'plan-design']) for (let i = 0; i < 4; i++) fs.writeFileSync(path.join(root, name, `large-${i}.bin`), Buffer.alloc(1024 * 1024));
    assert.throws(() => load(root), undefined, variant);
  }
});

test('snapshot stays consistent, binary resources round-trip, restart changes revision', async t => {
  const { dir, root } = fixture(t);
  const entryDir = path.join(dir, 'tools/ownhands-skill-provider'); fs.mkdirSync(entryDir, { recursive: true });
  fs.copyFileSync(server, path.join(entryDir, 'server.mjs'));
  fs.symlinkSync(path.join(provider, 'node_modules'), path.join(entryDir, 'node_modules'));
  fs.writeFileSync(path.join(root, 'eli5', 'sample.bin'), Buffer.from([0xff, 0x00, 0xfe]));
  // A nested frontmatter value must survive parsing, not just name/description.
  const skillFile = path.join(root, 'eli5', 'SKILL.md');
  fs.writeFileSync(skillFile, fs.readFileSync(skillFile, 'utf8').replace('\n---\n\n#', '\nmetadata:\n  labels: [one, two]\n  enabled: true\n---\n\n#'));
  const s = session(t, path.join(entryDir, 'server.mjs')); await s.initialize();
  const uri = 'skill://ownhands/eli5/SKILL.md';
  const before = (await s.request('resources/read', { uri })).result;
  const status = (await s.request('tools/call', { name: 'ownhands_status' })).result.structuredContent;
  const skill = (await s.request('skills/get', { uri })).result.skill;
  assert.deepEqual(skill.frontmatter.metadata, { labels: ['one', 'two'], enabled: true });
  const binary = (await s.request('resources/read', { uri: 'skill://ownhands/eli5/sample.bin' })).result.contents[0];
  assert.deepEqual(Buffer.from(binary.blob, 'base64'), Buffer.from([0xff, 0x00, 0xfe]));
  fs.appendFileSync(skillFile, '\nChanged after startup.\n');
  assert.deepEqual((await s.request('resources/read', { uri })).result, before);
  assert.deepEqual((await s.request('tools/call', { name: 'ownhands_status' })).result.structuredContent, status);
  const after = session(t, path.join(entryDir, 'server.mjs')); await after.initialize();
  assert.notEqual((await after.request('tools/call', { name: 'ownhands_status' })).result.structuredContent.revision, status.revision);
  assert.match((await after.request('resources/read', { uri })).result.contents[0].text, /Changed after startup/);
});

test('invalid startup exits without protocol output or source contents in the error', async t => {
  const { dir, root } = fixture(t);
  const entryDir = path.join(dir, 'tools/ownhands-skill-provider'); fs.mkdirSync(entryDir, { recursive: true });
  fs.copyFileSync(server, path.join(entryDir, 'server.mjs'));
  fs.symlinkSync(path.join(provider, 'node_modules'), path.join(entryDir, 'node_modules'));
  fs.writeFileSync(path.join(root, 'eli5/SKILL.md'), '---\nname: [SENSITIVE_TEST_MARKER\n---\n');
  const child = spawn(process.execPath, [path.join(entryDir, 'server.mjs')]);
  t.after(() => child.kill());
  let stdout = ''; let stderr = '';
  child.stdout.on('data', b => { stdout += b; }); child.stderr.on('data', b => { stderr += b; });
  const exit = await new Promise((resolve, reject) => {
    const timer = setTimeout(() => { child.kill(); reject(new Error('startup failure did not exit')); }, 5000);
    child.on('close', code => { clearTimeout(timer); resolve(code); });
  });
  assert.equal(exit, 1); assert.equal(stdout, '');
  assert.match(stderr, /startup failed/); assert.doesNotMatch(stderr, /SENSITIVE_TEST_MARKER/);
});

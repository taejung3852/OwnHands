const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const crypto = require('node:crypto');
const test = require('node:test');
const root = path.resolve(__dirname, '../plugins/ownhands');

function files(dir) {
  return fs.readdirSync(dir, { withFileTypes: true }).flatMap(entry => {
    const file = path.join(dir, entry.name);
    return entry.isDirectory() ? files(file) : [file];
  });
}

test('portable skills-only package has exactly the two intended skill entrypoints', () => {
  assert.ok(fs.existsSync(path.join(root, 'plugin.json')));
  assert.deepEqual(fs.readdirSync(path.join(root, 'skills')).sort(), ['eli5', 'plan-design']);
  for (const skill of ['eli5', 'plan-design']) {
    assert.ok(fs.existsSync(path.join(root, 'skills', skill, 'SKILL.md')));
    assert.ok(fs.existsSync(path.join(root, 'skills', skill, 'agents/openai.yaml')));
  }
  assert.equal(files(root).some(file => /(?:mcp\.json|hooks\.json)$/.test(file)), false);
  const manifest = JSON.parse(fs.readFileSync(path.join(root, 'plugin.json')));
  assert.equal(manifest.$schema, 'https://agent-plugins.org/schemas/1.0.0/plugin.schema.json');
  assert.equal(manifest.name, 'ownhands');
});

test('portable manifest retains the uploaded branding with bundled image paths', () => {
  const manifest = JSON.parse(fs.readFileSync(path.join(root, 'plugin.json')));
  const branding = manifest.extensions?.['com.openai']?.interface;
  assert.equal(branding?.displayName, 'OwnHands');
  assert.match(branding?.shortDescription ?? '', /software changes/);
  assert.equal(branding?.composerIcon, './assets/ownhands.png');
  assert.equal(branding?.logo, './assets/ownhands.png');
  for (const asset of [branding.composerIcon, branding.logo]) {
    assert.ok(fs.existsSync(path.join(root, asset)), `${asset} must be bundled`);
  }
});

test('plugin markdown relative links resolve inside this repository', () => {
  const repo = path.resolve(root, '../..');
  for (const file of files(root).filter(file => file.endsWith('.md'))) {
    // Templates inside code are not navigable Markdown links.
    const text = fs.readFileSync(file, 'utf8').replace(/```[\s\S]*?```/g, '').replace(/`[^`\n]*`/g, '');
    for (const [, target] of text.matchAll(/\[[^\]]*\]\(([^)]+)\)/g)) {
      if (/^(?:https?:|#)/.test(target)) continue;
      const resolved = path.resolve(path.dirname(file), target.split('#')[0]);
      assert.ok(resolved.startsWith(repo + path.sep), `${file}: ${target}`);
      assert.ok(fs.existsSync(resolved), `${file}: ${target}`);
    }
  }
});

test('ELI5 skill bytes match the inspected pinned upstream blob', () => {
  const content = fs.readFileSync(path.join(root, 'skills/eli5/SKILL.md'));
  const blob = crypto.createHash('sha1').update(`blob ${content.length}\0`).update(content).digest('hex');
  assert.equal(blob, 'ff6b33c9b3277c493e03e47fad327c6ad318e1d5');
  assert.match(fs.readFileSync(path.join(root, 'skills/eli5/LICENSE'), 'utf8'), /Apache License/);
});

test('plan-design resolves the target repository before repository-specific fact gathering', () => {
  const skill = fs.readFileSync(path.join(root, 'skills/plan-design/SKILL.md'), 'utf8');
  const workflow = fs.readFileSync(path.join(root, 'skills/plan-design/references/github-workflow.md'), 'utf8');
  const interview = fs.readFileSync(path.join(root, 'skills/plan-design/references/interview-guide.md'), 'utf8');

  assert.match(skill, /Target Repository Resolution/);
  assert.match(workflow, /Plugin source repository.*target repository/);
  assert.match(workflow, /taejung3852\/OwnHands.*기본값으로.*않는다/);
  assert.match(workflow, /Repository.*미확정.*repository-specific Fact Gathering.*전에.*선택/);
  assert.match(interview, /repository-specific Fact Gathering.*Target Repository.*확정.*뒤/);
});

test('plan-design makes the persistence route choice the only write approval', () => {
  const skill = fs.readFileSync(path.join(root, 'skills/plan-design/SKILL.md'), 'utf8');
  const workflow = fs.readFileSync(path.join(root, 'skills/plan-design/references/github-workflow.md'), 'utf8');
  const intent = fs.readFileSync(path.join(root, 'skills/plan-design/references/intent-guide.md'), 'utf8');
  const spec = fs.readFileSync(path.join(root, 'skills/plan-design/references/spec-guide.md'), 'utf8');

  assert.match(skill, /새 Issue\/Branch 저장 경로는 Content Approval 뒤 Persistence Decision에서 결정한다/);
  assert.match(workflow, /## Planning-time read[\s\S]*## Persistence topology/);
  assert.match(workflow, /1\/2 선택 자체가 Persistence Approval/);
  assert.match(workflow, /추가 write 승인을 묻지 않는다/);
  assert.match(workflow, /최신 HEAD.*다시 읽는다/);
  assert.match(intent, /Content Approval[\s\S]*Persistence Decision[\s\S]*Issue\/Branch[\s\S]*Stage commit/);
  assert.match(spec, /Persistence Decision[\s\S]*Stage commit/);
});

test('explicit ELI5 requests do not advance stage completion or approval', () => {
  const skill = fs.readFileSync(path.join(root, 'skills/plan-design/SKILL.md'), 'utf8');
  const interview = fs.readFileSync(path.join(root, 'skills/plan-design/references/interview-guide.md'), 'utf8');

  assert.match(skill, /명시적.*ELI5.*언제든.*Stage.*승인.*자동.*않는다/);
  assert.match(interview, /명시적.*ELI5.*Stage.*완료.*승인.*자동.*않는다/);
});

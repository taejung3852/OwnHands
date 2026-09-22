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

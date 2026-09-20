#!/usr/bin/env node

const { execFileSync } = require('node:child_process');
const crypto = require('node:crypto');
const fs = require('node:fs');
const path = require('node:path');

const USAGE = `Usage:
  node scripts/review-gate.js fingerprint --base <ref>
  node scripts/review-gate.js record --base <ref> --plan <path> --reviewed-fingerprint <sha256> --verdict PASS
  node scripts/review-gate.js check-hook
  node scripts/review-gate.js clear`;

const DENY = {
  hookSpecificOutput: {
    hookEventName: 'PreToolUse',
    permissionDecision: 'deny',
    permissionDecisionReason: 'OwnHands Review Gate: valid review evidence is missing or stale.',
  },
};
const SHELL_CONTROL = '[;&|()\\r\\n]';

class UsageError extends Error {}

function git(args, cwd = process.cwd()) {
  return execFileSync('git', args, { cwd, stdio: ['ignore', 'pipe', 'pipe'] });
}

function textGit(args, cwd) {
  return git(args, cwd).toString('utf8').trim();
}

function repository() {
  const root = fs.realpathSync(textGit(['rev-parse', '--show-toplevel']));
  const gitDirValue = textGit(['rev-parse', '--git-dir'], root);
  const gitDir = fs.realpathSync(path.resolve(root, gitDirValue));
  return { root, gitDir };
}

function parseFlags(args, allowed, required) {
  const values = {};
  for (let index = 0; index < args.length; index += 2) {
    const flag = args[index];
    const value = args[index + 1];
    if (!allowed.has(flag) || value === undefined || value.startsWith('--')) throw new UsageError();
    if (values[flag] !== undefined) throw new UsageError();
    values[flag] = value;
  }
  for (const flag of required) if (values[flag] === undefined) throw new UsageError();
  return values;
}

function addFrame(hash, label, value) {
  const buffer = Buffer.isBuffer(value) ? value : Buffer.from(value);
  hash.update(`${label}\0${buffer.length}\0`);
  hash.update(buffer);
}

function calculateFingerprint(baseRef, repo = repository()) {
  let baseSha;
  let headSha;
  try {
    baseSha = textGit(['rev-parse', '--verify', `${baseRef}^{commit}`], repo.root);
    headSha = textGit(['rev-parse', '--verify', 'HEAD^{commit}'], repo.root);
  } catch {
    throw new Error(`Unable to resolve base or HEAD: ${baseRef}`);
  }

  const hash = crypto.createHash('sha256');
  addFrame(hash, 'base_sha', baseSha);
  addFrame(hash, 'head_sha', headSha);
  addFrame(hash, 'committed', git(['diff', '--binary', `${baseSha}...HEAD`], repo.root));
  addFrame(hash, 'staged', git(['diff', '--binary', '--cached'], repo.root));
  addFrame(hash, 'unstaged', git(['diff', '--binary'], repo.root));

  const paths = git(['ls-files', '--others', '--exclude-standard', '-z'], repo.root)
    .toString('utf8')
    .split('\0')
    .filter(Boolean)
    .sort();
  for (const relativePath of paths) {
    addFrame(hash, 'untracked_path', relativePath);
    const filePath = path.join(repo.root, relativePath);
    const content = fs.lstatSync(filePath).isSymbolicLink()
      ? Buffer.from(`symlink\0${fs.readlinkSync(filePath)}`)
      : fs.readFileSync(filePath);
    addFrame(
      hash,
      'untracked_content_sha256',
      crypto.createHash('sha256').update(content).digest('hex'),
    );
  }

  return { baseSha, headSha, fingerprint: hash.digest('hex') };
}

function reviewSection(markdown) {
  let fence = null;
  const outsideFences = markdown.split(/(?<=\n)/).map((line) => {
    const marker = /^ {0,3}(`{3,}|~{3,})/.exec(line)?.[1];
    if (!fence && marker) {
      fence = marker;
      return '\n';
    }
    if (fence && marker?.[0] === fence[0] && marker.length >= fence.length) fence = null;
    return fence || marker ? '\n' : line;
  }).join('');
  const headings = [...outsideFences.matchAll(/^##\s+(?:\d+\.\s+)?Review Results\s*$/gm)];
  if (headings.length !== 1) throw new Error('Exactly one Review Results section is required.');
  const heading = headings[0];
  const start = heading.index + heading[0].length;
  const remainder = outsideFences.slice(start);
  const nextHeading = /^##\s+/m.exec(remainder);
  return nextHeading ? remainder.slice(0, nextHeading.index) : remainder;
}

function field(section, name) {
  const match = new RegExp(`^- \\*\\*${name}\\*\\*:[ \\t]*(.*)$`, 'm').exec(section);
  return match ? match[1].trim().replace(/^`|`$/g, '') : '';
}

function evidenceField(section) {
  const marker = /^- \*\*Evidence\*\*:[ \t]*(.*)$/m.exec(section);
  if (!marker) return '';
  const lineEnd = section.indexOf('\n', marker.index + marker[0].length);
  const after = lineEnd === -1 ? '' : section.slice(lineEnd + 1);
  const bullets = after.match(/^(?:[ \t]{2,}-[ \t]+\S.*(?:\n|$))+/);
  return [marker[1].trim(), bullets?.[0].trim() || ''].filter(Boolean).join('\n');
}

function parseFindings(markdown) {
  const section = reviewSection(markdown);
  const findingHeadings = [...section.matchAll(/^###\s+Finding\b.*$/gm)];
  const starts = [...section.matchAll(/^###\s+Finding\s+`([^`]+)`\s*$/gm)];
  if (findingHeadings.length !== starts.length) throw new Error('Malformed Finding heading.');
  if (new Set(starts.map((match) => match[1])).size !== starts.length) throw new Error('Finding IDs must be unique.');
  const findings = starts.map((match, index) => {
    const bodyStart = match.index + match[0].length;
    const bodyEnd = starts[index + 1]?.index ?? section.length;
    const body = section.slice(bodyStart, bodyEnd);
    return {
      id: match[1],
      status: field(body, 'Status'),
      resolution: field(body, 'Resolution'),
      claim: field(body, 'Reviewer claim'),
      reason: field(body, 'Reason'),
      evidence: evidenceField(body),
    };
  });

  const allowedStatuses = new Set(['accepted', 'rejected-with-evidence', 'needs-human']);
  for (const finding of findings) {
    if (!allowedStatuses.has(finding.status)) throw new Error(`Invalid status for ${finding.id}.`);
    if (!['open', 'resolved'].includes(finding.resolution)) throw new Error(`Invalid resolution for ${finding.id}.`);
    if (!finding.claim || !finding.reason || !finding.evidence) throw new Error(`Incomplete finding ${finding.id}.`);
    if (finding.status === 'rejected-with-evidence' && finding.resolution !== 'resolved') {
      throw new Error(`Rejected finding ${finding.id} must be resolved.`);
    }
  }
  return findings;
}

function planPath(repo, suppliedPath) {
  const resolved = fs.realpathSync(path.resolve(repo.root, suppliedPath));
  const relative = path.relative(repo.root, resolved);
  if (!relative || relative.startsWith('..') || path.isAbsolute(relative)) throw new UsageError();
  return resolved;
}

function evidencePath(repo) {
  return path.join(repo.gitDir, 'ownhands', 'review-evidence.json');
}

function atomicWrite(file, value) {
  fs.mkdirSync(path.dirname(file), { recursive: true });
  const temporary = `${file}.${process.pid}.tmp`;
  fs.writeFileSync(temporary, `${JSON.stringify(value, null, 2)}\n`, { mode: 0o600 });
  fs.renameSync(temporary, file);
}

function record(flags) {
  if (flags['--verdict'] !== 'PASS') throw new Error('Only PASS evidence can be recorded.');
  if (!/^[a-f0-9]{64}$/.test(flags['--reviewed-fingerprint'])) throw new Error('Invalid reviewed fingerprint.');

  const repo = repository();
  const resolvedPlanPath = planPath(repo, flags['--plan']);
  const current = calculateFingerprint(flags['--base'], repo);
  if (current.fingerprint !== flags['--reviewed-fingerprint']) throw new Error('Reviewed fingerprint is stale.');

  const findings = parseFindings(fs.readFileSync(resolvedPlanPath, 'utf8'));
  const counts = {
    accepted: findings.filter((item) => item.status === 'accepted' && item.resolution === 'open').length,
    'rejected-with-evidence': findings.filter((item) => item.status === 'rejected-with-evidence').length,
    'needs-human': findings.filter((item) => item.status === 'needs-human' && item.resolution === 'open').length,
  };
  if (counts.accepted || counts['needs-human']) throw new Error('Unresolved findings remain.');

  atomicWrite(evidencePath(repo), {
    version: 1,
    base_ref: flags['--base'],
    base_sha: current.baseSha,
    head_sha: current.headSha,
    diff_fingerprint: current.fingerprint,
    reviewer: 'reviewer',
    verdict: 'PASS',
    finding_counts: counts,
    recorded_at: new Date().toISOString(),
  });
}

function scanShell(command) {
  let quote = null;
  let escaped = false;
  let compound = false;
  let searchable = '';
  for (let index = 0; index < command.length; index += 1) {
    const char = command[index];
    if (escaped) {
      searchable += ' ';
      escaped = false;
    } else if (char === '\\' && quote !== "'") {
      searchable += ' ';
      escaped = true;
    } else if (quote) {
      searchable += /[;&|()\r\n]/.test(char) ? ' ' : char;
      if (quote === '"' && (char === '`' || (char === '$' && command[index + 1] === '('))) {
        compound = true;
      }
      if (char === quote) quote = null;
    } else if (char === "'" || char === '"') {
      quote = char;
      searchable += char;
    } else {
      searchable += char;
      if (/[;&|()\r\n`]/.test(char)) compound = true;
    }
  }
  return { searchable, compound };
}

function targetsExternalGit(command) {
  const boundary = `(?:^|${SHELL_CONTROL})\\s*`;
  const value = `(?:"[^"]*"|'[^']*'|[^\\s;&|]+)`;
  const gitPush = `git(?:\\s+-C\\s+${value})?\\s+push\\b`;
  const repositoryOption = `(?:--repo|-R)\\s+${value}|--repo=${value}|-R[^\\s;&|]+`;
  const ghPr = `gh(?:\\s+(?:${repositoryOption}))*\\s+pr(?:\\s+(?:${repositoryOption}))*\\s+(?:create|merge)\\b`;
  return new RegExp(`${boundary}(?:${gitPush}|${ghPr})`).test(command);
}

function shellWords(command) {
  const words = [];
  let word = '';
  let quote = null;
  let escaped = false;
  let started = false;
  for (const char of command) {
    if (escaped) {
      word += char;
      started = true;
      escaped = false;
    } else if (char === '\\' && quote !== "'") {
      escaped = true;
      started = true;
    } else if (quote) {
      if (char === quote) quote = null;
      else word += char;
      started = true;
    } else if (char === "'" || char === '"') {
      quote = char;
      started = true;
    } else if (/\s/.test(char)) {
      if (started) words.push(word);
      word = '';
      started = false;
    } else {
      word += char;
      started = true;
    }
  }
  if (quote || escaped) return null;
  if (started) words.push(word);
  return words;
}

function normalizeGitHubRepository(value) {
  if (!value) return null;
  let candidate = value.trim().replace(/\/$/, '').replace(/\.git$/, '');
  const scp = /^(?:[^@\s]+@)?github\.com:([^/\s]+\/[^/\s]+)$/i.exec(candidate);
  if (scp) return scp[1].toLowerCase();
  const url = /^(?:https?|ssh):\/\/(?:[^@/\s]+@)?github\.com\/([^/\s]+\/[^/\s]+)$/i.exec(candidate);
  if (url) return url[1].toLowerCase();
  return /^[^/\s]+\/[^/\s]+$/.test(candidate) ? candidate.toLowerCase() : null;
}

function remoteRepositories(repo, remote = 'origin', push = false) {
  try {
    const args = ['remote', 'get-url'];
    if (push) args.push('--push', '--all');
    args.push(remote);
    return textGit(args, repo.root).split('\n').map(normalizeGitHubRepository);
  } catch {
    return [];
  }
}

function remoteRepository(repo, remote = 'origin') {
  const repositories = remoteRepositories(repo, remote);
  return repositories.length === 1 ? repositories[0] : null;
}

function configValue(repo, key) {
  try {
    return textGit(['config', '--get', key], repo.root) || null;
  } catch {
    return null;
  }
}

function defaultPushRemote(repo) {
  let branch = null;
  try {
    branch = textGit(['symbolic-ref', '--quiet', '--short', 'HEAD'], repo.root);
  } catch {}
  if (branch) {
    const branchPushRemote = configValue(repo, `branch.${branch}.pushRemote`);
    if (branchPushRemote) return branchPushRemote;
  }
  const pushDefault = configValue(repo, 'remote.pushDefault');
  if (pushDefault) return pushDefault;
  if (branch) {
    const branchRemote = configValue(repo, `branch.${branch}.remote`);
    if (branchRemote) return branchRemote;
  }
  const remotes = textGit(['remote'], repo.root).split('\n').filter(Boolean);
  if (remotes.includes('origin')) return 'origin';
  return remotes.length === 1 ? remotes[0] : null;
}

function pushTargetMatches(repo, target, current) {
  if (!target) return false;
  const remoteTargets = remoteRepositories(repo, target, true);
  if (remoteTargets.length) return remoteTargets.every((item) => item === current);
  if (/^[^/:@\s]+\/[^/\s]+$/.test(target)) return false;
  return normalizeGitHubRepository(target) === current;
}

function gitTargetMatches(words, repo) {
  let index = 1;
  let commandRoot = repo.root;
  if (words[index] === '-C') {
    const directory = words[index + 1];
    if (!directory) return false;
    try {
      commandRoot = fs.realpathSync(textGit(['-C', directory, 'rev-parse', '--show-toplevel']));
    } catch {
      return false;
    }
    index += 2;
  }
  if (words[index] !== 'push' || commandRoot !== repo.root) return false;

  const noValueOptions = new Set([
    '--all', '--atomic', '--delete', '--dry-run', '--follow-tags', '--force',
    '--force-with-lease', '--mirror', '--no-atomic', '--porcelain', '--prune',
    '--quiet', '--set-upstream', '--tags', '--verbose', '-f', '-n', '-q', '-u', '-v',
  ]);
  let target = null;
  let explicitTarget = false;
  for (index += 1; index < words.length; index += 1) {
    const token = words[index];
    if (token === '--repo') {
      explicitTarget = true;
      target = words[index + 1] || null;
      break;
    }
    if (token.startsWith('--repo=')) {
      explicitTarget = true;
      target = token.slice('--repo='.length);
      break;
    }
    if (noValueOptions.has(token)) continue;
    if (token.startsWith('-')) return false;
    target = token;
    break;
  }

  const current = remoteRepository(repo);
  if (!current) return false;
  if (explicitTarget && !target) return false;
  return pushTargetMatches(repo, target || defaultPushRemote(repo), current);
}

function ghPrCommand(words) {
  const prIndex = words.indexOf('pr', 1);
  if (prIndex === -1) return null;
  let actionIndex = prIndex + 1;
  while (actionIndex < words.length) {
    const token = words[actionIndex];
    if (token === '--repo' || token === '-R') {
      if (!words[actionIndex + 1]) return null;
      actionIndex += 2;
      continue;
    }
    if (token.startsWith('--repo=') || (token.startsWith('-R') && token.length > 2)) {
      actionIndex += 1;
      continue;
    }
    break;
  }
  return ['create', 'merge'].includes(words[actionIndex]) ? { prIndex, actionIndex } : null;
}

function pullRequestRepository(value) {
  const match = /^https?:\/\/github\.com\/([^/\s]+\/[^/\s]+)\/pull\/\d+\/?$/i.exec(value || '');
  return match ? match[1].replace(/\.git$/i, '').toLowerCase() : null;
}

function ghTargetMatches(words, repo) {
  const current = remoteRepository(repo);
  if (!current) return false;
  const command = ghPrCommand(words);
  if (!command) return false;
  const targets = [];
  for (let index = 1; index < words.length; index += 1) {
    const token = words[index];
    if (token === '--repo' || token === '-R') {
      const target = words[index + 1];
      if (!target) return false;
      targets.push(normalizeGitHubRepository(target));
      index += 1;
      continue;
    }
    if (token.startsWith('--repo=')) {
      targets.push(normalizeGitHubRepository(token.slice('--repo='.length)));
      continue;
    }
    if (token.startsWith('-R') && token.length > 2) {
      targets.push(normalizeGitHubRepository(token.slice(2)));
    }
  }
  if (words[command.actionIndex] === 'merge') {
    const pullTarget = words.slice(command.actionIndex + 1).map(pullRequestRepository).find(Boolean);
    if (pullTarget) targets.push(pullTarget);
  }
  return targets.every((target) => target === current);
}

function repositoryTargetMatches(command, repo) {
  const words = shellWords(command);
  if (!words) return false;
  if (words[0] === 'git') return gitTargetMatches(words, repo);
  if (words[0] === 'gh' && ghPrCommand(words)) {
    return ghTargetMatches(words, repo);
  }
  return false;
}

function validEvidence(repo) {
  try {
    const evidence = JSON.parse(fs.readFileSync(evidencePath(repo), 'utf8'));
    if (
      evidence.version !== 1 ||
      evidence.verdict !== 'PASS' ||
      evidence.finding_counts?.accepted !== 0 ||
      evidence.finding_counts?.['needs-human'] !== 0
    ) return false;
    const current = calculateFingerprint(evidence.base_ref, repo);
    return (
      current.baseSha === evidence.base_sha &&
      current.headSha === evidence.head_sha &&
      current.fingerprint === evidence.diff_fingerprint
    );
  } catch {
    return false;
  }
}

function deny() {
  process.stdout.write(`${JSON.stringify(DENY)}\n`);
}

function checkHook() {
  let input;
  try {
    input = JSON.parse(fs.readFileSync(0, 'utf8'));
  } catch {
    deny();
    return;
  }
  const command = input?.tool_input?.command;
  if (input?.tool_name !== 'Bash' || typeof command !== 'string') return;
  const shell = scanShell(command);
  if (!targetsExternalGit(shell.searchable)) return;
  if (shell.compound) {
    deny();
    return;
  }
  let repo;
  try {
    repo = repository();
  } catch {
    deny();
    return;
  }
  if (!repositoryTargetMatches(command, repo) || !validEvidence(repo)) deny();
}

function main(args) {
  const command = args[0];
  if (command === 'fingerprint') {
    const flags = parseFlags(args.slice(1), new Set(['--base']), ['--base']);
    process.stdout.write(`${calculateFingerprint(flags['--base']).fingerprint}\n`);
    return;
  }
  if (command === 'record') {
    const allowed = new Set(['--base', '--plan', '--reviewed-fingerprint', '--verdict']);
    const flags = parseFlags(args.slice(1), allowed, [...allowed]);
    record(flags);
    return;
  }
  if (command === 'check-hook') {
    if (args.length !== 1) throw new UsageError();
    checkHook();
    return;
  }
  if (command === 'clear') {
    if (args.length !== 1) throw new UsageError();
    fs.rmSync(evidencePath(repository()), { force: true });
    return;
  }
  throw new UsageError();
}

try {
  main(process.argv.slice(2));
} catch (error) {
  if (error instanceof UsageError) {
    process.stderr.write(`${USAGE}\n`);
    process.exitCode = 2;
  } else {
    process.stderr.write(`Review Gate: ${error.message}\n`);
    process.exitCode = 1;
  }
}

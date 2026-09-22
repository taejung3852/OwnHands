import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { createHash } from 'node:crypto';
import { Server } from '@modelcontextprotocol/sdk/server/index.js';
import { StdioServerTransport } from '@modelcontextprotocol/sdk/server/stdio.js';
import { RequestSchema, ListToolsRequestSchema, CallToolRequestSchema, ListResourcesRequestSchema, ReadResourceRequestSchema, McpError, ErrorCode } from '@modelcontextprotocol/sdk/types.js';
import { z } from 'zod/v4';
import { parseDocument } from 'yaml';

const SKILLS = ['plan-design', 'eli5'];
const ROOT = fileURLToPath(new URL('../../plugins/ownhands/skills/', import.meta.url));
const INSTRUCTIONS = 'Provides the canonical OwnHands plan-design and ELI5 skill resources. It does not provide GitHub, shell, or repository mutation tools.';
const sha256 = bytes => `sha256:${createHash('sha256').update(bytes).digest('hex')}`;
const order = (a, b) => a < b ? -1 : a > b ? 1 : 0;

function invalidSnapshot() { throw new Error('Invalid canonical Skill snapshot; check files, paths, frontmatter and import limits.'); }

// Reject symlinks in the canonical root and every ancestor as well as below it.
function checkedRoot(root) {
  const absolute = path.resolve(root);
  let current = path.parse(absolute).root;
  for (const part of absolute.slice(current.length).split(path.sep).filter(Boolean)) {
    current = path.join(current, part);
    const stat = fs.lstatSync(current);
    if (stat.isSymbolicLink() || !stat.isDirectory()) invalidSnapshot();
  }
  return fs.realpathSync(absolute);
}

function jsonValue(value, ancestors = new Set()) {
  if (value === null || typeof value === 'string' || typeof value === 'boolean') return true;
  if (typeof value === 'number') return Number.isFinite(value);
  if (typeof value !== 'object' || ancestors.has(value)) return false;
  if (!Array.isArray(value) && Object.getPrototypeOf(value) !== Object.prototype) return false;
  const next = new Set(ancestors).add(value);
  return Object.values(value).every(item => jsonValue(item, next));
}

function frontmatter(bytes, name) {
  let text;
  try { text = new TextDecoder('utf-8', { fatal: true, ignoreBOM: true }).decode(bytes); } catch { invalidSnapshot(); }
  const match = /^---\r?\n([\s\S]*?)\r?\n---(?:\r?\n|$)/.exec(text);
  if (!match) invalidSnapshot();
  try {
    const doc = parseDocument(match[1], { uniqueKeys: true, strict: true });
    if (doc.errors.length || doc.warnings.length) invalidSnapshot();
    const data = doc.toJS({ maxAliasCount: 100 });
    if (!jsonValue(data) || !data || Array.isArray(data) || data.name !== name || typeof data.description !== 'string' || !data.description.trim()) invalidSnapshot();
    return data;
  } catch { invalidSnapshot(); }
}

// Startup-only reader. Requests can only access the resulting in-memory URI map.
export function loadSnapshot(root = ROOT) {
  const safeRoot = checkedRoot(root);
  const contents = new Map();
  const skills = [];
  let archiveBound = 22; // ZIP end-of-central-directory record.
  for (const name of SKILLS) {
    const resources = [];
    let totalBytes = 0;
    let mainBytes;
    const normalized = new Set();
    function walk(directory, relative = '') {
      const dirStat = fs.lstatSync(directory);
      if (dirStat.isSymbolicLink() || !dirStat.isDirectory()) invalidSnapshot();
      for (const entry of fs.readdirSync(directory).sort(order)) {
        // A bounded safe subset of portable paths; do not decode request URIs.
        if (!/^[A-Za-z0-9][A-Za-z0-9._-]*$/.test(entry) || entry === '.' || entry === '..') invalidSnapshot();
        const rel = `${relative}${entry}`;
        const key = rel.normalize('NFC').toLowerCase();
        if (normalized.has(key)) invalidSnapshot();
        normalized.add(key);
        const file = path.join(directory, entry);
        const stat = fs.lstatSync(file);
        if (stat.isSymbolicLink()) invalidSnapshot();
        if (stat.isDirectory()) { walk(file, `${rel}/`); continue; }
        if (!stat.isFile() || resources.length >= 100) invalidSnapshot();
        const real = fs.realpathSync(file);
        if (!real.startsWith(`${safeRoot}${path.sep}${name}${path.sep}`)) invalidSnapshot();
        const limit = rel === 'SKILL.md' ? 256 * 1024 : 1024 * 1024;
        if (stat.size > limit) invalidSnapshot();
        const fd = fs.openSync(file, fs.constants.O_RDONLY | fs.constants.O_NOFOLLOW);
        let bytes;
        try {
          const opened = fs.fstatSync(fd);
          if (!opened.isFile() || opened.size > limit) invalidSnapshot();
          bytes = fs.readFileSync(fd);
        } finally { fs.closeSync(fd); }
        if (bytes.length > limit) invalidSnapshot();
        totalBytes += bytes.length;
        if (totalBytes > 5 * 1024 * 1024) invalidSnapshot();
        // Conservative stored/deflate ZIP size allowance, including names/headers.
        archiveBound += Math.ceil(bytes.length * 1.01) + 1024 + Buffer.byteLength(`${name}/${rel}`) * 2;
        if (archiveBound > 8 * 1024 * 1024) invalidSnapshot();
        const uri = `skill://ownhands/${name}/${rel}`;
        if (contents.has(uri)) invalidSnapshot();
        let content;
        try {
          const text = new TextDecoder('utf-8', { fatal: true, ignoreBOM: true }).decode(bytes);
          content = { uri, mimeType: 'text/plain', text };
        } catch { content = { uri, mimeType: 'application/octet-stream', blob: bytes.toString('base64') }; }
        contents.set(uri, content);
        resources.push({ uri, digest: sha256(bytes) });
        if (rel === 'SKILL.md') mainBytes = bytes;
      }
    }
    walk(path.join(safeRoot, name));
    if (!mainBytes) invalidSnapshot();
    skills.push({ uri: `skill://ownhands/${name}/SKILL.md`, frontmatter: frontmatter(mainBytes, name), resources });
  }
  const entries = skills.flatMap(skill => skill.resources.map(r => [r.uri, r.digest])).sort((a, b) => order(a[0], b[0]));
  return { skills, contents, revision: sha256(JSON.stringify(entries)) };
}

function noCursor(params) {
  if (params?.cursor !== undefined) throw new McpError(ErrorCode.InvalidParams, 'Unknown cursor.');
}

async function serve() {
  const snapshot = loadSnapshot();
  const server = new Server({ name: 'ownhands-skill-provider', version: '0.1.0' }, {
    instructions: INSTRUCTIONS,
    capabilities: { tools: {}, resources: {}, extensions: { 'io.modelcontextprotocol/skills': {} } },
  });
  const listSchema = RequestSchema.extend({ method: z.literal('skills/list'), params: z.object({ cursor: z.string().optional() }).optional() });
  const getSchema = RequestSchema.extend({ method: z.literal('skills/get'), params: z.object({ uri: z.string() }) });
  server.setRequestHandler(listSchema, ({ params }) => {
    noCursor(params); return { skills: snapshot.skills };
  });
  server.setRequestHandler(getSchema, ({ params }) => {
    const skill = snapshot.skills.find(skill => skill.uri === params.uri);
    if (!skill) throw new McpError(ErrorCode.InvalidParams, 'Unknown Skill URI.');
    return { skill };
  });
  server.setRequestHandler(ListResourcesRequestSchema, ({ params }) => {
    noCursor(params);
    return { resources: [...snapshot.contents.values()].map(({ uri, mimeType }) => ({ uri, name: uri.slice('skill://ownhands/'.length), mimeType })) };
  });
  server.setRequestHandler(ReadResourceRequestSchema, ({ params }) => {
    const content = snapshot.contents.get(params.uri);
    if (!content) throw new McpError(-32002, 'Unknown resource URI.');
    return { contents: [content] };
  });
  server.setRequestHandler(ListToolsRequestSchema, ({ params }) => {
    noCursor(params);
    return { tools: [{
      name: 'ownhands_status', title: 'OwnHands status',
      description: 'Check whether the private OwnHands MCP skill provider is reachable and report the currently served skill names and revision. This tool is read-only.',
      inputSchema: { type: 'object', properties: {}, additionalProperties: false },
      annotations: { readOnlyHint: true, destructiveHint: false, idempotentHint: true, openWorldHint: false },
    }] };
  });
  server.setRequestHandler(CallToolRequestSchema, ({ params }) => {
    if (params.name !== 'ownhands_status' || Object.keys(params.arguments ?? {}).length) throw new McpError(ErrorCode.InvalidParams, 'Unknown tool or invalid arguments.');
    const status = { status: 'ok', skills: SKILLS, revision: snapshot.revision };
    return { content: [{ type: 'text', text: JSON.stringify(status) }], structuredContent: status };
  });
  server.onerror = () => { process.stderr.write('OwnHands MCP protocol error.\n'); };
  await server.connect(new StdioServerTransport());
}

if (process.argv[1] && path.resolve(process.argv[1]) === fileURLToPath(import.meta.url)) {
  serve().catch(() => {
    process.stderr.write('OwnHands Skill Provider startup failed; check canonical files, paths and import limits.\n');
    process.exitCode = 1;
  });
}

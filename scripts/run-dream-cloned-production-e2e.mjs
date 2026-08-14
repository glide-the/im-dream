#!/usr/bin/env node

import { spawn } from 'node:child_process';
import { promisify } from 'node:util';
import { randomBytes, scrypt as scryptCallback } from 'node:crypto';
import { chmod, mkdtemp, readFile, rm } from 'node:fs/promises';
import { createServer as createNetServer } from 'node:net';
import { tmpdir } from 'node:os';
import { join, resolve } from 'node:path';

const dreamRoot = resolve(new URL('../', import.meta.url).pathname);
const adminRoot = resolve(dreamRoot, '../ink-admin-memory');
const backendRoot = resolve(dreamRoot, 'backend');
const frontendRoot = resolve(dreamRoot, 'frontend');
const python = resolve(backendRoot, '.venv/bin/python');
const pgDump = '/opt/homebrew/opt/libpq/bin/pg_dump';
const pgRestore = '/opt/homebrew/opt/libpq/bin/pg_restore';
const pgIsReady = '/opt/homebrew/opt/libpq/bin/pg_isready';
const scrypt = promisify(scryptCallback);
const suffix = randomBytes(6).toString('hex');
const databaseName = `ink_memory_dream_clone_${suffix}_test`;
const containerName = `ink-dream-clone-e2e-${suffix}`;
const postgresPassword = `pg_${randomBytes(24).toString('base64url')}`;
const adminEmail = `dream-clone-${suffix}@example.test`;
const adminPassword = `Dream-clone-${suffix}-E2E!`;
const adminUserId = `admin_clone_${suffix}`;
const adminSessionSecret = `session_${randomBytes(48).toString('base64url')}`;
const jwtSecret = `jwt_${randomBytes(48).toString('base64url')}`;
const targetRunId = 'run_b81d3731b56b4703868b66af76e7b656';
const runtimeRoot = await mkdtemp(join(tmpdir(), 'ink-dream-clone-e2e-'));
await chmod(runtimeRoot, 0o700);
const dumpPath = join(runtimeRoot, 'source-readonly.dump');
const dreamEvidence = join(runtimeRoot, 'dream-evidence');
const dreamOutput = join(runtimeRoot, 'dream-playwright');
const adminOutput = join(runtimeRoot, 'admin-playwright');
const adminDistName = `.next-e2e-dream-clone-${suffix}`;
const adminDistPath = resolve(adminRoot, adminDistName);
const ownedProcesses = [];
let containerStarted = false;

function envValue(text, name) {
  for (const rawLine of text.split(/\r?\n/)) {
    const line = rawLine.trim();
    if (!line || line.startsWith('#')) continue;
    const normalized = line.startsWith('export ') ? line.slice(7).trim() : line;
    const separator = normalized.indexOf('=');
    if (separator <= 0 || normalized.slice(0, separator).trim() !== name) continue;
    const raw = normalized.slice(separator + 1).trim();
    if (raw.startsWith('"') && raw.endsWith('"')) {
      try { return JSON.parse(raw); } catch { return raw.slice(1, -1); }
    }
    if (raw.startsWith("'") && raw.endsWith("'")) return raw.slice(1, -1);
    return raw;
  }
  return undefined;
}

function execute(command, args, { cwd = dreamRoot, env = process.env, inherit = false } = {}) {
  return new Promise((resolvePromise, reject) => {
    const child = spawn(command, args, {
      cwd,
      env,
      stdio: inherit ? 'inherit' : ['ignore', 'pipe', 'pipe'],
    });
    let stdout = '';
    let stderr = '';
    if (!inherit) {
      child.stdout.on('data', (chunk) => { stdout += chunk; });
      child.stderr.on('data', (chunk) => { stderr += chunk; });
    }
    child.once('error', reject);
    child.once('exit', (code, signal) => {
      if (code === 0) resolvePromise(stdout.trim());
      else reject(new Error(`${command} exited with ${code ?? signal}${stderr.trim() ? `: ${stderr.trim()}` : ''}`));
    });
  });
}

function startOwned(command, args, { cwd, env }) {
  const child = spawn(command, args, { cwd, env, stdio: ['ignore', 'pipe', 'pipe'] });
  const tail = [];
  const collect = (chunk) => {
    tail.push(String(chunk));
    if (tail.length > 100) tail.shift();
  };
  child.stdout.on('data', collect);
  child.stderr.on('data', collect);
  ownedProcesses.push({ child, command, tail });
  return child;
}

async function stopOwned() {
  for (const item of [...ownedProcesses].reverse()) {
    if (item.child.exitCode !== null) continue;
    item.child.kill('SIGTERM');
    await new Promise((resolvePromise) => {
      const timer = setTimeout(() => {
        if (item.child.exitCode === null) item.child.kill('SIGKILL');
        resolvePromise();
      }, 5_000);
      item.child.once('exit', () => { clearTimeout(timer); resolvePromise(); });
    });
  }
}

async function availablePort() {
  const server = createNetServer();
  await new Promise((resolvePromise, reject) => {
    server.once('error', reject);
    server.listen(0, '127.0.0.1', resolvePromise);
  });
  const address = server.address();
  if (!address || typeof address === 'string') throw new Error('dynamic port unavailable');
  await new Promise((resolvePromise) => server.close(resolvePromise));
  return address.port;
}

async function waitForPostgres(env) {
  const deadline = Date.now() + 60_000;
  while (Date.now() < deadline) {
    try {
      await execute(pgIsReady, [], { env });
      return;
    } catch {
      await new Promise((resolvePromise) => setTimeout(resolvePromise, 500));
    }
  }
  throw new Error('owned PostgreSQL did not become ready');
}

async function waitForUrl(url, child, label) {
  const deadline = Date.now() + 90_000;
  while (Date.now() < deadline) {
    if (child.exitCode !== null) {
      const owned = ownedProcesses.find((item) => item.child === child);
      throw new Error(`${label} exited early\n${owned?.tail.join('') ?? ''}`);
    }
    try {
      const response = await fetch(url);
      if (response.status < 500) return;
    } catch {}
    await new Promise((resolvePromise) => setTimeout(resolvePromise, 300));
  }
  throw new Error(`${label} did not become ready`);
}

function pgEnv(url, { readOnly = false } = {}) {
  const parsed = new URL(url);
  if (!['postgres:', 'postgresql:'].includes(parsed.protocol)) {
    throw new Error('PostgreSQL URL required');
  }
  const database = decodeURIComponent(parsed.pathname.slice(1));
  if (!database) throw new Error('PostgreSQL database name required');
  const sslmode = parsed.searchParams.get('sslmode');
  return {
    ...process.env,
    PGHOST: parsed.hostname,
    PGPORT: parsed.port || '5432',
    PGUSER: decodeURIComponent(parsed.username),
    PGPASSWORD: decodeURIComponent(parsed.password),
    PGDATABASE: database,
    ...(sslmode ? { PGSSLMODE: sslmode } : {}),
    ...(readOnly ? { PGOPTIONS: '-c default_transaction_read_only=on' } : {}),
  };
}

async function passwordHash(password) {
  const salt = randomBytes(16);
  const derived = await scrypt(password, salt, 64, {
    N: 16_384,
    r: 8,
    p: 1,
    maxmem: 64 * 1024 * 1024,
  });
  return `scrypt$16384$8$1$${salt.toString('base64')}$${Buffer.from(derived).toString('base64')}`;
}

async function queryCloneFixture(databaseUrl) {
  const source = [
    'import json, psycopg, sys',
    'from psycopg.rows import dict_row',
    'with psycopg.connect(sys.argv[1], row_factory=dict_row) as c:',
    ' rows=c.execute("""SELECT id,source_run_id,source_project_id,script_revision,review_status,status FROM story_workspace_stories WHERE artifact_source_type=%s ORDER BY CASE WHEN source_run_id=%s THEN 0 ELSE 1 END,id""",("dream_episode",sys.argv[2])).fetchall()',
    ' assert len(rows)>=2 and rows[0]["source_run_id"]==sys.argv[2]',
    ' assert rows[0]["review_status"]=="pending" and rows[1]["review_status"]=="pending"',
    ' constraints=c.execute("""SELECT conname,convalidated FROM pg_constraint WHERE conrelid=\'story_workspace_stories\'::regclass AND conname IN (\'story_workspace_stories_artifact_status_check\',\'story_workspace_stories_artifact_identity_check\',\'story_workspace_stories_artifact_revision_state_check\',\'story_workspace_stories_review_integrity_check\',\'story_workspace_stories_business_review_check\') ORDER BY conname""").fetchall()',
    ' assert len(constraints)==5 and all(row["convalidated"] for row in constraints)',
    ' print(json.dumps({"story":rows[0],"rejectStory":rows[1],"validatedConstraints":len(constraints)},separators=(",",":")))',
  ].join('\n');
  const result = await execute(python, ['-c', source, databaseUrl, targetRunId], { cwd: backendRoot });
  return JSON.parse(result);
}

async function provisionCloneAdmin(databaseUrl) {
  const hash = await passwordHash(adminPassword);
  const source = [
    'import psycopg, sys',
    'with psycopg.connect(sys.argv[1]) as c:',
    ' role=c.execute("SELECT id FROM admin_roles WHERE code=\'super_admin\'").fetchone()',
    ' assert role is not None',
    ' c.execute("""INSERT INTO admin_users (id,email,display_name,password_hash,status) VALUES (%s,%s,%s,%s,\'active\')""",(sys.argv[2],sys.argv[3],"Dream Clone E2E",sys.argv[4]))',
    ' c.execute("INSERT INTO admin_user_roles (admin_user_id,role_id) VALUES (%s,%s)",(sys.argv[2],role[0]))',
  ].join('\n');
  await execute(python, ['-c', source, databaseUrl, adminUserId, adminEmail, hash], { cwd: backendRoot });
}

const adminEnvText = await readFile(resolve(adminRoot, '.env.local'), 'utf8');
const backendEnvText = await readFile(resolve(backendRoot, '.env'), 'utf8');
const sourceUrl = envValue(adminEnvText, 'DATABASE_URL');
const artifactRoot = envValue(backendEnvText, 'AGENT_CWD');
if (!sourceUrl) throw new Error('Admin source DATABASE_URL is not configured');
if (!artifactRoot || !resolve(artifactRoot).startsWith('/')) {
  throw new Error('Dream AGENT_CWD must be an absolute configured path');
}
const sourceIdentity = new URL(sourceUrl);
if (sourceIdentity.pathname.slice(1).toLowerCase().includes('test')) {
  throw new Error('source database unexpectedly has a test identity');
}

try {
  const postgresPort = await availablePort();
  const dreamApiPort = await availablePort();
  const dreamWebPort = await availablePort();
  const adminPort = await availablePort();
  const targetUrl = `postgresql://postgres:${encodeURIComponent(postgresPassword)}@127.0.0.1:${postgresPort}/${databaseName}`;
  const targetPgEnv = pgEnv(targetUrl);

  console.log('Starting owned PostgreSQL clone target...');
  await execute('docker', [
    'run', '--detach', '--rm', '--name', containerName,
    '--env', 'POSTGRES_USER=postgres',
    '--env', `POSTGRES_PASSWORD=${postgresPassword}`,
    '--env', `POSTGRES_DB=${databaseName}`,
    '--publish', `127.0.0.1:${postgresPort}:5432`,
    'postgres:18-alpine',
  ]);
  containerStarted = true;
  await waitForPostgres(targetPgEnv);

  console.log('Dumping the source through a forced read-only libpq session...');
  await execute(pgDump, [
    '--format=custom', '--no-owner', '--no-acl', '--file', dumpPath,
  ], { env: pgEnv(sourceUrl, { readOnly: true }) });
  await chmod(dumpPath, 0o600);
  console.log('Restoring only into the owned _test target...');
  await execute(pgRestore, [
    '--no-owner', '--no-acl', '--exit-on-error', '--dbname', databaseName, dumpPath,
  ], { env: targetPgEnv });

  const migrationEnv = {
    ...process.env,
    DATABASE_URL: targetUrl,
    TEST_DATABASE_URL: targetUrl,
    INK_USE_TEST_DATABASE_URL: '1',
  };
  console.log('Applying current Admin contract migrations to the clone...');
  await execute('node', ['scripts/migrate.mjs'], { cwd: adminRoot, env: migrationEnv });
  const fixture = await queryCloneFixture(targetUrl);
  await provisionCloneAdmin(targetUrl);
  console.log(JSON.stringify({
    restoredArtifactStories: 2,
    targetRunResolved: fixture.story.source_run_id === targetRunId,
    validatedConstraints: fixture.validatedConstraints,
  }));

  const dreamApiBase = `http://127.0.0.1:${dreamApiPort}`;
  const dreamWebBase = `http://127.0.0.1:${dreamWebPort}`;
  const dreamEnv = {
    ...migrationEnv,
    JWT_SECRET: jwtSecret,
    AGENT_CWD: artifactRoot,
    INK_CORS_ALLOW_ORIGINS: dreamWebBase,
  };
  const dreamApi = startOwned(resolve(backendRoot, '.venv/bin/uvicorn'), [
    'server:app', '--host', '127.0.0.1', '--port', String(dreamApiPort),
  ], { cwd: backendRoot, env: dreamEnv });
  await waitForUrl(`${dreamApiBase}/health`, dreamApi, 'Dream FastAPI');
  const dreamWeb = startOwned('pnpm', [
    'exec', 'vite', '--host', '127.0.0.1', '--port', String(dreamWebPort), '--strictPort',
  ], { cwd: frontendRoot, env: { ...dreamEnv, VITE_DEV_API_PROXY_TARGET: dreamApiBase } });
  await waitForUrl(dreamWebBase, dreamWeb, 'Dream Vite');

  console.log('Running real persisted Dream Workflow/Episode/Story Chromium on the clone...');
  await execute('pnpm', [
    'exec', 'playwright', 'test', 'e2e/story-workspace-real-episode-artifacts.spec.ts',
    '--workers=1', '--reporter=line', `--output=${dreamOutput}`,
  ], {
    cwd: frontendRoot,
    env: {
      ...dreamEnv,
      INK_REAL_EPISODE_QA: '1',
      INK_REAL_EPISODE_WEB_BASE: dreamWebBase,
      INK_REAL_EPISODE_API_BASE: dreamApiBase,
      INK_REAL_EPISODE_RUN_ID: targetRunId,
      INK_REAL_EPISODE_EVIDENCE_DIR: dreamEvidence,
    },
    inherit: true,
  });
  await stopOwned();

  const adminBase = `http://127.0.0.1:${adminPort}`;
  console.log('Running Admin real Artifact read and review CAS Chromium on the clone...');
  await execute('pnpm', [
    'exec', 'playwright', 'test', 'tests/e2e/story-artifact-clone-real.spec.ts',
    '--project=chromium', '--workers=1', '--reporter=line', `--output=${adminOutput}`,
  ], {
    cwd: adminRoot,
    env: {
      ...migrationEnv,
      NODE_ENV: 'development',
      PORT: String(adminPort),
      PLAYWRIGHT_BASE_URL: adminBase,
      ADMIN_CONSOLE_ENABLED: 'true',
      ADMIN_SESSION_SECRET: adminSessionSecret,
      ADMIN_ORIGIN_ALLOWLIST: adminBase,
      ARTIFACT_WORKSPACE_ROOT: artifactRoot,
      INK_ADMIN_E2E_DIST_DIR: adminDistName,
      INK_CLONE_STORY_ID: fixture.story.id,
      INK_CLONE_REJECT_STORY_ID: fixture.rejectStory.id,
      INK_CLONE_RUN_ID: fixture.story.source_run_id,
      INK_CLONE_PROJECT_ID: fixture.story.source_project_id,
      INK_CLONE_SCRIPT_REVISION: fixture.story.script_revision,
      INK_CLONE_REJECT_SCRIPT_REVISION: fixture.rejectStory.script_revision,
      INK_CLONE_ADMIN_EMAIL: adminEmail,
      INK_CLONE_ADMIN_PASSWORD: adminPassword,
    },
    inherit: true,
  });

  console.log(JSON.stringify({
    sourceMode: 'read-only-dump',
    cloneDatabase: databaseName,
    workflowRun: targetRunId,
    dreamBrowser: 'passed',
    adminReviewBrowser: 'passed',
  }));
} finally {
  await stopOwned();
  if (containerStarted) {
    await execute('docker', ['stop', '--time', '2', containerName]).catch(() => undefined);
  }
  await rm(adminDistPath, { recursive: true, force: true });
  await rm(runtimeRoot, { recursive: true, force: true });
}

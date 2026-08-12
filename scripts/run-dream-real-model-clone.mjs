#!/usr/bin/env node

import { spawn } from 'node:child_process';
import { createHash, randomBytes } from 'node:crypto';
import { createReadStream, createWriteStream } from 'node:fs';
import {
  chmod,
  mkdtemp,
  mkdir,
  readFile,
  rm,
  symlink,
} from 'node:fs/promises';
import { createServer as createNetServer } from 'node:net';
import { tmpdir } from 'node:os';
import { join, resolve } from 'node:path';
import { pipeline } from 'node:stream/promises';

const dreamRoot = resolve(new URL('../', import.meta.url).pathname);
const adminRoot = resolve(dreamRoot, '../ink-admin-memory');
const backendRoot = resolve(dreamRoot, 'backend');
const python = resolve(backendRoot, '.venv/bin/python');
const pgIsReady = '/opt/homebrew/opt/libpq/bin/pg_isready';
const sourcePostgresContainer = 'ink-memory-postgres';
const targetModelAlias = 'hy-preview';
const expectedUpstreamModel = 'hy3-preview';
const suffix = randomBytes(6).toString('hex');
const runLabel = `ink-r22-real-model-${suffix}`;
const databaseName = `ink_memory_r22_${suffix}_test`;
const containerName = `${runLabel}-postgres`;
const volumeName = `${runLabel}-pgdata`;
const postgresPassword = `pg_${randomBytes(24).toString('base64url')}`;
const cloneEmail = `gateway-real-${suffix}@example.test`;
const clonePlatformUserId = `platform_r22_${suffix}`;
const cloneJwtSecret = `jwt_${randomBytes(48).toString('base64url')}`;
const preflightOnly = ['1', 'true', 'yes', 'on'].includes(
  String(process.env.INK_R22_PREFLIGHT_ONLY ?? '').trim().toLowerCase(),
);
const selfInterruptAfterVolumeCreate = ['1', 'true', 'yes', 'on'].includes(
  String(process.env.INK_R25_SELF_INTERRUPT_AFTER_VOLUME_CREATE ?? '')
    .trim()
    .toLowerCase(),
);
const activeChildren = new Set();
let interruptedSignal;
let cleanupPhase = false;
for (const signal of ['SIGINT', 'SIGTERM']) {
  process.on(signal, () => {
    interruptedSignal ??= signal;
    if (!cleanupPhase) {
      for (const child of activeChildren) {
        if (child.exitCode === null && child.signalCode === null) child.kill('SIGTERM');
      }
    }
  });
}
const runtimeRoot = await mkdtemp(join(tmpdir(), 'ink-r22-real-model-'));
await chmod(runtimeRoot, 0o700);
const dumpPath = join(runtimeRoot, 'source-readonly.dump');
const workspaceRoot = join(runtimeRoot, 'workspace');
const localFilesRoot = join(runtimeRoot, 'files');
const adminRuntimeRoot = join(runtimeRoot, 'admin-src');
await mkdir(workspaceRoot, { recursive: true, mode: 0o700 });
await mkdir(localFilesRoot, { recursive: true, mode: 0o700 });
const adminDistName = `.next-e2e-r22-${suffix}`;
const ownedProcesses = [];
let sourceFingerprintBefore;
let targetDatabaseUrl;
let ownedPorts = [];
let runEvidence;
let runError;
let runPhase = 'initialization';
let failedPhase;

function throwIfInterrupted() {
  if (interruptedSignal && !cleanupPhase) throw new Error('verification interrupted');
}

function trackChild(child) {
  activeChildren.add(child);
  child.once('exit', () => activeChildren.delete(child));
  return child;
}

function parseEnv(text) {
  const values = {};
  for (const rawLine of text.split(/\r?\n/)) {
    const line = rawLine.trim();
    if (!line || line.startsWith('#')) continue;
    const normalized = line.startsWith('export ') ? line.slice(7).trim() : line;
    const separator = normalized.indexOf('=');
    if (separator <= 0) continue;
    const key = normalized.slice(0, separator).trim();
    if (!/^[A-Za-z_][A-Za-z0-9_]*$/.test(key)) continue;
    const raw = normalized.slice(separator + 1).trim();
    if (raw.startsWith('"') && raw.endsWith('"')) {
      try {
        values[key] = JSON.parse(raw);
      } catch {
        values[key] = raw.slice(1, -1);
      }
    } else if (raw.startsWith("'") && raw.endsWith("'")) {
      values[key] = raw.slice(1, -1);
    } else {
      values[key] = raw;
    }
  }
  return values;
}

function execute(command, args, { cwd = dreamRoot, env = process.env, inherit = false } = {}) {
  return new Promise((resolvePromise, reject) => {
    throwIfInterrupted();
    const child = trackChild(spawn(command, args, {
      cwd,
      env,
      stdio: inherit ? 'inherit' : ['ignore', 'pipe', 'pipe'],
    }));
    let stdout = '';
    if (!inherit) {
      child.stdout.on('data', (chunk) => { stdout += chunk; });
      child.stderr.resume();
    }
    child.once('error', reject);
    child.once('exit', (code, signal) => {
      if (code === 0) resolvePromise(stdout.trim());
      else reject(new Error(`${command} exited with ${code ?? signal}`));
    });
  });
}

async function streamCommandToFile(command, args, filePath, { cwd = dreamRoot, env = process.env } = {}) {
  throwIfInterrupted();
  const child = trackChild(spawn(command, args, {
    cwd,
    env,
    stdio: ['ignore', 'pipe', 'pipe'],
  }));
  child.stderr.resume();
  const exit = new Promise((resolvePromise, reject) => {
    child.once('error', reject);
    child.once('exit', (code, signal) => resolvePromise({ code, signal }));
  });
  try {
    await pipeline(child.stdout, createWriteStream(filePath, { mode: 0o600 }));
  } catch (error) {
    child.kill('SIGTERM');
    throw error;
  }
  const result = await exit;
  if (result.code !== 0) {
    throw new Error(`${command} binary stream exited with ${result.code ?? result.signal}`);
  }
}

async function streamFileToCommand(filePath, command, args, { cwd = dreamRoot, env = process.env } = {}) {
  throwIfInterrupted();
  const child = trackChild(spawn(command, args, {
    cwd,
    env,
    stdio: ['pipe', 'ignore', 'pipe'],
  }));
  child.stderr.resume();
  const exit = new Promise((resolvePromise, reject) => {
    child.once('error', reject);
    child.once('exit', (code, signal) => resolvePromise({ code, signal }));
  });
  try {
    await pipeline(createReadStream(filePath), child.stdin);
  } catch (error) {
    child.kill('SIGTERM');
    throw error;
  }
  const result = await exit;
  if (result.code !== 0) {
    throw new Error(`${command} binary restore exited with ${result.code ?? result.signal}`);
  }
}

function startOwned(command, args, { cwd, env }) {
  throwIfInterrupted();
  const child = trackChild(spawn(command, args, {
    cwd,
    env,
    stdio: ['ignore', 'pipe', 'pipe'],
  }));
  child.stdout.resume();
  child.stderr.resume();
  ownedProcesses.push({ child, command });
  return child;
}

async function stopOwned() {
  for (const item of [...ownedProcesses].reverse()) {
    if (item.child.exitCode !== null || item.child.signalCode !== null) continue;
    item.child.kill('SIGTERM');
    await new Promise((resolvePromise) => {
      const timer = setTimeout(() => {
        if (item.child.exitCode === null && item.child.signalCode === null) {
          item.child.kill('SIGKILL');
        }
        resolvePromise();
      }, 5_000);
      item.child.once('exit', () => {
        clearTimeout(timer);
        resolvePromise();
      });
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

async function waitForPostgres(env) {
  const deadline = Date.now() + 60_000;
  while (Date.now() < deadline) {
    throwIfInterrupted();
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
  const deadline = Date.now() + 120_000;
  while (Date.now() < deadline) {
    throwIfInterrupted();
    if (child.exitCode !== null) throw new Error(`${label} exited before readiness`);
    try {
      const response = await fetch(url);
      if (response.status < 500) return;
    } catch {}
    await new Promise((resolvePromise) => setTimeout(resolvePromise, 300));
  }
  throw new Error(`${label} did not become ready`);
}

async function listenerPids(port) {
  try {
    return (await execute('lsof', [
      '-nP', `-iTCP:${port}`, '-sTCP:LISTEN', '-t',
    ])).split(/\s+/).filter(Boolean).sort();
  } catch {
    return [];
  }
}

async function containerIdentity(name) {
  try {
    return await execute('docker', [
      'inspect', '--format', '{{.Id}}|{{.State.StartedAt}}|{{if .State.Health}}{{.State.Health.Status}}{{end}}', name,
    ]);
  } catch {
    return null;
  }
}

async function databaseFingerprint(databaseUrl, { readOnly = true } = {}) {
  const source = [
    'import hashlib,json,os,psycopg',
    'from psycopg import sql',
    'tables=["users","platform_users","chat_thread","chat_message","workflow_runs","story_workspace_stories","ai_providers","ai_models","gateway_api_keys","subscriptions","subscription_usage_allowances","gateway_requests","subscription_token_ledger_entries"]',
    'options="-c default_transaction_read_only=on" if os.environ["INK_R24_DATABASE_READ_ONLY"]=="1" else None',
    'result={}',
    'with psycopg.connect(os.environ["INK_R24_DATABASE_URL"], options=options) as c:',
    ' for table in tables:',
    '  digest=hashlib.sha256(); count=0',
    '  with c.cursor() as cur:',
    '   cur.execute(sql.SQL("SELECT to_jsonb(t)::text FROM {} AS t ORDER BY to_jsonb(t)::text").format(sql.Identifier(table)))',
    '   for row in cur:',
    '    digest.update(row[0].encode("utf-8")); digest.update(b"\\n"); count+=1',
    '  result[table]={"count":count,"sha256":digest.hexdigest()}',
    'print(json.dumps(result,separators=(",",":"),sort_keys=True))',
  ].join('\n');
  return JSON.parse(await execute(
    python,
    ['-c', source],
    {
      cwd: backendRoot,
      env: {
        ...process.env,
        INK_R24_DATABASE_URL: databaseUrl,
        INK_R24_DATABASE_READ_ONLY: readOnly ? '1' : '0',
      },
    },
  ));
}

async function databaseServerMajor(databaseUrl) {
  const source = [
    'import os,psycopg',
    'with psycopg.connect(os.environ["INK_R24_DATABASE_URL"], options="-c default_transaction_read_only=on") as c:',
    ' print(int(c.execute("SHOW server_version_num").fetchone()[0])//10000)',
  ].join('\n');
  return Number(await execute(python, ['-c', source], {
    cwd: backendRoot,
    env: { ...process.env, INK_R24_DATABASE_URL: databaseUrl },
  }));
}

function postgresClientMajor(versionOutput) {
  const match = String(versionOutput).match(/PostgreSQL\)\s+(\d+)/);
  if (!match) throw new Error('unable to resolve PostgreSQL client major');
  return Number(match[1]);
}

function fingerprintDigest(value) {
  return createHash('sha256').update(JSON.stringify(value)).digest('hex');
}

async function provisionCloneUser(databaseUrl) {
  const source = [
    'import json,os,psycopg,sys',
    'with psycopg.connect(os.environ["INK_R24_DATABASE_URL"]) as c:',
    ' row=c.execute("""INSERT INTO users (email,password_hash,display_name,role,status) VALUES (%s,%s,%s,\'user\',\'active\') RETURNING id""",(sys.argv[1],"clone-only-no-login","Gateway Real Model Clone")).fetchone()',
    ' user_id=str(row[0])',
    ' projection=c.execute("SELECT id FROM platform_users WHERE source=\'ink-dream\' AND external_user_id=%s",(user_id,)).fetchone()',
    ' if projection is None:',
    '  c.execute("""INSERT INTO platform_users (id,source,external_user_id,email,display_name,tier,status,metadata) VALUES (%s,\'ink-dream\',%s,%s,%s,\'free\',\'active\',\'{}\'::jsonb)""",(sys.argv[2],user_id,sys.argv[1],"Gateway Real Model Clone"))',
    '  platform_id=sys.argv[2]',
    ' else:',
    '  platform_id=str(projection[0])',
    'print(json.dumps({"canonicalUserId":user_id,"platformUserId":platform_id},separators=(",",":")))',
  ].join('\n');
  return JSON.parse(await execute(
    python,
    ['-c', source, cloneEmail, clonePlatformUserId],
    { cwd: backendRoot, env: { ...process.env, INK_R24_DATABASE_URL: databaseUrl } },
  ));
}

async function verifyCloneModel(databaseUrl) {
  const source = [
    'import json,os,psycopg,sys',
    'with psycopg.connect(os.environ["INK_R24_DATABASE_URL"], options="-c default_transaction_read_only=on") as c:',
    ' rows=c.execute("""SELECT m.code,m.upstream_model,m.enabled,p.protocol,p.status,(p.api_key_ciphertext IS NOT NULL AND p.api_key_iv IS NOT NULL AND p.api_key_tag IS NOT NULL),COUNT(pr.id) FILTER (WHERE pr.status=\'active\' AND pr.effective_from<=now() AND (pr.effective_to IS NULL OR pr.effective_to>now())),COUNT(e.id) FILTER (WHERE e.enabled AND e.gateway_scopes @> ARRAY[\'messages:create\']::text[] AND v.status=\'published\') FROM ai_models m JOIN ai_providers p ON p.id=m.provider_id LEFT JOIN ai_pricing_rules pr ON pr.model_id=m.id LEFT JOIN subscription_plan_entitlements e ON e.model_id=m.id LEFT JOIN subscription_plan_versions v ON v.id=e.plan_version_id WHERE m.code=%s AND m.upstream_model=%s GROUP BY m.id,p.id""",(sys.argv[1],sys.argv[2])).fetchall()',
    ' assert len(rows)==1',
    ' row=rows[0]',
    ' assert row[2] and row[4]=="active" and row[5] and int(row[6])>0 and int(row[7])>0',
    ' print(json.dumps({"alias":row[0],"upstream":row[1],"enabled":bool(row[2]),"protocol":row[3],"providerActive":row[4]=="active","credentialReady":bool(row[5]),"activePricing":int(row[6]),"publishedEntitlements":int(row[7])},separators=(",",":")))',
  ].join('\n');
  return JSON.parse(await execute(
    python,
    ['-c', source, targetModelAlias, expectedUpstreamModel],
    { cwd: backendRoot, env: { ...process.env, INK_R24_DATABASE_URL: databaseUrl } },
  ));
}

async function verifyFreshThreadFallback(databaseUrl, canonicalUserId) {
  const source = [
    'import json,os,psycopg,sys',
    'with psycopg.connect(os.environ["INK_R24_DATABASE_URL"], options="-c default_transaction_read_only=on") as c:',
    ' count=c.execute("""SELECT COUNT(*) FROM workflow_runs AS run JOIN chat_thread AS thread ON thread.id=run.source_voice_thread_id WHERE thread.user_id=%s AND run.status IN (\'completed\',\'failed\',\'cancelled\') AND run.source_voice_thread_id IS NOT NULL""",(int(sys.argv[1]),)).fetchone()[0]',
    ' assert int(count)==0',
    ' print(json.dumps({"eligibleTerminalDreamThreads":int(count),"freshGenericThreadFallback":True},separators=(",",":")))',
  ].join('\n');
  return JSON.parse(await execute(python, ['-c', source, canonicalUserId], {
    cwd: backendRoot,
    env: { ...process.env, INK_R24_DATABASE_URL: databaseUrl },
  }));
}

const adminFileEnv = parseEnv(await readFile(resolve(adminRoot, '.env.local'), 'utf8'));
const backendFileEnv = parseEnv(await readFile(resolve(backendRoot, '.env'), 'utf8'));
const sourceDatabaseUrl = adminFileEnv.DATABASE_URL;
if (!sourceDatabaseUrl) throw new Error('source DATABASE_URL is not configured');
const sourceIdentity = new URL(sourceDatabaseUrl);
if (sourceIdentity.pathname.slice(1).toLowerCase().includes('test')) {
  throw new Error('source database unexpectedly has a test identity');
}
for (const name of [
  'AI_CREDENTIAL_ENCRYPTION_KEY',
  'GATEWAY_API_KEY_PEPPER',
  'GATEWAY_SUBJECT_JWT_ISSUER',
  'GATEWAY_SUBJECT_JWT_AUDIENCE',
]) {
  if (!adminFileEnv[name]) throw new Error(`Admin ${name} is not configured`);
}
for (const name of [
  'INK_GATEWAY_SERVICE_KEY',
  'INK_GATEWAY_SUBJECT_JWT_ISSUER',
  'INK_GATEWAY_SUBJECT_JWT_AUDIENCE',
  'INK_GATEWAY_SERVICE_CLIENT_ID',
  'INK_ADMIN_PRODUCT_JWT_SECRET',
]) {
  if (!backendFileEnv[name]) throw new Error(`Dream ${name} is not configured`);
}

const existingContainerBaselines = Object.fromEntries(await Promise.all(
  ['ink-memory-postgres', 'ink-memory-minio'].map(async (name) => [
    name,
    await containerIdentity(name),
  ]),
));
const adminPortBaseline = await listenerPids(3000);
const dreamGitBaseline = await execute('git', ['status', '--porcelain=v1'], { cwd: dreamRoot });
const adminGitBaseline = await execute('git', ['status', '--porcelain=v1'], { cwd: adminRoot });

try {
  if (selfInterruptAfterVolumeCreate && !preflightOnly) {
    throw new Error('self-interruption check is restricted to provider-free preflight');
  }
  runPhase = 'isolated-admin-checkout';
  await execute('git', ['clone', '--quiet', '--shared', adminRoot, adminRuntimeRoot], {
    cwd: runtimeRoot,
  });
  const [sourceAdminHead, runtimeAdminHead] = await Promise.all([
    execute('git', ['rev-parse', 'HEAD'], { cwd: adminRoot }),
    execute('git', ['rev-parse', 'HEAD'], { cwd: adminRuntimeRoot }),
  ]);
  if (sourceAdminHead !== runtimeAdminHead) {
    throw new Error('isolated Admin runtime checkout does not match source HEAD');
  }
  await symlink(resolve(adminRoot, 'node_modules'), resolve(adminRuntimeRoot, 'node_modules'));

  runPhase = 'owned-port-allocation';
  const postgresPort = await availablePort();
  const adminPort = await availablePort();
  const dreamApiPort = await availablePort();
  ownedPorts = [postgresPort, adminPort, dreamApiPort];
  targetDatabaseUrl = `postgresql://postgres:${encodeURIComponent(postgresPassword)}@127.0.0.1:${postgresPort}/${databaseName}`;
  const targetPgEnv = pgEnv(targetDatabaseUrl);

  runPhase = 'source-readonly-fingerprint';
  sourceFingerprintBefore = await databaseFingerprint(sourceDatabaseUrl);
  const sourceServerMajor = await databaseServerMajor(sourceDatabaseUrl);
  const dumpClientMajor = postgresClientMajor(await execute('docker', [
    'exec', sourcePostgresContainer, 'pg_dump', '--version',
  ]));
  if (sourceServerMajor !== 16 || dumpClientMajor !== 16) {
    throw new Error('source server and dump client must both be PostgreSQL 16');
  }
  const sourceUser = decodeURIComponent(sourceIdentity.username);
  const sourcePassword = decodeURIComponent(sourceIdentity.password);
  const sourceDatabase = decodeURIComponent(sourceIdentity.pathname.slice(1));
  if (!sourceUser || !sourcePassword || !sourceDatabase) {
    throw new Error('source database credentials are incomplete');
  }
  runPhase = 'source-readonly-dump';
  await streamCommandToFile('docker', [
    'exec',
    '--env', 'PGPASSWORD',
    '--env', 'PGOPTIONS',
    sourcePostgresContainer,
    'pg_dump',
    '--host=127.0.0.1',
    '--port=5432',
    `--username=${sourceUser}`,
    `--dbname=${sourceDatabase}`,
    '--format=custom',
    '--serializable-deferrable',
    '--no-owner',
    '--no-acl',
  ], dumpPath, {
    env: {
      ...process.env,
      PGPASSWORD: sourcePassword,
      PGOPTIONS: '-c default_transaction_read_only=on',
    },
  });
  await chmod(dumpPath, 0o600);

  runPhase = 'owned-postgres-volume';
  await execute('docker', [
    'volume', 'create', '--label', `ink.r22.run=${runLabel}`, volumeName,
  ]);
  if (selfInterruptAfterVolumeCreate) {
    process.kill(process.pid, 'SIGINT');
    await new Promise((resolvePromise) => setImmediate(resolvePromise));
    throwIfInterrupted();
  }
  runPhase = 'owned-postgres-container';
  await execute('docker', [
    'run', '--detach', '--rm', '--name', containerName,
    '--label', `ink.r22.run=${runLabel}`,
    '--mount', `type=volume,source=${volumeName},target=/var/lib/postgresql/data`,
    '--env', 'POSTGRES_USER=postgres',
    '--env', 'POSTGRES_PASSWORD',
    '--env', 'POSTGRES_DB',
    '--publish', `127.0.0.1:${postgresPort}:5432`,
    'postgres:16-alpine',
  ], {
    env: {
      ...process.env,
      POSTGRES_PASSWORD: postgresPassword,
      POSTGRES_DB: databaseName,
    },
  });
  await waitForPostgres(targetPgEnv);
  const targetServerMajor = await databaseServerMajor(targetDatabaseUrl);
  const restoreClientMajor = postgresClientMajor(await execute('docker', [
    'exec', containerName, 'pg_restore', '--version',
  ]));
  if (targetServerMajor !== 16 || restoreClientMajor !== 16) {
    throw new Error('target server and restore client must both be PostgreSQL 16');
  }
  runPhase = 'clone-database-restore';
  await streamFileToCommand(dumpPath, 'docker', [
    'exec', '--interactive', '--env', 'PGPASSWORD', containerName,
    'pg_restore',
    '--host=127.0.0.1',
    '--port=5432',
    '--username=postgres',
    `--dbname=${databaseName}`,
    '--no-owner',
    '--no-acl',
    '--exit-on-error',
  ], {
    env: { ...process.env, PGPASSWORD: postgresPassword },
  });

  runPhase = 'clone-fingerprint-match';
  const restoredFingerprint = await databaseFingerprint(targetDatabaseUrl);
  if (JSON.stringify(restoredFingerprint) !== JSON.stringify(sourceFingerprintBefore)) {
    throw new Error('restored clone fingerprint does not match the read-only source snapshot');
  }

  runPhase = 'clone-schema-migrations';
  const migrationEnv = {
    ...process.env,
    MIGRATION_DATABASE_URL: targetDatabaseUrl,
    DATABASE_URL: targetDatabaseUrl,
    TEST_DATABASE_URL: targetDatabaseUrl,
    INK_USE_TEST_DATABASE_URL: '1',
  };
  await execute('node', ['scripts/migrate.mjs'], {
    cwd: adminRoot,
    env: migrationEnv,
  });

  runPhase = 'clone-subject-and-model-preflight';
  const cloneUser = await provisionCloneUser(targetDatabaseUrl);
  const modelEvidence = await verifyCloneModel(targetDatabaseUrl);
  const fallbackEvidence = await verifyFreshThreadFallback(
    targetDatabaseUrl,
    cloneUser.canonicalUserId,
  );
  const adminBaseUrl = `http://127.0.0.1:${adminPort}`;
  const dreamApiBase = `http://127.0.0.1:${dreamApiPort}`;
  const productOrigin = dreamApiBase;
  const adminEnv = {
    ...process.env,
    ...adminFileEnv,
    DATABASE_URL: targetDatabaseUrl,
    TEST_DATABASE_URL: targetDatabaseUrl,
    INK_USE_TEST_DATABASE_URL: '1',
    NODE_ENV: 'development',
    PORT: String(adminPort),
    ADMIN_CONSOLE_ENABLED: 'true',
    ADMIN_ORIGIN_ALLOWLIST: adminBaseUrl,
    PRODUCT_API_ORIGIN_ALLOWLIST: productOrigin,
    ARTIFACT_WORKSPACE_ROOT: workspaceRoot,
    INK_ADMIN_E2E_DIST_DIR: adminDistName,
    FILE_STORAGE_TYPE: 'local',
    FILE_STORAGE_LOCAL_DIR: localFilesRoot,
  };
  runPhase = 'isolated-admin-start';
  const admin = startOwned(
    'pnpm',
    ['dev', '--hostname', '127.0.0.1', '--webpack'],
    {
    cwd: adminRuntimeRoot,
    env: adminEnv,
    },
  );
  await waitForUrl(`${adminBaseUrl}/v1/models`, admin, 'isolated Admin Gateway');

  runPhase = 'isolated-dream-start';
  const dreamEnv = {
    ...process.env,
    ...backendFileEnv,
    DATABASE_URL: targetDatabaseUrl,
    TEST_DATABASE_URL: targetDatabaseUrl,
    INK_USE_TEST_DATABASE_URL: '1',
    INK_LOAD_DATABASE_URL_FROM_ENV_FILE: '0',
    JWT_SECRET: cloneJwtSecret,
    AGENT_CWD: workspaceRoot,
    FILE_STORAGE_TYPE: 'local',
    FILE_STORAGE_LOCAL_DIR: localFilesRoot,
    INK_GATEWAY_ENABLED: '1',
    INK_GATEWAY_BASE_URL: adminBaseUrl,
    INK_GATEWAY_TEXT_MODEL_ALIAS: targetModelAlias,
    INK_ADMIN_PRODUCT_API_BASE_URL: adminBaseUrl,
    INK_ADMIN_PRODUCT_ORIGIN: productOrigin,
    INK_ENVIRONMENT: 'test',
    INK_AGENT_MAX_TURNS: '1',
    ANTHROPIC_API_KEY: '',
    ANTHROPIC_AUTH_TOKEN: '',
    CLAUDE_CODE_OAUTH_TOKEN: '',
    CLAUDE_CONFIG_DIR: '',
  };
  const dreamApi = startOwned(resolve(backendRoot, '.venv/bin/uvicorn'), [
    'server:app', '--host', '127.0.0.1', '--port', String(dreamApiPort),
  ], { cwd: backendRoot, env: dreamEnv });
  await waitForUrl(`${dreamApiBase}/api/health`, dreamApi, 'isolated Dream API');

  runPhase = preflightOnly ? 'provider-free-contract-preflight' : 'real-model-contract-proof';
  await execute(python, ['script/verify_gateway_e2e.py'], {
    cwd: backendRoot,
    env: {
      ...dreamEnv,
      INK_GATEWAY_E2E_EMAIL: cloneEmail,
      INK_GATEWAY_E2E_DREAM_BASE_URL: dreamApiBase,
      INK_GATEWAY_E2E_MODEL_ALIAS: targetModelAlias,
      INK_GATEWAY_E2E_EXPECTED_UPSTREAM_MODEL: expectedUpstreamModel,
      INK_GATEWAY_E2E_PROVISION_SUBSCRIPTION: '1',
      INK_GATEWAY_E2E_PRODUCT_ORIGIN: productOrigin,
      INK_GATEWAY_E2E_PREFLIGHT_ONLY: preflightOnly ? '1' : '0',
    },
    inherit: true,
  });

  runPhase = 'evidence-assembly';
  runEvidence = {
    sourceMode: 'read-only-logical-clone',
    restoredFingerprintMatched: true,
    sourceFingerprint: fingerprintDigest(sourceFingerprintBefore),
    databaseMajors: {
      sourceServer: sourceServerMajor,
      dumpClient: dumpClientMajor,
      targetServer: targetServerMajor,
      restoreClient: restoreClientMajor,
    },
    cloneOnlyCanonicalUser: Boolean(cloneUser.canonicalUserId),
    cloneOnlyPlatformProjection: Boolean(cloneUser.platformUserId),
    conversationFixture: fallbackEvidence,
    adminRuntimeCheckout: 'isolated-head-clone',
    adminBundler: 'webpack-isolated-external-dependency-link',
    model: modelEvidence,
    preflightOnly,
    browser: 'provider-proof-only; run headed Dream/Chat convergence separately',
  };
} catch (error) {
  runError = error;
  failedPhase = runPhase;
} finally {
  cleanupPhase = true;
  await stopOwned();
  await execute('docker', ['rm', '--force', containerName]).catch(() => undefined);
  await execute('docker', ['volume', 'rm', volumeName]).catch(() => undefined);
  await rm(runtimeRoot, { recursive: true, force: true });
}

const sourceFingerprintAfter = sourceFingerprintBefore
  ? await databaseFingerprint(sourceDatabaseUrl)
  : undefined;
const sourceUnchanged = Boolean(
  sourceFingerprintBefore
  && JSON.stringify(sourceFingerprintBefore) === JSON.stringify(sourceFingerprintAfter),
);
const existingContainersUnchanged = (
  await Promise.all(Object.entries(existingContainerBaselines).map(
    async ([name, identity]) => (await containerIdentity(name)) === identity,
  ))
).every(Boolean);
const adminPortUnchanged = JSON.stringify(await listenerPids(3000)) === JSON.stringify(adminPortBaseline);
const ownedPortsReleased = (
  await Promise.all(ownedPorts.map(async (port) => (await listenerPids(port)).length === 0))
).every(Boolean);
const ownedContainerRemoved = await containerIdentity(containerName) === null;
let ownedVolumeRemoved = false;
try {
  await execute('docker', ['volume', 'inspect', volumeName]);
} catch {
  ownedVolumeRemoved = true;
}
const dreamGitUnchanged = await execute('git', ['status', '--porcelain=v1'], { cwd: dreamRoot }) === dreamGitBaseline;
const adminGitUnchanged = await execute('git', ['status', '--porcelain=v1'], { cwd: adminRoot }) === adminGitBaseline;
const cleanup = {
  sourceUnchanged,
  existingContainersUnchanged,
  adminPortUnchanged,
  ownedPortsReleased,
  ownedContainerRemoved,
  ownedVolumeRemoved,
  dreamGitUnchanged,
  adminGitUnchanged,
  temporaryPrivateCloneRemoved: true,
};

if (runError) {
  console.error(JSON.stringify({
    phase: failedPhase ?? 'r22-real-model-proof',
    cleanup,
    errorClass: runError?.constructor?.name ?? 'Error',
    interrupted: Boolean(interruptedSignal),
  }));
  process.exitCode = interruptedSignal === 'SIGINT'
    ? 130
    : interruptedSignal === 'SIGTERM' ? 143 : 1;
} else if (!Object.values(cleanup).every(Boolean)) {
  console.error(JSON.stringify({
    phase: 'r22-cleanup-integrity',
    cleanup,
    errorClass: 'CleanupIntegrityError',
  }));
  process.exitCode = 1;
} else {
  console.log(JSON.stringify({
    [preflightOnly ? 'r22ProviderFreePreflight' : 'r22RealModelProof']: 'passed',
    ...runEvidence,
    cleanup,
  }));
}

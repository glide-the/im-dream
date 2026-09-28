// [Input] Explicit local Admin root, Python/runtime audience and a maintenance URL or Admin env file.
// [Output] Owned migrated database, Admin HTTP and Dream scheduled Chat probe receipt with deterministic cleanup.
// [Pos] Reproducible cross-repository technical E2E runner; never targets the normal business database.
// [Sync] 2026-09-28: derive local maintenance connection safely, migrate an owned database and exercise due/manual Chat triggers.
import { createRequire } from 'node:module';
import { readFileSync } from 'node:fs';
import { spawn } from 'node:child_process';
import { createServer } from 'node:net';
import { randomBytes, randomUUID } from 'node:crypto';
import { rm } from 'node:fs/promises';
import { resolve } from 'node:path';
import { fileURLToPath } from 'node:url';

function required(name) {
  const value = process.env[name];
  if (!value) throw new Error(`Missing required isolated-test setting: ${name}`);
  return value;
}

const adminRoot = resolve(required('INK_SCHEDULED_TEST_ADMIN_ROOT'));
const dreamRoot = resolve(fileURLToPath(new URL('..', import.meta.url)));
const python = resolve(required('INK_SCHEDULED_TEST_PYTHON'));
const resource = required('INK_SCHEDULED_TEST_RESOURCE');
const require = createRequire(`${adminRoot}/package.json`);
const pg = require('pg');
const dotenv = require('dotenv');
const jose = require('jose');
const local = process.env.INK_SCHEDULED_TEST_ADMIN_ENV_FILE
  ? dotenv.parse(readFileSync(resolve(process.env.INK_SCHEDULED_TEST_ADMIN_ENV_FILE))) : {};
const maintenanceSource = process.env.INK_SCHEDULED_TEST_MAINTENANCE_URL ?? local.DATABASE_URL;
if (!maintenanceSource) throw new Error('Missing isolated-test maintenance URL or explicit Admin env file');
const maintenanceUrl = new URL(maintenanceSource);
if (!['postgres:', 'postgresql:'].includes(maintenanceUrl.protocol)
  || !['localhost', '127.0.0.1', '[::1]'].includes(maintenanceUrl.hostname)
  || !maintenanceUrl.pathname || maintenanceUrl.pathname === '/') {
  throw new Error('TEST_MAINTENANCE_URL_MUST_BE_LOCAL');
}
if (process.env.INK_SCHEDULED_TEST_MAINTENANCE_URL
  && decodeURIComponent(maintenanceUrl.pathname) !== '/postgres') {
  throw new Error('EXPLICIT_MAINTENANCE_URL_MUST_TARGET_POSTGRES');
}
maintenanceUrl.pathname = '/postgres';
const suffix = randomBytes(6).toString('hex');
const databaseName = `ink_scheduled_cross_service_test_${suffix}`;
const distDir = `.next-e2e-scheduled-${suffix}`;
const serviceId = `scheduled-proof-service-${suffix}`;
const gatewayClientId = `scheduled-proof-gateway-${suffix}`;
const browserClientId = `scheduled-proof-browser-${suffix}`;
const databaseUrl = new URL(maintenanceUrl); databaseUrl.pathname = `/${databaseName}`;
const maintenance = new pg.Client({ connectionString: maintenanceUrl.toString(), connectionTimeoutMillis: 5000 });
let created = false;
let adminProcess;
const tail = [];

async function port() {
  const server = createServer();
  await new Promise((resolve, reject) => { server.once('error', reject); server.listen(0, '127.0.0.1', resolve); });
  const value = server.address().port;
  await new Promise((resolve, reject) => server.close(error => error ? reject(error) : resolve()));
  return value;
}

function execute(command, args, cwd, env, timeoutMs = 180_000) {
  return new Promise((resolve, reject) => {
    const child = spawn(command, args, { cwd, env, stdio: ['ignore', 'pipe', 'pipe'], detached: true });
    let output = '';
    child.stdout.on('data', data => { output += data; });
    child.stderr.on('data', data => { output += data; });
    let timedOut = false;
    let forceTimer;
    const timer = setTimeout(() => {
      timedOut = true;
      try { process.kill(-child.pid, 'SIGTERM'); } catch { /* already exited */ }
      forceTimer = setTimeout(() => {
        if (child.exitCode === null && child.signalCode === null) {
          try { process.kill(-child.pid, 'SIGKILL'); } catch { /* already exited */ }
        }
      }, 5000);
    }, timeoutMs);
    child.once('error', error => { clearTimeout(timer); clearTimeout(forceTimer); reject(error); });
    child.once('exit', code => {
      clearTimeout(timer);
      clearTimeout(forceTimer);
      console.log(`command ${command} ${args.join(' ')} exit=${code}`);
      if (code === 0 && args[0] === 'backend/tests/probe_scheduled_task_http.py') {
        const receipt = output.trim().split('\n').findLast(line => line.startsWith('{"status": "passed"'));
        if (receipt) console.log(receipt);
      }
      if (timedOut) reject(new Error(`TEST_COMMAND_TIMEOUT:${command}`));
      else code === 0 ? resolve(output) : reject(new Error(`COMMAND_FAILED:${code}`));
    });
  });
}

async function waitReady(base) {
  for (let attempt = 0; attempt < 120; attempt++) {
    if (adminProcess.exitCode !== null || adminProcess.signalCode !== null) throw new Error('ADMIN_EXITED_BEFORE_READY');
    try {
      const response = await fetch(`${base}/api/internal/dream/v1/capabilities`, { signal: AbortSignal.timeout(1000) });
      if (response.status < 500) return;
    } catch { /* startup */ }
    await new Promise(resolve => setTimeout(resolve, 500));
  }
  throw new Error('ADMIN_NOT_READY');
}

async function seed(pool) {
  const identity = (await pool.query('SELECT current_database() AS name')).rows[0]?.name;
  if (identity !== databaseName) throw new Error('TEST_DATABASE_IDENTITY_MISMATCH');
  const rows = (await pool.query('SELECT count(*)::int AS count FROM users')).rows[0]?.count;
  if (rows !== 0) throw new Error('TEST_DATABASE_NOT_EMPTY');
  const capabilities = await pool.query(`SELECT capability FROM drizzle.schema_capabilities WHERE capability IN
    ('dream.chat-scheduled-task.v1', 'identity.scheduled-chat-runtime.v1',
     'dream.chat-scheduled-turn-binding.v1', 'dream.chat-scheduled-link-lifecycle.v1')`);
  if (capabilities.rowCount !== 4) throw new Error('SCHEDULED_CAPABILITIES_MISSING');
  const { publicKey, privateKey } = await jose.generateKeyPair('ES256', { extractable: true });
  const publicJwk = await jose.exportJWK(publicKey);
  const privateJwk = await jose.exportJWK(privateKey);
  const kid = `schedule-proof-${randomUUID()}`;
  await pool.query('INSERT INTO identity.jwks (id,"publicKey","privateKey","createdAt",alg,crv) VALUES ($1,$2,$3,now(),$4,$5)',
    [kid, JSON.stringify(publicJwk), JSON.stringify(privateJwk), 'ES256', 'P-256']);
  await pool.query("INSERT INTO users (id,email,password_hash) VALUES (1,'scheduled-one@example.invalid','fixture'),(2,'scheduled-two@example.invalid','fixture')");
  await pool.query(`INSERT INTO identity."user" (id,name,email,"emailVerified","createdAt","updatedAt") VALUES
    ('scheduled-subject-1','Scheduled One','scheduled-auth-one@example.invalid',true,now(),now()),
    ('scheduled-subject-2','Scheduled Two','scheduled-auth-two@example.invalid',true,now(),now())`);
  await pool.query("INSERT INTO identity.subject_links (auth_user_id,canonical_user_id,evidence) VALUES ('scheduled-subject-1',1,'fixture'),('scheduled-subject-2',2,'fixture')");
  await pool.query(`INSERT INTO gateway_api_keys
    (id,subject_mode,service_client_id,name,key_prefix,key_hash,scopes,status)
    VALUES ($1,'canonical_subject',$2,'Scheduled probe key',$3,$4,$5,'active')`,
    [`scheduled-proof-key-${randomUUID()}`, gatewayClientId, 'scheduled-proof', randomBytes(32).toString('hex'),
      ['messages:create', 'messages:count_tokens', 'models:list']]);
  console.log(`identity_ok ${databaseName}; scheduled_capabilities=${capabilities.rowCount}`);
  return { privateKey, kid };
}

async function token(privateKey, kid, issuer, audience, subject, clientId, scopes) {
  return new jose.SignJWT({ client_id: clientId, scope: scopes.join(' ') })
    .setProtectedHeader({ alg: 'ES256', typ: 'at+jwt', kid })
    .setIssuer(issuer).setAudience(audience).setSubject(subject)
    .setJti(randomUUID()).setIssuedAt().setExpirationTime('4m')
    .sign(privateKey);
}

try {
  await maintenance.connect();
  const actual = (await maintenance.query('SELECT current_database() AS name')).rows[0]?.name;
  if (actual !== 'postgres') throw new Error('MAINTENANCE_DATABASE_MISMATCH');
  if ((await maintenance.query('SELECT 1 FROM pg_database WHERE datname=$1', [databaseName])).rowCount)
    throw new Error(`TEST_DATABASE_ALREADY_EXISTS:${databaseName}`);
  await maintenance.query(`CREATE DATABASE "${databaseName}"`);
  created = true;
  const dbEnv = { ...process.env, ...local };
  for (const key of Object.keys(dbEnv)) {
    if (key === 'DATABASE_URL' || key.endsWith('_DATABASE_URL')) dbEnv[key] = databaseUrl.toString();
  }
  Object.assign(dbEnv, {
    DATABASE_URL: databaseUrl.toString(), AUTH_DATABASE_URL: databaseUrl.toString(),
    ADMIN_CONTROL_DATABASE_URL: databaseUrl.toString(), DREAM_DATA_DATABASE_URL: databaseUrl.toString(),
    MIGRATION_DATABASE_URL: databaseUrl.toString(), POSTGRES_DB: databaseName,
    PGDATABASE: databaseName,
  });
  await execute('pnpm', ['db:migrate'], adminRoot, dbEnv);
  const pool = new pg.Pool({ connectionString: databaseUrl.toString() });
  let key;
  try { key = await seed(pool); } finally { await pool.end(); }
  const adminPort = await port();
  const origin = `http://127.0.0.1:${adminPort}`;
  const issuer = `${origin}/api/auth`;
  const serviceSecret = randomBytes(32).toString('base64url');
  const env = { ...dbEnv, NODE_ENV: 'development', PORT: String(adminPort),
    INK_ADMIN_E2E_DIST_DIR: distDir,
    BETTER_AUTH_URL: issuer, BETTER_AUTH_SECRET: randomBytes(48).toString('base64url'),
    AUTH_TRUSTED_ORIGINS: origin, DREAM_API_RESOURCE: resource,
    GOOGLE_CLIENT_ID: 'scheduled-proof-google', GOOGLE_CLIENT_SECRET: 'scheduled-proof-secret',
    AUTH_DEVICE_CLIENT_ID: 'scheduled-proof-device',
    AUTH_TOKEN_ENCRYPTION_KEY: randomBytes(32).toString('hex'),
    AUTH_CHAT_SCHEDULE_AUTHORITY_SECRET: randomBytes(48).toString('base64url'),
    AUTH_RUNTIME_DELEGATION_TTL_SECONDS: '120', AUTH_RUNTIME_DELEGATION_MAX_TTL_SECONDS: '600',
    DREAM_DATA_MAX_BODY_BYTES: '65536',
    DREAM_GATEWAY_CLIENT_BINDINGS: JSON.stringify([{ service_client_id: serviceId,
      gateway_client_id: gatewayClientId, oauth_client_ids: [browserClientId] }]),
    DREAM_DATA_SERVICE_CLIENTS: JSON.stringify([{ id: serviceId, secret: serviceSecret,
      origin, oauthClientId: browserClientId, redirectUri: `${origin}/callback`,
      backgroundScopes: ['capabilities:read', 'schedule:execute'] }]),
  };
  const serviceToken = await token(key.privateKey, key.kid, issuer, resource, serviceId, serviceId, ['capabilities:read', 'schedule:execute']);
  const userToken = await token(key.privateKey, key.kid, issuer, resource, 'scheduled-subject-1', browserClientId, ['dream:read','dream:write']);
  const foreignToken = await token(key.privateKey, key.kid, issuer, resource, 'scheduled-subject-2', browserClientId, ['dream:read','dream:write']);
  adminProcess = spawn('pnpm', ['exec', 'next', 'dev', '--webpack', '-H', '127.0.0.1', '-p', String(adminPort)], { cwd: adminRoot, env, stdio: ['ignore', 'pipe', 'pipe'], detached: true });
  for (const stream of [adminProcess.stdout, adminProcess.stderr]) stream.on('data', data => { tail.push(String(data)); if (tail.length > 80) tail.shift(); });
  await waitReady(origin);
  console.log(`admin_ready ${origin}`);
  await execute(python, ['backend/tests/probe_scheduled_task_http.py'], dreamRoot, {
    ...process.env, PYTHONPATH: `${dreamRoot}/backend`,
    SCHEDULE_PROBE_ADMIN_ORIGIN: origin, SCHEDULE_PROBE_SERVICE_ID: serviceId,
    SCHEDULE_PROBE_SERVICE_SECRET: serviceSecret, SCHEDULE_PROBE_SERVICE_TOKEN: serviceToken,
    SCHEDULE_PROBE_USER_TOKEN: userToken, SCHEDULE_PROBE_FOREIGN_USER_TOKEN: foreignToken,
    SCHEDULE_PROBE_RESOURCE: resource,
  }, 180_000);
} finally {
  if (adminProcess && adminProcess.exitCode === null && adminProcess.signalCode === null) {
    try { process.kill(-adminProcess.pid, 'SIGTERM'); } catch { /* already exited */ }
    await new Promise(resolve => { const timeout = setTimeout(resolve, 5000); adminProcess.once('exit', () => { clearTimeout(timeout); resolve(); }); });
    if (adminProcess.exitCode === null && adminProcess.signalCode === null) {
      try { process.kill(-adminProcess.pid, 'SIGKILL'); } catch { /* already exited */ }
      await new Promise(resolve => { const timeout = setTimeout(resolve, 5000); adminProcess.once('exit', () => { clearTimeout(timeout); resolve(); }); });
    }
  }
  if (created) {
    const existing = await maintenance.query('SELECT 1 FROM pg_database WHERE datname=$1', [databaseName]);
    if (existing.rowCount) {
      await maintenance.query(`DROP DATABASE "${databaseName}" WITH (FORCE)`);
      console.log(`cleaned ${databaseName}`);
    }
  }
  await rm(`${adminRoot}/${distDir}`, { recursive: true, force: true });
  await maintenance.end().catch(() => {});
}

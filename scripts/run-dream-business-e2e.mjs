#!/usr/bin/env node

import { spawn } from 'node:child_process';
import { createHash, randomBytes } from 'node:crypto';
import { readFile, rm, writeFile, mkdtemp } from 'node:fs/promises';
import { createServer as createHttpServer } from 'node:http';
import { createServer as createNetServer } from 'node:net';
import { tmpdir } from 'node:os';
import { join, resolve } from 'node:path';
import { startDreamProducerProvider } from './dream-producer-provider.mjs';

const dreamRoot = resolve(new URL('../', import.meta.url).pathname);
const adminRoot = resolve(dreamRoot, '../ink-admin-memory');
const backendRoot = resolve(dreamRoot, 'backend');
const frontendRoot = resolve(dreamRoot, 'frontend');
const python = resolve(backendRoot, '.venv/bin/python');
const alembic = resolve(backendRoot, '.venv/bin/alembic');
const suffix = randomBytes(6).toString('hex');
const databaseName = `ink_memory_dream_business_${suffix}_test`;
const containerName = `ink-dream-business-e2e-${suffix}`;
const postgresPassword = `pg_${randomBytes(24).toString('base64url')}`;
const bootstrapToken = `bootstrap_${randomBytes(32).toString('base64url')}`;
const adminEmail = 'dream-e2e-admin@example.invalid';
const adminPassword = 'Dream-business-E2E-2026!';
const gatewayIssuer = `ink-admin-e2e-${suffix}`;
const gatewayAudience = `ink-dream-e2e-${suffix}`;
const gatewayClientId = `ink-dream-business-${suffix}`;
const adminDistDir = `.next-e2e-dream-business-${suffix}`;
const outputRoot = await mkdtemp(join(tmpdir(), 'ink-dream-business-e2e-'));
const artifactRoot = await mkdtemp(join(tmpdir(), 'ink-dream-agent-workspaces-'));
const tsconfigPath = resolve(adminRoot, 'tsconfig.json');
const originalTsconfig = await readFile(tsconfigPath, 'utf8');
const ownedProcesses = [];
let containerStarted = false;
let provider;
let databaseUrl;

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
    if (tail.length > 80) tail.shift();
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
  if (!address || typeof address === 'string') throw new Error('Failed to allocate an owned port');
  await new Promise((resolvePromise, reject) => server.close((error) => error ? reject(error) : resolvePromise()));
  return address.port;
}

async function waitForUrl(url, processToWatch, label) {
  const deadline = Date.now() + 120_000;
  while (Date.now() < deadline) {
    if (processToWatch.exitCode !== null) {
      const owner = ownedProcesses.find((item) => item.child === processToWatch);
      throw new Error(`${label} exited before readiness:\n${owner?.tail.join('') ?? ''}`);
    }
    try {
      const response = await fetch(url, { signal: AbortSignal.timeout(1_000) });
      if (response.status < 500) return;
    } catch {
      // Service is not ready yet.
    }
    await new Promise((resolvePromise) => setTimeout(resolvePromise, 500));
  }
  throw new Error(`${label} did not become ready`);
}

async function waitForPostgres(databaseUrl) {
  const probe = [
    'import psycopg, sys, time',
    'url=sys.argv[1]',
    'deadline=time.time()+60',
    'last=None',
    'while True:',
    '  try:',
    '    with psycopg.connect(url, connect_timeout=1) as c: c.execute("SELECT 1")',
    '    break',
    '  except Exception as exc:',
    '    last=exc',
    '    if time.time() >= deadline: raise last',
    '    time.sleep(0.5)',
  ].join('\n');
  await execute(python, ['-c', probe, databaseUrl], { cwd: backendRoot });
}

async function baselineAclSha256(databaseUrl) {
  const source = [
    'import json, psycopg, sys',
    'with psycopg.connect(sys.argv[1]) as c:',
    ' rows=c.execute("""SELECT table_name, grantee, privilege_type, is_grantable FROM information_schema.role_table_grants WHERE table_schema=current_schema() AND table_name=ANY(%s::text[]) ORDER BY table_name, grantee, privilege_type, is_grantable""", (["story_workspace_stories","story_workspace_workspaces","users"],)).fetchall()',
    ' print(json.dumps([[str(v) for v in row] for row in rows],separators=(",",":")))',
  ].join('\n');
  const rows = await execute(python, ['-c', source, databaseUrl], { cwd: backendRoot });
  return createHash('sha256').update(rows).digest('hex');
}

async function provisionUsers(databaseUrl) {
  const source = [
    'import psycopg, sys',
    'from services.deck.builtin_plugin import seed_builtin_deck_plugin',
    'with psycopg.connect(sys.argv[1]) as c:',
    ' c.execute("""INSERT INTO users (id,email,password_hash,display_name,role) VALUES (101,%s,%s,%s,\'user\'),(102,%s,%s,%s,\'user\')""", ("ink-dream-round-20260810@example.invalid","fixture-hash-not-a-secret","Dream Creator","other-dream-e2e@example.invalid","fixture-hash-not-a-secret","Other Creator"))',
    ' c.execute("""INSERT INTO story_workspace_workspaces (id,name,owner_id,settings,status) VALUES (%s,%s,101,%s::jsonb,\'active\')""", ("workspace-dream-producer-e2e","Dream Producer E2E","{}"))',
    ' c.execute("""INSERT INTO decks (id,name,name_zh,owner_id,enabled) VALUES (%s,%s,%s,101,TRUE)""", ("deck-dream-producer-e2e","Dream Producer","Dream 剧本生产"))',
    ' c.execute("""INSERT INTO voices (id,deck_id,name,name_zh,system_prompt,enabled,order_index) VALUES (%s,%s,%s,%s,%s,TRUE,0)""", ("voice-dream-producer-e2e","deck-dream-producer-e2e","Producer Agent","剧本生产 Agent","Execute only the server-authorized Dream producer step."))',
    ' c.commit()',
    ' seed_builtin_deck_plugin(c)',
  ].join('\n');
  await execute(python, ['-c', source, databaseUrl], { cwd: backendRoot, env: { ...process.env, PYTHONPATH: backendRoot } });
}

async function seedLegacyArtifactStatusBackfill(databaseUrl) {
  const source = [
    'import psycopg, sys',
    'with psycopg.connect(sys.argv[1]) as c:',
    ' c.execute("""INSERT INTO story_workspace_workspaces (id,name,owner_id,settings,status) VALUES (%s,%s,102,%s::jsonb,\'active\')""", ("workspace-artifact-backfill", "Artifact Backfill", "{}"))',
    ' c.execute("""INSERT INTO story_workspace_stories (id,identifier,title,status,review_status,type,author_id,workspace_id,artifact_source_type,source_run_id,source_thread_ref,source_project_id,episode_count,artifact_manifest_revision,script_revision,artifact_sync_status,artifact_indexed_at,script_size_bytes,artifact_available,reconcile_version) VALUES (%s,%s,%s,\'draft\',\'pending\',\'script\',102,%s,\'dream_episode\',%s,%s,%s,1,%s,%s,\'indexed\',CURRENT_TIMESTAMP,128,TRUE,1)""", ("08f3f1dd-d601-59dd-ab31-b966cfd14d52", "artifact-backfill", "Artifact Backfill", "workspace-artifact-backfill", "run_aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa", "thread-artifact-backfill", "artifact-backfill", "sha256:"+"a"*64, "sha256:"+"b"*64))',
  ].join('\n');
  await execute(python, ['-c', source, databaseUrl], { cwd: backendRoot });
}

async function verifyLegacyArtifactStatusBackfill(databaseUrl) {
  const source = [
    'import json, psycopg, sys',
    'with psycopg.connect(sys.argv[1]) as c:',
    ' row=c.execute("SELECT artifact_status,artifact_available FROM story_workspace_stories WHERE id=%s", ("08f3f1dd-d601-59dd-ab31-b966cfd14d52",)).fetchone()',
    ' assert row == ("available", True), "artifact status backfill mismatch"',
    ' validated=c.execute("""SELECT convalidated FROM pg_constraint WHERE conname=\'story_workspace_stories_artifact_status_check\'""").fetchone()',
    ' assert validated == (True,), "artifact status constraint is not validated"',
    ' print(json.dumps({"legacyArtifactStatus":row[0],"legacyCompatibilityBoolean":row[1],"artifactStatusConstraintValidated":validated[0]},separators=(",",":")))',
  ].join('\n');
  const receipt = await execute(python, ['-c', source, databaseUrl], { cwd: backendRoot });
  console.log(receipt);
}

async function verifyDreamLaunchPrerequisites(env) {
  const source = [
    'import asyncio, database, json',
    'from services.admin_gateway import resolve_platform_model_alias',
    'from services.story_workspace.dream_launch_gateway import StoryWorkspaceDreamLaunchProvisioner',
    'async def main():',
    ' model=resolve_platform_model_alias(101)',
    ' db=database.get_db()',
    ' try:',
    '  binding=await StoryWorkspaceDreamLaunchProvisioner(db).ensure_binding(deck_id="deck-dream-producer-e2e",actor_id="101",workspace_id="workspace-dream-producer-e2e")',
    '  print(json.dumps({"catalog":"callable","modelAlias":model,"deckBinding":"ready","bindingRevision":binding.binding_revision},separators=(",",":")))',
    ' finally:',
    '  db.close()',
    'asyncio.run(main())',
  ].join('\n');
  return execute(python, ['-c', source], { cwd: backendRoot, env: { ...env, PYTHONPATH: backendRoot } });
}

async function bootstrapBusiness(adminBaseUrl, providerUrl) {
  const origin = new URL(adminBaseUrl).origin;
  const bootstrap = await fetch(`${adminBaseUrl}/api/admin/auth/bootstrap`, {
    method: 'POST',
    headers: { origin, 'content-type': 'application/json', 'x-admin-bootstrap-token': bootstrapToken },
    body: JSON.stringify({ email: adminEmail, displayName: 'Dream E2E Admin', password: adminPassword }),
  });
  if (bootstrap.status !== 201) throw new Error(`Admin bootstrap failed with ${bootstrap.status}: ${await bootstrap.text()}`);
  const cookie = bootstrap.headers.getSetCookie().map((value) => value.split(';', 1)[0]).join('; ');
  const request = async (path, method = 'GET', body) => {
    const response = await fetch(`${adminBaseUrl}${path}`, {
      method,
      headers: { origin, cookie, ...(body === undefined ? {} : { 'content-type': 'application/json' }) },
      ...(body === undefined ? {} : { body: JSON.stringify(body) }),
    });
    const payload = await response.json().catch(() => ({}));
    if (response.status < 200 || response.status >= 300) {
      throw new Error(`${method} ${path} failed with ${response.status}: ${JSON.stringify(payload)}`);
    }
    return payload.data;
  };
  const platformUsers = await request('/api/admin/platform-users?sort=email&order=asc');
  const platformUserId = String(platformUsers.find((user) => user.external_user_id === '101')?.id ?? '');
  if (!platformUserId) throw new Error('Canonical Dream actor projection is missing');
  const providerRow = await request('/api/admin/providers', 'POST', {
    code: `dream-e2e-provider-${suffix}`, name: 'Dream E2E Provider', protocol: 'anthropic',
    baseUrl: providerUrl, apiKey: 'local-provider-fixture-secret', status: 'active',
    timeoutMs: 5_000, maxRetries: 0, config: { authMode: 'x-api-key' },
  });
  const modelIds = [];
  const modelAliases = [`dream-e2e-balanced-${suffix}`, `dream-e2e-fast-${suffix}`];
  for (const [code, upstreamModel, displayName] of [
    [modelAliases[0], 'dream-producer-upstream-balanced', 'Dream Balanced'],
    [modelAliases[1], 'dream-producer-upstream-fast', 'Dream Fast'],
  ]) {
    const model = await request('/api/admin/models', 'POST', {
      providerId: providerRow.id, code, upstreamModel, displayName,
      contextWindow: 100_000, maxOutputTokens: 1_024,
      capabilities: { chat: true, streaming: true }, enabled: true,
    });
    modelIds.push(model.id);
    await request('/api/admin/pricing-rules', 'POST', {
      modelId: model.id, userTier: 'free', inputPriceMicrousdPerMillion: 1_000,
      outputPriceMicrousdPerMillion: 2_000, cacheReadPriceMicrousdPerMillion: 0,
      cacheWritePriceMicrousdPerMillion: 0, markupBps: 0, discountBps: 0,
      status: 'active', effectiveFrom: new Date(Date.now() - 60_000).toISOString(), effectiveTo: null,
    });
  }
  const plan = await request('/api/admin/subscription-plans', 'POST', { code: `dream-e2e-${suffix}`, name: 'Dream E2E', description: 'Owned cross-service E2E' });
  const version = await request('/api/admin/subscription-plan-versions', 'POST', { planId: plan.id, trialDays: 0, gracePeriodDays: 0, allowanceTokens: 5_000_000 });
  for (const [index, modelId] of modelIds.entries()) {
    await request('/api/admin/subscription-entitlements', 'POST', {
      planVersionId: version.id, modelId, gatewayScopes: ['messages:create', 'models:list'],
      requestsPerMinute: 500, dailyTokenLimit: 5_000_000, monthlyTokenLimit: 5_000_000,
      storageBytesLimit: 1_000_000, isDefault: index === 0, enabled: true,
    });
  }
  await request(`/api/admin/subscription-plan-versions/${version.id}/publish`, 'POST', { idempotencyKey: `publish:${suffix}`, reason: 'Owned Dream business E2E' });
  const subscription = await request('/api/admin/subscriptions', 'POST', {
    platformUserId, planVersionId: version.id, startInTrial: false,
    idempotencyKey: `activate:${suffix}`, reason: 'Owned Dream business E2E',
  });
  const gatewayKey = await request('/api/admin/gateway-api-keys', 'POST', {
    subjectMode: 'canonical_subject', serviceClientId: gatewayClientId,
    name: 'Dream business E2E BFF', scopes: ['messages:create', 'models:list'], expiresAt: null,
  });
  return { plaintextKey: gatewayKey.plaintextKey, subscriptionId: subscription.id, platformUserId, modelAliases };
}

async function queryProducedStory(databaseUrl) {
  const source = [
    'import json, psycopg, sys',
    'from psycopg.rows import dict_row',
    'with psycopg.connect(sys.argv[1], row_factory=dict_row) as c:',
    ' rows=c.execute("""SELECT id,source_run_id,source_project_id,script_revision,artifact_status,artifact_sync_status,review_status FROM story_workspace_stories WHERE author_id=101 AND artifact_source_type=\'dream_episode\' ORDER BY updated_at DESC""").fetchall()',
    ' assert len(rows)==1, f"expected one generated Dream Story, got {len(rows)}"',
    ' row=rows[0]',
    ' assert row["artifact_status"]=="available" and row["artifact_sync_status"]=="indexed"',
    ' assert row["script_revision"] is not None',
    ' print(json.dumps(row,separators=(",",":")))',
  ].join('\n');
  return JSON.parse(await execute(python, ['-c', source, databaseUrl], { cwd: backendRoot }));
}

async function verifyCorrelation(databaseUrl) {
  const idempotencyKey = `dream-turn-${createHash('sha256').update('101\n' + process.env.INK_DREAM_E2E_THREAD_ID + '\ndream-business-e2e-turn-001').digest('hex')}`;
  const source = [
    'import json, psycopg, sys',
    'with psycopg.connect(sys.argv[1]) as c:',
    ' row=c.execute("""SELECT id,idempotency_key,outcome,status,http_status,requested_model,resolved_model,input_tokens,output_tokens,allowance_charged_tokens,subscription_id FROM gateway_requests WHERE idempotency_key=%s""",(sys.argv[2],)).fetchall()',
    ' assert len(row)==1, f"expected one correlated gateway request, got {len(row)}"',
    ' request=row[0]',
    ' ledger=c.execute("""SELECT request_sequence,entry_type,amount_tokens FROM subscription_token_ledger_entries WHERE gateway_request_id=%s ORDER BY request_sequence""",(request[0],)).fetchall()',
    ' allowance=c.execute("""SELECT reserved_tokens FROM subscription_usage_allowances WHERE subscription_id=%s""",(request[10],)).fetchall()',
    ' reserve=sum(int(x[2]) for x in ledger if x[1]=="reserve")',
    ' terminal=sum(int(x[2]) for x in ledger if x[1] in ("capture","release"))',
    ' assert request[2]=="succeeded" and request[4]==200',
    ' assert request[5]=="dream-fast" and request[6]=="dream-upstream-fast"',
    ' assert reserve==terminal and reserve>0',
    ' assert all(int(x[0])==0 for x in allowance)',
    ' print(json.dumps({"gatewayRequests":len(row),"idempotencyKey":request[1],"outcome":request[2],"httpStatus":request[4],"requestedModel":request[5],"resolvedModel":request[6],"inputTokens":int(request[7]),"outputTokens":int(request[8]),"chargedTokens":int(request[9]),"ledger":[{"sequence":int(x[0]),"type":x[1],"amount":int(x[2])} for x in ledger],"reserveEqualsTerminal":reserve==terminal,"reservedTokens":sum(int(x[0]) for x in allowance)},separators=(",",":")))',
  ].join('\n');
  return execute(python, ['-c', source, databaseUrl, idempotencyKey], { cwd: backendRoot });
}

async function diagnoseGateway(databaseUrl) {
  const source = [
    'import json, psycopg, sys',
    'with psycopg.connect(sys.argv[1]) as c:',
    ' rows=c.execute("SELECT outcome,status,http_status,COUNT(*) FROM gateway_requests GROUP BY outcome,status,http_status ORDER BY outcome,status,http_status").fetchall()',
    ' allowance=c.execute("SELECT COALESCE(SUM(reserved_tokens),0) FROM subscription_usage_allowances").fetchone()[0]',
    ' ledger=c.execute("SELECT entry_type,COUNT(*),COALESCE(SUM(amount_tokens),0) FROM subscription_token_ledger_entries GROUP BY entry_type ORDER BY entry_type").fetchall()',
    ' activity=c.execute("SELECT state,wait_event_type,wait_event,LEFT(REGEXP_REPLACE(query, %s, %s, %s),120) FROM pg_stat_activity WHERE datname=current_database() AND pid<>pg_backend_pid() ORDER BY state,wait_event_type,wait_event", ("\\\\s+", " ", "g")).fetchall()',
    ' print(json.dumps({"gatewayStates":[{"outcome":r[0],"status":r[1],"httpStatus":r[2],"count":int(r[3])} for r in rows],"reservedTokens":int(allowance),"ledger":[{"type":r[0],"count":int(r[1]),"tokens":int(r[2])} for r in ledger],"databaseActivity":[{"state":r[0],"waitType":r[1],"waitEvent":r[2],"query":r[3]} for r in activity]},separators=(",",":")))',
  ].join('\n');
  return execute(python, ['-c', source, databaseUrl], { cwd: backendRoot });
}

async function verifyBusinessGatewayState(databaseUrl, providerRequestCount) {
  const evidence = JSON.parse(await diagnoseGateway(databaseUrl));
  const gatewayRequestCount = evidence.gatewayStates.reduce(
    (total, row) => total + Number(row.count),
    0,
  );
  const ledgerByType = Object.fromEntries(
    evidence.ledger.map((row) => [row.type, { count: Number(row.count), tokens: Number(row.tokens) }]),
  );
  const succeeded = evidence.gatewayStates.length === 1
    && evidence.gatewayStates[0].outcome === 'succeeded'
    && evidence.gatewayStates[0].status === 'settled'
    && evidence.gatewayStates[0].httpStatus === 200;
  const terminalTokens = (ledgerByType.capture?.tokens ?? 0) + (ledgerByType.release?.tokens ?? 0);
  if (
    !succeeded
    || gatewayRequestCount !== providerRequestCount
    || evidence.reservedTokens !== 0
    || (ledgerByType.reserve?.count ?? 0) !== gatewayRequestCount
    || (ledgerByType.reserve?.tokens ?? 0) !== terminalTokens
  ) {
    throw new Error(`Gateway/Token settlement mismatch: ${JSON.stringify(evidence)}`);
  }
  return evidence;
}

try {
  const postgresPort = await availablePort();
  const adminPort = await availablePort();
  const dreamApiPort = await availablePort();
  const dreamWebPort = await availablePort();
  databaseUrl = `postgresql://postgres:${encodeURIComponent(postgresPassword)}@127.0.0.1:${postgresPort}/${databaseName}`;
  await execute('docker', ['run', '--detach', '--rm', '--name', containerName, '--env', 'POSTGRES_USER=postgres', '--env', `POSTGRES_PASSWORD=${postgresPassword}`, '--env', `POSTGRES_DB=${databaseName}`, '--publish', `127.0.0.1:${postgresPort}:5432`, 'postgres:16-alpine']);
  containerStarted = true;
  await waitForPostgres(databaseUrl);

  const migrationEnv = { ...process.env, DATABASE_URL: databaseUrl, TEST_DATABASE_URL: databaseUrl, INK_USE_TEST_DATABASE_URL: '1' };
  console.log('Applying the owned unified schema in the supported 0026 → Dream → Admin order...');
  await execute('node', ['scripts/migrate.mjs', '--through', '0026_harsh_victor_mancha'], { cwd: adminRoot, env: migrationEnv });
  const aclSha256 = await baselineAclSha256(databaseUrl);
  await execute(alembic, ['-c', resolve(backendRoot, 'alembic.ini'), 'upgrade', 'head'], {
    cwd: backendRoot,
    env: { ...process.env, DATABASE_URL: '', TEST_DATABASE_URL: databaseUrl, DREAM_EXPECTED_BASELINE_OWNER: 'postgres', DREAM_EXPECTED_BASELINE_ACL_SHA256: aclSha256 },
  });
  await execute('node', ['scripts/migrate.mjs', '--through', '0029_solid_garia'], { cwd: adminRoot, env: migrationEnv });
  console.log('Running rollback-only PostgreSQL runtime service integration on the owned empty clone...');
  await execute(python, [
    '-m', 'pytest', '-q',
    'tests/test_postgres_runtime_services_integration.py',
  ], {
    cwd: backendRoot,
    env: {
      ...migrationEnv,
      DATABASE_URL: '',
      TEST_DATABASE_URL: databaseUrl,
      PYTHONPATH: backendRoot,
    },
    inherit: true,
  });
  await provisionUsers(databaseUrl);
  await seedLegacyArtifactStatusBackfill(databaseUrl);
  await execute('node', ['scripts/migrate.mjs'], { cwd: adminRoot, env: migrationEnv });
  await verifyLegacyArtifactStatusBackfill(databaseUrl);
  console.log('Running Story Artifact PostgreSQL contract tests on the owned clone...');
  await execute(python, [
    '-m', 'pytest', '-q',
    'tests/test_story_workspace_artifact_story_index_postgres.py',
    'tests/test_story_workspace_artifact_story_index_reconcile.py',
  ], {
    cwd: backendRoot,
    env: {
      ...migrationEnv,
      DATABASE_URL: '',
      TEST_DATABASE_URL: databaseUrl,
      PYTHONPATH: backendRoot,
    },
    inherit: true,
  });

  provider = await startDreamProducerProvider();
  const providerUrl = provider.url;
  const adminBaseUrl = `http://127.0.0.1:${adminPort}`;
  const adminEnv = {
    ...migrationEnv, NODE_ENV: 'development', PORT: String(adminPort),
    ADMIN_CONSOLE_ENABLED: 'true', ADMIN_BOOTSTRAP_TOKEN: bootstrapToken,
    ADMIN_SESSION_SECRET: `session_${randomBytes(48).toString('base64url')}`,
    ADMIN_ORIGIN_ALLOWLIST: adminBaseUrl,
    GATEWAY_API_KEY_PEPPER: `pepper_${randomBytes(48).toString('base64url')}`,
    AI_CREDENTIAL_ENCRYPTION_KEY: randomBytes(32).toString('hex'),
    AI_PROVIDER_ALLOW_INSECURE_LOCALHOST: 'true', AI_PROVIDER_HOST_ALLOWLIST: '127.0.0.1,localhost',
    GATEWAY_SUBJECT_JWT_ISSUER: gatewayIssuer, GATEWAY_SUBJECT_JWT_AUDIENCE: gatewayAudience,
    INK_ADMIN_E2E_DIST_DIR: adminDistDir,
    ARTIFACT_WORKSPACE_ROOT: artifactRoot,
  };
  const admin = startOwned('pnpm', ['dev', '--hostname', '127.0.0.1'], { cwd: adminRoot, env: adminEnv });
  await waitForUrl(`${adminBaseUrl}/api/admin/auth/bootstrap`, admin, 'Admin Gateway');
  const fixture = await bootstrapBusiness(adminBaseUrl, providerUrl);

  const dreamApiBase = `http://127.0.0.1:${dreamApiPort}`;
  const dreamWebBase = `http://127.0.0.1:${dreamWebPort}`;
  const dreamEnv = {
    ...process.env, DATABASE_URL: databaseUrl, TEST_DATABASE_URL: databaseUrl,
    INK_USE_TEST_DATABASE_URL: '1', JWT_SECRET: `jwt_${randomBytes(48).toString('base64url')}`,
    AGENT_CWD: artifactRoot, INK_CORS_ALLOW_ORIGINS: dreamWebBase,
    INK_GATEWAY_ENABLED: '1', INK_GATEWAY_BASE_URL: adminBaseUrl,
    INK_GATEWAY_SERVICE_KEY: fixture.plaintextKey,
    INK_GATEWAY_SUBJECT_JWT_ISSUER: gatewayIssuer,
    INK_GATEWAY_SUBJECT_JWT_AUDIENCE: gatewayAudience,
    INK_GATEWAY_SERVICE_CLIENT_ID: gatewayClientId,
    INK_GATEWAY_SUBJECT_TOKEN_LIFETIME_SECONDS: '240',
    INK_GATEWAY_TEXT_MODEL_ALIAS: fixture.modelAliases[0],
    INK_ENVIRONMENT: 'test',
    INK_WORKFLOW_TOKEN_SECRET: `workflow_${randomBytes(48).toString('base64url')}`,
  };
  console.log(await verifyDreamLaunchPrerequisites(dreamEnv));
  const dreamApi = startOwned(resolve(backendRoot, '.venv/bin/uvicorn'), ['server:app', '--host', '127.0.0.1', '--port', String(dreamApiPort)], { cwd: backendRoot, env: dreamEnv });
  await waitForUrl(`${dreamApiBase}/health`, dreamApi, 'Dream FastAPI');
  const dreamWeb = startOwned('pnpm', ['exec', 'vite', '--host', '127.0.0.1', '--port', String(dreamWebPort), '--strictPort'], {
    cwd: frontendRoot,
    env: { ...dreamEnv, VITE_DEV_API_PROXY_TARGET: dreamApiBase },
  });
  await waitForUrl(dreamWebBase, dreamWeb, 'Dream Vite');

  const playwrightEnv = {
    ...dreamEnv, E2E_WEB_BASE: dreamWebBase, INK_REAL_DREAM_API_BASE: dreamApiBase,
    INK_REAL_DREAM_PG_QA: '1', INK_REAL_DREAM_BUSINESS_QA: '1',
    INK_E2E_BALANCED_ALIAS: fixture.modelAliases[0],
    INK_E2E_FAST_ALIAS: fixture.modelAliases[1],
  };
  console.log('Running real Chromium model selection and Gateway-backed Agent turn...');
  await execute('pnpm', ['exec', 'playwright', 'test', 'e2e/dream-model-postgres-real.spec.ts', '--reporter=line', '--workers=1', `--output=${outputRoot}`], { cwd: frontendRoot, env: playwrightEnv, inherit: true });
  await execute('pnpm', ['exec', 'playwright', 'test', 'e2e/dream-producer-chain-postgres-real.spec.ts', '--reporter=line', '--workers=1', `--output=${outputRoot}`], { cwd: frontendRoot, env: playwrightEnv, inherit: true });

  const producedStory = await queryProducedStory(databaseUrl);
  console.log('Running real Chromium Admin read/review against the same generated Dream Story...');
  await execute('pnpm', ['exec', 'playwright', 'test', 'e2e/admin-dream-story-generated-real.spec.ts', '--reporter=line', '--workers=1', `--output=${outputRoot}`], {
    cwd: frontendRoot,
    env: {
      ...playwrightEnv,
      INK_REAL_ADMIN_DREAM_STORY_QA: '1',
      INK_REAL_ADMIN_BASE_URL: adminBaseUrl,
      INK_REAL_ADMIN_STORY_ID: producedStory.id,
      INK_REAL_ADMIN_PROJECT_ID: producedStory.source_project_id,
      INK_REAL_ADMIN_RUN_ID: producedStory.source_run_id,
      INK_REAL_ADMIN_SCRIPT_REVISION: producedStory.script_revision,
      INK_REAL_ADMIN_EMAIL: adminEmail,
      INK_REAL_ADMIN_PASSWORD: adminPassword,
    },
    inherit: true,
  });

  const gatewayEvidence = await verifyBusinessGatewayState(databaseUrl, provider.observations.length);
  console.log(JSON.stringify({ gatewayTokenEvidence: gatewayEvidence }));
  console.log(JSON.stringify({
    providerRequests: provider.observations.length,
    providerModels: [...new Set(provider.observations.map((item) => item.model))],
    providerKinds: [...new Set(provider.observations.map((item) => item.kind))],
    allProviderRequestsBoundToRun: provider.observations.every((item) => item.hasRunId),
    database: databaseName,
    externalProviderCalls: 0,
  }));
} catch (error) {
  if (databaseUrl && containerStarted) {
    console.error(await diagnoseGateway(databaseUrl).catch(() => '{"gatewayDiagnostics":"unavailable"}'));
  }
  if (provider) {
    console.error(JSON.stringify({
      providerRequests: provider.observations.length,
      providerModels: [...new Set(provider.observations.map((item) => item.model))],
      providerKinds: [...new Set(provider.observations.map((item) => item.kind))],
      allProviderRequestsBoundToRun: provider.observations.every((item) => item.hasRunId),
      providerSequence: provider.observations.map((item) => ({
        requestNumber: item.requestNumber,
        kind: item.kind,
        step: item.step,
        toolResultEvidence: item.toolResultEvidence,
      })),
    }));
  }
  const dreamTail = ownedProcesses.find((item) => item.command.includes('uvicorn'))?.tail.join('') ?? '';
  if (dreamTail) console.error(dreamTail);
  const adminTail = ownedProcesses.find((item) => item.command === 'pnpm')?.tail.join('') ?? '';
  if (adminTail) console.error(adminTail);
  throw error;
} finally {
  await stopOwned();
  if (provider) await provider.close();
  if (containerStarted) await execute('docker', ['stop', '--time', '2', containerName]).catch(() => undefined);
  await rm(resolve(adminRoot, adminDistDir), { recursive: true, force: true });
  await rm(outputRoot, { recursive: true, force: true });
  await rm(artifactRoot, { recursive: true, force: true });
  if (await readFile(tsconfigPath, 'utf8') !== originalTsconfig) await writeFile(tsconfigPath, originalTsconfig, 'utf8');
}

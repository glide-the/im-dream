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
const frontendRoot = resolve(dreamRoot, 'frontend');
const python = resolve(backendRoot, '.venv/bin/python');
const pgIsReady = '/opt/homebrew/opt/libpq/bin/pg_isready';
const sourcePostgresContainer = 'ink-memory-postgres';
const targetModelAlias = String(
  process.env.INK_REAL_DREAM_MODEL_ALIAS ?? '',
).trim();
const expectedUpstreamModel = String(
  process.env.INK_REAL_DREAM_EXPECTED_UPSTREAM_MODEL ?? '',
).trim();
const modelIdentifier = /^[A-Za-z0-9][A-Za-z0-9._:-]{0,119}$/;
if (
  !modelIdentifier.test(targetModelAlias)
  || !modelIdentifier.test(expectedUpstreamModel)
) {
  throw new Error(
    'INK_REAL_DREAM_MODEL_ALIAS and INK_REAL_DREAM_EXPECTED_UPSTREAM_MODEL are required',
  );
}
const suffix = randomBytes(6).toString('hex');
const runLabel = `ink-r22-real-model-${suffix}`;
const databaseName = `ink_memory_r22_${suffix}_test`;
const containerName = `${runLabel}-postgres`;
const volumeName = `${runLabel}-pgdata`;
const postgresPassword = `pg_${randomBytes(24).toString('base64url')}`;
const testAccountEmail = String(
  process.env.INK_REAL_DREAM_ACCOUNT_EMAIL ?? '',
).trim().toLowerCase();
if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(testAccountEmail)) {
  throw new Error('INK_REAL_DREAM_ACCOUNT_EMAIL must name the existing account under test');
}
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
const launchReceiptPath = join(runtimeRoot, 'accepted-run.json');
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
  const tail = [];
  const collect = (chunk) => {
    tail.push(String(chunk));
    if (tail.length > 160) tail.shift();
  };
  child.stdout.on('data', collect);
  child.stderr.on('data', collect);
  ownedProcesses.push({ child, command, tail });
  return child;
}

function safeProcessTail(value) {
  return String(value)
    .replace(/Bearer\s+[A-Za-z0-9._~-]+/gi, 'Bearer [REDACTED]')
    .replace(/postgres(?:ql)?:\/\/[^\s]+/gi, '[REDACTED_DATABASE_URL]')
    .replace(/eyJ[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+/g, '[REDACTED_JWT]')
    .slice(-12_000);
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

async function verifyAdminProductPlans(
  baseUrl,
  canonicalUserId,
  configuration,
) {
  const requestId = `r22_product_${suffix}`;
  const source = [
    'import json,os,re,sys',
    'from datetime import UTC,datetime',
    'import httpx,jwt',
    'from pydantic import ValidationError',
    'from services.admin_product.models import PlansEnvelope',
    'now=int(datetime.now(UTC).timestamp())',
    'token=jwt.encode({"sub":sys.argv[2],"iss":os.environ["INK_R22_PRODUCT_ISSUER"],"aud":os.environ["INK_R22_PRODUCT_AUDIENCE"],"client_id":os.environ["INK_R22_PRODUCT_CLIENT_ID"],"scope":"product:read","iat":now,"exp":now+240,"jti":sys.argv[3]},os.environ["INK_R22_PRODUCT_SECRET"],algorithm="HS256")',
    'try:',
    ' response=httpx.get(sys.argv[1]+"/api/product/v1/plans",params={"page":1,"pageSize":20},headers={"accept":"application/json","authorization":"Bearer "+token,"x-request-id":sys.argv[3]},timeout=15,follow_redirects=False,trust_env=False)',
    ' try: payload=response.json()',
    ' except (ValueError,UnicodeError): payload={}',
    ' error=payload.get("error") if isinstance(payload,dict) else None',
    ' code=error.get("code") if isinstance(error,dict) else None',
    ' meta=payload.get("meta") if isinstance(payload,dict) else None',
    ' data=payload.get("data") if isinstance(payload,dict) else None',
    ' safe_code=code if isinstance(code,str) and re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._:-]{0,199}",code) else None',
    ' issues=[]',
    ' try: PlansEnvelope.model_validate(payload); contract_valid=True',
    ' except ValidationError as exc: contract_valid=False; issues=[{"path":".".join(str(item) for item in issue.get("loc",())),"type":str(issue.get("type","invalid"))} for issue in exc.errors()[:8]]',
    ' print(json.dumps({"status":response.status_code,"errorCode":safe_code,"requestIdMatches":isinstance(meta,dict) and meta.get("requestId")==sys.argv[3],"planCount":len(data) if isinstance(data,list) else None,"contractValid":contract_valid,"issues":issues},separators=(",",":")))',
    'except httpx.HTTPError:',
    ' print(json.dumps({"status":None,"errorCode":"PRODUCT_ROUTE_UNREACHABLE","requestIdMatches":False,"planCount":None},separators=(",",":")))',
  ].join('\n');
  const result = JSON.parse(await execute(python, [
    '-c', source, baseUrl, canonicalUserId, requestId,
  ], {
    cwd: backendRoot,
    env: {
      ...process.env,
      INK_R22_PRODUCT_SECRET: configuration.jwtSecret,
      INK_R22_PRODUCT_ISSUER: configuration.jwtIssuer,
      INK_R22_PRODUCT_AUDIENCE: configuration.jwtAudience,
      INK_R22_PRODUCT_CLIENT_ID: configuration.clientId,
    },
  }));
  if (
    result.status !== 200
    || result.requestIdMatches !== true
    || !Number.isInteger(result.planCount)
    || result.contractValid !== true
  ) {
    console.error(JSON.stringify({
      phase: 'isolated-admin-product-contract',
      status: result.status,
      errorCode: result.errorCode,
      requestIdMatches: result.requestIdMatches === true,
      contractValid: result.contractValid === true,
      issues: Array.isArray(result.issues) ? result.issues : [],
    }));
    throw new Error('isolated Admin Product plans contract is unavailable');
  }
  return result;
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

async function resolveCloneAccount(databaseUrl) {
  const source = [
    'import json,os,psycopg,sys',
    'with psycopg.connect(os.environ["INK_R24_DATABASE_URL"], options="-c default_transaction_read_only=on") as c:',
    ' row=c.execute("""SELECT canonical.id,projection.id,canonical.status,projection.status FROM users canonical JOIN platform_users projection ON projection.source=\'ink-dream\' AND projection.external_user_id=canonical.id::text WHERE lower(canonical.email)=lower(%s)""",(sys.argv[1],)).fetchone()',
    ' assert row is not None and row[2]=="active" and row[3]=="active"',
    ' print(json.dumps({"canonicalUserId":str(row[0]),"platformUserId":str(row[1]),"existingAccountResolved":True},separators=(",",":")))',
  ].join('\n');
  return JSON.parse(await execute(
    python,
    ['-c', source, testAccountEmail],
    { cwd: backendRoot, env: { ...process.env, INK_R24_DATABASE_URL: databaseUrl } },
  ));
}

async function provisionCloneDreamSurface(databaseUrl, canonicalUserId) {
  const workspaceId = `workspace-r44-${suffix}`;
  const deckId = `deck-r44-${suffix}`;
  const voiceId = `voice-r44-${suffix}`;
  const source = [
    'import json,os,psycopg,sys',
    'try:',
    ' with psycopg.connect(os.environ["INK_R44_DATABASE_URL"]) as c:',
    '  c.execute("""INSERT INTO story_workspace_workspaces (id,name,owner_id,settings,status) VALUES (%s,%s,%s,%s::jsonb,\'active\')""",(sys.argv[2],"Real Model Dream Clone",int(sys.argv[1]),"{}"))',
    '  c.execute("""INSERT INTO decks (id,name,name_zh,owner_id,enabled) VALUES (%s,%s,%s,%s,TRUE)""",(sys.argv[3],"Real Model Dream","真实模型 Dream",int(sys.argv[1])))',
    '  c.execute("""INSERT INTO voices (id,deck_id,name,name_zh,system_prompt,enabled,order_index) VALUES (%s,%s,%s,%s,%s,TRUE,0)""",(sys.argv[4],sys.argv[3],"Dream Producer","Dream 剧本 Agent","Execute the server-authorized Dream producer workflow."))',
    ' print(json.dumps({"ok":True,"workspaceId":sys.argv[2],"deckId":sys.argv[3],"voiceId":sys.argv[4]},separators=(",",":")))',
    'except Exception as exc:',
    ' diagnostic=getattr(exc,"diag",None)',
    ' print(json.dumps({"ok":False,"errorClass":type(exc).__name__,"sqlstate":getattr(exc,"sqlstate",None),"constraint":getattr(diagnostic,"constraint_name",None)},separators=(",",":")))',
  ].join('\n');
  const result = JSON.parse(await execute(
    python,
    ['-c', source, canonicalUserId, workspaceId, deckId, voiceId],
    {
      cwd: backendRoot,
      env: {
        ...process.env,
        PYTHONPATH: backendRoot,
        INK_R44_DATABASE_URL: databaseUrl,
      },
    },
  ));
  if (result.ok !== true) {
    console.error(JSON.stringify({
      phase: 'clone-dream-surface-provision-detail',
      errorClass: result.errorClass ?? 'Error',
      sqlstate: result.sqlstate ?? null,
      constraint: result.constraint ?? null,
    }));
    throw new Error(`clone Dream surface provision failed: ${result.errorClass ?? 'Error'}:${result.sqlstate ?? 'unknown'}:${result.constraint ?? 'unknown'}`);
  }
  return {
    workspaceId: result.workspaceId,
    deckId: result.deckId,
    voiceId: result.voiceId,
  };
}

async function verifyCloneDreamLaunch(databaseUrl, canonicalUserId, platformUserId) {
  const source = [
    'import json,os,psycopg,sys',
    'with psycopg.connect(os.environ["INK_R44_DATABASE_URL"], options="-c default_transaction_read_only=on") as c:',
    ' run=c.execute("""SELECT id,status,status_version,source_voice_thread_id,runtime_load_receipt_id,agent_session_id FROM workflow_runs WHERE created_by=%s AND workspace_id=%s ORDER BY created_at DESC""",(sys.argv[1],sys.argv[3])).fetchall()',
    ' assert len(run)==1',
    ' run=run[0]',
    ' assert run[1]=="pending_review" and run[3] and run[4] and run[5]',
    ' sessions=c.execute("""SELECT status,deployment_tier,runtime_environment_id,runtime_pool_id,runtime_node_id,distribution_mode FROM agent_sessions WHERE workflow_run_id=%s""",(run[0],)).fetchall()',
    ' assert len(sessions)==1 and sessions[0]==("terminated","local","ink-local","ink-local","local","local_persistent")',
    ' receipts=c.execute("""SELECT deployment_tier,runtime_environment_id,runtime_pool_id,runtime_node_id,distribution_mode FROM runtime_load_receipts WHERE workflow_run_id=%s""",(run[0],)).fetchall()',
    ' assert len(receipts)>=1 and all(row==("local","ink-local","ink-local","local","local_persistent") for row in receipts)',
    ' requests=c.execute("""SELECT status,outcome,http_status,requested_model,resolved_model,response_summary->>\'model\',settled_at IS NOT NULL FROM gateway_requests WHERE platform_user_id=%s ORDER BY created_at""",(sys.argv[2],)).fetchall()',
    ' assert len(requests)>=1',
    ' assert all(row[0]=="settled" and row[1]=="succeeded" and row[2]==200 and row[3]==sys.argv[4] and row[4]==sys.argv[5] and row[5]==sys.argv[5] and row[6] for row in requests)',
    ' reserved=c.execute("""SELECT COALESCE(SUM(reserved_tokens),0) FROM subscription_usage_allowances WHERE platform_user_id=%s""",(sys.argv[2],)).fetchone()[0]',
    ' assert int(reserved)==0',
    ' messages=c.execute("SELECT role,COUNT(*) FROM chat_message WHERE thread_id=%s GROUP BY role",(run[3],)).fetchall()',
    ' counts={role:int(count) for role,count in messages}',
    ' assert counts.get("user",0)>=1 and counts.get("assistant",0)>=1',
    ' terminals=c.execute("SELECT COUNT(*) FROM workflow_run_transitions WHERE workflow_run_id=%s AND to_status IN (\'completed\',\'failed\',\'cancelled\')",(run[0],)).fetchone()[0]',
    ' assert int(terminals)==0',
    ' print(json.dumps({"workflowRunId":run[0],"workflowStatus":run[1],"statusVersion":int(run[2]),"threadId":run[3],"agentSessionStatus":sessions[0][0],"placement":{"tier":sessions[0][1],"environment":sessions[0][2],"pool":sessions[0][3],"node":sessions[0][4],"distribution":sessions[0][5]},"gatewayRequestCount":len(requests),"requestedAlias":requests[0][3],"resolvedUpstream":requests[0][4],"gatewaySettled":True,"reservedTokens":int(reserved),"messageRoleCounts":counts,"workflowTerminalTransitions":int(terminals)},separators=(",",":"),sort_keys=True))',
  ].join('\n');
  return JSON.parse(await execute(
    python,
    ['-c', source, canonicalUserId, platformUserId, `workspace-r44-${suffix}`, targetModelAlias, expectedUpstreamModel],
    {
      cwd: backendRoot,
      env: { ...process.env, INK_R44_DATABASE_URL: databaseUrl },
    },
  ));
}

async function readLaunchReceipt() {
  try {
    const value = JSON.parse(await readFile(launchReceiptPath, 'utf8'));
    if (
      !value
      || typeof value !== 'object'
      || !/^run_[0-9a-f]{32}$/.test(String(value.workflowRunId ?? ''))
      || !/^[0-9a-f-]{36}$/.test(String(value.threadId ?? ''))
    ) return null;
    return value;
  } catch {
    return null;
  }
}

async function diagnoseCloneDreamFailure(databaseUrl, launchReceipt) {
  if (!launchReceipt) {
    return {
      receiptPresent: false,
      runPresent: false,
      browserReceipt: null,
    };
  }
  const source = [
    'import json,os,psycopg,sys',
    'with psycopg.connect(os.environ["INK_R44_DATABASE_URL"], options="-c default_transaction_read_only=on") as c:',
    ' run=c.execute("""SELECT id,status,status_version,failed_step,error_code,source_voice_thread_id,agent_session_id FROM workflow_runs WHERE id=%s""",(sys.argv[1],)).fetchone()',
    ' if run is None: print(json.dumps({"receiptPresent":bool(sys.argv[1]),"runPresent":False},separators=(",",":"))); raise SystemExit(0)',
    ' transitions=c.execute("""SELECT transition_seq,from_status,to_status,reason_code,failed_step,error_code FROM workflow_run_transitions WHERE workflow_run_id=%s ORDER BY transition_seq""",(run[0],)).fetchall()',
    ' sessions=c.execute("""SELECT status,error_code,termination_reason_code,deployment_tier,runtime_environment_id,runtime_pool_id,runtime_node_id FROM agent_sessions WHERE workflow_run_id=%s ORDER BY attempt_number""",(run[0],)).fetchall()',
    ' gateway=c.execute("""SELECT status,outcome,http_status,error_code,requested_model,resolved_model,COUNT(*) FROM gateway_requests WHERE platform_user_id IN (SELECT id FROM platform_users WHERE source=\'ink-dream\' AND external_user_id=(SELECT created_by FROM workflow_runs WHERE id=%s)) GROUP BY status,outcome,http_status,error_code,requested_model,resolved_model ORDER BY status,outcome,http_status,error_code""",(run[0],)).fetchall()',
    ' messages=c.execute("SELECT role,COUNT(*) FROM chat_message WHERE thread_id=%s GROUP BY role ORDER BY role",(run[5],)).fetchall() if run[5] else []',
    ' thread=c.execute("SELECT claude_session_id IS NOT NULL,agent_contract_version IS NOT NULL FROM chat_thread WHERE id=%s",(run[5],)).fetchone() if run[5] else None',
    ' print(json.dumps({"receiptPresent":bool(sys.argv[1]),"runPresent":True,"run":{"status":run[1],"statusVersion":int(run[2]),"failedStep":run[3],"errorCode":run[4],"threadPresent":bool(run[5]),"threadMatchesReceipt":bool(sys.argv[2]) and run[5]==sys.argv[2],"sessionPresent":bool(run[6])},"transitions":[{"sequence":int(row[0]),"from":row[1],"to":row[2],"reasonCode":row[3],"failedStep":row[4],"errorCode":row[5]} for row in transitions],"sessions":[{"status":row[0],"errorCode":row[1],"terminationReason":row[2],"tier":row[3],"environment":row[4],"pool":row[5],"node":row[6]} for row in sessions],"gateway":[{"status":row[0],"outcome":row[1],"httpStatus":row[2],"errorCode":row[3],"requestedModel":row[4],"resolvedModel":row[5],"count":int(row[6])} for row in gateway],"messageRoles":{row[0]:int(row[1]) for row in messages},"thread":{"present":thread is not None,"sdkSessionPresent":bool(thread and thread[0]),"agentContractPresent":bool(thread and thread[1])}},separators=(",",":"),sort_keys=True))',
  ].join('\n');
  const databaseEvidence = JSON.parse(await execute(python, [
    '-c', source,
    launchReceipt?.workflowRunId ?? '',
    launchReceipt?.threadId ?? '',
  ], {
    cwd: backendRoot,
    env: { ...process.env, INK_R44_DATABASE_URL: databaseUrl },
  }));
  const safeBrowserReceipt = launchReceipt ? {
    runStatus: String(launchReceipt.runStatus ?? 'unknown'),
    runErrorCode: typeof launchReceipt.runErrorCode === 'string'
      ? launchReceipt.runErrorCode
      : null,
    runRevision: Number(launchReceipt.runRevision ?? 0),
    canConfirm: launchReceipt.canConfirm === true,
    stages: Object.fromEntries(Object.entries(launchReceipt.stages ?? {}).map(
      ([stage, value]) => [stage, {
        revision: Number(value?.revision ?? 0),
        itemCount: Number(value?.itemCount ?? 0),
      }],
    )),
  } : null;
  return { ...databaseEvidence, browserReceipt: safeBrowserReceipt };
}

async function verifyCloneModel(databaseUrl) {
  const source = [
    'import json,os,psycopg,sys',
    'with psycopg.connect(os.environ["INK_R24_DATABASE_URL"], options="-c default_transaction_read_only=on") as c:',
    ' rows=c.execute("""SELECT m.code,m.upstream_model,m.enabled,p.protocol,p.status,(p.api_key_ciphertext IS NOT NULL AND p.api_key_iv IS NOT NULL AND p.api_key_tag IS NOT NULL),COUNT(pr.id) FILTER (WHERE pr.status=\'active\' AND pr.effective_from<=now() AND (pr.effective_to IS NULL OR pr.effective_to>now())),COUNT(e.id) FILTER (WHERE e.enabled AND e.gateway_scopes @> ARRAY[\'messages:create\']::text[] AND v.status=\'published\') FROM ai_models m JOIN ai_providers p ON p.id=m.provider_id LEFT JOIN ai_pricing_rules pr ON pr.model_id=m.id LEFT JOIN subscription_plan_entitlements e ON e.model_id=m.id LEFT JOIN subscription_plan_versions v ON v.id=e.plan_version_id WHERE m.code=%s AND m.upstream_model=%s GROUP BY m.id,p.id""",(sys.argv[1],sys.argv[2])).fetchall()',
    ' assert len(rows)==1',
    ' row=rows[0]',
    ' assert row[2] and row[4]=="active" and row[5] and int(row[6])>0',
    ' print(json.dumps({"alias":row[0],"upstream":row[1],"enabled":bool(row[2]),"protocol":row[3],"providerActive":row[4]=="active","credentialReady":bool(row[5]),"activePricing":int(row[6]),"publishedEntitlements":int(row[7])},separators=(",",":")))',
  ].join('\n');
  return JSON.parse(await execute(
    python,
    ['-c', source, targetModelAlias, expectedUpstreamModel],
    { cwd: backendRoot, env: { ...process.env, INK_R24_DATABASE_URL: databaseUrl } },
  ));
}

async function verifyCloneEffectiveLimits(databaseUrl, platformUserId) {
  const source = [
    'import json,os,psycopg,sys',
    'with psycopg.connect(os.environ["INK_R44_DATABASE_URL"], options="-c default_transaction_read_only=on") as c:',
    ' row=c.execute("""SELECT plan.code,entitlement.id,entitlement.requests_per_minute,entitlement.daily_token_limit,entitlement.monthly_token_limit,permission.enabled,permission.requests_per_minute,permission.daily_token_limit,permission.monthly_token_limit,allowance.granted_tokens+allowance.bonus_granted_tokens-allowance.reserved_tokens-allowance.consumed_tokens,platform_user.daily_token_limit,platform_user.monthly_token_limit FROM subscriptions subscription JOIN subscription_plan_versions version ON version.id=subscription.plan_version_id JOIN subscription_plans plan ON plan.id=version.plan_id JOIN ai_models model ON model.code=%s JOIN platform_users platform_user ON platform_user.id=subscription.platform_user_id LEFT JOIN subscription_plan_entitlements entitlement ON entitlement.plan_version_id=version.id AND entitlement.model_id=model.id AND entitlement.enabled AND entitlement.gateway_scopes @> ARRAY[\'messages:create\']::text[] LEFT JOIN user_model_permissions permission ON permission.platform_user_id=subscription.platform_user_id AND permission.model_id=model.id LEFT JOIN subscription_usage_allowances allowance ON allowance.subscription_id=subscription.id AND allowance.period_start=subscription.current_period_start AND allowance.period_end=subscription.current_period_end WHERE subscription.platform_user_id=%s AND subscription.status IN (\'active\',\'trial\',\'cancel_at_period_end\')""",(sys.argv[2],sys.argv[1])).fetchone()',
    ' assert row is not None',
    ' assert row[5] is not False and row[9] is not None and int(row[9])>0',
    ' print(json.dumps({"planCode":row[0],"accessMode":"plan-entitlement" if row[1] is not None else "allowance-only","entitlementRpm":row[2],"entitlementDailyTokens":row[3],"entitlementMonthlyTokens":row[4],"userPermissionEnabled":row[5],"userModelRpm":row[6],"userModelDailyTokens":row[7],"userModelMonthlyTokens":row[8],"allowanceRemainingTokens":int(row[9]),"principalDailyTokens":int(row[10]) if row[10] is not None else None,"principalMonthlyTokens":int(row[11]) if row[11] is not None else None},separators=(",",":")))',
  ].join('\n');
  return JSON.parse(await execute(
    python,
    ['-c', source, platformUserId, targetModelAlias],
    { cwd: backendRoot, env: { ...process.env, INK_R44_DATABASE_URL: databaseUrl } },
  ));
}

async function inspectCloneAccountDreamHistory(databaseUrl, canonicalUserId) {
  const source = [
    'import json,os,psycopg,sys',
    'with psycopg.connect(os.environ["INK_R24_DATABASE_URL"], options="-c default_transaction_read_only=on") as c:',
    ' count=c.execute("""SELECT COUNT(*) FROM workflow_runs AS run JOIN chat_thread AS thread ON thread.id=run.source_voice_thread_id WHERE thread.user_id=%s AND run.status IN (\'completed\',\'failed\',\'cancelled\') AND run.source_voice_thread_id IS NOT NULL""",(int(sys.argv[1]),)).fetchone()[0]',
    ' print(json.dumps({"existingTerminalDreamThreads":int(count)},separators=(",",":")))',
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
  'INK_ADMIN_PRODUCT_JWT_ISSUER',
  'INK_ADMIN_PRODUCT_JWT_AUDIENCE',
  'INK_ADMIN_PRODUCT_CLIENT_ID',
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
  const dreamWebPort = await availablePort();
  ownedPorts = [postgresPort, adminPort, dreamApiPort, dreamWebPort];
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

  runPhase = 'clone-existing-account-resolution';
  const cloneUser = await resolveCloneAccount(targetDatabaseUrl);
  runPhase = 'clone-dream-surface-provision';
  const dreamSurface = await provisionCloneDreamSurface(
    targetDatabaseUrl,
    cloneUser.canonicalUserId,
  );
  runPhase = 'clone-model-contract';
  const modelEvidence = await verifyCloneModel(targetDatabaseUrl);
  runPhase = 'clone-account-history-inspection';
  const accountHistoryEvidence = await inspectCloneAccountDreamHistory(
    targetDatabaseUrl,
    cloneUser.canonicalUserId,
  );
  const adminBaseUrl = `http://127.0.0.1:${adminPort}`;
  const dreamApiBase = `http://127.0.0.1:${dreamApiPort}`;
  const dreamWebBase = `http://127.0.0.1:${dreamWebPort}`;
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
  runPhase = 'isolated-admin-product-contract';
  const productPlansEvidence = await verifyAdminProductPlans(
    adminBaseUrl,
    cloneUser.canonicalUserId,
    {
      jwtSecret: backendFileEnv.INK_ADMIN_PRODUCT_JWT_SECRET,
      jwtIssuer: backendFileEnv.INK_ADMIN_PRODUCT_JWT_ISSUER,
      jwtAudience: backendFileEnv.INK_ADMIN_PRODUCT_JWT_AUDIENCE,
      clientId: backendFileEnv.INK_ADMIN_PRODUCT_CLIENT_ID,
    },
  );

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
    INK_WORKFLOW_TOKEN_SECRET: `workflow_${randomBytes(48).toString('base64url')}`,
    INK_CORS_ALLOW_ORIGINS: dreamWebBase,
    INK_DECK_HOST_COMPATIBLE: '1',
    INK_CLAUDE_AGENT_CONTRACT_COMPATIBLE: '1',
    INK_STORY_SCHEMA_COMPATIBLE: '1',
    INK_DECK_RUNTIME_CONFIG_COMPATIBLE: '1',
    ANTHROPIC_API_KEY: '',
    ANTHROPIC_AUTH_TOKEN: '',
    CLAUDE_CODE_OAUTH_TOKEN: '',
    CLAUDE_CONFIG_DIR: '',
  };
  const dreamApi = startOwned(resolve(backendRoot, '.venv/bin/uvicorn'), [
    'server:app', '--host', '127.0.0.1', '--port', String(dreamApiPort),
  ], { cwd: backendRoot, env: dreamEnv });
  await waitForUrl(`${dreamApiBase}/api/health`, dreamApi, 'isolated Dream API');

  runPhase = 'provider-free-contract-preflight';
  await execute(python, ['script/verify_gateway_e2e.py'], {
    cwd: backendRoot,
    env: {
      ...dreamEnv,
      INK_GATEWAY_E2E_EMAIL: testAccountEmail,
      INK_GATEWAY_E2E_DREAM_BASE_URL: dreamApiBase,
      INK_GATEWAY_E2E_MODEL_ALIAS: targetModelAlias,
      INK_GATEWAY_E2E_EXPECTED_UPSTREAM_MODEL: expectedUpstreamModel,
      INK_GATEWAY_E2E_PROVISION_SUBSCRIPTION: '0',
      INK_GATEWAY_E2E_PRODUCT_ORIGIN: productOrigin,
      INK_GATEWAY_E2E_PREFLIGHT_ONLY: '1',
    },
    inherit: true,
  });
  const effectiveLimits = await verifyCloneEffectiveLimits(
    targetDatabaseUrl,
    cloneUser.platformUserId,
  );

  let browserEvidence = null;
  if (!preflightOnly) {
    runPhase = 'real-model-headed-dream-launch';
    const dreamWeb = startOwned(
      'pnpm',
      ['exec', 'vite', '--host', '127.0.0.1', '--port', String(dreamWebPort), '--strictPort'],
      {
        cwd: frontendRoot,
        env: { ...dreamEnv, VITE_DEV_API_PROXY_TARGET: dreamApiBase },
      },
    );
    await waitForUrl(dreamWebBase, dreamWeb, 'isolated Dream web');
    await execute('pnpm', [
      'exec', 'playwright', 'test', 'e2e/dream-launch-real-model.spec.ts',
      '--headed', '--workers=1', '--reporter=line',
      `--output=${join(runtimeRoot, 'playwright-output')}`,
    ], {
      cwd: frontendRoot,
      env: {
        ...dreamEnv,
        E2E_WEB_BASE: dreamWebBase,
        INK_REAL_DREAM_API_BASE: dreamApiBase,
        INK_REAL_DREAM_LAUNCH_QA: '1',
        INK_REAL_DREAM_LAUNCH_EMAIL: testAccountEmail,
        INK_REAL_DREAM_LAUNCH_DECK_ID: dreamSurface.deckId,
        INK_REAL_DREAM_LAUNCH_RECEIPT_PATH: launchReceiptPath,
      },
      inherit: true,
    });
    browserEvidence = await verifyCloneDreamLaunch(
      targetDatabaseUrl,
      cloneUser.canonicalUserId,
      cloneUser.platformUserId,
    );
  }

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
    existingAccountResolved: cloneUser.existingAccountResolved === true,
    existingPlatformProjectionResolved: Boolean(cloneUser.platformUserId),
    dreamSurface,
    accountHistory: accountHistoryEvidence,
    productPlans: productPlansEvidence,
    adminRuntimeCheckout: 'isolated-head-clone',
    adminBundler: 'webpack-isolated-external-dependency-link',
    model: modelEvidence,
    effectiveLimits,
    preflightOnly,
    browser: preflightOnly ? 'provider-free' : 'headed-chromium-workers-1',
    dreamLaunch: browserEvidence,
  };
} catch (error) {
  runError = error;
  failedPhase = runPhase;
  if (targetDatabaseUrl) {
    const launchReceipt = await readLaunchReceipt();
    const failureEvidence = await diagnoseCloneDreamFailure(
      targetDatabaseUrl,
      launchReceipt,
    )
      .catch(() => ({ unavailable: true }));
    console.error(JSON.stringify({ phase: 'clone-dream-failure-evidence', failureEvidence }));
  }
  const failedProcesses = ownedProcesses
    .filter((item) => item.child.exitCode !== null || item.child.signalCode !== null)
    .map((item) => ({
      command: item.command,
      exitCode: item.child.exitCode,
      signal: item.child.signalCode,
      tail: safeProcessTail(item.tail.join('')),
    }));
  if (failedProcesses.length > 0) {
    console.error(JSON.stringify({ phase: 'owned-process-diagnostics', failedProcesses }));
  }
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

// [Input] Explicit official MCP App artifact roots and test-owned loopback policy endpoints.
// [Output] Owned official processes, an auditable upstream relay, and a fake Python connection-view service.
// [Pos] Provider-free Phase 1-3 Node harness; never imported by production or connected to real business data.
// [Sync] 2026-09-06: exercise official artifacts through the real Runtime with actor/workspace policy revalidation.

import { spawn } from 'node:child_process';
import { createHash } from 'node:crypto';
import { createServer } from 'node:http';
import { readFile } from 'node:fs/promises';
import { createServer as createNetServer } from 'node:net';
import path from 'node:path';


const LOOPBACK_HOST = '127.0.0.1';
const HOP_BY_HOP_HEADERS = new Set([
  'connection',
  'content-length',
  'keep-alive',
  'proxy-authenticate',
  'proxy-authorization',
  'te',
  'trailer',
  'transfer-encoding',
  'upgrade',
]);


async function listen(server, port = 0) {
  await new Promise((resolve, reject) => {
    server.once('error', reject);
    server.listen(port, LOOPBACK_HOST, resolve);
  });
  const address = server.address();
  if (address === null || typeof address === 'string') {
    throw new Error('Could not resolve an isolated loopback listener.');
  }
  return `http://${LOOPBACK_HOST}:${address.port}`;
}


async function closeServer(server) {
  await new Promise((resolve, reject) => server.close((error) => (
    error ? reject(error) : resolve()
  )));
}


async function readBody(request) {
  const chunks = [];
  for await (const chunk of request) chunks.push(chunk);
  return Buffer.concat(chunks);
}


function writeFetchResponse(fetchResponse, response, body) {
  response.statusCode = fetchResponse.status;
  for (const [name, value] of fetchResponse.headers) {
    if (!HOP_BY_HOP_HEADERS.has(name.toLowerCase())) response.setHeader(name, value);
  }
  response.end(body);
}


function parseRpcMethod(body) {
  try {
    const parsed = JSON.parse(body.toString('utf8'));
    return typeof parsed?.method === 'string' ? parsed.method : null;
  } catch {
    return null;
  }
}


export async function reserveEphemeralPort() {
  const server = createNetServer();
  const origin = await listen(server);
  const port = Number(new URL(origin).port);
  await closeServer(server);
  return port;
}


export async function startOfficialArtifact({ artifactRoot, expectedVersion }) {
  if (!path.isAbsolute(artifactRoot)) {
    throw new Error('The official MCP App artifact root must be absolute.');
  }
  const manifestPath = path.join(artifactRoot, 'manifest.json');
  const packageRoot = path.join(
    artifactRoot,
    'offline-consumer',
    'node_modules',
    '@modelcontextprotocol',
    'server-basic-vanillajs',
  );
  const [manifest, packageJson] = await Promise.all([
    readFile(manifestPath, 'utf8').then(JSON.parse),
    readFile(path.join(packageRoot, 'package.json'), 'utf8').then(JSON.parse),
  ]);
  const tarballRecord = Array.isArray(manifest.files)
    ? manifest.files.find((item) => typeof item?.name === 'string' && item.name.endsWith('.tgz'))
    : null;
  const tarballName = tarballRecord?.name ?? manifest.tarball;
  const expectedTarballSha256 = tarballRecord?.sha256 ?? manifest.tarballSha256;
  const manifestPackage = manifest.package ?? manifest.artifact;
  if (manifestPackage !== '@modelcontextprotocol/server-basic-vanillajs'
    || manifest.version !== expectedVersion
    || packageJson.name !== manifestPackage
    || packageJson.version !== expectedVersion
    || manifest.sourceRepository !== 'https://github.com/modelcontextprotocol/ext-apps'
    || manifest.sourceTag !== `v${expectedVersion}`
    || !/^[a-f0-9]{40}$/.test(manifest.sourceCommit)
    || typeof tarballName !== 'string'
    || !/^[a-f0-9]{64}$/.test(expectedTarballSha256)) {
    throw new Error(`Official MCP App artifact ${expectedVersion} failed provenance validation.`);
  }
  const actualTarballSha256 = createHash('sha256')
    .update(await readFile(path.join(artifactRoot, tarballName)))
    .digest('hex');
  if (actualTarballSha256 !== expectedTarballSha256) {
    throw new Error(`Official MCP App artifact ${expectedVersion} failed digest validation.`);
  }
  const port = await reserveEphemeralPort();
  const entry = path.join(packageRoot, 'dist', 'index.js');
  const stdout = [];
  const stderr = [];
  const child = spawn(process.execPath, [entry], {
    cwd: packageRoot,
    env: { ...process.env, PORT: String(port) },
    stdio: ['ignore', 'pipe', 'pipe'],
  });
  child.stdout.on('data', (chunk) => stdout.push(chunk.toString('utf8')));
  child.stderr.on('data', (chunk) => stderr.push(chunk.toString('utf8')));
  try {
    await new Promise((resolve, reject) => {
      const timeout = setTimeout(() => {
        reject(new Error(`Official MCP App ${expectedVersion} did not start. ${stderr.join('')}`));
      }, 10_000);
      const inspect = () => {
        if (!stdout.join('').includes('MCP server listening on')) return;
        clearTimeout(timeout);
        child.off('exit', onExit);
        child.stdout.off('data', inspect);
        resolve();
      };
      const onExit = (code) => {
        clearTimeout(timeout);
        child.stdout.off('data', inspect);
        reject(new Error(`Official MCP App ${expectedVersion} exited with ${code}. ${stderr.join('')}`));
      };
      child.once('exit', onExit);
      child.stdout.on('data', inspect);
    });
  } catch (error) {
    if (child.exitCode === null && child.signalCode === null) child.kill('SIGTERM');
    throw error;
  }
  let closed = false;
  return {
    artifactRoot,
    expectedVersion,
    manifest,
    endpointUrl: `http://${LOOPBACK_HOST}:${port}/mcp`,
    logs: { stdout, stderr },
    async close() {
      if (closed) return;
      closed = true;
      if (child.exitCode !== null || child.signalCode !== null) return;
      const exited = new Promise((resolve) => child.once('exit', resolve));
      child.kill('SIGTERM');
      await Promise.race([
        exited,
        new Promise((_, reject) => setTimeout(
          () => reject(new Error(`Official MCP App ${expectedVersion} did not stop.`)),
          5_000,
        )),
      ]);
    },
  };
}


export async function startAuditedUpstreamRelay({ targetEndpointUrl, upstreamSecret }) {
  const methods = [];
  const requests = [];
  const server = createServer(async (request, response) => {
    const body = await readBody(request);
    const method = parseRpcMethod(body);
    if (method) methods.push(method);
    requests.push(Object.freeze({
      method: request.method,
      rpcMethod: method,
      upstreamSecretPresent: request.headers['x-ink-e2e-upstream-secret'] === upstreamSecret,
    }));
    try {
      const target = new URL(request.url ?? '/', targetEndpointUrl);
      const headers = new Headers();
      for (const [name, value] of Object.entries(request.headers)) {
        if (value === undefined || HOP_BY_HOP_HEADERS.has(name.toLowerCase())) continue;
        headers.set(name, Array.isArray(value) ? value.join(', ') : value);
      }
      const upstreamResponse = await fetch(target, {
        method: request.method,
        headers,
        body: request.method === 'GET' || request.method === 'HEAD' ? undefined : body,
      });
      writeFetchResponse(upstreamResponse, response, Buffer.from(await upstreamResponse.arrayBuffer()));
    } catch (error) {
      response.statusCode = 502;
      response.end(error instanceof Error ? error.message : 'Upstream relay failed.');
    }
  });
  const origin = await listen(server);
  const targetPath = new URL(targetEndpointUrl).pathname;
  return {
    endpointUrl: `${origin}${targetPath}`,
    origin,
    methods,
    requests,
    async close() {
      await closeServer(server);
    },
  };
}


export async function startConnectionViewService({
  serverRef,
  workspaceScope = null,
  upstreamEndpointUrl,
  serviceToken,
  browserAuthorization,
  upstreamSecret,
}) {
  const requests = [];
  const state = {
    configRevision: 1,
    credentialRevision: 1,
    policyRevision: 1,
    resourceReads: true,
    lowRiskToolCalls: false,
  };
  const server = createServer(async (request, response) => {
    const url = new URL(request.url ?? '/', 'http://connection-view.invalid');
    if (request.method === 'GET'
      && url.pathname === '/api/claude-mcp/app-runtime/static') {
      if (request.headers.authorization !== browserAuthorization
        || request.headers['x-ink-mcp-apps-service'] !== serviceToken) {
        response.statusCode = 403;
        response.end();
        return;
      }
      response.statusCode = 200;
      response.setHeader('content-type', 'application/json');
      response.setHeader('cache-control', 'no-store');
      response.end(JSON.stringify({
        protocolVersion: '2026-01-26',
        productionAppsEffective: false,
        transports: ['streamable_http'],
        policy: {
          version: 1,
          revision: state.policyRevision,
          default: { resourceReads: false, lowRiskToolCalls: false },
          desired: {
            resourceReads: state.resourceReads,
            lowRiskToolCalls: state.lowRiskToolCalls,
          },
          effective: {
            resourceReads: state.resourceReads,
            lowRiskToolCalls: state.lowRiskToolCalls,
          },
        },
      }));
      return;
    }
    const expectedPath = `/api/claude-mcp/app-runtime/connections/${encodeURIComponent(serverRef)}`;
    if (request.method !== 'POST' || url.pathname !== expectedPath) {
      response.statusCode = 404;
      response.end();
      return;
    }
    const bodyBuffer = await readBody(request);
    let body;
    try {
      body = JSON.parse(bodyBuffer.toString('utf8'));
    } catch {
      response.statusCode = 400;
      response.end();
      return;
    }
    requests.push(Object.freeze({
      workspaceScope: body.workspace_scope ?? null,
      expectedConfigRevision: body.expected_config_revision ?? null,
      expectedCredentialRevision: body.expected_credential_revision ?? null,
      expectedPolicyRevision: body.expected_policy_revision ?? null,
    }));
    if (request.headers.authorization !== browserAuthorization
      || request.headers['x-ink-mcp-apps-service'] !== serviceToken
      || (body.workspace_scope ?? null) !== workspaceScope) {
      response.statusCode = 403;
      response.end();
      return;
    }
    for (const [field, expected] of [
      ['expected_config_revision', state.configRevision],
      ['expected_credential_revision', state.credentialRevision],
      ['expected_policy_revision', state.policyRevision],
    ]) {
      if (body[field] !== undefined && body[field] !== expected) {
        response.statusCode = 409;
        response.end();
        return;
      }
    }
    const enabledTools = ['get-time'];
    response.statusCode = 200;
    response.setHeader('content-type', 'application/json');
    response.setHeader('cache-control', 'no-store');
    response.end(JSON.stringify({
      actorScope: 'mcp-apps-e2e-actor',
      workspaceScope,
      serverId: 'mcp-apps-e2e-official-basic',
      serverRef,
      transportKind: 'streamable_http',
      enabled: true,
      configRevision: state.configRevision,
      credentialRevision: state.credentialRevision,
      expiresAt: new Date(Date.now() + 300_000).toISOString(),
      allowedTools: enabledTools,
      allowedResources: ['ui://get-time/mcp-app.html'],
      appCallableLowRiskTools: state.lowRiskToolCalls ? enabledTools : [],
      policy: {
        version: 1,
        revision: state.policyRevision,
        default: { resourceReads: false, lowRiskToolCalls: false },
        desired: {
          resourceReads: state.resourceReads,
          lowRiskToolCalls: state.lowRiskToolCalls,
        },
        effective: {
          resourceReads: state.resourceReads,
          lowRiskToolCalls: state.lowRiskToolCalls,
        },
      },
      connectionProfile: {
        type: 'streamable_http',
        url: upstreamEndpointUrl,
        headers: { 'x-ink-e2e-upstream-secret': upstreamSecret },
      },
    }));
  });
  const origin = await listen(server);
  return {
    origin,
    requests,
    state,
    async close() {
      await closeServer(server);
    },
  };
}

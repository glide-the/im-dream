// [Input] Test-owned loopback requests, static proxy HTML, and immutable permission decision.
// [Output] Separate-origin proxy responses with revision-bound headers and redacted evidence.
// [Pos] phase0-app-renderer-harness helper; never used by production or real business data.
// [Sync] 2026-09-04: bind proxy HTML and Permissions-Policy to the DEC-002 decision.

import { createServer } from 'node:http';
import { readFile } from 'node:fs/promises';


const PROXY_HTML = await readFile(new URL('./sandbox-proxy.html', import.meta.url), 'utf8');
export const PHASE0_PROXY_CSP = [
  "default-src 'none'",
  "script-src 'unsafe-inline'",
  "connect-src 'self'",
  "frame-src 'self' data: blob:",
  "style-src 'unsafe-inline'",
  "base-uri 'none'",
  "object-src 'none'",
].join('; ');


async function readJson(request) {
  const chunks = [];
  for await (const chunk of request) chunks.push(chunk);
  return JSON.parse(Buffer.concat(chunks).toString('utf8'));
}


const PERMISSION_FEATURES = {
  camera: 'camera',
  microphone: 'microphone',
  geolocation: 'geolocation',
  clipboardWrite: 'clipboard-write',
};


function buildPermissionsPolicy(effectivePermissions) {
  return Object.entries(PERMISSION_FEATURES).map(([key, feature]) => (
    effectivePermissions[key] ? `${feature}=(self)` : `${feature}=()`
  )).join(', ');
}


export async function startPhase0SandboxServer({
  effectivePermissions = {},
  revision = 'phase0-deny-all',
  sandboxTokens = 'allow-scripts allow-same-origin',
} = {}) {
  const evidence = [];
  const permissionsPolicy = buildPermissionsPolicy(effectivePermissions);
  const policy = Object.freeze({ effectivePermissions, revision, sandboxTokens });
  const proxyHtml = PROXY_HTML.replace(
    '__PHASE0_POLICY_JSON__',
    JSON.stringify(policy).replaceAll('<', '\\u003c'),
  );
  const server = createServer(async (request, response) => {
    const url = new URL(request.url ?? '/', 'http://phase0.invalid');
    if (request.method === 'GET' && url.pathname === '/phase0/sandbox-proxy.html') {
      response.statusCode = 200;
      response.setHeader('Content-Type', 'text/html; charset=utf-8');
      response.setHeader('Content-Security-Policy', PHASE0_PROXY_CSP);
      response.setHeader('Permissions-Policy', permissionsPolicy);
      response.setHeader('Cache-Control', 'no-store');
      response.end(proxyHtml);
      return;
    }
    if (request.method === 'POST' && url.pathname === '/phase0/proxy-evidence') {
      try {
        const item = await readJson(request);
        evidence.push(item);
        response.statusCode = 204;
        response.end();
      } catch {
        response.statusCode = 400;
        response.end();
      }
      return;
    }
    response.statusCode = 404;
    response.end();
  });

  await new Promise((resolve, reject) => {
    server.once('error', reject);
    server.listen(0, '127.0.0.1', resolve);
  });
  const address = server.address();
  if (address === null || typeof address === 'string') {
    throw new Error('Could not resolve isolated sandbox address.');
  }
  const origin = `http://127.0.0.1:${address.port}`;
  return {
    origin,
    proxyUrl: `${origin}/phase0/sandbox-proxy.html`,
    permissionsPolicy,
    evidence,
    async close() {
      await new Promise((resolve, reject) => server.close((error) => (
        error ? reject(error) : resolve()
      )));
    },
  };
}

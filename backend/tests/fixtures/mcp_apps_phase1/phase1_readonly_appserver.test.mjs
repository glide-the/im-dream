// [Input] The canonical Phase 1 stdio AppServer and locked standard MCP Client.
// [Output] Protocol, descriptor/resource, fallback-equivalence, count, and teardown evidence.
// [Pos] Provider-free S1-01 contract test.
// [Sync] 2026-09-05: cover the canonical read-only fixture end to end.

import assert from 'node:assert/strict';
import { createRequire } from 'node:module';
import { pathToFileURL } from 'node:url';
import test from 'node:test';

import {
  PHASE1_APP_HTML,
  PHASE1_CSP,
  PHASE1_RESOURCE_URI,
  PHASE1_SERVER_INFO,
  PHASE1_STATE,
  PHASE1_TOOL_NAME,
} from './phase1_readonly_appserver.mjs';

const frontendRequire = createRequire(
  new URL('../../../../frontend/package.json', import.meta.url),
);
const loadFrontendModule = async (specifier) => (
  import(pathToFileURL(frontendRequire.resolve(specifier)).href)
);
const [{ Client }, { StdioClientTransport }, { RESOURCE_MIME_TYPE }] = await Promise.all([
  loadFrontendModule('@modelcontextprotocol/sdk/client/index.js'),
  loadFrontendModule('@modelcontextprotocol/sdk/client/stdio.js'),
  loadFrontendModule('@modelcontextprotocol/ext-apps'),
]);

test('standard Client reads one deterministic App descriptor, result, and resource', async (t) => {
  const transport = new StdioClientTransport({
    command: process.execPath,
    args: [new URL('./phase1_readonly_appserver.mjs', import.meta.url).pathname],
    stderr: 'pipe',
  });
  const client = new Client({ name: 'phase1-contract-client', version: '1.0.0' });
  t.after(async () => {
    await client.close();
  });

  await client.connect(transport);
  const tools = await client.listTools();
  assert.equal(tools.tools.length, 1);
  assert.equal(tools.tools[0].name, PHASE1_TOOL_NAME);
  assert.equal(tools.tools[0]._meta.ui.resourceUri, PHASE1_RESOURCE_URI);
  assert.deepEqual(tools.tools[0]._meta.ui.visibility, ['model']);

  const result = await client.callTool({ name: PHASE1_TOOL_NAME, arguments: {} });
  assert.equal(result.isError, false);
  assert.deepEqual(result.structuredContent, {
    state: PHASE1_STATE,
    source: 'repo-owned-appserver',
    callCount: 1,
  });
  assert.equal(result.content[0].text, `Read-only state: ${PHASE1_STATE}`);
  assert.equal(result._meta.ui.resourceUri, PHASE1_RESOURCE_URI);

  const resources = await client.listResources();
  assert.equal(resources.resources.length, 1);
  assert.equal(resources.resources[0].uri, PHASE1_RESOURCE_URI);
  const resource = await client.readResource({ uri: PHASE1_RESOURCE_URI });
  assert.equal(resource.contents.length, 1);
  assert.equal(resource.contents[0].mimeType, RESOURCE_MIME_TYPE);
  assert.equal(resource.contents[0].text, PHASE1_APP_HTML);
  assert.deepEqual(resource.contents[0]._meta.ui.csp, PHASE1_CSP);
  assert.deepEqual(resource.contents[0]._meta.ui.permissions, {});
  assert.equal(resource.contents[0].text.startsWith('<!doctype html>'), true);
});

test('a fresh canonical process has the same logical identity and a fresh count', async (t) => {
  const transport = new StdioClientTransport({
    command: process.execPath,
    args: [new URL('./phase1_readonly_appserver.mjs', import.meta.url).pathname],
    stderr: 'pipe',
  });
  const client = new Client({ name: 'phase1-repeat-client', version: '1.0.0' });
  t.after(async () => client.close());
  await client.connect(transport);
  assert.equal(client.getServerVersion()?.name, PHASE1_SERVER_INFO.name);
  const result = await client.callTool({ name: PHASE1_TOOL_NAME, arguments: {} });
  assert.equal(result.structuredContent.callCount, 1);
});

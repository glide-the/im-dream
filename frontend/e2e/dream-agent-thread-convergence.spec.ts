// [Input] Deterministic canonical history/status/SSE fixtures for the shared Dream/Chat thread.
// [Output] Independently discoverable S01-S10 browser proof for the canonical Dream/Chat
//          transport, confirmation, subagent, Stop, failure, reconnect, and reload contracts.
// [Pos] R10 convergence acceptance lane; uses the production ChatView, ChatPanel, and
//       StoryWorkspaceDreamThreadChat against a strict in-process fake API (never a model).
// [Sync] 2026-08-24: serve the shell's read-only Dream Run collection alongside
//                    canonical Thread fixtures while retaining strict API rejection.

import { expect, test, type Page } from '@playwright/test';
import {
  createServer as createHttpServer,
  type IncomingMessage,
  type ServerResponse,
} from 'node:http';
import { fileURLToPath } from 'node:url';
import { createServer, type ViteDevServer } from 'vite';

test.use({ channel: 'chromium' });
test.setTimeout(90_000);

const FRONTEND_ROOT = fileURLToPath(new URL('../', import.meta.url));

interface HarnessServer {
  readonly origin: string;
  close: () => Promise<void>;
}

interface StrictApiRequest {
  readonly method: string;
  readonly path: string;
  readonly rejected: boolean;
  readonly url: URL;
}

interface FailureScenario {
  readonly id: string;
  readonly name: string;
  readonly partialText: string | null;
}

type SurfaceName = 'dream' | 'chat';

function buildDreamHarnessModule(threadId: string): string {
  return `
    import React, { useState } from 'react';
    import { createRoot } from 'react-dom/client';
    import '/src/i18n.ts';
    import '/src/styles/tokens.css';
    import '/src/styles/markdown.css';
    import '/src/pages/story-workspace/StoryWorkspaceDreamPage.css';
    import { StoryWorkspaceDreamThreadChat } from '/src/components/story-workspace/dream/StoryWorkspaceDreamThreadChat.tsx';

    function Harness() {
      const [settled, setSettled] = useState(0);
      return React.createElement('main', {
        style: { height: '820px', display: 'flex', padding: '16px' },
      },
        React.createElement('output', { id: 'settled-count' }, String(settled)),
        React.createElement(StoryWorkspaceDreamThreadChat, {
          threadId: '${threadId}',
          onSettled: () => setSettled((value) => value + 1),
        }),
      );
    }
    createRoot(document.querySelector('#root')).render(React.createElement(Harness));
  `;
}

function buildSurfaceHarnessModule(threadId: string, initialSurface: SurfaceName): string {
  return `
    import React, { useState } from 'react';
    import { createRoot } from 'react-dom/client';
    import '/src/i18n.ts';
    import '/src/styles/tokens.css';
    import '/src/styles/markdown.css';
    import '/src/pages/story-workspace/StoryWorkspaceDreamPage.css';
    import ChatView from '/src/components/chat/ChatView.tsx';
    import { StoryWorkspaceDreamThreadChat } from '/src/components/story-workspace/dream/StoryWorkspaceDreamThreadChat.tsx';

    function Harness() {
      const [surface, setSurface] = useState('${initialSurface}');
      const [settled, setSettled] = useState(0);
      return React.createElement('main', {
        style: { height: '100vh', display: 'flex', flexDirection: 'column' },
      },
        React.createElement('nav', { 'aria-label': 'Surface handoff' },
          React.createElement('button', { type: 'button', onClick: () => setSurface('dream') }, 'Show Dream'),
          React.createElement('button', { type: 'button', onClick: () => setSurface('chat') }, 'Show Chat'),
          React.createElement('output', { id: 'active-surface' }, surface),
          React.createElement('output', { id: 'settled-count' }, String(settled)),
        ),
        React.createElement('section', {
          'data-testid': 'active-thread-surface',
          'data-surface': surface,
          style: { minHeight: 0, flex: 1, display: 'flex' },
        }, surface === 'dream'
          ? React.createElement(StoryWorkspaceDreamThreadChat, {
              threadId: '${threadId}',
              onSettled: () => setSettled((value) => value + 1),
            })
          : React.createElement(ChatView, {
              requestedThreadId: '${threadId}',
              requestedThreadNonce: 1,
            })),
      );
    }
    createRoot(document.querySelector('#root')).render(React.createElement(Harness));
  `;
}

async function seedEnglishAuth(page: Page, token: string): Promise<void> {
  await page.addInitScript(({ authToken }) => {
    localStorage.setItem('auth_token', authToken);
    localStorage.setItem('ink-language', 'en');
  }, { authToken: token });
}

function threadRecord(threadId: string, title: string): Record<string, unknown> {
  return {
    id: threadId,
    title,
    created_at: '2026-08-11T00:00:00Z',
    updated_at: '2026-08-11T00:00:03Z',
  };
}

function threadStatus(
  running: boolean,
  pendingToolCallIds: readonly string[] = [],
  turnCount = running ? 0 : 1,
): Record<string, unknown> {
  return {
    running,
    lifecycle: running ? 'running' : 'idle',
    turn_count: turnCount,
    pending_tool_call_ids: [...pendingToolCallIds],
    tool_confirmation_observation: 'known',
  };
}

function respondJson(
  response: ServerResponse,
  status: number,
  payload: unknown,
): void {
  response.statusCode = status;
  response.setHeader('Content-Type', 'application/json; charset=utf-8');
  response.end(JSON.stringify(payload));
}

function beginSse(response: ServerResponse): void {
  response.statusCode = 200;
  response.setHeader('Content-Type', 'text/event-stream; charset=utf-8');
  response.setHeader('Cache-Control', 'no-cache, no-transform');
  response.setHeader('X-Accel-Buffering', 'no');
  response.flushHeaders();
}

function inspectStrictApiRequest(
  request: IncomingMessage,
  response: ServerResponse,
  expectedToken: string,
  apiRequests: string[],
  violations: string[],
): StrictApiRequest | null {
  const url = new URL(request.url ?? '/', 'http://127.0.0.1');
  if (!url.pathname.startsWith('/api/')) return null;

  const method = request.method ?? 'GET';
  apiRequests.push(`${method} ${url.pathname}`);
  const authorization = request.headers.authorization;
  if (authorization !== `Bearer ${expectedToken}`) {
    violations.push(
      `Unexpected Authorization for ${method} ${url.pathname}: ${String(authorization)}`,
    );
    respondJson(response, 401, { detail: 'Strict fake-server auth failure.' });
    return { method, path: url.pathname, rejected: true, url };
  }
  return { method, path: url.pathname, rejected: false, url };
}

function requireMethod(
  api: StrictApiRequest,
  response: ServerResponse,
  expectedMethod: string,
  violations: string[],
): boolean {
  if (api.method === expectedMethod) return true;
  violations.push(
    `Unexpected method ${api.method} for ${api.path}; expected ${expectedMethod}.`,
  );
  respondJson(response, 405, { detail: 'Strict fake-server method failure.' });
  return false;
}

function handleCommonChatApi(
  api: StrictApiRequest,
  response: ServerResponse,
  threadId: string,
  violations: string[],
): boolean {
  const get = () => requireMethod(api, response, 'GET', violations);
  if (api.path === '/api/system-config') {
    if (get()) {
      respondJson(response, 200, {
        data: { im_full_access_enabled: false, workspace_enabled: false },
      });
    }
    return true;
  }
  if (api.path === '/api/decks') {
    if (get()) respondJson(response, 200, { decks: [] });
    return true;
  }
  if (api.path === '/api/storage') {
    if (get()) {
      respondJson(response, 200, {
        type: 'unknown',
        supportsDirectUpload: false,
        isConfigured: true,
      });
    }
    return true;
  }
  if (api.path === '/api/claude-agent/threads') {
    if (get()) respondJson(response, 200, { threads: [] });
    return true;
  }
  if (api.path === '/api/story-workspace/dream-runs') {
    if (get()) respondJson(response, 200, { runs: [] });
    return true;
  }
  if (api.path === `/api/claude-agent/threads/${threadId}/plan`) {
    if (get()) {
      respondJson(response, 200, {
        exists: false,
        plan_mode: 'none',
        slug: null,
        file_name: null,
        content: null,
        updated_at: null,
      });
    }
    return true;
  }
  if (api.path === `/api/claude-agent/threads/${threadId}/todos`) {
    if (get()) {
      respondJson(response, 200, {
        exists: false,
        source: null,
        todos: [],
        truncated: false,
        updated_at: null,
      });
    }
    return true;
  }
  if (api.path === `/api/claude-agent/threads/${threadId}/subagents`) {
    if (get()) {
      respondJson(response, 200, {
        exists: false,
        tasks: [],
        counts: { running: 0, completed: 0, ended: 0, total: 0 },
        updated_at: null,
      });
    }
    return true;
  }
  if (api.path === `/api/claude-agent/threads/${threadId}/plugin-load-receipt`) {
    if (get()) {
      respondJson(response, 200, {
        thread_id: threadId,
        deck_id: null,
        workspace_found: true,
        receipt: {
          schema_version: 'fixture-v1',
          workspace: 'fixture',
          deck_id: null,
          packed_at: '2026-08-11T00:00:00Z',
          frozen: true,
          plugins: [{
            package_spec: 'fixture-plugin@1.0.0',
            resolved_version: '1.0.0',
            artifact_digest: `sha256:${'0'.repeat(64)}`,
            relative_path: 'fixture-plugin',
            verified: true,
          }],
        },
        launch_manifest: null,
      });
    }
    return true;
  }
  return false;
}

function rejectUnexpectedApi(
  api: StrictApiRequest,
  response: ServerResponse,
  violations: string[],
): void {
  violations.push(`Unexpected fake API request: ${api.method} ${api.url.pathname}${api.url.search}`);
  respondJson(response, 418, { detail: 'Unexpected fake API request.' });
}

function collectPageDiagnostics(
  page: Page,
  expectedRequestFailure?: (url: URL) => boolean,
  expectedConsoleError?: (text: string) => boolean,
): { diagnostics: string[]; expectedFailures: string[] } {
  const diagnostics: string[] = [];
  const expectedFailures: string[] = [];
  page.on('console', (message) => {
    if (message.type() !== 'error') return;
    const detail = message.text();
    if (expectedConsoleError?.(detail)) expectedFailures.push(`console: ${detail}`);
    else diagnostics.push(detail);
  });
  page.on('pageerror', (error) => diagnostics.push(error.message));
  page.on('requestfailed', (request) => {
    const detail = `${request.failure()?.errorText ?? 'failed'} ${request.url()}`;
    const url = new URL(request.url());
    if (expectedRequestFailure?.(url)) expectedFailures.push(detail);
    else diagnostics.push(detail);
  });
  return { diagnostics, expectedFailures };
}

async function startHarness(options: {
  readonly pagePath: string;
  readonly modulePath: string;
  readonly moduleSource: string;
  readonly pluginName: string;
  readonly handleApi: (request: IncomingMessage, response: ServerResponse) => boolean;
}): Promise<HarnessServer> {
  const vite: ViteDevServer = await createServer({
    root: FRONTEND_ROOT,
    appType: 'custom',
    configFile: false,
    logLevel: 'silent',
    server: { middlewareMode: true, hmr: false },
    plugins: [{
      name: options.pluginName,
      configureServer(viteServer) {
        viteServer.middlewares.use((request, response, next) => {
          if (options.handleApi(request, response)) return;
          const requestUrl = new URL(request.url ?? '/', 'http://127.0.0.1');
          if (requestUrl.pathname !== options.pagePath) {
            next();
            return;
          }
          void viteServer.transformIndexHtml(requestUrl.pathname, `
            <!doctype html><html><head><link rel="icon" href="data:,"></head>
            <body><div id="root" style="height:100vh"></div>
            <script type="module" src="${options.modulePath}"></script></body></html>
          `).then((html) => {
            response.statusCode = 200;
            response.setHeader('Content-Type', 'text/html; charset=utf-8');
            response.end(html);
          }, next);
        });
      },
      resolveId(id) {
        return id === options.modulePath ? `\0${options.modulePath}` : null;
      },
      load(id) {
        return id === `\0${options.modulePath}` ? options.moduleSource : null;
      },
    }],
  });
  const httpServer = createHttpServer((request, response) => {
    vite.middlewares.handle(request, response);
  });

  try {
    await new Promise<void>((resolve, reject) => {
      const onError = (error: Error) => reject(error);
      httpServer.once('error', onError);
      httpServer.listen(0, '127.0.0.1', () => {
        httpServer.off('error', onError);
        resolve();
      });
    });
  } catch (error) {
    await vite.close();
    throw error;
  }

  const address = httpServer.address();
  if (address === null || typeof address === 'string') {
    await new Promise<void>((resolve) => httpServer.close(() => resolve()));
    await vite.close();
    throw new Error('Dream convergence harness did not bind an OS-assigned TCP port.');
  }

  return {
    origin: `http://127.0.0.1:${address.port}`,
    close: async () => {
      try {
        await new Promise<void>((resolve, reject) => {
          httpServer.close((error) => error ? reject(error) : resolve());
        });
      } finally {
        await vite.close();
      }
    },
  };
}

test('S01 Dream normal send uses one canonical POST and renders ordered incremental output', async ({ page }) => {
  const token = 'dream-s01-send-token';
  const threadId = 'thread-dream-s01-send';
  const moduleSource = buildDreamHarnessModule(threadId);
  const apiRequests: string[] = [];
  const violations: string[] = [];
  const canonicalPosts: Array<Record<string, unknown>> = [];
  let phase: 'idle' | 'running' | 'terminal' = 'idle';
  let releaseIncrementalTurn: (() => void) | null = null;
  let terminalFrames = 0;

  const messages = (): Array<Record<string, unknown>> => phase === 'terminal'
    ? [
        {
          id: 's01-user',
          role: 'user',
          parts: [{ type: 'text', text: '请逐步生成同一条回复' }],
          metadata: { kind: 'story-workspace-dream-agent-user' },
          created_at: '2026-08-11T00:00:00Z',
        },
        {
          id: 's01-assistant',
          role: 'assistant',
          parts: [{ type: 'text', text: '第一段🙂 + 第二段' }],
          metadata: {},
          created_at: '2026-08-11T00:00:01Z',
        },
      ]
    : [];

  const handleApi = (request: IncomingMessage, response: ServerResponse): boolean => {
    const api = inspectStrictApiRequest(request, response, token, apiRequests, violations);
    if (api === null) return false;
    if (api.rejected) return true;
    if (handleCommonChatApi(api, response, threadId, violations)) return true;

    if (api.path === `/api/claude-agent/threads/${threadId}/messages`) {
      if (requireMethod(api, response, 'GET', violations)) {
        respondJson(response, 200, {
          thread: threadRecord(threadId, 'S01 canonical incremental send'),
          messages: messages(),
        });
      }
      return true;
    }
    if (api.path === `/api/claude-agent/threads/${threadId}/status`) {
      if (requireMethod(api, response, 'GET', violations)) {
        respondJson(response, 200, threadStatus(phase === 'running', [], phase === 'terminal' ? 1 : 0));
      }
      return true;
    }
    if (api.path === '/api/claude-agent') {
      if (!requireMethod(api, response, 'POST', violations)) return true;
      let rawBody = '';
      request.setEncoding('utf8');
      request.on('data', (chunk) => { rawBody += chunk; });
      request.on('end', () => {
        let body: Record<string, unknown>;
        try {
          body = JSON.parse(rawBody) as Record<string, unknown>;
        } catch {
          violations.push(`S01 canonical POST was not JSON: ${rawBody}`);
          respondJson(response, 400, { detail: 'Invalid JSON fixture request.' });
          return;
        }
        canonicalPosts.push(body);
        phase = 'running';
        beginSse(response);
        response.write([
          'data: {"type":"text-start","id":"s01-live"}',
          `data: ${JSON.stringify({ type: 'text-delta', id: 's01-live', delta: '第一段🙂' })}`,
          '',
        ].join('\n\n'));
        releaseIncrementalTurn = () => {
          if (response.destroyed) {
            violations.push('S01 incremental response was destroyed before its semantic release.');
            return;
          }
          phase = 'terminal';
          terminalFrames += 1;
          response.end([
            `data: ${JSON.stringify({ type: 'text-delta', id: 's01-live', delta: ' + 第二段' })}`,
            'data: {"type":"text-end","id":"s01-live"}',
            'data: {"type":"message-final","text":"第一段🙂 + 第二段"}',
            'data: {"type":"finish","finishReason":"stop"}',
            '',
          ].join('\n\n'));
          releaseIncrementalTurn = null;
        };
      });
      return true;
    }
    rejectUnexpectedApi(api, response, violations);
    return true;
  };

  const { diagnostics } = collectPageDiagnostics(page);
  await seedEnglishAuth(page, token);
  let harness: HarnessServer | null = null;
  try {
    harness = await startHarness({
      pagePath: '/dream-s01-send',
      modulePath: '/dream-s01-send-harness.js',
      moduleSource,
      pluginName: 'dream-s01-send-e2e',
      handleApi,
    });
    await page.goto(`${harness.origin}/dream-s01-send`);

    const input = page.getByRole('textbox', { name: 'Chat input' });
    await expect(input).toBeEnabled();
    await input.fill('请逐步生成同一条回复');
    await page.getByRole('button', { name: 'Send message' }).click();

    await expect(page.getByText('请逐步生成同一条回复', { exact: true })).toHaveCount(1);
    await expect(page.getByText('第一段🙂', { exact: true })).toBeVisible();
    await expect(page.getByText('第一段🙂 + 第二段', { exact: true })).toHaveCount(0);
    await expect.poll(() => releaseIncrementalTurn !== null).toBe(true);

    const release = releaseIncrementalTurn;
    if (release === null) throw new Error('S01 incremental turn was not releasable.');
    release();

    await expect(page.getByText('第一段🙂 + 第二段', { exact: true })).toHaveCount(1);
    await expect(page.locator('#settled-count')).toHaveText('1');
    await expect(page.getByRole('button', { name: 'Stop generating' })).toHaveCount(0);
    await expect(input).toBeEnabled();

    expect(terminalFrames).toBe(1);
    expect(canonicalPosts).toHaveLength(1);
    expect(canonicalPosts[0]).toMatchObject({
      id: threadId,
      resume: true,
      message: {
        role: 'user',
        parts: [{ type: 'text', text: '请逐步生成同一条回复' }],
      },
    });
    expect(canonicalPosts[0]).not.toHaveProperty('story_workspace_dream_context');
    expect(apiRequests.filter((entry) => entry === 'POST /api/claude-agent')).toHaveLength(1);
    expect(apiRequests.some((entry) => /\/dream-agent\//.test(entry))).toBe(false);
    expect(violations).toEqual([]);
    expect(diagnostics).toEqual([]);
  } finally {
    await page.close();
    await harness?.close();
  }
});

test('S02 Dream -> actual ChatView -> Dream keeps one active thread and never implies Stop', async ({ page }) => {
  const token = 'dream-handoff-fixture-token';
  const threadId = 'thread-dream-chat-handoff';
  const moduleSource = `
    import React, { useState } from 'react';
    import { createRoot } from 'react-dom/client';
    import '/src/i18n.ts';
    import '/src/styles/tokens.css';
    import '/src/styles/markdown.css';
    import '/src/pages/story-workspace/StoryWorkspaceDreamPage.css';
    import ChatView from '/src/components/chat/ChatView.tsx';
    import { StoryWorkspaceDreamThreadChat } from '/src/components/story-workspace/dream/StoryWorkspaceDreamThreadChat.tsx';

    function Harness() {
      const [surface, setSurface] = useState('dream');
      const [settled, setSettled] = useState(0);
      return React.createElement('main', {
        style: { height: '100vh', display: 'flex', flexDirection: 'column' },
      },
        React.createElement('nav', { 'aria-label': 'Surface handoff' },
          React.createElement('button', { type: 'button', onClick: () => setSurface('dream') }, 'Show Dream'),
          React.createElement('button', { type: 'button', onClick: () => setSurface('chat') }, 'Show Chat'),
          React.createElement('output', { id: 'active-surface' }, surface),
          React.createElement('output', { id: 'settled-count' }, String(settled)),
        ),
        React.createElement('section', {
          'data-testid': 'active-thread-surface',
          'data-surface': surface,
          style: { minHeight: 0, flex: 1, display: 'flex' },
        }, surface === 'dream'
          ? React.createElement(StoryWorkspaceDreamThreadChat, {
              threadId: '${threadId}',
              onSettled: () => setSettled((value) => value + 1),
            })
          : React.createElement(ChatView, {
              requestedThreadId: '${threadId}',
              requestedThreadNonce: 1,
            })),
      );
    }
    createRoot(document.querySelector('#root')).render(React.createElement(Harness));
  `;
  const apiRequests: string[] = [];
  const violations: string[] = [];
  const canonicalPosts: Array<Record<string, unknown>> = [];
  const stopRequests: string[] = [];
  let phase: 'running' | 'terminal' = 'running';
  let followupComplete = false;
  let streamGets = 0;
  let interruptedStreams = 0;
  let releaseActiveStream: (() => void) | null = null;

  const persistedMessages = (): Array<Record<string, unknown>> => {
    const messages: Array<Record<string, unknown>> = [{
      id: 'handoff-user',
      role: 'user',
      parts: [{ type: 'text', text: 'Dream handoff source' }],
      metadata: { kind: 'story-workspace-dream-agent-user' },
      created_at: '2026-08-11T00:00:00Z',
    }];
    if (phase === 'terminal') {
      messages.push({
        id: 'handoff-terminal',
        role: 'assistant',
        parts: [{ type: 'text', text: 'running handoff replay' }],
        metadata: {},
        created_at: '2026-08-11T00:00:01Z',
      });
    }
    if (followupComplete) {
      messages.push(
        {
          id: 'handoff-followup-user',
          role: 'user',
          parts: [{ type: 'text', text: 'continue after both handoffs' }],
          metadata: {},
          created_at: '2026-08-11T00:00:02Z',
        },
        {
          id: 'handoff-followup-assistant',
          role: 'assistant',
          parts: [{ type: 'text', text: 'one canonical followup' }],
          metadata: {},
          created_at: '2026-08-11T00:00:03Z',
        },
      );
    }
    return messages;
  };

  const handleApi = (request: IncomingMessage, response: ServerResponse): boolean => {
    const api = inspectStrictApiRequest(
      request,
      response,
      token,
      apiRequests,
      violations,
    );
    if (api === null) return false;
    if (api.rejected) return true;
    if (handleCommonChatApi(api, response, threadId, violations)) return true;

    if (api.path === `/api/claude-agent/threads/${threadId}/messages`) {
      if (requireMethod(api, response, 'GET', violations)) {
        respondJson(response, 200, {
          thread: {
            id: threadId,
            title: 'Dream canonical handoff',
            created_at: '2026-08-11T00:00:00Z',
            updated_at: '2026-08-11T00:00:03Z',
          },
          messages: persistedMessages(),
        });
      }
      return true;
    }
    if (api.path === `/api/claude-agent/threads/${threadId}/status`) {
      if (requireMethod(api, response, 'GET', violations)) {
        respondJson(response, 200, {
          running: phase === 'running',
          lifecycle: phase === 'running' ? 'running' : 'idle',
          turn_count: phase === 'running' ? 0 : followupComplete ? 2 : 1,
          pending_tool_call_ids: [],
          tool_confirmation_observation: 'known',
        });
      }
      return true;
    }
    if (api.path === `/api/claude-agent/threads/${threadId}/stream`) {
      if (!requireMethod(api, response, 'GET', violations)) return true;
      if (phase !== 'running') {
        violations.push('An idle handoff surface requested a new SSE stream.');
        respondJson(response, 409, { detail: 'Thread is already idle.' });
        return true;
      }
      streamGets += 1;
      let completed = false;
      beginSse(response);
      response.write([
        'data: {"type":"text-start","id":"handoff-live"}',
        'data: {"type":"text-delta","id":"handoff-live","delta":"running handoff replay"}',
        '',
      ].join('\n\n'));
      response.once('close', () => {
        if (!completed) interruptedStreams += 1;
      });
      const release = () => {
        if (response.destroyed) {
          violations.push('Attempted to terminally release an already-interrupted handoff stream.');
          return;
        }
        completed = true;
        phase = 'terminal';
        response.end([
          'data: {"type":"text-end","id":"handoff-live"}',
          'data: {"type":"message-final","text":"running handoff replay"}',
          'data: {"type":"finish","finishReason":"stop"}',
          '',
        ].join('\n\n'));
        if (releaseActiveStream === release) releaseActiveStream = null;
      };
      releaseActiveStream = release;
      return true;
    }
    if (api.path === '/api/claude-agent') {
      if (!requireMethod(api, response, 'POST', violations)) return true;
      let rawBody = '';
      request.setEncoding('utf8');
      request.on('data', (chunk) => { rawBody += chunk; });
      request.on('end', () => {
        try {
          canonicalPosts.push(JSON.parse(rawBody) as Record<string, unknown>);
        } catch {
          violations.push(`Canonical Chat POST was not JSON: ${rawBody}`);
          respondJson(response, 400, { detail: 'Invalid JSON fixture request.' });
          return;
        }
        followupComplete = true;
        beginSse(response);
        response.end([
          'data: {"type":"text-start","id":"handoff-followup"}',
          'data: {"type":"text-delta","id":"handoff-followup","delta":"one canonical followup"}',
          'data: {"type":"text-end","id":"handoff-followup"}',
          'data: {"type":"message-final","text":"one canonical followup"}',
          'data: {"type":"finish","finishReason":"stop"}',
          '',
        ].join('\n\n'));
      });
      return true;
    }
    if (api.path === `/api/claude-agent/threads/${threadId}/stop`) {
      if (requireMethod(api, response, 'POST', violations)) {
        stopRequests.push(`${api.method} ${api.path}`);
        respondJson(response, 200, { ok: true, stop_requested: true });
      }
      return true;
    }
    rejectUnexpectedApi(api, response, violations);
    return true;
  };

  const { diagnostics } = collectPageDiagnostics(
    page,
    (url) => url.pathname === `/api/claude-agent/threads/${threadId}/stream`,
  );
  await page.addInitScript(({ authToken }) => {
    localStorage.setItem('auth_token', authToken);
    localStorage.setItem('ink-language', 'en');
  }, { authToken: token });

  let harness: HarnessServer | null = null;
  try {
    harness = await startHarness({
      pagePath: '/dream-chat-handoff',
      modulePath: '/dream-chat-handoff-harness.js',
      moduleSource,
      pluginName: 'dream-chat-active-handoff-e2e',
      handleApi,
    });
    await page.goto(`${harness.origin}/dream-chat-handoff`);

    const surface = page.getByTestId('active-thread-surface');
    await expect(surface).toHaveAttribute('data-surface', 'dream');
    await expect.poll(() => streamGets).toBe(1);
    await expect(page.getByText('running handoff replay', { exact: true })).toBeVisible();

    await page.getByRole('button', { name: 'Show Chat' }).click();
    await expect(surface).toHaveAttribute('data-surface', 'chat');
    await expect.poll(() => streamGets).toBe(2);
    await expect.poll(() => interruptedStreams).toBe(1);
    await expect(page.getByText('running handoff replay', { exact: true })).toBeVisible();

    await page.getByRole('button', { name: 'Show Dream' }).click();
    await expect(surface).toHaveAttribute('data-surface', 'dream');
    await expect.poll(() => streamGets).toBe(3);
    await expect.poll(() => interruptedStreams).toBe(2);
    expect(canonicalPosts).toEqual([]);
    expect(stopRequests).toEqual([]);

    await expect.poll(() => releaseActiveStream !== null).toBe(true);
    const release = releaseActiveStream;
    if (release === null) throw new Error('The active Dream handoff stream was not releasable.');
    release();
    await expect(page.getByText('running handoff replay', { exact: true })).toHaveCount(1);
    await expect(page.locator('#settled-count')).toHaveText('1');
    await expect(page.getByRole('button', { name: 'Stop generating' })).toHaveCount(0);

    const input = page.getByRole('textbox', { name: 'Chat input' });
    await expect(input).toBeEnabled();
    await input.fill('continue after both handoffs');
    await page.getByRole('button', { name: 'Send message' }).click();
    await expect(page.getByText('one canonical followup', { exact: true })).toBeVisible();
    await expect(page.locator('#settled-count')).toHaveText('2');

    expect(canonicalPosts).toHaveLength(1);
    expect(canonicalPosts[0]).toMatchObject({
      id: threadId,
      resume: true,
      message: {
        role: 'user',
        parts: [{ type: 'text', text: 'continue after both handoffs' }],
      },
    });
    expect(canonicalPosts[0]).not.toHaveProperty('story_workspace_dream_context');
    expect(stopRequests).toEqual([]);
    expect(apiRequests.filter((entry) => entry === 'POST /api/claude-agent')).toHaveLength(1);
    expect(apiRequests.some((entry) => /\/dream-agent\//.test(entry))).toBe(false);
    expect(violations).toEqual([]);
    expect(diagnostics).toEqual([]);
  } finally {
    await page.close();
    await harness?.close();
  }
});

test('S03 actual ChatView -> Dream restores the same running thread without a second send', async ({ page }) => {
  const token = 'dream-s03-chat-to-dream-token';
  const threadId = 'thread-dream-s03-chat-to-dream';
  const moduleSource = buildSurfaceHarnessModule(threadId, 'chat');
  const apiRequests: string[] = [];
  const violations: string[] = [];
  let phase: 'running' | 'terminal' = 'running';
  let streamGets = 0;
  let interruptedStreams = 0;
  let releaseActiveStream: (() => void) | null = null;

  const messages = (): Array<Record<string, unknown>> => [
    {
      id: 's03-user',
      role: 'user',
      parts: [{ type: 'text', text: 'S03 Chat source message' }],
      metadata: {},
      created_at: '2026-08-11T00:00:00Z',
    },
    ...(phase === 'terminal' ? [{
      id: 's03-assistant',
      role: 'assistant',
      parts: [{ type: 'text', text: 'S03 same active output' }],
      metadata: {},
      created_at: '2026-08-11T00:00:01Z',
    }] : []),
  ];

  const handleApi = (request: IncomingMessage, response: ServerResponse): boolean => {
    const api = inspectStrictApiRequest(request, response, token, apiRequests, violations);
    if (api === null) return false;
    if (api.rejected) return true;
    if (handleCommonChatApi(api, response, threadId, violations)) return true;
    if (api.path === `/api/claude-agent/threads/${threadId}/messages`) {
      if (requireMethod(api, response, 'GET', violations)) {
        respondJson(response, 200, {
          thread: threadRecord(threadId, 'S03 Chat to Dream'),
          messages: messages(),
        });
      }
      return true;
    }
    if (api.path === `/api/claude-agent/threads/${threadId}/status`) {
      if (requireMethod(api, response, 'GET', violations)) {
        respondJson(response, 200, threadStatus(phase === 'running'));
      }
      return true;
    }
    if (api.path === `/api/claude-agent/threads/${threadId}/stream`) {
      if (!requireMethod(api, response, 'GET', violations)) return true;
      if (phase !== 'running') {
        violations.push('S03 attempted to stream an already terminal thread.');
        respondJson(response, 409, { detail: 'S03 thread is terminal.' });
        return true;
      }
      streamGets += 1;
      let completed = false;
      beginSse(response);
      response.write([
        'data: {"type":"text-start","id":"s03-live"}',
        'data: {"type":"text-delta","id":"s03-live","delta":"S03 same active output"}',
        '',
      ].join('\n\n'));
      response.once('close', () => {
        if (!completed) interruptedStreams += 1;
      });
      const release = () => {
        if (response.destroyed) {
          violations.push('S03 attempted to finish an interrupted reader.');
          return;
        }
        completed = true;
        phase = 'terminal';
        response.end([
          'data: {"type":"text-end","id":"s03-live"}',
          'data: {"type":"message-final","text":"S03 same active output"}',
          'data: {"type":"finish","finishReason":"stop"}',
          '',
        ].join('\n\n'));
        if (releaseActiveStream === release) releaseActiveStream = null;
      };
      releaseActiveStream = release;
      return true;
    }
    rejectUnexpectedApi(api, response, violations);
    return true;
  };

  const { diagnostics } = collectPageDiagnostics(
    page,
    (url) => url.pathname === `/api/claude-agent/threads/${threadId}/stream`,
  );
  await seedEnglishAuth(page, token);
  let harness: HarnessServer | null = null;
  try {
    harness = await startHarness({
      pagePath: '/dream-s03-chat-to-dream',
      modulePath: '/dream-s03-chat-to-dream-harness.js',
      moduleSource,
      pluginName: 'dream-s03-chat-to-dream-e2e',
      handleApi,
    });
    await page.goto(`${harness.origin}/dream-s03-chat-to-dream`);

    const surface = page.getByTestId('active-thread-surface');
    await expect(surface).toHaveAttribute('data-surface', 'chat');
    await expect.poll(() => streamGets).toBe(1);
    await expect(page.getByText('S03 same active output', { exact: true })).toBeVisible();

    await page.getByRole('button', { name: 'Show Dream' }).click();
    await expect(surface).toHaveAttribute('data-surface', 'dream');
    await expect.poll(() => streamGets).toBe(2);
    await expect.poll(() => interruptedStreams).toBe(1);
    await expect(page.getByText('S03 same active output', { exact: true })).toBeVisible();

    await expect.poll(() => releaseActiveStream !== null).toBe(true);
    const release = releaseActiveStream;
    if (release === null) throw new Error('S03 Dream reader was not releasable.');
    release();

    await expect(page.locator('#settled-count')).toHaveText('1');
    await expect(page.getByText('S03 same active output', { exact: true })).toHaveCount(1);
    await expect(page.getByRole('button', { name: 'Stop generating' })).toHaveCount(0);
    await expect(page.getByRole('textbox', { name: 'Chat input' })).toBeEnabled();
    expect(apiRequests.filter((entry) => entry === 'POST /api/claude-agent')).toHaveLength(0);
    expect(apiRequests.filter((entry) => entry.endsWith('/stop'))).toHaveLength(0);
    expect(apiRequests.some((entry) => /\/dream-agent\//.test(entry))).toBe(false);
    expect(violations).toEqual([]);
    expect(diagnostics).toEqual([]);
  } finally {
    await page.close();
    await harness?.close();
  }
});

test('S04 approve/reject/AskUser/network/reject-only stay canonical across Dream and Chat', async ({ page }) => {
  const token = 'dream-s04-confirmation-token';
  const threadId = 'thread-dream-s04-confirmation';
  const moduleSource = buildSurfaceHarnessModule(threadId, 'dream');
  const apiRequests: string[] = [];
  const violations: string[] = [];
  const confirmationRequests: Array<Record<string, unknown>> = [];
  const pendingToolCallIds = new Set([
    's04-approve',
    's04-reject',
    's04-ask-user',
    's04-network',
    's04-reject-only',
  ]);
  const expectedApproval = new Map<string, boolean>([
    ['s04-approve', true],
    ['s04-reject', false],
    ['s04-ask-user', true],
    ['s04-network', true],
    ['s04-reject-only', false],
  ]);
  let streamGets = 0;
  let interruptedStreams = 0;
  let terminalFrames = 0;
  let activeStreamResponse: ServerResponse | null = null;

  const toolParts = [
    {
      type: 'dynamic-tool',
      toolCallId: 's04-approve',
      toolName: 'Bash',
      state: 'input-available',
      input: { command: 'echo approve' },
      toolMetadata: { approvalRequested: true },
    },
    {
      type: 'dynamic-tool',
      toolCallId: 's04-reject',
      toolName: 'Bash',
      state: 'input-available',
      input: { command: 'echo reject' },
      toolMetadata: { approvalRequested: true },
    },
    {
      type: 'dynamic-tool',
      toolCallId: 's04-ask-user',
      toolName: 'AskUserQuestion',
      state: 'input-available',
      input: {
        questions: [{
          id: 'story-direction',
          question: 'Choose a direction',
          required: true,
          options: ['Gentle path', 'Mystery path'],
        }],
      },
      toolMetadata: { approvalRequested: true },
    },
    {
      type: 'dynamic-tool',
      toolCallId: 's04-network',
      toolName: 'Bash',
      state: 'input-available',
      input: { command: 'curl https://example.test/story' },
      toolMetadata: {
        approvalRequested: true,
        confirmationKind: 'sandbox_network',
        networkRequest: {
          host: 'example.test',
          policyMode: 'allowlist',
          matchedAllowedDomain: null,
        },
      },
    },
    {
      type: 'dynamic-tool',
      toolCallId: 's04-reject-only',
      toolName: 'Bash',
      state: 'input-available',
      input: { command: '[redacted unsafe request]' },
      toolMetadata: {
        approvalRequested: true,
        confirmationKind: 'reject_only',
      },
    },
  ];

  const handleApi = (request: IncomingMessage, response: ServerResponse): boolean => {
    const api = inspectStrictApiRequest(request, response, token, apiRequests, violations);
    if (api === null) return false;
    if (api.rejected) return true;
    if (handleCommonChatApi(api, response, threadId, violations)) return true;

    if (api.path === `/api/claude-agent/threads/${threadId}/messages`) {
      if (requireMethod(api, response, 'GET', violations)) {
        respondJson(response, 200, {
          thread: threadRecord(threadId, 'S04 canonical confirmations'),
          messages: [{
            id: 's04-user',
            role: 'user',
            parts: [{ type: 'text', text: 'Resolve every canonical confirmation' }],
            metadata: {},
            created_at: '2026-08-11T00:00:00Z',
          }, {
            id: 's04-assistant-tools',
            role: 'assistant',
            parts: toolParts,
            metadata: {},
            created_at: '2026-08-11T00:00:01Z',
          }],
        });
      }
      return true;
    }
    if (api.path === `/api/claude-agent/threads/${threadId}/status`) {
      if (requireMethod(api, response, 'GET', violations)) {
        respondJson(response, 200, threadStatus(
          pendingToolCallIds.size > 0,
          [...pendingToolCallIds],
        ));
      }
      return true;
    }
    if (api.path === `/api/claude-agent/threads/${threadId}/stream`) {
      if (!requireMethod(api, response, 'GET', violations)) return true;
      if (pendingToolCallIds.size === 0) {
        violations.push('S04 opened an SSE reader after all confirmations settled.');
        respondJson(response, 409, { detail: 'S04 confirmation turn is terminal.' });
        return true;
      }
      streamGets += 1;
      let completed = false;
      beginSse(response);
      activeStreamResponse = response;
      response.once('close', () => {
        if (!completed) interruptedStreams += 1;
        if (activeStreamResponse === response) activeStreamResponse = null;
      });
      response.once('finish', () => { completed = true; });
      return true;
    }
    if (api.path === '/api/claude-agent/tool-confirm') {
      if (!requireMethod(api, response, 'POST', violations)) return true;
      let rawBody = '';
      request.setEncoding('utf8');
      request.on('data', (chunk) => { rawBody += chunk; });
      request.on('end', () => {
        let body: Record<string, unknown>;
        try {
          body = JSON.parse(rawBody) as Record<string, unknown>;
        } catch {
          violations.push(`S04 confirmation body was not JSON: ${rawBody}`);
          respondJson(response, 400, { detail: 'Invalid confirmation JSON.' });
          return;
        }
        confirmationRequests.push(body);
        const toolCallId = typeof body.tool_call_id === 'string' ? body.tool_call_id : '';
        if (body.thread_id !== threadId || !pendingToolCallIds.has(toolCallId)) {
          violations.push(`S04 confirmation ownership mismatch: ${rawBody}`);
          respondJson(response, 409, { detail: 'Confirmation ownership mismatch.' });
          return;
        }
        if (body.approved !== expectedApproval.get(toolCallId)) {
          violations.push(`S04 confirmation decision mismatch: ${rawBody}`);
          respondJson(response, 400, { detail: 'Confirmation decision mismatch.' });
          return;
        }
        pendingToolCallIds.delete(toolCallId);
        respondJson(response, 200, { ok: true, approved: body.approved });

        if (pendingToolCallIds.size === 0) {
          const stream = activeStreamResponse;
          if (stream === null || stream.destroyed) {
            violations.push('S04 final confirmation had no live canonical stream to finish.');
            return;
          }
          terminalFrames += 1;
          stream.end([
            'data: {"type":"finish","finishReason":"stop"}',
            '',
          ].join('\n\n'));
        }
      });
      return true;
    }
    rejectUnexpectedApi(api, response, violations);
    return true;
  };

  const { diagnostics } = collectPageDiagnostics(
    page,
    (url) => url.pathname === `/api/claude-agent/threads/${threadId}/stream`,
  );
  await seedEnglishAuth(page, token);
  let harness: HarnessServer | null = null;
  try {
    harness = await startHarness({
      pagePath: '/dream-s04-confirmations',
      modulePath: '/dream-s04-confirmations-harness.js',
      moduleSource,
      pluginName: 'dream-s04-confirmations-e2e',
      handleApi,
    });
    await page.goto(`${harness.origin}/dream-s04-confirmations`);

    const surface = page.getByTestId('active-thread-surface');
    await expect(surface).toHaveAttribute('data-surface', 'dream');
    await expect.poll(() => streamGets).toBe(1);

    let dock = page.getByRole('alertdialog', { name: /Allow I&M to call the Bash tool/ });
    await expect(dock).toContainText('echo approve');
    await dock.getByRole('button', { name: 'Approve' }).click();
    await expect.poll(() => confirmationRequests.length).toBe(1);
    dock = page.getByRole('alertdialog', { name: /Allow I&M to call the Bash tool/ });
    await expect(dock).toContainText('echo reject');

    await page.getByRole('button', { name: 'Show Chat' }).click();
    await expect(surface).toHaveAttribute('data-surface', 'chat');
    await expect.poll(() => streamGets).toBe(2);
    await expect.poll(() => interruptedStreams).toBe(1);
    dock = page.getByRole('alertdialog', { name: /Allow I&M to call the Bash tool/ });
    await expect(dock).toContainText('echo reject');
    await dock.getByRole('button', { name: 'Reject' }).click();

    const askUserDock = page.getByRole('alertdialog', { name: 'I&M needs your answer' });
    await expect(askUserDock).toBeVisible();
    await askUserDock.getByRole('radio', { name: 'Gentle path' }).check();
    await askUserDock.getByRole('button', { name: 'Submit' }).click();
    await expect.poll(() => confirmationRequests.length).toBe(3);

    await page.getByRole('button', { name: 'Show Dream' }).click();
    await expect(surface).toHaveAttribute('data-surface', 'dream');
    await expect.poll(() => streamGets).toBe(3);
    await expect.poll(() => interruptedStreams).toBe(2);

    const networkDock = page.getByRole('alertdialog', {
      name: /Allow I&M to make a network request via Bash/,
    });
    await expect(networkDock).toContainText('example.test');
    await expect(networkDock).toContainText('Allowlist');
    await networkDock.getByRole('button', { name: 'Approve' }).click();
    await expect.poll(() => confirmationRequests.length).toBe(4);

    const rejectOnlyDock = page.getByRole('alertdialog', {
      name: 'This request requires safe handling',
    });
    await expect(rejectOnlyDock).toBeVisible();
    await expect(rejectOnlyDock.getByRole('button')).toHaveCount(1);
    await page.keyboard.press('Control+Enter');
    expect(confirmationRequests).toHaveLength(4);
    await expect(rejectOnlyDock).toBeVisible();
    await rejectOnlyDock.getByRole('button', { name: 'Reject and continue' }).click();

    await expect.poll(() => terminalFrames).toBe(1);
    await expect(page.locator('#settled-count')).toHaveText('1');
    await expect(page.getByRole('alertdialog')).toHaveCount(0);
    await expect(page.getByRole('textbox', { name: 'Chat input' })).toBeEnabled();
    await expect(page.getByRole('button', { name: 'Stop generating' })).toHaveCount(0);

    expect(confirmationRequests).toEqual([
      {
        thread_id: threadId,
        tool_call_id: 's04-approve',
        approved: true,
      },
      {
        thread_id: threadId,
        tool_call_id: 's04-reject',
        approved: false,
        reason: 'User rejected the tool execution',
      },
      {
        thread_id: threadId,
        tool_call_id: 's04-ask-user',
        approved: true,
        answers: { 'Choose a direction': 'Gentle path' },
      },
      {
        thread_id: threadId,
        tool_call_id: 's04-network',
        approved: true,
      },
      {
        thread_id: threadId,
        tool_call_id: 's04-reject-only',
        approved: false,
        reason: 'User rejected the tool execution',
      },
    ]);
    expect(apiRequests.filter((entry) => entry === 'POST /api/claude-agent/tool-confirm'))
      .toHaveLength(5);
    expect(apiRequests.filter((entry) => entry === 'POST /api/claude-agent')).toHaveLength(0);
    expect(apiRequests.some((entry) => /\/dream-agent\//.test(entry))).toBe(false);
    expect(violations).toEqual([]);
    expect(diagnostics).toEqual([]);
  } finally {
    await page.close();
    await harness?.close();
  }
});

test('S05 subagent running -> completed projection stays observational and history never shows Stop', async ({ page }) => {
  const token = 'dream-s05-subagent-token';
  const threadId = 'thread-dream-s05-subagent';
  const moduleSource = buildSurfaceHarnessModule(threadId, 'chat');
  const apiRequests: string[] = [];
  const violations: string[] = [];
  let subagentPhase: 'running' | 'completed' = 'running';
  let subagentReads = 0;

  const subagentTask = (): Record<string, unknown> => ({
    task_id: 's05-task',
    agent_id: 's05-agent',
    agent_type: 'Explore',
    description: 'Investigate shared runtime',
    summary: subagentPhase === 'completed' ? 'Shared runtime verified' : null,
    status: subagentPhase,
    tool_call_id: 's05-agent-tool',
    spawn_depth: 1,
    started_at: '2026-08-11T00:00:01Z',
    finished_at: subagentPhase === 'completed' ? '2026-08-11T00:00:02Z' : null,
    duration_ms: subagentPhase === 'completed' ? 1000 : null,
    error: null,
    activity: [],
    messages: [],
    message_count: 0,
    messages_truncated: false,
    projection_version: 2,
  });

  const handleApi = (request: IncomingMessage, response: ServerResponse): boolean => {
    const api = inspectStrictApiRequest(request, response, token, apiRequests, violations);
    if (api === null) return false;
    if (api.rejected) return true;

    if (api.path === `/api/claude-agent/threads/${threadId}/messages`) {
      if (requireMethod(api, response, 'GET', violations)) {
        respondJson(response, 200, {
          thread: threadRecord(threadId, 'S05 subagent projection'),
          messages: [{
            id: 's05-user',
            role: 'user',
            parts: [{ type: 'text', text: 'Delegate a bounded investigation' }],
            metadata: {},
            created_at: '2026-08-11T00:00:00Z',
          }, {
            id: 's05-assistant-tool',
            role: 'assistant',
            parts: [{
              type: 'dynamic-tool',
              toolCallId: 's05-agent-tool',
              toolName: 'Agent',
              state: 'output-available',
              input: { description: 'Investigate shared runtime' },
              output: { task_id: 's05-task' },
            }],
            metadata: {},
            created_at: '2026-08-11T00:00:01Z',
          }],
        });
      }
      return true;
    }
    if (api.path === `/api/claude-agent/threads/${threadId}/status`) {
      if (requireMethod(api, response, 'GET', violations)) {
        respondJson(response, 200, threadStatus(false, [], 1));
      }
      return true;
    }
    if (api.path === `/api/claude-agent/threads/${threadId}/subagents`) {
      if (requireMethod(api, response, 'GET', violations)) {
        subagentReads += 1;
        respondJson(response, 200, {
          exists: true,
          tasks: [subagentTask()],
          counts: {
            running: subagentPhase === 'running' ? 1 : 0,
            completed: subagentPhase === 'completed' ? 1 : 0,
            ended: 0,
            total: 1,
          },
          updated_at: subagentPhase === 'completed'
            ? '2026-08-11T00:00:02Z'
            : '2026-08-11T00:00:01Z',
        });
      }
      return true;
    }
    if (handleCommonChatApi(api, response, threadId, violations)) return true;
    rejectUnexpectedApi(api, response, violations);
    return true;
  };

  const { diagnostics } = collectPageDiagnostics(page);
  await seedEnglishAuth(page, token);
  let harness: HarnessServer | null = null;
  try {
    harness = await startHarness({
      pagePath: '/dream-s05-subagent',
      modulePath: '/dream-s05-subagent-harness.js',
      moduleSource,
      pluginName: 'dream-s05-subagent-e2e',
      handleApi,
    });
    await page.goto(`${harness.origin}/dream-s05-subagent`);

    const surface = page.getByTestId('active-thread-surface');
    await expect(surface).toHaveAttribute('data-surface', 'chat');
    const runningSummary = page.getByRole('button', {
      name: 'Subagent tasks: 1 running · 0 completed',
    });
    await expect(runningSummary).toBeVisible();
    await expect(page.getByRole('button', { name: 'Stop generating' })).toHaveCount(0);
    await expect(page.getByRole('textbox', { name: 'Chat input' })).toBeEnabled();

    await runningSummary.click();
    const chatSidebar = page.locator('aside[aria-label="Subagents"]');
    await expect(chatSidebar).toBeVisible();
    await expect(chatSidebar).toContainText('Investigate shared runtime');
    await expect(chatSidebar.getByText('Running', { exact: true })).toBeVisible();

    subagentPhase = 'completed';
    await chatSidebar.getByRole('button', { name: 'Refresh tasks' }).click();
    const completedSummary = page.getByRole('button', {
      name: 'Subagent tasks: 1 completed',
    });
    await expect(completedSummary).toBeVisible();
    await expect(chatSidebar.getByText('Completed', { exact: true }).first()).toBeVisible();

    await page.getByRole('button', { name: 'Show Dream' }).click();
    await expect(surface).toHaveAttribute('data-surface', 'dream');
    const historicalTask = page.getByRole('button', {
      name: 'Open subagent task: Investigate shared runtime',
    });
    await expect(historicalTask).toBeVisible();
    await expect(page.getByRole('button', { name: 'Stop generating' })).toHaveCount(0);
    const input = page.getByRole('textbox', { name: 'Chat input' });
    await expect(input).toBeEnabled();
    await input.fill('Continue the main thread after the historical task');
    await expect(page.getByRole('button', { name: 'Send message' })).toBeEnabled();

    await historicalTask.click();
    const dreamSidebar = page.locator('aside[aria-label="Subagents"]');
    await expect(dreamSidebar).toBeVisible();
    await expect(dreamSidebar).toContainText('Investigate shared runtime');
    await expect(dreamSidebar.getByText('Completed', { exact: true }).first()).toBeVisible();

    expect(subagentReads).toBeGreaterThanOrEqual(2);
    expect(apiRequests.filter((entry) => entry === 'POST /api/claude-agent')).toHaveLength(0);
    expect(apiRequests.filter((entry) => entry.endsWith('/stream'))).toHaveLength(0);
    expect(apiRequests.filter((entry) => entry.endsWith('/stop'))).toHaveLength(0);
    expect(apiRequests.some((entry) => /\/dream-agent\//.test(entry))).toBe(false);
    expect(violations).toEqual([]);
    expect(diagnostics).toEqual([]);
  } finally {
    await page.close();
    await harness?.close();
  }
});

test('S06 uncertain Stop keeps Dream locked, then typed success recovers canonical idle history', async ({ page }) => {
  const token = 'dream-stop-fixture-token';
  const threadId = 'thread-dream-stop';
  const moduleSource = `
    import React, { useState } from 'react';
    import { createRoot } from 'react-dom/client';
    import '/src/i18n.ts';
    import '/src/styles/tokens.css';
    import '/src/styles/markdown.css';
    import '/src/pages/story-workspace/StoryWorkspaceDreamPage.css';
    import { StoryWorkspaceDreamThreadChat } from '/src/components/story-workspace/dream/StoryWorkspaceDreamThreadChat.tsx';

    function Harness() {
      const [settled, setSettled] = useState(0);
      return React.createElement('main', {
        style: { height: '820px', display: 'flex', padding: '16px' },
      },
        React.createElement('output', { id: 'settled-count' }, String(settled)),
        React.createElement(StoryWorkspaceDreamThreadChat, {
          threadId: '${threadId}',
          onSettled: () => setSettled((value) => value + 1),
        }),
      );
    }
    createRoot(document.querySelector('#root')).render(React.createElement(Harness));
  `;
  const apiRequests: string[] = [];
  const violations: string[] = [];
  let phase: 'running' | 'terminal' = 'running';
  let stopAttempts = 0;
  let statusReads = 0;
  let streamGets = 0;
  let interruptedStreams = 0;

  const handleApi = (request: IncomingMessage, response: ServerResponse): boolean => {
    const api = inspectStrictApiRequest(
      request,
      response,
      token,
      apiRequests,
      violations,
    );
    if (api === null) return false;
    if (api.rejected) return true;
    if (handleCommonChatApi(api, response, threadId, violations)) return true;

    if (api.path === `/api/claude-agent/threads/${threadId}/messages`) {
      if (requireMethod(api, response, 'GET', violations)) {
        respondJson(response, 200, {
          thread: {
            id: threadId,
            title: 'Dream Stop recovery',
            created_at: '2026-08-11T00:00:00Z',
            updated_at: '2026-08-11T00:00:01Z',
          },
          messages: [{
            id: 'stop-user',
            role: 'user',
            parts: [{ type: 'text', text: 'Stop the active main turn' }],
            metadata: {},
            created_at: '2026-08-11T00:00:00Z',
          }, ...(phase === 'terminal' ? [{
            id: 'stop-partial-terminal',
            role: 'assistant',
            parts: [{ type: 'text', text: 'partial retained after acknowledged Stop' }],
            metadata: {},
            created_at: '2026-08-11T00:00:01Z',
          }] : [])],
        });
      }
      return true;
    }
    if (api.path === `/api/claude-agent/threads/${threadId}/status`) {
      if (requireMethod(api, response, 'GET', violations)) {
        statusReads += 1;
        respondJson(response, 200, {
          running: phase === 'running',
          lifecycle: phase === 'running' ? 'running' : 'idle',
          turn_count: phase === 'running' ? 0 : 1,
          pending_tool_call_ids: [],
          tool_confirmation_observation: 'known',
        });
      }
      return true;
    }
    if (api.path === `/api/claude-agent/threads/${threadId}/stream`) {
      if (!requireMethod(api, response, 'GET', violations)) return true;
      streamGets += 1;
      beginSse(response);
      response.write([
        'data: {"type":"text-start","id":"stop-live"}',
        'data: {"type":"text-delta","id":"stop-live","delta":"partial before Stop"}',
        '',
      ].join('\n\n'));
      response.once('close', () => { interruptedStreams += 1; });
      return true;
    }
    if (api.path === `/api/claude-agent/threads/${threadId}/stop`) {
      if (!requireMethod(api, response, 'POST', violations)) return true;
      stopAttempts += 1;
      if (stopAttempts === 1) {
        // Non-2xx is authoritative-unknown and must preserve the lock/readers.
        respondJson(response, 503, { detail: 'Transient stop owner unavailable.' });
      } else if (stopAttempts === 2) {
        // A 2xx response without the required stop_requested boolean is also
        // authoritative-unknown and must preserve the running lock/readers.
        respondJson(response, 200, { ok: true });
      } else if (stopAttempts === 3) {
        phase = 'terminal';
        respondJson(response, 200, { ok: true, stop_requested: true });
      } else {
        violations.push('The Stop UI submitted more than the three explicit user attempts.');
        respondJson(response, 409, { detail: 'Unexpected extra Stop.' });
      }
      return true;
    }
    rejectUnexpectedApi(api, response, violations);
    return true;
  };

  const { diagnostics, expectedFailures } = collectPageDiagnostics(
    page,
    (url) => url.pathname === `/api/claude-agent/threads/${threadId}/stream`,
    (text) => text.includes('503 (Service Unavailable)'),
  );
  await page.addInitScript(({ authToken }) => {
    localStorage.setItem('auth_token', authToken);
    localStorage.setItem('ink-language', 'en');
  }, { authToken: token });

  let harness: HarnessServer | null = null;
  try {
    harness = await startHarness({
      pagePath: '/dream-stop-recovery',
      modulePath: '/dream-stop-recovery-harness.js',
      moduleSource,
      pluginName: 'dream-stop-recovery-e2e',
      handleApi,
    });
    await page.goto(`${harness.origin}/dream-stop-recovery`);

    await expect.poll(() => streamGets).toBe(1);
    await expect(page.getByText('partial before Stop', { exact: true })).toBeVisible();
    const input = page.getByRole('textbox', { name: 'Chat input' });
    const stop = page.getByRole('button', { name: 'Stop generating' });
    await expect(input).toBeEnabled();
    await expect(stop).toBeEnabled();
    await expect(page.getByRole('button', { name: 'Send message' })).toHaveCount(0);

    const statusReadsBeforeUncertainStop = statusReads;
    await stop.click();
    await expect.poll(() => stopAttempts).toBe(1);
    await expect.poll(() => statusReads).toBeGreaterThan(statusReadsBeforeUncertainStop);
    await expect(stop).toBeEnabled();
    await expect(page.getByRole('button', { name: 'Send message' })).toHaveCount(0);
    expect(apiRequests.filter((entry) => entry === 'POST /api/claude-agent')).toHaveLength(0);
    expect(interruptedStreams).toBe(0);
    await expect(page.locator('#settled-count')).toHaveText('0');

    await stop.click();
    await expect.poll(() => stopAttempts).toBe(2);
    await expect(stop).toBeEnabled();
    await expect(page.getByRole('button', { name: 'Send message' })).toHaveCount(0);
    expect(interruptedStreams).toBe(0);
    await expect(page.locator('#settled-count')).toHaveText('0');

    await stop.click();
    await expect.poll(() => stopAttempts).toBe(3);
    await expect.poll(() => interruptedStreams).toBe(1);
    await expect(page.getByText('partial retained after acknowledged Stop', { exact: true }))
      .toHaveCount(1);
    await expect(page.locator('#settled-count')).toHaveText('1');
    await expect(input).toBeEnabled();
    await expect(stop).toHaveCount(0);

    expect(apiRequests.filter((entry) => entry.endsWith('/stop'))).toHaveLength(3);
    expect(apiRequests.filter((entry) => entry === 'POST /api/claude-agent')).toHaveLength(0);
    expect(expectedFailures.some((entry) => entry.includes('503 (Service Unavailable)'))).toBe(true);
    expect(violations).toEqual([]);
    expect(diagnostics).toEqual([]);
  } finally {
    await page.close();
    await harness?.close();
  }
});

async function runFailureRecoveryScenario(page: Page, scenario: FailureScenario): Promise<void> {
  const token = `dream-${scenario.id.toLowerCase()}-fixture-token`;
  const threadId = `thread-dream-${scenario.id.toLowerCase()}`;
  const moduleSource = `
    import React, { useState } from 'react';
    import { createRoot } from 'react-dom/client';
    import '/src/i18n.ts';
    import '/src/styles/tokens.css';
    import '/src/styles/markdown.css';
    import '/src/pages/story-workspace/StoryWorkspaceDreamPage.css';
    import { StoryWorkspaceDreamThreadChat } from '/src/components/story-workspace/dream/StoryWorkspaceDreamThreadChat.tsx';

    function Harness() {
      const [settled, setSettled] = useState(0);
      return React.createElement('main', {
        style: { height: '820px', display: 'flex', padding: '16px' },
      },
        React.createElement('output', { id: 'settled-count' }, String(settled)),
        React.createElement(StoryWorkspaceDreamThreadChat, {
          threadId: '${threadId}',
          onSettled: () => setSettled((value) => value + 1),
        }),
      );
    }
    createRoot(document.querySelector('#root')).render(React.createElement(Harness));
  `;
  const apiRequests: string[] = [];
  const violations: string[] = [];
  let phase: 'running' | 'terminal' = 'running';
  let partialPersisted = false;
  let streamGets = 0;
  let terminalFrames = 0;
  let releaseFirstDisconnect: (() => void) | null = null;

  const handleApi = (request: IncomingMessage, response: ServerResponse): boolean => {
    const api = inspectStrictApiRequest(
      request,
      response,
      token,
      apiRequests,
      violations,
    );
    if (api === null) return false;
    if (api.rejected) return true;
    if (handleCommonChatApi(api, response, threadId, violations)) return true;

    if (api.path === `/api/claude-agent/threads/${threadId}/messages`) {
      if (requireMethod(api, response, 'GET', violations)) {
        respondJson(response, 200, {
          thread: {
            id: threadId,
            title: `${scenario.id} failure recovery`,
            created_at: '2026-08-11T00:00:00Z',
            updated_at: '2026-08-11T00:00:01Z',
          },
          messages: [{
            id: `${scenario.id}-user`,
            role: 'user',
            parts: [{ type: 'text', text: `${scenario.id} user row retained` }],
            metadata: {},
            created_at: '2026-08-11T00:00:00Z',
          }, ...(partialPersisted && scenario.partialText ? [{
            id: `${scenario.id}-partial-assistant`,
            role: 'assistant',
            parts: [{ type: 'text', text: scenario.partialText }],
            metadata: { interrupted: true },
            created_at: '2026-08-11T00:00:01Z',
          }] : [])],
        });
      }
      return true;
    }
    if (api.path === `/api/claude-agent/threads/${threadId}/status`) {
      if (requireMethod(api, response, 'GET', violations)) {
        respondJson(response, 200, {
          running: phase === 'running',
          lifecycle: phase === 'running' ? 'running' : 'idle',
          turn_count: phase === 'running' ? 0 : 1,
          pending_tool_call_ids: [],
          tool_confirmation_observation: 'known',
        });
      }
      return true;
    }
    if (api.path === `/api/claude-agent/threads/${threadId}/stream`) {
      if (!requireMethod(api, response, 'GET', violations)) return true;
      streamGets += 1;
      beginSse(response);
      if (streamGets === 1) {
        if (scenario.partialText) {
          response.write([
            `data: {"type":"text-start","id":"${scenario.id}-live"}`,
            `data: ${JSON.stringify({
              type: 'text-delta',
              id: `${scenario.id}-live`,
              delta: scenario.partialText,
            })}`,
            '',
          ].join('\n\n'));
        }
        releaseFirstDisconnect = () => {
          partialPersisted = scenario.partialText !== null;
          response.end();
          releaseFirstDisconnect = null;
        };
      } else if (streamGets === 2) {
        phase = 'terminal';
        terminalFrames += 1;
        response.end([
          `data: ${JSON.stringify({
            type: 'error',
            errorText: `${scenario.id} deterministic provider failure`,
          })}`,
          'data: {"type":"finish","finishReason":"error"}',
          '',
        ].join('\n\n'));
      } else {
        violations.push(`Unexpected third SSE request for ${scenario.id}.`);
        response.end();
      }
      return true;
    }
    rejectUnexpectedApi(api, response, violations);
    return true;
  };

  const { diagnostics } = collectPageDiagnostics(page);
  await page.addInitScript(({ authToken }) => {
    localStorage.setItem('auth_token', authToken);
    localStorage.setItem('ink-language', 'en');
  }, { authToken: token });

  let harness: HarnessServer | null = null;
  try {
    harness = await startHarness({
      pagePath: `/dream-${scenario.id.toLowerCase()}-failure`,
      modulePath: `/dream-${scenario.id.toLowerCase()}-failure-harness.js`,
      moduleSource,
      pluginName: `dream-${scenario.id.toLowerCase()}-failure-recovery-e2e`,
      handleApi,
    });
    const url = `${harness.origin}/dream-${scenario.id.toLowerCase()}-failure`;
    await page.goto(url);

    await expect.poll(() => streamGets).toBe(1);
    await expect(page.getByText(`${scenario.id} user row retained`, { exact: true })).toHaveCount(1);
    if (scenario.partialText) {
      await expect(page.getByText(scenario.partialText, { exact: true })).toBeVisible();
    } else {
      await expect(page.getByRole('button', { name: 'Stop generating' })).toBeVisible();
    }

    await expect.poll(() => releaseFirstDisconnect !== null).toBe(true);
    const release = releaseFirstDisconnect;
    if (release === null) throw new Error(`${scenario.id} disconnect was not releasable.`);
    release();

    await expect.poll(() => streamGets).toBe(2);
    await expect.poll(() => terminalFrames).toBe(1);
    await expect(page.locator('#settled-count')).toHaveText('1');
    await expect(page.getByRole('textbox', { name: 'Chat input' })).toBeEnabled();
    await expect(page.getByRole('button', { name: 'Stop generating' })).toHaveCount(0);
    await expect(page.getByText(`${scenario.id} user row retained`, { exact: true })).toHaveCount(1);
    if (scenario.partialText) {
      await expect(page.getByText(scenario.partialText, { exact: true })).toHaveCount(1);
    }

    await page.reload();
    await expect(page.getByRole('textbox', { name: 'Chat input' })).toBeEnabled();
    await expect(page.locator('#settled-count')).toHaveText('0');
    await expect(page.getByText(`${scenario.id} user row retained`, { exact: true })).toHaveCount(1);
    if (scenario.partialText) {
      await expect(page.getByText(scenario.partialText, { exact: true })).toHaveCount(1);
    }
    expect(streamGets).toBe(2);
    expect(terminalFrames).toBe(1);
    expect(apiRequests.filter((entry) => entry === 'POST /api/claude-agent')).toHaveLength(0);
    expect(apiRequests.filter((entry) => entry.endsWith('/stop'))).toHaveLength(0);
    expect(violations).toEqual([]);
    expect(diagnostics).toEqual([]);
  } finally {
    await page.close();
    await harness?.close();
  }
}

for (const scenario of [
  {
    id: 'S07',
    name: 'pre-output disconnect recovers one failed terminal across reload',
    partialText: null,
  },
  {
    id: 'S08',
    name: 'partial-output disconnect retains one failed terminal across reload',
    partialText: 'partial output retained after failure',
  },
] satisfies FailureScenario[]) {
  test(`${scenario.id} ${scenario.name}`, async ({ page }) => {
    await runFailureRecoveryScenario(page, scenario);
  });
}

test('S09 browser disconnect reconnects the running thread and preserves AskUser draft input', async ({ page }) => {
  const token = 'dream-s09-reconnect-token';
  const threadId = 'thread-dream-s09-reconnect';
  const toolCallId = 's09-ask-user';
  const moduleSource = buildDreamHarnessModule(threadId);
  const apiRequests: string[] = [];
  const violations: string[] = [];
  const confirmationRequests: Array<Record<string, unknown>> = [];
  let complete = false;
  let streamGets = 0;
  let terminalFrames = 0;
  let disconnectFirstStream: (() => void) | null = null;
  let activeReconnectStream: ServerResponse | null = null;

  const messages = (): Array<Record<string, unknown>> => [{
    id: 's09-user',
    role: 'user',
    parts: [{ type: 'text', text: 'Keep my answer while reconnecting' }],
    metadata: {},
    created_at: '2026-08-11T00:00:00Z',
  }, {
    id: 's09-assistant',
    role: 'assistant',
    parts: [{
      type: 'dynamic-tool',
      toolCallId,
      toolName: 'AskUserQuestion',
      state: 'input-available',
      input: {
        questions: [{
          id: 'reconnect-answer',
          question: 'Reconnect answer',
          type: 'text',
          required: true,
        }],
      },
      toolMetadata: complete
        ? { approvalRequested: false, approvalSettled: true }
        : { approvalRequested: true },
    }, ...(complete ? [{ type: 'text', text: 'S09 continued after preserved answer' }] : [])],
    metadata: {},
    created_at: '2026-08-11T00:00:01Z',
  }];

  const handleApi = (request: IncomingMessage, response: ServerResponse): boolean => {
    const api = inspectStrictApiRequest(request, response, token, apiRequests, violations);
    if (api === null) return false;
    if (api.rejected) return true;
    if (handleCommonChatApi(api, response, threadId, violations)) return true;
    if (api.path === `/api/claude-agent/threads/${threadId}/messages`) {
      if (requireMethod(api, response, 'GET', violations)) {
        respondJson(response, 200, {
          thread: threadRecord(threadId, 'S09 reconnect input preservation'),
          messages: messages(),
        });
      }
      return true;
    }
    if (api.path === `/api/claude-agent/threads/${threadId}/status`) {
      if (requireMethod(api, response, 'GET', violations)) {
        respondJson(response, 200, threadStatus(!complete, complete ? [] : [toolCallId]));
      }
      return true;
    }
    if (api.path === `/api/claude-agent/threads/${threadId}/stream`) {
      if (!requireMethod(api, response, 'GET', violations)) return true;
      if (complete) {
        violations.push('S09 opened an SSE reader after the turn completed.');
        respondJson(response, 409, { detail: 'S09 turn already completed.' });
        return true;
      }
      streamGets += 1;
      beginSse(response);
      if (streamGets === 1) {
        disconnectFirstStream = () => {
          response.end();
          disconnectFirstStream = null;
        };
      } else if (streamGets === 2) {
        activeReconnectStream = response;
        response.once('close', () => {
          if (activeReconnectStream === response) activeReconnectStream = null;
        });
      } else {
        violations.push(`S09 opened unexpected stream #${streamGets}.`);
        response.end();
      }
      return true;
    }
    if (api.path === '/api/claude-agent/tool-confirm') {
      if (!requireMethod(api, response, 'POST', violations)) return true;
      let rawBody = '';
      request.setEncoding('utf8');
      request.on('data', (chunk) => { rawBody += chunk; });
      request.on('end', () => {
        let body: Record<string, unknown>;
        try {
          body = JSON.parse(rawBody) as Record<string, unknown>;
        } catch {
          violations.push(`S09 confirmation was not JSON: ${rawBody}`);
          respondJson(response, 400, { detail: 'Invalid S09 confirmation JSON.' });
          return;
        }
        confirmationRequests.push(body);
        if (body.thread_id !== threadId || body.tool_call_id !== toolCallId || body.approved !== true) {
          violations.push(`S09 confirmation ownership mismatch: ${rawBody}`);
          respondJson(response, 409, { detail: 'S09 confirmation ownership mismatch.' });
          return;
        }
        complete = true;
        respondJson(response, 200, { ok: true, approved: true });
        const stream = activeReconnectStream;
        if (stream === null || stream.destroyed) {
          violations.push('S09 answer completed without a live reconnected stream.');
          return;
        }
        terminalFrames += 1;
        stream.end([
          'data: {"type":"text-start","id":"s09-final"}',
          'data: {"type":"text-delta","id":"s09-final","delta":"S09 continued after preserved answer"}',
          'data: {"type":"text-end","id":"s09-final"}',
          'data: {"type":"message-final","text":"S09 continued after preserved answer"}',
          'data: {"type":"finish","finishReason":"stop"}',
          '',
        ].join('\n\n'));
      });
      return true;
    }
    rejectUnexpectedApi(api, response, violations);
    return true;
  };

  const { diagnostics } = collectPageDiagnostics(page);
  await seedEnglishAuth(page, token);
  let harness: HarnessServer | null = null;
  try {
    harness = await startHarness({
      pagePath: '/dream-s09-reconnect',
      modulePath: '/dream-s09-reconnect-harness.js',
      moduleSource,
      pluginName: 'dream-s09-reconnect-e2e',
      handleApi,
    });
    await page.goto(`${harness.origin}/dream-s09-reconnect`);

    await expect.poll(() => streamGets).toBe(1);
    const answer = page.getByRole('textbox', { name: 'Reconnect answer' });
    await expect(answer).toBeVisible();
    await answer.fill('保留这个答案🙂');
    await expect.poll(() => disconnectFirstStream !== null).toBe(true);
    const disconnect = disconnectFirstStream;
    if (disconnect === null) throw new Error('S09 first stream was not disconnectable.');
    disconnect();

    await expect.poll(() => streamGets).toBe(2);
    await expect(answer).toHaveValue('保留这个答案🙂');
    await page.getByRole('button', { name: 'Submit' }).click();

    await expect.poll(() => terminalFrames).toBe(1);
    await expect(page.locator('#settled-count')).toHaveText('1');
    await expect(page.getByText('S09 continued after preserved answer', { exact: true }))
      .toHaveCount(1);
    await expect(page.getByRole('alertdialog')).toHaveCount(0);
    await expect(page.getByRole('textbox', { name: 'Chat input' })).toBeEnabled();
    await expect(page.getByRole('button', { name: 'Stop generating' })).toHaveCount(0);

    expect(confirmationRequests).toEqual([{
      thread_id: threadId,
      tool_call_id: toolCallId,
      approved: true,
      answers: { 'Reconnect answer': '保留这个答案🙂' },
    }]);
    expect(apiRequests.filter((entry) => entry.endsWith('/stream'))).toHaveLength(2);
    expect(apiRequests.filter((entry) => entry === 'POST /api/claude-agent/tool-confirm'))
      .toHaveLength(1);
    expect(apiRequests.filter((entry) => entry === 'POST /api/claude-agent')).toHaveLength(0);
    expect(apiRequests.filter((entry) => entry.endsWith('/stop'))).toHaveLength(0);
    expect(violations).toEqual([]);
    expect(diagnostics).toEqual([]);
  } finally {
    await page.close();
    await harness?.close();
  }
});

test('S10 page refresh reconstructs terminal history and settled confirmation without a new turn', async ({ page }) => {
  const token = 'dream-s10-refresh-token';
  const threadId = 'thread-dream-s10-refresh';
  const moduleSource = buildDreamHarnessModule(threadId);
  const apiRequests: string[] = [];
  const violations: string[] = [];

  const handleApi = (request: IncomingMessage, response: ServerResponse): boolean => {
    const api = inspectStrictApiRequest(request, response, token, apiRequests, violations);
    if (api === null) return false;
    if (api.rejected) return true;
    if (handleCommonChatApi(api, response, threadId, violations)) return true;
    if (api.path === `/api/claude-agent/threads/${threadId}/messages`) {
      if (requireMethod(api, response, 'GET', violations)) {
        respondJson(response, 200, {
          thread: threadRecord(threadId, 'S10 terminal refresh'),
          messages: [{
            id: 's10-user',
            role: 'user',
            parts: [{ type: 'text', text: 'S10 persisted user row' }],
            metadata: {},
            created_at: '2026-08-11T00:00:00Z',
          }, {
            id: 's10-assistant',
            role: 'assistant',
            parts: [{
              type: 'dynamic-tool',
              toolCallId: 's10-settled-tool',
              toolName: 'Bash',
              state: 'input-available',
              input: { command: 'echo historical' },
              toolMetadata: { approvalRequested: true },
            }, {
              type: 'text',
              text: 'S10 persisted terminal answer',
            }],
            metadata: {},
            created_at: '2026-08-11T00:00:01Z',
          }],
        });
      }
      return true;
    }
    if (api.path === `/api/claude-agent/threads/${threadId}/status`) {
      if (requireMethod(api, response, 'GET', violations)) {
        respondJson(response, 200, threadStatus(false, [], 1));
      }
      return true;
    }
    rejectUnexpectedApi(api, response, violations);
    return true;
  };

  const { diagnostics } = collectPageDiagnostics(page);
  await seedEnglishAuth(page, token);
  let harness: HarnessServer | null = null;
  try {
    harness = await startHarness({
      pagePath: '/dream-s10-refresh',
      modulePath: '/dream-s10-refresh-harness.js',
      moduleSource,
      pluginName: 'dream-s10-refresh-e2e',
      handleApi,
    });
    const url = `${harness.origin}/dream-s10-refresh`;
    await page.goto(url);

    const terminalText = page.getByText('S10 persisted terminal answer', { exact: true });
    await expect(terminalText).toHaveCount(1);
    await expect(page.getByText('S10 persisted user row', { exact: true })).toHaveCount(1);
    await expect(page.getByRole('alertdialog')).toHaveCount(0);
    await expect(page.getByRole('button', { name: 'Stop generating' })).toHaveCount(0);
    await expect(page.getByRole('textbox', { name: 'Chat input' })).toBeEnabled();

    await page.reload();

    await expect(terminalText).toHaveCount(1);
    await expect(page.getByText('S10 persisted user row', { exact: true })).toHaveCount(1);
    await expect(page.getByRole('alertdialog')).toHaveCount(0);
    await expect(page.getByRole('button', { name: 'Stop generating' })).toHaveCount(0);
    await expect(page.getByRole('textbox', { name: 'Chat input' })).toBeEnabled();

    expect(apiRequests.filter((entry) => entry.endsWith('/messages'))).toHaveLength(4);
    expect(apiRequests.filter((entry) => entry.endsWith('/status'))).toHaveLength(2);
    expect(apiRequests.filter((entry) => entry.endsWith('/stream'))).toHaveLength(0);
    expect(apiRequests.filter((entry) => entry === 'POST /api/claude-agent')).toHaveLength(0);
    expect(apiRequests.filter((entry) => entry === 'POST /api/claude-agent/tool-confirm'))
      .toHaveLength(0);
    expect(apiRequests.some((entry) => /\/dream-agent\//.test(entry))).toBe(false);
    expect(violations).toEqual([]);
    expect(diagnostics).toEqual([]);
  } finally {
    await page.close();
    await harness?.close();
  }
});

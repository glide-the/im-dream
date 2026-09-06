// [Input] Versioned sandbox request plus server-owned parent-origin and compatibility policy.
// [Output] Independently deployable opaque-origin proxy with a closed-network CSP, strict relay, and actor-effective window.im shim.
// [Pos] Browser sandbox asset; it never receives upstream URLs, credentials, Chat history, or Runtime snapshots.
// [Sync] 2026-09-06: derive window.im feature detection from the authenticated app/_dream Host handshake and fail closed before it.

import { readMcpAppsPluginManifest } from '@ink-dream/mcp-apps-runtime';
import { MCP_APPS_HOST_MANIFEST } from '../_dream/components/chat/mcp-apps/host-policy';

export const runtime = 'nodejs';
export const dynamic = 'force-dynamic';

const WINDOW_IM_SHIM_SOURCE = String.raw`(() => {
  const state = { context: {}, nextId: 0, pending: new Map() };
  const request = (method, params) => new Promise((resolve, reject) => {
    const id = 'window.im:' + (++state.nextId);
    const timer = setTimeout(() => {
      state.pending.delete(id);
      reject(new Error('window.im request timed out.'));
    }, __IM_REQUEST_TIMEOUT_MS__);
    state.pending.set(id, { resolve, reject, timer });
    parent.postMessage({ jsonrpc: '2.0', id, method, params }, '*');
  });
  const buildApi = (toolCalls, uiMessage) => {
    if (!toolCalls && !uiMessage) return undefined;
    const api = {};
    if (toolCalls) {
      Object.defineProperty(api, 'callTool', {
        enumerable: true,
        value: (name, args = {}) => request('tools/call', { name, arguments: args }),
      });
    }
    if (uiMessage) {
      Object.defineProperty(api, 'sendFollowUpMessage', {
        enumerable: true,
        value: ({ prompt, scrollToBottom } = {}) => {
          if (typeof prompt !== 'string' || !prompt.trim() || (scrollToBottom !== undefined && typeof scrollToBottom !== 'boolean')) {
            return Promise.reject(new TypeError('sendFollowUpMessage requires a non-empty prompt.'));
          }
          return request('ui/message', {
            role: 'user',
            content: [{ type: 'text', text: prompt }],
          });
        },
      });
    }
    for (const key of ['toolInput', 'toolOutput', 'toolResponseMetadata', 'theme', 'locale', 'displayMode']) {
      Object.defineProperty(api, key, { enumerable: true, get: () => state.context[key] });
    }
    return Object.freeze(api);
  };
  let exposedApi;
  Object.defineProperty(window, 'im', {
    configurable: false,
    enumerable: true,
    get: () => exposedApi,
  });
  window.addEventListener('message', (event) => {
    if (event.source !== parent || !event.data || typeof event.data !== 'object') return;
    const message = event.data;
    if (message.method === 'im/notifications/window-api-capabilities') {
      event.stopImmediatePropagation();
      const params = message.params;
      const toolCalls = Boolean(__IM_TOOL_CALLS__ && params && params.toolCalls === true);
      const uiMessage = Boolean(__IM_UI_MESSAGE__ && params && params.uiMessage === true);
      exposedApi = buildApi(toolCalls, uiMessage);
      return;
    }
    if (typeof message.id === 'string'
      && message.id.startsWith('window.im:')
      && ('result' in message || 'error' in message)) {
      event.stopImmediatePropagation();
      if (!state.pending.has(message.id)) return;
      const pending = state.pending.get(message.id);
      state.pending.delete(message.id);
      clearTimeout(pending.timer);
      if ('error' in message) pending.reject(new Error(String(message.error?.message || 'window.im request failed.')));
      else pending.resolve(message.result);
      return;
    }
    if (message.result?.hostContext && typeof message.result.hostContext === 'object') {
      state.context = { ...message.result.hostContext };
    }
    if (message.method === 'ui/notifications/host-context-changed'
      && message.params && typeof message.params === 'object') {
      state.context = { ...state.context, ...message.params };
    }
    if (message.method === 'ui/notifications/tool-input') {
      state.context = { ...state.context, toolInput: message.params?.arguments };
    }
    if (message.method === 'ui/notifications/tool-result') {
      state.context = {
        ...state.context,
        toolOutput: message.params,
        toolResponseMetadata: message.params?._meta,
      };
    }
  }, true);
})();`;

function enabled(value: string | undefined): boolean {
  return value === 'true';
}

function positiveInteger(value: string | undefined, fallback: number): number | null {
  if (!value) return fallback;
  const parsed = Number(value);
  return Number.isSafeInteger(parsed) && parsed > 0 ? parsed : null;
}

function configuredParentOrigins(value: string | undefined): readonly string[] {
  if (!value) return [];
  const origins = new Set<string>();
  for (const candidate of value.split(',')) {
    try {
      const url = new URL(candidate.trim());
      if (['http:', 'https:'].includes(url.protocol) && url.href === `${url.origin}/`) origins.add(url.origin);
    } catch {
      return [];
    }
  }
  return Object.freeze([...origins]);
}

function buildWindowImShim(toolCalls: boolean, uiMessage: boolean, timeoutMs: number): string {
  return WINDOW_IM_SHIM_SOURCE
    .replace('__IM_TOOL_CALLS__', JSON.stringify(toolCalls))
    .replace('__IM_UI_MESSAGE__', JSON.stringify(uiMessage))
    .replace('__IM_REQUEST_TIMEOUT_MS__', String(timeoutMs));
}

function buildSandboxProxyHtml(input: Readonly<{
  parentOrigins: readonly string[];
  windowIm: boolean;
  toolCalls: boolean;
  uiMessage: boolean;
  requestTimeoutMs: number;
}>): string {
  const parentOrigins = JSON.stringify(input.parentOrigins);
  const shim = JSON.stringify(input.windowIm
    ? buildWindowImShim(input.toolCalls, input.uiMessage, input.requestTimeoutMs)
    : '');
  return String.raw`<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><style>html,body{margin:0;width:100%;height:100%;overflow:hidden}.im-mcp-app-resource-frame{display:block;width:100%;height:100%;border:0}</style></head>
<body><script>
(() => {
  const allowedParentOrigins = new Set(${parentOrigins});
  let parentOrigin = null;
  try {
    const referrerOrigin = document.referrer ? new URL(document.referrer).origin : null;
    if (referrerOrigin && allowedParentOrigins.has(referrerOrigin)) parentOrigin = referrerOrigin;
  } catch {}
  const sandboxTokens = 'allow-scripts';
  const allow = "camera 'none'; microphone 'none'; geolocation 'none'; clipboard-write 'none'";
  const windowImShim = ${shim};
  let appFrame = null;
  let initializeRequestId = null;
  const isRecord = (value) => typeof value === 'object' && value !== null && !Array.isArray(value);
  const isRpcId = (value) => typeof value === 'string' || (typeof value === 'number' && Number.isFinite(value));
  const emptyDomains = (csp) => isRecord(csp)
    && ['connectDomains','resourceDomains','frameDomains','baseUriDomains']
      .every((key) => Array.isArray(csp[key]) && csp[key].length === 0);
  const withCsp = (html) => {
    const policy = "default-src 'none'; script-src 'unsafe-inline'; style-src 'unsafe-inline'; img-src data:; font-src 'none'; media-src 'none'; connect-src 'none'; frame-src 'none'; base-uri 'none'; object-src 'none'";
    const meta = '<meta http-equiv="Content-Security-Policy" content="' + policy + '">';
    const compatibility = windowImShim ? '<scr' + 'ipt>' + windowImShim + '</scr' + 'ipt>' : '';
    return /<head(?:\s[^>]*)?>/i.test(html)
      ? html.replace(/<head(?:\s[^>]*)?>/i, (head) => head + meta + compatibility)
      : meta + compatibility + html;
  };
  window.addEventListener('message', (event) => {
    const message = event.data;
    if (!parentOrigin || !message || message.jsonrpc !== '2.0') return;
    if (event.source === parent) {
      if (event.origin !== parentOrigin) return;
      if (message.method === 'ui/notifications/sandbox-resource-ready') {
        const params = message.params || {};
        if (typeof params.html !== 'string' || params.sandbox !== sandboxTokens
          || !isRecord(params.permissions) || Object.keys(params.permissions).length !== 0
          || !emptyDomains(params.csp)) return;
        initializeRequestId = null;
        appFrame?.remove();
        appFrame = document.createElement('iframe');
        appFrame.dataset.testid = 'im-mcp-app-resource-frame';
        appFrame.setAttribute('sandbox', sandboxTokens);
        appFrame.setAttribute('allow', allow);
        appFrame.referrerPolicy = 'no-referrer';
        appFrame.className = 'im-mcp-app-resource-frame';
        appFrame.srcdoc = withCsp(params.html);
        document.body.replaceChildren(appFrame);
        return;
      }
      if (appFrame
        && initializeRequestId !== null
        && message.method === undefined
        && ('result' in message || 'error' in message)
        && message.id === initializeRequestId) {
        initializeRequestId = null;
        const capabilities = isRecord(message.result) && isRecord(message.result.hostCapabilities)
          ? message.result.hostCapabilities
          : null;
        appFrame.contentWindow?.postMessage({
          jsonrpc: '2.0',
          method: 'im/notifications/window-api-capabilities',
          params: {
            toolCalls: Boolean(capabilities && isRecord(capabilities.serverTools)),
            uiMessage: Boolean(capabilities && isRecord(capabilities.message)),
          },
        }, '*');
      }
      appFrame?.contentWindow?.postMessage(message, '*');
      return;
    }
    if (appFrame && event.source === appFrame.contentWindow && event.origin === 'null') {
      if (message.method === 'ui/initialize') {
        initializeRequestId = isRpcId(message.id) ? message.id : null;
      }
      parent.postMessage(message, parentOrigin);
    }
  });
  if (parentOrigin) {
    parent.postMessage({ jsonrpc: '2.0', method: 'ui/notifications/sandbox-proxy-ready', params: {} }, parentOrigin);
  }
})();
</script></body></html>`;
}

export function GET(request: Request) {
  const url = new URL(request.url);
  let plugin;
  try {
    plugin = readMcpAppsPluginManifest();
  } catch {
    return new Response('Not found.', { status: 404 });
  }
  const configuredRevision = String(plugin.revision);
  const parentOrigins = configuredParentOrigins(process.env.INK_MCP_APPS_PARENT_ORIGINS);
  const requestTimeoutMs = positiveInteger(
    process.env.INK_MCP_APPS_WINDOW_IM_REQUEST_TIMEOUT_MS,
    MCP_APPS_HOST_MANIFEST.defaults.compatibilityRequestTimeoutMs,
  );
  if (!enabled(process.env.INK_MCP_APPS_PHASE1_PREVIEW)
    || plugin.lifecycle !== 'enabled'
    || plugin.pluginId !== MCP_APPS_HOST_MANIFEST.pluginId
    || plugin.pluginVersion !== MCP_APPS_HOST_MANIFEST.version
    || plugin.browserEntry !== MCP_APPS_HOST_MANIFEST.browserEntry
    || plugin.nodeEntry !== MCP_APPS_HOST_MANIFEST.nodeEntry
    || !plugin.features.resourceReads
    || url.searchParams.get('v') !== MCP_APPS_HOST_MANIFEST.version
    || url.searchParams.get('revision') !== configuredRevision
    || parentOrigins.length === 0
    || requestTimeoutMs === null) {
    return new Response('Not found.', { status: 404 });
  }
  const toolCalls = plugin.features.lowRiskToolCalls && enabled(process.env.INK_MCP_APPS_PHASE2_TOOL_CALLS);
  const uiMessage = plugin.features.uiMessage && enabled(process.env.INK_MCP_APPS_PHASE2_UI_MESSAGE);
  const windowIm = plugin.features.windowIm
    && enabled(process.env.INK_MCP_APPS_WINDOW_IM)
    && (toolCalls || uiMessage);
  return new Response(buildSandboxProxyHtml({
    parentOrigins,
    windowIm,
    toolCalls,
    uiMessage,
    requestTimeoutMs,
  }), {
    headers: {
      'content-type': 'text/html; charset=utf-8',
      'cache-control': 'no-store',
      'content-security-policy': "default-src 'none'; script-src 'unsafe-inline'; style-src 'unsafe-inline'; img-src data:; font-src 'none'; media-src 'none'; connect-src 'none'; frame-src 'self'; base-uri 'none'; object-src 'none'",
      'permissions-policy': 'camera=(), microphone=(), geolocation=(), clipboard-write=()',
      'x-content-type-options': 'nosniff',
      'referrer-policy': 'no-referrer',
      'cross-origin-resource-policy': 'cross-origin',
    },
  });
}

'use client';

// [Input] Connected same-origin MCP Client, trusted saved result, server-owned Host policy, and current Chat ingress.
// [Output] Metadata-validated AppBridge host with controlled calls/messages, context updates, and ordered teardown.
// [Pos] Phase 1-3 sole iframe owner; Browser never receives upstream connection or credential material.
// [Sync] 2026-09-06: disable AppBridge auto-forwarding and wire only policy-enabled resources, calls, messages, and context.
// [Sync] 2026-09-06: keep the mounted official App stable when the current Chat ingress callback identity changes during parent polling/renders.

import { useEffect, useRef, useState } from 'react';
import { AppBridge, PostMessageTransport } from '@mcp-ui/client';
import {
  McpUiHostCapabilitiesSchema,
  McpUiResourceMetaSchema,
  McpUiSandboxProxyReadyNotificationSchema,
  McpUiSandboxResourceReadyNotificationSchema,
  RESOURCE_MIME_TYPE,
} from '@modelcontextprotocol/ext-apps';
import type { McpUiHostContext, McpUiMessageRequest } from '@modelcontextprotocol/ext-apps/app-bridge';
import type { Client } from '@modelcontextprotocol/sdk/client/index.js';
import { CallToolResultSchema, type CallToolResult, type Tool } from '@modelcontextprotocol/sdk/types.js';

import type { McpAppsHostPolicy } from './host-policy';

const EMPTY_CSP = Object.freeze({
  connectDomains: [],
  resourceDomains: [],
  frameDomains: [],
  baseUriDomains: [],
});
const ZERO_ALLOW = "camera 'none'; microphone 'none'; geolocation 'none'; clipboard-write 'none'";

export type SendMcpAppUserMessage = (
  content: McpUiMessageRequest['params']['content'],
) => Promise<void>;

export type McpAppBrowserFailureStage = 'transport' | 'resource' | 'iframe' | 'bridge';
export type McpAppBrowserFailureCode =
  | 'descriptor_request_failed'
  | 'descriptor_missing'
  | 'descriptor_resource_invalid'
  | 'descriptor_identity_changed'
  | 'resource_request_failed'
  | 'resource_count_invalid'
  | 'resource_format_invalid'
  | 'resource_policy_invalid'
  | 'transport_failed'
  | 'session_revalidation_failed'
  | 'iframe_failed'
  | 'bridge_failed';

export class McpAppBrowserError extends Error {
  constructor(
    readonly stage: McpAppBrowserFailureStage,
    readonly code: McpAppBrowserFailureCode,
    cause: unknown,
  ) {
    super('MCP App failed to load.', { cause });
    this.name = 'McpAppBrowserError';
  }
}

class McpAppResourceError extends Error {
  constructor(
    readonly code: Extract<McpAppBrowserFailureCode, `${string}_request_failed` | `descriptor_${string}` | `resource_${string}`>,
    cause?: unknown,
  ) {
    super('MCP App resource is unavailable.', { cause });
    this.name = 'McpAppResourceError';
  }
}

type Props = Readonly<{
  client: Client;
  toolName: string;
  toolInput: Record<string, unknown>;
  toolResult: CallToolResult;
  expectedResourceUri: string;
  policy: McpAppsHostPolicy;
  onSendMessage?: SendMcpAppUserMessage;
  onError: (error: McpAppBrowserError) => void;
}>;

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === 'object' && value !== null && !Array.isArray(value);
}

function isEmptyCsp(value: unknown): boolean {
  return value === undefined || (isRecord(value) && Object.keys(EMPTY_CSP).every((key) => (
    Array.isArray(value[key]) && (value[key] as unknown[]).length === 0
  )));
}

function currentTheme(): 'light' | 'dark' {
  const root = document.documentElement;
  if (root.dataset.theme === 'dark' || root.classList.contains('dark')) return 'dark';
  if (root.dataset.theme === 'light' || root.classList.contains('light')) return 'light';
  return window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light';
}

function hostContext(container: HTMLElement, descriptor: Tool): McpUiHostContext {
  return {
    toolInfo: { tool: descriptor },
    theme: currentTheme(),
    locale: navigator.language || 'en',
    displayMode: 'inline',
    availableDisplayModes: ['inline'],
    containerDimensions: {
      maxWidth: Math.max(0, Math.round(container.getBoundingClientRect().width)),
      maxHeight: Math.max(0, Math.round(container.getBoundingClientRect().height)),
    },
  };
}

function waitForProxy(iframe: HTMLIFrameElement, policy: McpAppsHostPolicy): Promise<void> {
  return new Promise((resolve, reject) => {
    const timeout = window.setTimeout(() => {
      window.removeEventListener('message', onMessage);
      reject(new Error('MCP App sandbox did not become ready.'));
    }, policy.readyTimeoutMs);
    const onMessage = (event: MessageEvent) => {
      // The outer proxy is itself sandboxed without allow-same-origin, so its
      // effective postMessage origin is precisely the opaque "null" origin.
      // Source identity remains the exact independent-origin iframe Window.
      if (event.source !== iframe.contentWindow || event.origin !== 'null') return;
      const parsed = McpUiSandboxProxyReadyNotificationSchema.safeParse(event.data);
      if (!parsed.success) return;
      window.clearTimeout(timeout);
      window.removeEventListener('message', onMessage);
      resolve();
    };
    window.addEventListener('message', onMessage);
  });
}

async function findToolDescriptor(client: Client, toolName: string): Promise<Tool> {
  let cursor: string | undefined;
  do {
    let page;
    try {
      page = await client.listTools(cursor ? { cursor } : undefined);
    } catch (error) {
      throw new McpAppResourceError('descriptor_request_failed', error);
    }
    const descriptor = page.tools.find((tool) => tool.name === toolName);
    if (descriptor) return descriptor;
    cursor = page.nextCursor;
  } while (cursor);
  throw new McpAppResourceError('descriptor_missing');
}

async function readAppResource(client: Client, toolName: string, expectedResourceUri: string) {
  const descriptor = await findToolDescriptor(client, toolName);
  const resourceUri = (descriptor._meta as { ui?: { resourceUri?: unknown } } | undefined)?.ui?.resourceUri;
  if (typeof resourceUri !== 'string' || !resourceUri.startsWith('ui://')) {
    throw new McpAppResourceError('descriptor_resource_invalid');
  }
  if (resourceUri !== expectedResourceUri) {
    throw new McpAppResourceError('descriptor_identity_changed');
  }
  let resource;
  try {
    resource = await client.readResource({ uri: resourceUri });
  } catch (error) {
    throw new McpAppResourceError('resource_request_failed', error);
  }
  if (resource.contents.length !== 1) throw new McpAppResourceError('resource_count_invalid');
  const content = resource.contents[0];
  if (!('text' in content) || typeof content.text !== 'string' || content.mimeType !== RESOURCE_MIME_TYPE) {
    throw new McpAppResourceError('resource_format_invalid');
  }
  const ui = isRecord(content._meta) && isRecord(content._meta.ui) ? content._meta.ui : null;
  const parsedMeta = McpUiResourceMetaSchema.safeParse(ui ?? {});
  if (!parsedMeta.success
    || !isEmptyCsp(parsedMeta.data.csp)
    || (ui?.permissions !== undefined
      && (!isRecord(ui.permissions) || Object.keys(ui.permissions).length !== 0))) {
    throw new McpAppResourceError('resource_policy_invalid');
  }
  return { html: content.text, csp: EMPTY_CSP, descriptor };
}

export default function ImMcpAppHostAdapter({
  client,
  toolName,
  toolInput,
  toolResult,
  expectedResourceUri,
  policy,
  onSendMessage,
  onError,
}: Props) {
  const containerRef = useRef<HTMLDivElement>(null);
  const onSendMessageRef = useRef(onSendMessage);
  const [status, setStatus] = useState<'loading' | 'ready' | 'degraded'>('loading');
  const messageIngressAvailable = Boolean(onSendMessage);

  useEffect(() => {
    onSendMessageRef.current = onSendMessage;
  }, [onSendMessage]);

  useEffect(() => {
    let active = true;
    let bridge: AppBridge | null = null;
    let outer: HTMLIFrameElement | null = null;
    let resizeObserver: ResizeObserver | null = null;
    let themeObserver: MutationObserver | null = null;
    let hostDescriptor: Tool | null = null;
    const media = window.matchMedia('(prefers-color-scheme: dark)');
    const teardown = async () => {
      resizeObserver?.disconnect();
      resizeObserver = null;
      themeObserver?.disconnect();
      themeObserver = null;
      media.removeEventListener('change', publishContext);
      if (bridge) {
        await bridge.teardownResource({}, { timeout: policy.readyTimeoutMs }).catch(() => undefined);
        await bridge.close().catch(() => undefined);
        bridge = null;
      }
      outer?.remove();
      outer = null;
    };
    const publishContext = () => {
      const target = containerRef.current;
      const current = bridge;
      if (!active || !target || !current) return;
      if (hostDescriptor) current.setHostContext(hostContext(target, hostDescriptor));
    };
    const mount = async () => {
      let failureStage: McpAppBrowserFailureStage = 'resource';
      try {
        const resource = await readAppResource(client, toolName, expectedResourceUri);
        hostDescriptor = resource.descriptor;
        const container = containerRef.current;
        if (!active || !container) return;
        outer = document.createElement('iframe');
        outer.dataset.testid = 'im-mcp-app-host-frame';
        outer.dataset.policyRevision = policy.revision;
        outer.title = 'Ink & Memory MCP App';
        outer.style.width = '100%';
        outer.style.height = '320px';
        outer.style.border = '0';
        outer.referrerPolicy = 'origin';
        const sandboxTokens = policy.sandboxTokens.join(' ');
        outer.setAttribute('sandbox', sandboxTokens);
        outer.setAttribute('allow', ZERO_ALLOW);
        outer.src = policy.sandboxUrl;
        container.replaceChildren(outer);
        failureStage = 'iframe';
        await waitForProxy(outer, policy);
        if (!active || !outer.contentWindow) return;
        const hostCapabilities = McpUiHostCapabilitiesSchema.parse({
          serverResources: {},
          ...(policy.features.appToolCalls ? { serverTools: {} } : {}),
          ...(policy.features.uiMessage && messageIngressAvailable ? { message: { text: {} } } : {}),
          sandbox: { csp: EMPTY_CSP, permissions: {} },
        });
        bridge = new AppBridge(
          null,
          { name: 'Ink & Memory MCP Apps Host', version: policy.manifestVersion },
          hostCapabilities,
          { hostContext: hostContext(container, resource.descriptor) },
        );
        bridge.onlistresources = async (params, extra) => client.listResources(
          params,
          { signal: extra.signal },
        );
        bridge.onreadresource = async (params, extra) => client.readResource(
          params,
          { signal: extra.signal },
        );
        if (policy.features.appToolCalls) {
          bridge.oncalltool = async (params, extra) => CallToolResultSchema.parse(
            await client.callTool(
              params,
              CallToolResultSchema,
              { signal: extra.signal },
            ),
          );
        }
        if (policy.features.uiMessage && messageIngressAvailable) {
          bridge.onmessage = async (params) => {
            if (params.role !== 'user' || params.content.length === 0) {
              throw new Error('MCP App message is invalid.');
            }
            const sendMessage = onSendMessageRef.current;
            if (!sendMessage) {
              throw new Error('MCP App message ingress is unavailable.');
            }
            await sendMessage(params.content);
            return {};
          };
        }
        let initialized = false;
        bridge.oninitialized = () => {
          if (!active || initialized) return;
          initialized = true;
          void bridge?.sendToolInput({ arguments: toolInput });
          void bridge?.sendToolResult(toolResult);
          setStatus('ready');
        };
        failureStage = 'bridge';
        await bridge.connect(new PostMessageTransport(outer.contentWindow, outer.contentWindow));
        const notification = McpUiSandboxResourceReadyNotificationSchema.parse({
          method: 'ui/notifications/sandbox-resource-ready',
          params: {
            html: resource.html,
            sandbox: sandboxTokens,
            csp: resource.csp,
            permissions: {},
          },
        });
        await bridge.sendSandboxResourceReady(notification.params);
        resizeObserver = new ResizeObserver(publishContext);
        resizeObserver.observe(container);
        themeObserver = new MutationObserver(publishContext);
        themeObserver.observe(document.documentElement, {
          attributes: true,
          attributeFilter: ['class', 'data-theme'],
        });
        media.addEventListener('change', publishContext);
      } catch (error) {
        if (!active) return;
        await teardown();
        setStatus('degraded');
        const code = error instanceof McpAppResourceError
          ? error.code
          : failureStage === 'iframe'
            ? 'iframe_failed'
            : failureStage === 'bridge'
              ? 'bridge_failed'
              : 'resource_request_failed';
        onError(new McpAppBrowserError(failureStage, code, error));
      }
    };
    void mount();
    return () => {
      active = false;
      void teardown();
    };
  }, [client, expectedResourceUri, messageIngressAvailable, onError, policy, toolInput, toolName, toolResult]);

  return <div data-testid="im-mcp-app-host" data-status={status} ref={containerRef} />;
}

// [Input] Connected MCP Client, completed tool result, and immutable sandbox/permission snapshots.
// [Output] A metadata-validated two-iframe MCP App host with fail-closed permissions and lifecycle.
// [Pos] Task_301 Phase 0 Browser-only Host adapter; never imported by production entrypoints.
// [Sync] 2026-09-04: implement DEC-002 navigation-before-policy enforcement for the bounded P0-04 rerun.
// [Sync] 2026-09-06: keep the test-only mixed contract/component module explicit to the lint gate.

/* eslint-disable react-refresh/only-export-components -- provider-free harness intentionally colocates its contracts */

import React, { useEffect, useRef, useState } from 'react';
import { AppBridge, PostMessageTransport } from '@mcp-ui/client';
import {
  McpUiHostCapabilitiesSchema,
  McpUiResourceMetaSchema,
  McpUiResourcePermissionsSchema,
  McpUiSandboxProxyReadyNotificationSchema,
  McpUiSandboxResourceReadyNotificationSchema,
  RESOURCE_MIME_TYPE,
} from '@modelcontextprotocol/ext-apps';
import type { Client } from '@modelcontextprotocol/sdk/client/index.js';
import type { CallToolResult } from '@modelcontextprotocol/sdk/types.js';


export const PHASE0_PERMISSION_KEYS = [
  'camera',
  'microphone',
  'geolocation',
  'clipboardWrite',
] as const;

type PermissionKey = typeof PHASE0_PERMISSION_KEYS[number];
export type Phase0Permissions = Partial<Record<PermissionKey, Record<string, never>>>;

export type Phase0PermissionPolicy = Readonly<{
  revision: string;
  desired?: unknown;
}>;

export type Phase0PolicyEvidence = {
  requestedPermissions: PermissionKey[];
  effectivePermissions: PermissionKey[];
  policyRevision: string;
  outerAllow: string;
  sandboxTokens: string;
  hostCapabilitiesPermissions: PermissionKey[];
};

type ImMcpAppHostAdapterProps = {
  client: Client;
  toolName: string;
  toolInput: Record<string, unknown>;
  toolResult: CallToolResult;
  sandboxUrl: string;
  sandboxTokens: string;
  permissionPolicy?: Phase0PermissionPolicy;
  closeRequested: boolean;
  onClosed: () => void;
  onLoggingMessage: (data: unknown) => void;
  onPolicyEvidence: (evidence: Phase0PolicyEvidence) => void;
  onError: (error: Error) => void;
};

type LoadedResource = {
  html: string;
  csp: Record<string, unknown> | undefined;
  requested: Phase0Permissions;
};

const HOST_SUPPORTED = Object.freeze(
  Object.fromEntries(PHASE0_PERMISSION_KEYS.map((key) => [key, {}])) as Phase0Permissions,
);

const ALLOW_FEATURE: Record<PermissionKey, string> = {
  camera: 'camera',
  microphone: 'microphone',
  geolocation: 'geolocation',
  clipboardWrite: 'clipboard-write',
};


function isPlainRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === 'object' && value !== null && !Array.isArray(value);
}


function parsePermissions(value: unknown, label: string): Phase0Permissions {
  if (value === undefined) return {};
  if (!isPlainRecord(value)) throw new Error(`${label} must be an object.`);
  const unknownKeys = Object.keys(value).filter(
    (key) => !PHASE0_PERMISSION_KEYS.includes(key as PermissionKey),
  );
  if (unknownKeys.length) throw new Error(`${label} contains an unknown permission key.`);
  const parsed = McpUiResourcePermissionsSchema.safeParse(value);
  if (!parsed.success) throw new Error(`${label} has an invalid permission structure.`);
  return parsed.data as Phase0Permissions;
}


function permissionKeys(permissions: Phase0Permissions): PermissionKey[] {
  return PHASE0_PERMISSION_KEYS.filter((key) => permissions[key] !== undefined);
}


function intersectPermissions(
  requested: Phase0Permissions,
  desired: Phase0Permissions,
): Phase0Permissions {
  return Object.fromEntries(PHASE0_PERMISSION_KEYS
    .filter((key) => requested[key] && desired[key] && HOST_SUPPORTED[key])
    .map((key) => [key, {}])) as Phase0Permissions;
}


export function buildPhase0AllowAttribute(effective: Phase0Permissions): string {
  return PHASE0_PERMISSION_KEYS.map((key) => (
    effective[key] ? ALLOW_FEATURE[key] : `${ALLOW_FEATURE[key]} 'none'`
  )).join('; ');
}


async function findToolResourceUri(client: Client, toolName: string): Promise<string> {
  let cursor: string | undefined;
  do {
    const result = await client.listTools(cursor ? { cursor } : undefined);
    const tool = result.tools.find((candidate) => candidate.name === toolName);
    if (tool) {
      const resourceUri = (tool._meta as { ui?: { resourceUri?: unknown } } | undefined)
        ?.ui?.resourceUri;
      if (typeof resourceUri !== 'string' || !resourceUri.startsWith('ui://')) {
        throw new Error('Tool descriptor has no valid UI resource URI.');
      }
      return resourceUri;
    }
    cursor = result.nextCursor;
  } while (cursor);
  throw new Error('Tool descriptor was not found.');
}


async function loadResource(client: Client, toolName: string): Promise<LoadedResource> {
  const uri = await findToolResourceUri(client, toolName);
  const result = await client.readResource({ uri });
  if (result.contents.length !== 1) throw new Error('UI resource must contain exactly one item.');
  const content = result.contents[0];
  if (
    !('text' in content)
    || typeof content.text !== 'string'
    || content.mimeType !== RESOURCE_MIME_TYPE
  ) {
    throw new Error('UI resource has an unsupported content format.');
  }
  const rawUiMeta = isPlainRecord(content._meta) ? content._meta.ui : undefined;
  if (rawUiMeta !== undefined && !isPlainRecord(rawUiMeta)) {
    throw new Error('Resource UI metadata must be an object.');
  }
  const rawPermissions = isPlainRecord(rawUiMeta) ? rawUiMeta.permissions : undefined;
  const requested = parsePermissions(rawPermissions, 'Resource permissions');
  const parsedMeta = McpUiResourceMetaSchema.safeParse(rawUiMeta ?? {});
  if (!parsedMeta.success) throw new Error('Resource UI metadata is invalid.');
  return {
    html: content.text,
    csp: parsedMeta.data.csp as Record<string, unknown> | undefined,
    requested,
  };
}


function waitForSandboxReady(iframe: HTMLIFrameElement, origin: string): Promise<void> {
  return new Promise((resolve, reject) => {
    const timeout = window.setTimeout(() => {
      window.removeEventListener('message', onMessage);
      reject(new Error('Timed out waiting for the sandbox proxy.'));
    }, 10_000);
    const onMessage = (event: MessageEvent) => {
      if (event.source !== iframe.contentWindow || event.origin !== origin) return;
      const parsed = McpUiSandboxProxyReadyNotificationSchema.safeParse(event.data);
      if (!parsed.success) return;
      window.clearTimeout(timeout);
      window.removeEventListener('message', onMessage);
      resolve();
    };
    window.addEventListener('message', onMessage);
  });
}


export function ImMcpAppHostAdapter({
  client,
  toolName,
  toolInput,
  toolResult,
  sandboxUrl,
  sandboxTokens,
  permissionPolicy,
  closeRequested,
  onClosed,
  onLoggingMessage,
  onPolicyEvidence,
  onError,
}: ImMcpAppHostAdapterProps) {
  const containerRef = useRef<HTMLDivElement>(null);
  const bridgeRef = useRef<AppBridge | null>(null);
  const frameRef = useRef<HTMLIFrameElement | null>(null);
  const teardownRef = useRef<() => Promise<void>>(async () => undefined);
  const [status, setStatus] = useState<'loading' | 'ready' | 'degraded'>('loading');

  useEffect(() => {
    let active = true;

    const teardown = async () => {
      const bridge = bridgeRef.current;
      bridgeRef.current = null;
      if (bridge) {
        try {
          await bridge.teardownResource({}, { timeout: 1_500 });
        } catch {
          // A failing guest teardown cannot retain the iframe or transport.
        }
        await bridge.close().catch(() => undefined);
      }
      frameRef.current?.remove();
      frameRef.current = null;
    };
    teardownRef.current = teardown;

    const mount = async () => {
      try {
        if (!permissionPolicy || typeof permissionPolicy.revision !== 'string'
          || permissionPolicy.revision.length === 0) {
          throw new Error('Permission policy revision is missing or invalid.');
        }
        const desired = parsePermissions(permissionPolicy.desired, 'Desired permissions');
        const resource = await loadResource(client, toolName);
        if (!active) return;
        const effective = intersectPermissions(resource.requested, desired);
        const allow = buildPhase0AllowAttribute(effective);
        const hostCapabilities = McpUiHostCapabilitiesSchema.parse({
          serverResources: {},
          sandbox: {
            csp: resource.csp,
            permissions: effective,
          },
          logging: {},
        });

        const outer = document.createElement('iframe');
        outer.dataset.testid = 'im-mcp-app-host-frame';
        outer.title = 'Phase 0 isolated MCP App';
        outer.style.width = '100%';
        outer.style.height = '600px';
        outer.style.border = 'none';
        outer.setAttribute('sandbox', sandboxTokens);
        outer.setAttribute('allow', allow);
        const parsedSandboxUrl = new URL(sandboxUrl);
        outer.src = parsedSandboxUrl.href;
        frameRef.current = outer;
        containerRef.current?.appendChild(outer);

        await waitForSandboxReady(outer, parsedSandboxUrl.origin);
        if (!active || !outer.contentWindow) return;

        const bridge = new AppBridge(
          client,
          { name: 'Ink Memory Phase 0 PoC', version: '1.0.0' },
          hostCapabilities,
        );
        bridgeRef.current = bridge;
        let initialized = false;
        bridge.onloggingmessage = ({ data }) => onLoggingMessage(data);
        bridge.oninitialized = () => {
          if (!active || initialized) return;
          initialized = true;
          void bridge.sendToolInput({ arguments: toolInput });
          void bridge.sendToolResult(toolResult);
          setStatus('ready');
        };
        await bridge.connect(new PostMessageTransport(outer.contentWindow, outer.contentWindow));

        const readyNotification = {
          method: 'ui/notifications/sandbox-resource-ready' as const,
          params: {
            html: resource.html,
            sandbox: sandboxTokens,
            csp: resource.csp,
            permissions: effective,
          },
        };
        const parsedReady = McpUiSandboxResourceReadyNotificationSchema.safeParse(readyNotification);
        if (!parsedReady.success) throw new Error('Sandbox resource-ready message is invalid.');
        await bridge.sendSandboxResourceReady(parsedReady.data.params);
        onPolicyEvidence({
          requestedPermissions: permissionKeys(resource.requested),
          effectivePermissions: permissionKeys(effective),
          policyRevision: permissionPolicy.revision,
          outerAllow: allow,
          sandboxTokens,
          hostCapabilitiesPermissions: permissionKeys(effective),
        });
      } catch (error) {
        if (!active) return;
        await teardown();
        const normalized = error instanceof Error ? error : new Error(String(error));
        setStatus('degraded');
        onError(normalized);
      }
    };

    void mount();
    return () => {
      active = false;
      void teardown();
    };
  }, [
    client,
    onError,
    onLoggingMessage,
    onPolicyEvidence,
    permissionPolicy,
    sandboxTokens,
    sandboxUrl,
    toolInput,
    toolName,
    toolResult,
  ]);

  useEffect(() => {
    if (!closeRequested) return;
    void teardownRef.current().then(onClosed);
  }, [closeRequested, onClosed]);

  return <div data-testid="im-mcp-app-host" data-status={status} ref={containerRef} />;
}

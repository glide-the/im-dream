// [Input] A validated, short-lived Node-only Streamable HTTP connection view.
// [Output] A bounded standard MCP SDK Client with allowlisted resources and low-risk tool calls.
// [Pos] Upstream Node connector; URLs and headers never cross the Runtime public HTTP response.
// [Sync] 2026-09-06: enforce no-redirect networking plus bounded catalog, timeout, resource, and app-call policy.

import { Client } from '@modelcontextprotocol/sdk/client/index.js';
import { StreamableHTTPClientTransport } from '@modelcontextprotocol/sdk/client/streamableHttp.js';
import {
  CallToolResultSchema,
  ErrorCode,
  McpError,
  type CallToolResult,
  type Resource,
  type Tool,
} from '@modelcontextprotocol/sdk/types.js';

import type {
  ConnectorFactory,
  ManagedConnector,
  McpAppsConnectionView,
} from './contracts.ts';
import { McpAppsRuntimeError } from './contracts.ts';
import {
  type McpAppsRuntimeLimits,
  requireAllowedConnection,
  requireResourceWithinLimit,
} from './runtime-policy.ts';

function upstreamFailure(error: unknown, action: 'connection' | 'resource' | 'tool'): McpAppsRuntimeError {
  if (error instanceof McpError && error.code === ErrorCode.RequestTimeout) {
    return new McpAppsRuntimeError(504, 'UPSTREAM_TIMEOUT', `MCP Apps upstream ${action} timed out.`);
  }
  return new McpAppsRuntimeError(502, 'UPSTREAM_FAILED', `MCP Apps upstream ${action} failed.`);
}

async function noRedirectFetch(url: string | URL, init?: RequestInit): Promise<Response> {
  const response = await fetch(url, { ...init, redirect: 'manual' });
  if (response.status >= 300 && response.status < 400) {
    await response.body?.cancel().catch(() => undefined);
    throw new McpAppsRuntimeError(502, 'UPSTREAM_REDIRECT_DENIED', 'MCP Apps upstream redirect is unavailable.');
  }
  return response;
}

export async function listAllowedCatalog<T extends Tool | Resource>(input: Readonly<{
  maximumPages: number;
  allowed: ReadonlySet<string>;
  listPage: (cursor: string | undefined) => Promise<Readonly<{
    values: T[];
    nextCursor?: string;
  }>>;
  identity: (value: T) => string;
}>): Promise<readonly T[]> {
  const values = new Map<string, T>();
  const cursors = new Set<string>();
  let cursor: string | undefined;
  for (let pageIndex = 0; pageIndex < input.maximumPages; pageIndex += 1) {
    const page = await input.listPage(cursor);
    for (const value of page.values) {
      const identity = input.identity(value);
      if (input.allowed.has(identity)) values.set(identity, value);
    }
    if (values.size === input.allowed.size || !page.nextCursor) {
      return Object.freeze([...values.values()]);
    }
    if (cursors.has(page.nextCursor)) {
      throw new McpAppsRuntimeError(502, 'CATALOG_CURSOR_INVALID', 'MCP Apps upstream catalog is invalid.');
    }
    cursors.add(page.nextCursor);
    cursor = page.nextCursor;
  }
  throw new McpAppsRuntimeError(502, 'CATALOG_PAGE_LIMIT', 'MCP Apps upstream catalog exceeds policy.');
}

export class SdkConnectorFactory implements ConnectorFactory {
  constructor(readonly limits: McpAppsRuntimeLimits) {}

  async connect(view: McpAppsConnectionView): Promise<ManagedConnector> {
    const limits = this.limits;
    const client = new Client({ name: 'ink-dream-mcp-apps-runtime', version: '1.0.0' });
    const upstreamUrl = requireAllowedConnection(view, this.limits.networkHostAllowlist);
    const transport = new StreamableHTTPClientTransport(upstreamUrl, {
      requestInit: { headers: { ...view.connectionProfile.headers } },
      fetch: noRedirectFetch,
    });
    try {
      await client.connect(transport, { timeout: this.limits.upstreamTimeoutMs });
      const allowedTools = new Set(view.allowedTools);
      const allowedResources = new Set(view.allowedResources);
      const callableTools = new Set(view.appCallableLowRiskTools);
      const [tools, resources] = await Promise.all([
        listAllowedCatalog<Tool>({
          maximumPages: this.limits.maximumCatalogPages,
          allowed: allowedTools,
          listPage: async (cursor) => {
            const page = await client.listTools(
              cursor ? { cursor } : undefined,
              { timeout: this.limits.upstreamTimeoutMs },
            );
            return { values: page.tools, nextCursor: page.nextCursor };
          },
          identity: (tool) => tool.name,
        }),
        listAllowedCatalog<Resource>({
          maximumPages: this.limits.maximumCatalogPages,
          allowed: allowedResources,
          listPage: async (cursor) => {
            const page = await client.listResources(
              cursor ? { cursor } : undefined,
              { timeout: this.limits.upstreamTimeoutMs },
            );
            return { values: page.resources, nextCursor: page.nextCursor };
          },
          identity: (resource) => resource.uri,
        }),
      ]);
      const catalog = Object.freeze({
        tools,
        resources,
      });
      return {
        catalog,
        async readResource(uri) {
          if (!allowedResources.has(uri) || !catalog.resources.some((resource) => resource.uri === uri)) {
            throw new Error('MCP App resource is not allowed.');
          }
          let result;
          try {
            result = await client.readResource(
              { uri },
              { timeout: limits.upstreamTimeoutMs },
            );
          } catch (error) {
            throw upstreamFailure(error, 'resource');
          }
          return requireResourceWithinLimit(result, limits.maximumResourceBytes);
        },
        async callTool(name, args) {
          if (
            !callableTools.has(name)
            || !allowedTools.has(name)
            || !catalog.tools.some((tool) => tool.name === name)
          ) {
            throw new McpAppsRuntimeError(403, 'TOOL_DENIED', 'MCP App tool is not allowed.');
          }
          try {
            return await client.callTool(
              { name, arguments: { ...args } },
              CallToolResultSchema,
              { timeout: limits.upstreamTimeoutMs },
            ) as CallToolResult;
          } catch (error) {
            throw upstreamFailure(error, 'tool');
          }
        },
        async close() {
          await client.close();
        },
      };
    } catch (error) {
      await client.close().catch(() => undefined);
      if (error instanceof McpAppsRuntimeError) throw error;
      throw upstreamFailure(error, 'connection');
    }
  }
}

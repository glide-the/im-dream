// [Input] Current IM authorization, scoped Server selector, revisions, and server-owned backend configuration.
// [Output] A strictly validated short-lived single-Server connection view.
// [Pos] Node-to-Python service boundary; secrets remain in Node memory and never enter Browser responses.
// [Sync] 2026-09-06: read authenticated static policy and send workspace/config/credential/policy identity on revalidation.

import {
  McpAppsRuntimeError,
  type ConnectionViewProvider,
  type McpAppsConnectionView,
  type McpAppsStaticView,
  parseConnectionView,
  parseMcpAppsStaticView,
} from './contracts.ts';

type ProviderOptions = Readonly<{
  backendBaseUrl: string;
  serviceToken: string;
  fetchImpl?: typeof fetch;
}>;

export class PythonConnectionViewProvider implements ConnectionViewProvider {
  readonly #backendBaseUrl: string;
  readonly #serviceToken: string;
  readonly #fetch: typeof fetch;

  constructor(options: ProviderOptions) {
    this.#backendBaseUrl = options.backendBaseUrl.replace(/\/+$/, '');
    this.#serviceToken = options.serviceToken;
    this.#fetch = options.fetchImpl ?? fetch;
    if (!this.#backendBaseUrl || !this.#serviceToken) {
      throw new McpAppsRuntimeError(503, 'CONFIG_PROVIDER_UNAVAILABLE', 'MCP Apps configuration is unavailable.');
    }
  }

  async getStaticView(authorization: string): Promise<McpAppsStaticView> {
    if (!authorization.startsWith('Bearer ') || authorization.length <= 7) {
      throw new McpAppsRuntimeError(403, 'CONFIG_PROVIDER_REJECTED', 'MCP Apps policy is unavailable.');
    }
    let response: Response;
    try {
      response = await this.#fetch(
        `${this.#backendBaseUrl}/api/claude-mcp/app-runtime/static`,
        {
          method: 'GET',
          cache: 'no-store',
          headers: {
            authorization,
            'x-ink-mcp-apps-service': this.#serviceToken,
          },
        },
      );
    } catch {
      throw new McpAppsRuntimeError(503, 'CONFIG_PROVIDER_UNAVAILABLE', 'MCP Apps policy is unavailable.');
    }
    if (!response.ok) {
      const status = response.status === 401 || response.status === 403 ? 403 : 503;
      throw new McpAppsRuntimeError(status, 'CONFIG_PROVIDER_REJECTED', 'MCP Apps policy is unavailable.');
    }
    return parseMcpAppsStaticView(await response.json());
  }

  async getConnectionView(input: Readonly<{
    authorization: string;
    workspaceScope: string | null;
    serverRef: string;
    expectedConfigRevision?: number;
    expectedCredentialRevision?: number;
    expectedPolicyRevision?: number;
  }>): Promise<McpAppsConnectionView> {
    let response: Response;
    try {
      response = await this.#fetch(
        `${this.#backendBaseUrl}/api/claude-mcp/app-runtime/connections/${encodeURIComponent(input.serverRef)}`,
        {
          method: 'POST',
          cache: 'no-store',
          headers: {
            authorization: input.authorization,
            'content-type': 'application/json',
            'x-ink-mcp-apps-service': this.#serviceToken,
          },
          body: JSON.stringify({
            workspace_scope: input.workspaceScope,
            expected_config_revision: input.expectedConfigRevision,
            expected_credential_revision: input.expectedCredentialRevision,
            expected_policy_revision: input.expectedPolicyRevision,
          }),
        },
      );
    } catch {
      throw new McpAppsRuntimeError(503, 'CONFIG_PROVIDER_UNAVAILABLE', 'MCP Apps connection is unavailable.');
    }
    if (!response.ok) {
      const status = response.status === 409 ? 409 : response.status === 401 || response.status === 403 ? 403 : 503;
      throw new McpAppsRuntimeError(status, 'CONFIG_PROVIDER_REJECTED', 'MCP Apps connection is unavailable.');
    }
    const view = parseConnectionView(await response.json());
    if (view.serverRef !== input.serverRef || view.workspaceScope !== input.workspaceScope) {
      throw new McpAppsRuntimeError(403, 'CONNECTION_SCOPE_MISMATCH', 'MCP Apps connection scope is invalid.');
    }
    return view;
  }
}

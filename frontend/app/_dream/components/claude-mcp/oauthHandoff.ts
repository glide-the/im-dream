// [Sync] 2026-10-29: share the original public operation key/length with the concrete native Settings owner.
// [Input] One actor-owned managed MCP OAuth operation identifier and browser localStorage.
// [Output] A non-secret same-origin handoff reference for the SPA OAuth callback page.
// [Pos] Frontend-only correlation seam; never stores authorization URLs, callback URLs, codes, states, Tokens, or credentials.
// [Sync] 2026-08-25: replace manual callback copying with an automatic same-origin operation handoff.

export const MCP_OAUTH_OPERATION_STORAGE_KEY = 'ink-memory:claude-mcp:pending-oauth-operation';
export const MCP_OAUTH_OPERATION_ID_MAX_LENGTH = 128;

export function rememberClaudeMcpOAuthOperation(operationId: string): boolean {
  if (!operationId || operationId.length > MCP_OAUTH_OPERATION_ID_MAX_LENGTH) return false;
  try {
    window.localStorage.setItem(MCP_OAUTH_OPERATION_STORAGE_KEY, operationId);
    return true;
  } catch {
    return false;
  }
}

export function readClaudeMcpOAuthOperation(): string | null {
  try {
    const operationId = window.localStorage.getItem(MCP_OAUTH_OPERATION_STORAGE_KEY);
    if (!operationId || operationId.length > MCP_OAUTH_OPERATION_ID_MAX_LENGTH) return null;
    return operationId;
  } catch {
    return null;
  }
}

export function forgetClaudeMcpOAuthOperation(operationId?: string): void {
  try {
    const current = window.localStorage.getItem(MCP_OAUTH_OPERATION_STORAGE_KEY);
    if (operationId === undefined || current === operationId) {
      window.localStorage.removeItem(MCP_OAUTH_OPERATION_STORAGE_KEY);
    }
  } catch {
    // The backend operation still owns expiry/cancel when browser storage is unavailable.
  }
}

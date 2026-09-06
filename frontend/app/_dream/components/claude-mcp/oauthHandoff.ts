// [Input] One actor-owned managed MCP OAuth operation identifier and browser localStorage.
// [Output] A non-secret same-origin handoff reference for the SPA OAuth callback page.
// [Pos] Frontend-only correlation seam; never stores authorization URLs, callback URLs, codes, states, Tokens, or credentials.
// [Sync] 2026-08-25: replace manual callback copying with an automatic same-origin operation handoff.

const STORAGE_KEY = 'ink-memory:claude-mcp:pending-oauth-operation';
const MAX_OPERATION_ID_LENGTH = 128;

export function rememberClaudeMcpOAuthOperation(operationId: string): boolean {
  if (!operationId || operationId.length > MAX_OPERATION_ID_LENGTH) return false;
  try {
    window.localStorage.setItem(STORAGE_KEY, operationId);
    return true;
  } catch {
    return false;
  }
}

export function readClaudeMcpOAuthOperation(): string | null {
  try {
    const operationId = window.localStorage.getItem(STORAGE_KEY);
    if (!operationId || operationId.length > MAX_OPERATION_ID_LENGTH) return null;
    return operationId;
  } catch {
    return null;
  }
}

export function forgetClaudeMcpOAuthOperation(operationId?: string): void {
  try {
    const current = window.localStorage.getItem(STORAGE_KEY);
    if (operationId === undefined || current === operationId) {
      window.localStorage.removeItem(STORAGE_KEY);
    }
  } catch {
    // The backend operation still owns expiry/cancel when browser storage is unavailable.
  }
}

// [Input] Original managed MCP list labels, capability and auth predicates.
// [Output] Shared list presentation metadata and original safe errors.
// [Pos] Pure metadata; UI styles and backend state remain with their original owners.
// [Sync] 2026-10-29: extract original state for Web/native reuse; HTTP, business payloads and permissions keep their owners.
import {ClaudeMcpApiError,type ClaudeMcpCapability,type ClaudeMcpAuthState,type ClaudeMcpConfigScope,type ClaudeMcpOperation,type ClaudeMcpServer,type ClaudeMcpServerInventory,type ClaudeMcpState,type ClaudeMcpTool,type ClaudeMcpAppSettings,type ClaudeMcpApi} from '../../api/claudeMcpApi';
export const OPERATION_POLL_INTERVAL_MS = 1200;
export const CAPABILITY_RETRY_INTERVAL_MS = 2000;
export const CAPABILITY_UNAVAILABLE = 'CLAUDE_MCP_SCHEMA_CAPABILITY_UNAVAILABLE';
export const ACTIVE_STATES: ClaudeMcpState[] = [
  'auth_starting',
  'waiting_for_user',
  'exchanging_code',
  'cancelling',
];

export const STATE_LABELS: Record<ClaudeMcpState, string> = {
  not_configured: '未配置',
  configured: '已配置',
  needs_auth: '需要认证',
  auth_starting: '正在启动',
  waiting_for_user: '等待授权',
  exchanging_code: '正在连接',
  connected: '已连接',
  failed: '连接失败',
  cancelling: '正在取消',
  logged_out: '已退出',
  disabled: '不可用',
};

export const SCOPE_LABELS: Record<ClaudeMcpConfigScope, string> = {
  user: '用户配置',
  workspace: '工作空间配置',
  local: '本地项目配置',
  project: '共享项目配置',
  plugin: '插件配置',
  unknown: '来源未知',
};

export const AUTH_STATE_LABELS: Record<ClaudeMcpAuthState, string> = {
  anonymous: '匿名连接，无需 OAuth',
  required: '需要认证',
  authenticated: '已认证',
  unknown: '认证状态未知',
};

export function authStateOf(server: ClaudeMcpServer): ClaudeMcpAuthState {
  return server.auth_state ?? 'unknown';
}

export function serverStatusLabel(server: ClaudeMcpServer, state: ClaudeMcpState): string {
  if (state === 'connected') return AUTH_STATE_LABELS[authStateOf(server)];
  if (state === 'configured' && authStateOf(server) === 'unknown') return '已配置，等待检测连接';
  return STATE_LABELS[state];
}

export function canLogout(server: ClaudeMcpServer, state: ClaudeMcpState): boolean {
  const authState = authStateOf(server);
  if (server.credential_configured) return true;
  return state === 'connected' && (authState === 'authenticated' || authState === 'unknown');
}

export function canDetectConnection(server: ClaudeMcpServer, state: ClaudeMcpState): boolean {
  return state === 'configured'
    || state === 'failed'
    || state === 'logged_out'
    || (state === 'needs_auth' && authStateOf(server) === 'unknown');
}

export function safeApiErrorMessage(cause: unknown, fallback: string): string {
  return cause instanceof ClaudeMcpApiError
    ? `${cause.message}（${cause.code}）`
    : fallback;
}

export function safeOperationError(operation: ClaudeMcpOperation): string | null {
  return operation.error
    ? `${operation.error.message}（${operation.error.code}）`
    : null;
}

export function messageForCapability(capability: ClaudeMcpCapability): string {
  if (capability.reason_code === 'CLAUDE_MCP_SCHEMA_CAPABILITY_MISSING') {
    return '当前 PostgreSQL 未发布或不匹配 Dream MCP 管理 capability；请核对 Admin Drizzle 0038 迁移状态。';
  }
  if (capability.reason_code === CAPABILITY_UNAVAILABLE) {
    return 'Dream 暂时无法核验 PostgreSQL capability，数据库恢复后页面会自动重试。';
  }
  return 'Dream MCP 管理能力暂不可用，请检查数据库 capability 与服务策略。';
}

export function operationFor(
  operations: Record<string, ClaudeMcpOperation>,
  server: ClaudeMcpServer,
): ClaudeMcpOperation | null {
  if (server.active_operation_id && operations[server.active_operation_id]) {
    return operations[server.active_operation_id];
  }
  const matching = Object.values(operations)
    .filter((item) => item.server_name === server.name)
    .sort((left, right) => right.updated_at.localeCompare(left.updated_at));
  return matching.find((item) => ACTIVE_STATES.includes(item.state))
    ?? matching.find((item) => item.state === 'failed')
    ?? null;
}


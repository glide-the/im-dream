// [Input] Original MCP detail labels, connection state, errors and policy draft projection.
// [Output] Pure presentation and filtering shared by Web/native.
// [Pos] Server capability and policy authority remain in the original API.
// [Sync] 2026-10-29: extract original state for Web/native reuse; HTTP, business payloads and permissions keep their owners.
import {ClaudeMcpApiError,type ClaudeMcpCapability,type ClaudeMcpAuthState,type ClaudeMcpConfigScope,type ClaudeMcpOperation,type ClaudeMcpServer,type ClaudeMcpServerInventory,type ClaudeMcpState,type ClaudeMcpTool,type ClaudeMcpAppSettings,type ClaudeMcpApi} from '../../api/claudeMcpApi';
export type CapabilityTab = 'tools' | 'resources' | 'prompts';

export type ToolFilter = 'all' | 'read_only' | 'destructive' | 'open_world' | 'unspecified';

export type EditTransport = 'streamable_http' | 'sse' | 'stdio';

export type Tone = 'neutral' | 'success' | 'warning' | 'danger' | 'info';

export type AppUsagePolicyField = 'enabled' | 'lowRiskToolCalls' | 'uiMessages';

export interface AppUsagePolicyDraft {
  enabled: boolean;
  lowRiskToolCalls: boolean;
  uiMessages: boolean;
}

export const OPERATION_POLL_INTERVAL_MS = 1200;

export const APP_USAGE_POLICY_AUTO_SAVE_DELAY_MS = 350;

export const APP_USAGE_POLICY_RETRY_DELAY_MS = 1200;

export const APP_USAGE_POLICY_MAX_CONFLICT_REBASES = 3;

export const APP_SETTINGS_REVISION_CONFLICT = 'CLAUDE_MCP_APP_SETTINGS_REVISION_CONFLICT';

export const ACTIVE_STATES: ClaudeMcpState[] = [
  'auth_starting',
  'waiting_for_user',
  'exchanging_code',
  'cancelling',
];

export const DASHED_PAGE_BORDER = '1px dashed color-mix(in srgb, var(--color-border-paper) 62%, transparent)';

export const SOFT_CONTROL_BORDER = '1px solid color-mix(in srgb, var(--color-border-paper) 58%, transparent)';

export const SOFT_ROW_DIVIDER = '1px solid color-mix(in srgb, var(--color-border-paper) 34%, transparent)';

export const SOFT_ROW_SURFACE = 'color-mix(in srgb, var(--color-bg-paper) 28%, transparent)';

export const STATE_LABELS: Record<ClaudeMcpState, string> = {
  not_configured: '未配置',
  configured: '已配置',
  needs_auth: '需要认证',
  auth_starting: '正在启动',
  waiting_for_user: '等待授权',
  exchanging_code: '正在交换凭证',
  connected: '已连接',
  failed: '连接失败',
  cancelling: '正在取消',
  logged_out: '已退出',
  disabled: '已禁用',
};

export const AUTH_STATE_LABELS: Record<ClaudeMcpAuthState, string> = {
  anonymous: '匿名连接，无需 OAuth',
  required: '需要认证',
  authenticated: '已认证',
  unknown: '认证状态未知',
};

export function authStateOf(server: ClaudeMcpServer | null): ClaudeMcpAuthState {
  return server?.auth_state ?? 'unknown';
}

export function canLogout(server: ClaudeMcpServer | null, state: ClaudeMcpState | undefined): boolean {
  const authState = authStateOf(server);
  if (server?.credential_configured) return true;
  return state === 'connected' && (authState === 'authenticated' || authState === 'unknown');
}

export function connectionStateLabel(server: ClaudeMcpServer | null, state: ClaudeMcpState | undefined): string {
  if (state === 'connected' && authStateOf(server) === 'anonymous') return '已匿名连接';
  if (state === 'connected' && authStateOf(server) === 'authenticated') return '已认证连接';
  return state ? STATE_LABELS[state] : '状态未知';
}

export function errorMessage(error: unknown, fallback: string): string {
  return error instanceof ClaudeMcpApiError
    ? `${error.message}（${error.code}）`
    : fallback;
}

export function operationErrorMessage(operation: ClaudeMcpOperation): string | null {
  return operation.error
    ? `${operation.error.message}（${operation.error.code}）`
    : null;
}

export function appUsagePolicyDraft(settings: ClaudeMcpAppSettings): AppUsagePolicyDraft {
  return {
    enabled: settings.desired.enabled,
    lowRiskToolCalls: settings.desired.interactions.lowRiskToolCalls,
    uiMessages: settings.desired.interactions.uiMessages,
  };
}

export function connectionSummary(
  server: ClaudeMcpServer | null,
  state: ClaudeMcpState | undefined,
  toolCount: number | undefined,
): string {
  const count = toolCount ?? '—';
  if (state === 'connected' && authStateOf(server) === 'anonymous') {
    return `已匿名连接，无需 OAuth；已发现 ${count} 个工具，可供 Chat 会话使用。`;
  }
  if (state === 'connected' && authStateOf(server) === 'authenticated') {
    return `已通过认证连接；已发现 ${count} 个工具，可供 Chat 会话使用。`;
  }
  if (state === 'connected') {
    return `连接可用；已发现 ${count} 个工具。认证状态由 Runtime 回报为未知。`;
  }
  if (state === 'needs_auth' && authStateOf(server) === 'required') {
    return '服务已明确要求认证，完成 OAuth 后可继续检测工具能力。';
  }
  if (state === 'failed') {
    return '最近一次 inventory discovery 失败；单 Server 失败不会阻塞其他 Server。';
  }
  return 'Server 配置已从 Dream 数据库加载；正在自动读取远端能力清单。';
}

export function formatDateTime(value?: string): string {
  if (!value) return '尚未探测';
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return value;
  return new Intl.DateTimeFormat(undefined, {
    month: 'short',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit',
  }).format(date);
}

export function stateTone(state: ClaudeMcpState | undefined): Tone {
  if (state === 'connected') return 'success';
  if (state === 'failed') return 'danger';
  if (state === 'needs_auth' || state === 'logged_out') return 'warning';
  if (state && ACTIVE_STATES.includes(state)) return 'info';
  return 'neutral';
}

export function toolMatchesFilter(tool: ClaudeMcpTool, filter: ToolFilter): boolean {
  if (filter === 'read_only') return tool.annotations.read_only === true;
  if (filter === 'destructive') return tool.annotations.destructive === true;
  if (filter === 'open_world') return tool.annotations.open_world === true;
  if (filter === 'unspecified') {
    return tool.annotations.read_only !== true
      && tool.annotations.destructive !== true
      && tool.annotations.open_world !== true;
  }
  return true;
}


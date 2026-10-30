// [Input] Original Notion status labels, catalog/source selection and pagination constants.
// [Output] Pure formatting and source selection metadata shared by Web/native.
// [Pos] No network, authorization or synchronization owner is added.
// [Sync] 2026-10-29: extract original state for Web/native reuse; HTTP, business payloads and permissions keep their owners.
import {ResourceConnectorApiError,type ResourceConnector,type ConnectorSource,type ConnectorAuthStatus,type ConnectorStatus,type ConnectorResourceSelection,type NotionCapabilityAvailability,type NotionResourceOption,type NotionCapabilityCatalog,type NotionSkillDetail,type NotionSkillFileDescriptor,type NotionSkillFileContent,type ResourceConnectorApi} from '../../api/resourceConnectorApi';
export type DetailView = 'overview' | 'skill' | 'file' | 'resources' | 'sources';
export type DetailTone = 'neutral' | 'success' | 'warning' | 'danger' | 'info';
export type UnifiedResourceKind = 'database' | 'page';

export interface UnifiedResourceOption extends NotionResourceOption {
  kind: UnifiedResourceKind;
}

export interface DetailStatus {
  label: string;
  tone: DetailTone;
}

export const DEFAULT_NOTION_CONNECTOR_NAME = 'Notion Resource Connector';
export const RESOURCE_PAGE_SIZE = 10;
// Browser setTimeout uses a signed 32-bit delay; this is a timer bound, not a sync policy.
export const MAX_TIMER_DELAY_MS = 2_147_483_647;

export interface ResourceRequestOwner {
  key: string;
  generation: number;
  abort: AbortController;
}

export function resourceFailureMessage(error: unknown, fallback: string): string {
  return error instanceof ResourceConnectorApiError && error.code === 'NOTION_SYNC_BUSY'
    ? '连接器已有同步任务，请稍后重试。' : getErrorMessage(error, fallback);
}
export const NOTION_WEBSITE = 'https://developers.notion.com/cli/get-started/overview';
export const NOTION_PRIVACY = 'https://privacycenter.notion.so/policies';
export const NOTION_TERMS = 'https://notion.notion.site/Terms-and-Privacy-28ffdd083dc3473e9c2da6ec011b58ac';

export function getErrorMessage(error: unknown, fallback: string): string {
  return error instanceof Error && error.message ? error.message : fallback;
}

export function formatDateTime(value?: string): string {
  if (!value) return '未更新';
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return '暂时无法读取';
  return new Intl.DateTimeFormat(undefined, {
    month: 'short',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  }).format(date);
}

export function formatConnectionDate(connector: ResourceConnector | null): string {
  if (!connector) return '尚未连接';
  if (!connector.createdAt) return '暂时无法读取';
  const date = new Date(connector.createdAt);
  if (Number.isNaN(date.getTime())) return '暂时无法读取';
  return new Intl.DateTimeFormat(undefined, {
    year: 'numeric',
    month: 'long',
    day: 'numeric',
  }).format(date);
}

export function formatFileSize(sizeBytes: number): string {
  if (sizeBytes < 1024) return `${sizeBytes} B`;
  return `${(sizeBytes / 1024).toFixed(sizeBytes < 10 * 1024 ? 1 : 0)} KB`;
}

export function formatSyncInterval(minutes: number): string {
  if (minutes < 60) return `每 ${minutes} 分钟`;
  if (minutes % 1440 === 0) return `每 ${minutes / 1440} 天`;
  return `每 ${minutes / 60} 小时`;
}

export function formatStatusLabel(
  status?: ConnectorStatus | ConnectorSource['status'] | ConnectorAuthStatus | 'idle',
): string {
  switch (status) {
    case 'authenticating': return '认证中';
    case 'authenticated': return '已认证';
    case 'syncing': return '同步中';
    case 'synced': return '已同步';
    case 'expired': return '已过期';
    case 'error': return '错误';
    case 'draft': return '待连接';
    default: return '待处理';
  }
}

export function availabilityLabel(availability: NotionCapabilityAvailability): string {
  switch (availability) {
    case 'available': return '可用';
    case 'requires_installation': return '需安装 ntn';
    case 'requires_connection': return '连接后可用';
    case 'requires_scope': return '选择资源后可用';
    default: return '不可用';
  }
}

export function availabilityTone(availability: NotionCapabilityAvailability): DetailTone {
  switch (availability) {
    case 'available': return 'success';
    case 'requires_installation': return 'warning';
    case 'requires_connection': return 'warning';
    case 'requires_scope': return 'info';
    default: return 'neutral';
  }
}

export function operationSourceLabel(source: 'runtime_hook' | 'workspace_materializer'): string {
  return source === 'runtime_hook' ? '内置 Hook' : '工作区';
}

export function getDetailStatus(connector: ResourceConnector | null, loading: boolean): DetailStatus {
  if (loading) {
    return { label: '读取中', tone: 'info' };
  }
  if (!connector) {
    return { label: '未连接', tone: 'warning' };
  }
  if (connector.syncPolicy?.status === 'error' || connector.syncPolicy?.workerErrorCode) {
    return { label: '部分可用', tone: 'warning' };
  }
  if (connector.auth.warning) {
    return { label: '部分可用', tone: 'warning' };
  }
  if (connector.status === 'error' || connector.auth.status === 'error') {
    return { label: '异常', tone: 'danger' };
  }
  if (connector.auth.status === 'expired') {
    return { label: '已过期', tone: 'warning' };
  }
  if (connector.auth.status === 'authenticating' || connector.status === 'authenticating') {
    return { label: '认证中', tone: 'info' };
  }
  if (connector.status === 'syncing') {
    return { label: '同步中', tone: 'info' };
  }
  if (connector.syncPolicy?.scheduleDue) {
    return { label: '等待同步', tone: 'warning' };
  }
  if (connector.auth.status === 'authenticated') {
    return connector.lastSyncedAt
      ? { label: '已连接', tone: 'success' }
      : { label: '已连接', tone: 'info' };
  }
  return { label: '待连接', tone: 'warning' };
}

export function buildSelectionFromSources(sources: ConnectorSource[]): ConnectorResourceSelection {
  return {
    databaseIds: sources.filter((source) => source.type === 'notion_database').map((source) => source.id),
    pageIds: sources.filter((source) => source.type === 'notion_page').map((source) => source.id),
  };
}

export function resolveSingleNotionConnector(connectors: ResourceConnector[]): ResourceConnector | null {
  const notionConnectors = connectors.filter((connector) => connector.platform === 'notion');
  if (notionConnectors.length === 0) return null;
  return notionConnectors.slice().sort((a, b) => {
    const aTime = new Date(a.updatedAt || a.createdAt || 0).getTime();
    const bTime = new Date(b.updatedAt || b.createdAt || 0).getTime();
    return bTime - aTime;
  })[0] ?? null;
}

export function shouldShowPageCount(pageCount?: number): pageCount is number {
  return typeof pageCount === 'number' && pageCount > 0;
}

export function sourceKindLabel(type: ConnectorSource['type']): string {
  return type === 'notion_database' ? '数据库' : '页面';
}


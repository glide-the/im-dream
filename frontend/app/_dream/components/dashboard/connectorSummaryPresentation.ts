// [Input] Original connector-summary DTOs and existing resource health labels.
// [Output] Shared last-interaction, health tone and status projection.
// [Pos] Pure resource summary presentation; authentication and synchronization remain server-owned.
// [Sync] 2026-10-29: reuse the original Web summary for native Resources.
import type {ResourceConnector} from '../../api/resourceConnectorApi';
export type ConnectorTone = 'neutral' | 'success' | 'warning' | 'danger';

export function formatLastInteraction(connector: ResourceConnector | null): string {
  const value = connector?.lastSyncedAt ?? connector?.updatedAt ?? connector?.createdAt;
  if (!value) return '暂无交互';

  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return value;

  return new Intl.DateTimeFormat(undefined, {
    month: 'short',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  }).format(date);
}

export function getResourceHealthTone(connector: ResourceConnector | null): ConnectorTone {
  if (!connector) return 'neutral';
  if (connector.syncPolicy?.status === 'error' || connector.syncPolicy?.workerErrorCode
    || connector.syncPolicy?.scheduleDue || connector.status === 'syncing' || connector.auth.warning) {
    return 'warning';
  }
  if (connector.status === 'authenticated' || connector.status === 'synced' || connector.auth.status === 'authenticated') {
    return connector.syncPolicy?.scheduleDue === false ? 'success' : 'neutral';
  }
  if (connector.status === 'authenticating' || connector.auth.status === 'authenticating') {
    return 'warning';
  }
  if (connector.status === 'expired' || connector.auth.status === 'expired' || connector.status === 'error' || connector.auth.status === 'error') {
    return 'danger';
  }
  return 'neutral';
}

export function getNotionStatusLabel(notionConnector:ResourceConnector|null):string {
      if (!notionConnector) return '未连接';
      if (notionConnector.syncPolicy?.status === 'error' || notionConnector.syncPolicy?.workerErrorCode || notionConnector.auth.warning) {
        return '部分可用';
      }
      if (notionConnector.status === 'syncing') return '同步中';
      if (notionConnector.syncPolicy?.scheduleDue) return '等待同步';
      if (notionConnector.status === 'authenticated' || notionConnector.status === 'synced' || notionConnector.auth.status === 'authenticated') {
        return notionConnector.syncPolicy?.scheduleDue === false ? '健康' : '已连接';
      }
      if (notionConnector.status === 'authenticating' || notionConnector.auth.status === 'authenticating') {
        return '认证中';
      }
      if (notionConnector.status === 'expired' || notionConnector.auth.status === 'expired') {
        return '已过期';
      }
      if (notionConnector.status === 'error' || notionConnector.auth.status === 'error') {
        return '异常';
      }
      return '未连接';
}

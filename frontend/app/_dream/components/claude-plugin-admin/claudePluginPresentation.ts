// [Input] Original ClaudePlugin Marketplace steps and component inventory DTO.
// [Output] Unchanged stage labels and component-count presentation for Web and native.
// [Pos] Shared plugin presentation; install policy remains server-owned.
// [Sync] 2026-10-29: extract the original Web display metadata without changing its DOM or CSS.
import type {ClaudePluginMarketplaceEntry} from '../../api/claudePluginAdminApi';
import type {MarketplaceStep} from '../../hooks/useClaudePluginAdmin';
export const MARKETPLACE_STEPS: Array<{ id: MarketplaceStep; label: string }> = [
  { id: 'select', label: '选择插件' },
  { id: 'confirm', label: '确认安装' },
  { id: 'installing', label: '正在安装' },
  { id: 'result', label: '可以使用' },
];

export function componentSummary(entry: ClaudePluginMarketplaceEntry): string {
  const inventory = entry.component_inventory ?? {};
  const values = [
    ['skills', inventory.skills],
    ['commands', inventory.commands],
    ['agents', inventory.agents],
    ['MCP', inventory.mcpServers],
  ].filter(([, count]) => typeof count === 'number' && count > 0);
  return values.length
    ? values.map(([label, count]) => `${count} ${label}`).join(' · ')
    : '已通过 manifest 与目录校验';
}


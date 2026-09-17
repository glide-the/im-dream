// [Input] Searchable settings navigation items and the user's free-text query.
// [Output] Stable, token-aware navigation matches derived from labels, routes, section keys and aliases.
// [Pos] Pure search policy for the Story Workspace Settings sidebar; routing remains owned by the page.
// [Sync] 2026-09-17: index Deck Workflow and Claude Code plugin concepts under the shared Plugins route.
export const STORY_WORKSPACE_SETTINGS_STATIC_SEARCH_KEYS = {
  settings: [
    'settings', 'settings-general', '/story-workspace/settings',
    'general language appearance theme energy 常规 语言 外观 主题 能量',
  ],
  'settings-subscription': [
    'settings-subscription', 'subscription', '/story-workspace/subscription',
    'plan billing renewal 套餐 账单 续期',
  ],
  'settings-work': [
    'settings-work', 'work', 'deck', '/story-workspace/settings/work',
    '/story-workspace/settings/work?tab=deck', '工作 卡组',
  ],
  'settings-resources': [
    'settings-resources', 'resources', 'resource links', 'connector', 'notion',
    'claude mcp', 'mcp', '/story-workspace/settings/resources',
    '/story-workspace/settings/work?tab=resources', '资源 连接器',
  ],
  'settings-plugins': [
    'settings-plugins', 'plugins', 'plugin', 'marketplace', 'deck workflow',
    'deck plugin', 'claude code plugin', 'runtime plugin',
    '/story-workspace/settings/plugins', '/story-workspace/settings/work?tab=plugins',
    '插件 市场 工作流 运行时',
  ],
  'settings-model': [
    'settings-model', 'model', 'ai', '/story-workspace/settings/model',
    '模型',
  ],
  'settings-about': [
    'settings-about', 'about', 'version', 'release',
    '/story-workspace/settings/about', '关于 版本 发布',
  ],
} as const;

export type StoryWorkspaceSettingsSearchKey = keyof typeof STORY_WORKSPACE_SETTINGS_STATIC_SEARCH_KEYS;

export interface SearchableSettingsNavigationItem {
  searchKeys: readonly string[];
}

function normalize(value: string) {
  return value.normalize('NFKC').toLocaleLowerCase().trim();
}

export function filterStoryWorkspaceSettingsNavigation<
  T extends SearchableSettingsNavigationItem,
>(items: readonly T[], query: string): T[] {
  const tokens = normalize(query).split(/\s+/).filter(Boolean);
  if (tokens.length === 0) return [...items];
  return items.filter((item) => {
    const searchable = normalize(item.searchKeys.join(' '));
    return tokens.every((token) => searchable.includes(token));
  });
}

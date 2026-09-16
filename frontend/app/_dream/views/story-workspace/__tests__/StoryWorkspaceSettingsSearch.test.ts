// [Input] Settings navigation labels, section IDs, paths and nested connector aliases.
// [Output] Deterministic evidence that sidebar search resolves every indexed route, including MCP resources.
// [Pos] Pure Settings navigation search regression; no browser, API or persisted configuration.
// [Sync] 2026-09-16: cover normalized multi-token matching and nested Work destinations.
import { expect, test } from '@playwright/test';
import {
  filterStoryWorkspaceSettingsNavigation,
  STORY_WORKSPACE_SETTINGS_STATIC_SEARCH_KEYS,
} from '../storyWorkspaceSettingsSearch';
import { STORY_WORKSPACE_PATHS } from '../../../router/storyWorkspacePath';

const items = [
  {
    id: 'settings',
    path: '/story-workspace/settings',
    searchKeys: ['General', 'settings', 'language', 'appearance'],
  },
  {
    id: 'settings-resources',
    path: '/story-workspace/settings/work?tab=resources',
    searchKeys: ['Resource links', 'settings-resources', 'connector', 'Notion', 'Claude MCP'],
  },
  {
    id: 'settings-plugins',
    path: '/story-workspace/settings/work?tab=plugins',
    searchKeys: ['Plugins', 'settings-plugins', 'marketplace'],
  },
];

test('finds nested connector routes by product alias and section key', () => {
  expect(filterStoryWorkspaceSettingsNavigation(items, 'MCP').map(item => item.id))
    .toEqual(['settings-resources']);
  expect(filterStoryWorkspaceSettingsNavigation(items, 'settings resources').map(item => item.id))
    .toEqual(['settings-resources']);
});

test('normalizes case and requires every query token', () => {
  expect(filterStoryWorkspaceSettingsNavigation(items, 'claude mcp').map(item => item.id))
    .toEqual(['settings-resources']);
  expect(filterStoryWorkspaceSettingsNavigation(items, 'plugin missing')).toEqual([]);
});

test('returns the complete index for an empty query', () => {
  expect(filterStoryWorkspaceSettingsNavigation(items, '  ')).toEqual(items);
});

test('defines searchable keys for every Settings navigation destination', () => {
  const routeKeys = Object.keys(STORY_WORKSPACE_PATHS)
    .filter(key => key === 'subscription' || key.startsWith('settings'))
    .map(key => key === 'subscription' ? 'settings-subscription' : key)
    .sort();
  expect(Object.keys(STORY_WORKSPACE_SETTINGS_STATIC_SEARCH_KEYS).sort()).toEqual(routeKeys);
  for (const [id, searchKeys] of Object.entries(STORY_WORKSPACE_SETTINGS_STATIC_SEARCH_KEYS)) {
    expect(filterStoryWorkspaceSettingsNavigation([{ id, searchKeys }], id)).toHaveLength(1);
  }
});

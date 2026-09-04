// [Input] Backend common commands plus installed Claude-plugin inventories, Deck refs, and receipts.
// [Output] Contract coverage for safe merged slash Skill discovery and text-only matching.
// [Pos] Chat composer Skill suggestion unit contract.
// [Sync] 2026-09-04: cover validated common commands, common-first de-duplication, and filtering.
import { expect, test } from '@playwright/test';
import type {
  ClaudePluginInstallation,
  DeckClaudePluginRef,
  PluginLoadReceipt,
} from '../../../api/claudePluginAdminApi';
import {
  filterInstalledSkillCommands,
  mergeSkillCommands,
  resolveCommonSkillCommands,
  resolveInstalledSkillCommands,
} from '../slashSkillCommands';

const SKILLS = [
  'drama-init', 'drama-plan', 'drama-script', 'drama-asset', 'drama-storyboard',
  'drama-prompt', 'drama-render', 'drama-voice', 'drama-edit', 'drama-promote',
  'drama-query', 'drama-doctor', 'drama-payoff',
] as const;

function installation(overrides: Partial<ClaudePluginInstallation> = {}): ClaudePluginInstallation {
  return {
    id: 'installation-1',
    requested_package_spec: 'drama-forge@drama-studio',
    package_name: 'drama-forge',
    marketplace: 'drama-studio',
    requested_version: null,
    resolved_version: '1.0.1',
    source_type: 'marketplace',
    artifact_digest: `sha256:${'a'.repeat(64)}`,
    artifact_path: '/managed/artifact',
    claude_cli_version: '1.0.0',
    cli_git_commit_sha: null,
    manifest_json: null,
    component_inventory_json: JSON.stringify({
      skills: [...SKILLS, '<root>', '../unsafe'],
    }),
    compatibility_json: '{}',
    status: 'ready',
    operation_id: 'operation-1',
    error_code: null,
    error_summary: null,
    file_count: 1,
    created_at: '2026-08-13T00:00:00Z',
    updated_at: '2026-08-13T00:00:00Z',
    installed_at: '2026-08-13T00:00:00Z',
    ...overrides,
  };
}

function ref(overrides: Partial<DeckClaudePluginRef> = {}): DeckClaudePluginRef {
  return {
    deck_id: 'deck-1',
    plugin_installation_id: 'installation-1',
    package_spec: 'drama-forge@drama-studio',
    resolved_version: '1.0.1',
    artifact_digest: `sha256:${'a'.repeat(64)}`,
    enabled: 1,
    order_index: 0,
    ...overrides,
  };
}

function receipt(digest = `sha256:${'a'.repeat(64)}`): PluginLoadReceipt {
  return {
    thread_id: 'thread-1',
    deck_id: 'deck-1',
    workspace_found: true,
    receipt: {
      schema_version: 'plugin-load-receipt/v1',
      workspace: 'thread-1',
      deck_id: 'deck-1',
      packed_at: '2026-08-13T00:00:00Z',
      frozen: true,
      plugins: [{
        package_spec: 'drama-forge@drama-studio',
        resolved_version: '1.0.1',
        artifact_digest: digest,
        relative_path: 'plugins/drama-forge',
        verified: true,
      }],
    },
    launch_manifest: null,
  };
}

test('resolves the thirteen installed drama Skills without a stage order', () => {
  const commands = resolveInstalledSkillCommands({
    refs: [ref()],
    installations: [installation()],
  });

  expect(commands.map((item) => item.command)).toEqual(SKILLS.map((name) => `/${name}`));
  expect(commands).toHaveLength(13);
});

test('resolves safe backend common Skills and rejects malformed public commands', () => {
  expect(resolveCommonSkillCommands([
    { command: '/asr', name: 'asr' },
    { command: '/hhxg-market', name: 'hhxg-market' },
    { command: '/symbolic-board', name: 'symbolic-board' },
    { command: '/ASR', name: 'asr' },
    { command: '/../unsafe', name: '../unsafe' },
  ])).toEqual([
    { command: '/asr', name: 'asr', sourceLabel: 'Ink & Memory' },
    { command: '/hhxg-market', name: 'hhxg-market', sourceLabel: 'Ink & Memory' },
    { command: '/symbolic-board', name: 'symbolic-board', sourceLabel: 'Ink & Memory' },
  ]);
});

test('keeps the backend common command when a Deck plugin exposes the same name', () => {
  const common = resolveCommonSkillCommands([{ command: '/asr', name: 'asr' }]);
  const deck = [{ command: '/asr', name: 'asr', sourceLabel: 'audio@deck' }];

  expect(mergeSkillCommands(common, deck)).toEqual(common);
});

test('filters slash text only and never interprets a workflow stage', () => {
  const commands = resolveInstalledSkillCommands({
    refs: [ref()],
    installations: [installation()],
  });

  expect(filterInstalledSkillCommands('/', commands)).toHaveLength(13);
  expect(filterInstalledSkillCommands('/drama-p', commands).map((item) => item.command)).toEqual([
    '/drama-plan', '/drama-prompt', '/drama-promote', '/drama-payoff',
  ]);
  expect(filterInstalledSkillCommands('请执行 /drama-script', commands)).toEqual([]);
  expect(filterInstalledSkillCommands('/drama-script EP02', commands)).toEqual([]);
});

test('fails closed for disabled, stale, unsafe, duplicate, and non-ready inventories', () => {
  const commands = resolveInstalledSkillCommands({
    refs: [
      ref({ enabled: 0 }),
      ref({ plugin_installation_id: 'missing' }),
      ref(),
      ref({ order_index: 1 }),
    ],
    installations: [
      installation(),
      installation({ id: 'not-ready', status: 'error' }),
    ],
  });

  expect(commands).toHaveLength(13);
  expect(commands.some((item) => item.command === '/<root>')).toBe(false);
  expect(commands.some((item) => item.command.includes('unsafe'))).toBe(false);
});

test('a frozen thread receipt excludes Deck refs not loaded into that thread', () => {
  expect(resolveInstalledSkillCommands({
    refs: [ref()],
    installations: [installation()],
    receipt: receipt(`sha256:${'b'.repeat(64)}`),
  })).toEqual([]);

  expect(resolveInstalledSkillCommands({
    refs: [ref()],
    installations: [installation()],
    receipt: receipt(),
  })).toHaveLength(13);
});

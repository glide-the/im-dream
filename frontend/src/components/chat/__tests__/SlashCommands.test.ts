// [Input] Installed Claude-plugin inventories, Deck refs, and optional frozen thread receipts.
// [Output] Contract coverage for typed Skill and namespaced plugin-command slash discovery.
// [Pos] Chat composer slash suggestion unit contract.
// [Sync] 2026-08-20: cover Skill-only, Command-only, and mixed typed inventories.
import { expect, test } from '@playwright/test';
import type {
  ClaudePluginInstallation,
  DeckClaudePluginRef,
  PluginLoadReceipt,
} from '../../../api/claudePluginAdminApi';
import {
  filterInstalledSlashCommands,
  resolveInstalledSlashCommands,
} from '../slashCommands';

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
  const commands = resolveInstalledSlashCommands({
    refs: [ref()],
    installations: [installation()],
  });

  expect(commands.map((item) => item.command)).toEqual(SKILLS.map((name) => `/${name}`));
  expect(commands.every((item) => item.kind === 'skill')).toBe(true);
  expect(commands).toHaveLength(13);
});

test('resolves Comfy commands with the Claude plugin namespace and command type', () => {
  const commands = resolveInstalledSlashCommands({
    refs: [ref({
      plugin_installation_id: 'installation-comfy',
      package_spec: 'comfy-cloud@comfy-skills',
      resolved_version: '0.1.0',
    })],
    installations: [installation({
      id: 'installation-comfy',
      requested_package_spec: 'comfy-cloud@comfy-skills',
      package_name: 'comfy-cloud',
      marketplace: 'comfy-skills',
      resolved_version: '0.1.0',
      manifest_json: JSON.stringify({ name: 'comfy-cloud' }),
      component_inventory_json: JSON.stringify({
        commands: [
          'generate-image.md',
          'search-models.md',
          '../unsafe.md',
          'UPPERCASE.md',
        ],
      }),
    })],
  });

  expect(commands).toEqual([
    {
      command: '/comfy-cloud:generate-image',
      kind: 'command',
      name: 'generate-image',
      packageSpec: 'comfy-cloud@comfy-skills',
    },
    {
      command: '/comfy-cloud:search-models',
      kind: 'command',
      name: 'search-models',
      packageSpec: 'comfy-cloud@comfy-skills',
    },
  ]);
});

test('keeps Skill and Command types distinct when one plugin exposes both', () => {
  const commands = resolveInstalledSlashCommands({
    refs: [ref()],
    installations: [installation({
      manifest_json: JSON.stringify({ name: 'mixed-plugin' }),
      component_inventory_json: JSON.stringify({
        skills: ['draft-story'],
        commands: ['publish-story.md'],
      }),
    })],
  });

  expect(commands.map(({ command, kind }) => ({ command, kind }))).toEqual([
    { command: '/draft-story', kind: 'skill' },
    { command: '/mixed-plugin:publish-story', kind: 'command' },
  ]);
});

test('filters slash text only and never interprets a workflow stage', () => {
  const commands = resolveInstalledSlashCommands({
    refs: [ref()],
    installations: [installation()],
  });

  expect(filterInstalledSlashCommands('/', commands)).toHaveLength(13);
  expect(filterInstalledSlashCommands('/drama-p', commands).map((item) => item.command)).toEqual([
    '/drama-plan', '/drama-prompt', '/drama-promote', '/drama-payoff',
  ]);
  expect(filterInstalledSlashCommands('请执行 /drama-script', commands)).toEqual([]);
  expect(filterInstalledSlashCommands('/drama-script EP02', commands)).toEqual([]);
});

test('matches plugin commands by namespace or command name', () => {
  const commands = resolveInstalledSlashCommands({
    refs: [ref()],
    installations: [installation({
      package_name: 'comfy-cloud',
      manifest_json: JSON.stringify({ name: 'comfy-cloud' }),
      component_inventory_json: JSON.stringify({ commands: ['generate-image.md'] }),
    })],
  });

  expect(filterInstalledSlashCommands('/comfy', commands)).toHaveLength(1);
  expect(filterInstalledSlashCommands('/image', commands)).toHaveLength(1);
});

test('fails closed for disabled, stale, unsafe, duplicate, and non-ready inventories', () => {
  const commands = resolveInstalledSlashCommands({
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
  expect(resolveInstalledSlashCommands({
    refs: [ref()],
    installations: [installation()],
    receipt: receipt(`sha256:${'b'.repeat(64)}`),
  })).toEqual([]);

  expect(resolveInstalledSlashCommands({
    refs: [ref()],
    installations: [installation()],
    receipt: receipt(),
  })).toHaveLength(13);
});

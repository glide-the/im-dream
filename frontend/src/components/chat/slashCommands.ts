// [Input] Deck Claude-plugin refs, immutable thread load receipts, and installed plugin inventories.
// [Output] Resolve safe, typed Skill and namespaced plugin-command slash suggestions.
// [Pos] Pure Chat slash-discovery helper; it does not execute commands or inspect workflow state.
// [Sync] 2026-08-13: added installed-Skill slash suggestions without a workflow state machine.
// [Sync] 2026-08-20: enumerate skills and commands separately; namespace plugin commands.

import {
  getThreadPluginLoadReceipt,
  listClaudePluginInstallations,
  listDeckClaudePluginRefs,
  type ClaudePluginInstallation,
  type DeckClaudePluginRef,
  type PluginLoadReceipt,
} from '../../api/claudePluginAdminApi';

const SAFE_SLASH_SEGMENT = /^[a-z0-9][a-z0-9-]{0,63}$/;
const SAFE_COMMAND_FILE = /^([a-z0-9][a-z0-9-]{0,63})\.md$/;
const SLASH_DRAFT = /^\/[^\s]*$/;

export interface InstalledSlashCommand {
  readonly command: string;
  readonly kind: 'skill' | 'command';
  readonly name: string;
  readonly packageSpec: string;
}

interface ComponentInventory {
  readonly skills?: unknown;
  readonly commands?: unknown;
}

function componentInventory(raw: string | undefined): ComponentInventory {
  if (!raw) return {};
  try {
    const value = JSON.parse(raw) as unknown;
    return value !== null && typeof value === 'object' ? value as ComponentInventory : {};
  } catch {
    return {};
  }
}

function inventorySkills(inventory: ComponentInventory): readonly string[] {
  return Array.isArray(inventory.skills)
    ? inventory.skills.filter(
      (item): item is string => typeof item === 'string' && SAFE_SLASH_SEGMENT.test(item),
    )
    : [];
}

function inventoryCommands(inventory: ComponentInventory): readonly string[] {
  if (!Array.isArray(inventory.commands)) return [];
  return inventory.commands.flatMap((item) => {
    if (typeof item !== 'string') return [];
    const match = SAFE_COMMAND_FILE.exec(item);
    return match?.[1] ? [match[1]] : [];
  });
}

function pluginCommandNamespace(installation: ClaudePluginInstallation): string | null {
  if (installation.manifest_json) {
    try {
      const manifest = JSON.parse(installation.manifest_json) as { readonly name?: unknown };
      if (typeof manifest.name === 'string' && SAFE_SLASH_SEGMENT.test(manifest.name)) {
        return manifest.name;
      }
    } catch {
      return null;
    }
  }
  return SAFE_SLASH_SEGMENT.test(installation.package_name)
    ? installation.package_name
    : null;
}

function readyInstallationById(
  installations: readonly ClaudePluginInstallation[],
): ReadonlyMap<string, ClaudePluginInstallation> {
  return new Map(
    installations
      .filter((item) => item.status === 'ready')
      .map((item) => [item.id, item] as const),
  );
}

function receiptAllowsRef(
  receipt: PluginLoadReceipt | null,
  ref: DeckClaudePluginRef,
): boolean {
  if (receipt?.receipt?.frozen !== true) return true;
  return receipt.receipt.plugins.some(
    (plugin) => plugin.verified
      && plugin.package_spec === ref.package_spec
      && plugin.artifact_digest === ref.artifact_digest,
  );
}

export function resolveInstalledSlashCommands(input: {
  readonly refs: readonly DeckClaudePluginRef[];
  readonly installations: readonly ClaudePluginInstallation[];
  readonly receipt?: PluginLoadReceipt | null;
}): readonly InstalledSlashCommand[] {
  const installations = readyInstallationById(input.installations);
  const commands = new Map<string, InstalledSlashCommand>();
  const refs = [...input.refs]
    .filter((ref) => Boolean(ref.enabled))
    .sort((left, right) => left.order_index - right.order_index);
  for (const ref of refs) {
    if (!receiptAllowsRef(input.receipt ?? null, ref)) continue;
    const installation = installations.get(ref.plugin_installation_id);
    if (
      installation === undefined
      || installation.artifact_digest !== ref.artifact_digest
      || installation.resolved_version !== ref.resolved_version
    ) continue;
    const inventory = componentInventory(installation.component_inventory_json);
    for (const name of inventorySkills(inventory)) {
      const command = `/${name}`;
      if (!commands.has(command)) {
        commands.set(command, {
          command,
          kind: 'skill',
          name,
          packageSpec: ref.package_spec,
        });
      }
    }
    const namespace = pluginCommandNamespace(installation);
    if (!namespace) continue;
    for (const name of inventoryCommands(inventory)) {
      const command = `/${namespace}:${name}`;
      if (!commands.has(command)) {
        commands.set(command, {
          command,
          kind: 'command',
          name,
          packageSpec: ref.package_spec,
        });
      }
    }
  }
  return [...commands.values()];
}

export function filterInstalledSlashCommands(
  draft: string,
  commands: readonly InstalledSlashCommand[],
): readonly InstalledSlashCommand[] {
  if (!SLASH_DRAFT.test(draft)) return [];
  const query = draft.slice(1).toLowerCase();
  return commands.filter((item) => item.command.slice(1).toLowerCase().includes(query));
}

export async function loadInstalledSlashCommands(input: {
  readonly deckId?: string;
  readonly threadId?: string;
}): Promise<readonly InstalledSlashCommand[]> {
  const receipt = input.threadId
    ? await getThreadPluginLoadReceipt(input.threadId).catch(() => null)
    : null;
  const deckId = input.deckId ?? receipt?.deck_id ?? receipt?.receipt?.deck_id ?? null;
  if (deckId === null) return [];
  const [refs, installationResult] = await Promise.all([
    listDeckClaudePluginRefs(deckId),
    listClaudePluginInstallations(),
  ]);
  return resolveInstalledSlashCommands({
    refs,
    installations: installationResult.installations,
    receipt,
  });
}

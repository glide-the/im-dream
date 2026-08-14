// [Input] Deck Claude-plugin refs, immutable thread load receipts, and installed plugin inventories.
// [Output] Resolve safe, de-duplicated slash Skill suggestions for the Chat composer.
// [Pos] Pure Chat composer discovery helper; it does not execute commands or inspect workflow state.
// [Sync] 2026-08-13: added installed-Skill slash suggestions without a workflow state machine.

import {
  getThreadPluginLoadReceipt,
  listClaudePluginInstallations,
  listDeckClaudePluginRefs,
  type ClaudePluginInstallation,
  type DeckClaudePluginRef,
  type PluginLoadReceipt,
} from '../../api/claudePluginAdminApi';

const SAFE_SKILL_NAME = /^[a-z0-9][a-z0-9-]{0,63}$/;
const SLASH_DRAFT = /^\/[^\s]*$/;

export interface InstalledSkillCommand {
  readonly command: string;
  readonly name: string;
  readonly packageSpec: string;
}

function inventorySkills(raw: string | undefined): readonly string[] {
  if (!raw) return [];
  try {
    const value = JSON.parse(raw) as { readonly skills?: unknown };
    return Array.isArray(value.skills)
      ? value.skills.filter(
        (item): item is string => typeof item === 'string' && SAFE_SKILL_NAME.test(item),
      )
      : [];
  } catch {
    return [];
  }
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

export function resolveInstalledSkillCommands(input: {
  readonly refs: readonly DeckClaudePluginRef[];
  readonly installations: readonly ClaudePluginInstallation[];
  readonly receipt?: PluginLoadReceipt | null;
}): readonly InstalledSkillCommand[] {
  const installations = readyInstallationById(input.installations);
  const commands = new Map<string, InstalledSkillCommand>();
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
    for (const name of inventorySkills(installation.component_inventory_json)) {
      const command = `/${name}`;
      if (!commands.has(command)) {
        commands.set(command, { command, name, packageSpec: ref.package_spec });
      }
    }
  }
  return [...commands.values()];
}

export function filterInstalledSkillCommands(
  draft: string,
  commands: readonly InstalledSkillCommand[],
): readonly InstalledSkillCommand[] {
  if (!SLASH_DRAFT.test(draft)) return [];
  const query = draft.slice(1).toLowerCase();
  return commands.filter((item) => item.name.includes(query));
}

export async function loadInstalledSkillCommands(input: {
  readonly deckId?: string;
  readonly threadId?: string;
}): Promise<readonly InstalledSkillCommand[]> {
  const receipt = input.threadId
    ? await getThreadPluginLoadReceipt(input.threadId).catch(() => null)
    : null;
  const deckId = input.deckId ?? receipt?.deck_id ?? receipt?.receipt?.deck_id ?? null;
  if (deckId === null) return [];
  const [refs, installationResult] = await Promise.all([
    listDeckClaudePluginRefs(deckId),
    listClaudePluginInstallations(),
  ]);
  return resolveInstalledSkillCommands({
    refs,
    installations: installationResult.installations,
    receipt,
  });
}

// [Input] Backend common Skill catalog plus Deck Claude-plugin refs, receipts, and inventories.
// [Output] Resolve safe, de-duplicated common and Deck slash Skill suggestions for Chat.
// [Pos] Pure Chat composer discovery helper; it does not execute commands or inspect workflow state.
// [Sync] 2026-08-13: added installed-Skill slash suggestions without a workflow state machine.
// [Sync] 2026-09-04: merge backend-owned common Skills ahead of optional Deck plugin Skills.

import {
  listCommonSkillCommands,
  type CommonSkillCommandDto,
} from '../../api/claudeAgentSkillApi';
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

export interface AvailableSkillCommand {
  readonly command: string;
  readonly name: string;
  readonly sourceLabel: string;
}

const COMMON_SKILL_SOURCE_LABEL = 'Ink & Memory';

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
}): readonly AvailableSkillCommand[] {
  const installations = readyInstallationById(input.installations);
  const commands = new Map<string, AvailableSkillCommand>();
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
        commands.set(command, { command, name, sourceLabel: ref.package_spec });
      }
    }
  }
  return [...commands.values()];
}

export function resolveCommonSkillCommands(
  rawCommands: readonly CommonSkillCommandDto[],
): readonly AvailableSkillCommand[] {
  const commands = new Map<string, AvailableSkillCommand>();
  for (const item of rawCommands) {
    if (
      typeof item?.name !== 'string'
      || !SAFE_SKILL_NAME.test(item.name)
      || item.command !== `/${item.name}`
    ) continue;
    if (!commands.has(item.command)) {
      commands.set(item.command, {
        command: item.command,
        name: item.name,
        sourceLabel: COMMON_SKILL_SOURCE_LABEL,
      });
    }
  }
  return [...commands.values()];
}

export function mergeSkillCommands(
  commonCommands: readonly AvailableSkillCommand[],
  deckCommands: readonly AvailableSkillCommand[],
): readonly AvailableSkillCommand[] {
  const commands = new Map<string, AvailableSkillCommand>();
  for (const command of [...commonCommands, ...deckCommands]) {
    if (!commands.has(command.command)) commands.set(command.command, command);
  }
  return [...commands.values()];
}

export function filterInstalledSkillCommands(
  draft: string,
  commands: readonly AvailableSkillCommand[],
): readonly AvailableSkillCommand[] {
  if (!SLASH_DRAFT.test(draft)) return [];
  const query = draft.slice(1).toLowerCase();
  return commands.filter((item) => item.name.includes(query));
}

export async function loadAvailableSkillCommands(input: {
  readonly deckId?: string;
  readonly threadId?: string;
}): Promise<readonly AvailableSkillCommand[]> {
  const [commonCommands, receipt] = await Promise.all([
    listCommonSkillCommands()
      .then(resolveCommonSkillCommands)
      .catch(() => []),
    input.threadId
      ? getThreadPluginLoadReceipt(input.threadId).catch(() => null)
      : Promise.resolve(null),
  ]);
  const deckId = input.deckId ?? receipt?.deck_id ?? receipt?.receipt?.deck_id ?? null;
  if (deckId === null) return commonCommands;
  const deckCommands = await Promise.all([
    listDeckClaudePluginRefs(deckId),
    listClaudePluginInstallations(),
  ])
    .then(([refs, installationResult]) => resolveInstalledSkillCommands({
      refs,
      installations: installationResult.installations,
      receipt,
    }))
    .catch(() => []);
  return mergeSkillCommands(commonCommands, deckCommands);
}

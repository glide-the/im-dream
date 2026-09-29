// [Input] A completed create_scheduled_task Tool part output from the live turn or persisted process detail.
// [Output] A strict, display-safe scheduled-task snapshot or null when the Tool/result contract does not match.
// [Pos] Shared scheduled-task Tool decoder for Chat markers; it does not infer tasks from assistant prose.
// [Sync] 2026-09-29: mirror the production mcp__user__ Tool name and top-level ok/status/scheduled_task receipt instead of synthetic test shapes.

export type ScheduledTaskMarkerRule =
  | { kind: 'once'; local_date: string; local_time: string; time_zone: string }
  | { kind: 'daily'; local_time: string; time_zone: string };

export type ScheduledTaskMarkerSnapshot = {
  id: string;
  title: string;
  rule: ScheduledTaskMarkerRule;
  nextRunAt: string | null;
  status: 'active' | 'paused' | 'exhausted' | 'deleted';
  revision: number;
};

const CREATE_SCHEDULED_TASK_TOOL_NAMES = new Set([
  'create_scheduled_task',
  'mcp__user__create_scheduled_task',
]);

function objectValue(value: unknown): Record<string, unknown> | null {
  if (!value || typeof value !== 'object' || Array.isArray(value)) return null;
  return value as Record<string, unknown>;
}

function parseOutput(output: unknown): Record<string, unknown> | null {
  if (typeof output !== 'string') return objectValue(output);
  try { return objectValue(JSON.parse(output)); } catch { return null; }
}

function nonempty(value: unknown): value is string {
  return typeof value === 'string' && value.trim().length > 0;
}

export function decodeScheduledTaskMarker(toolName: string, output: unknown): ScheduledTaskMarkerSnapshot | null {
  if (!CREATE_SCHEDULED_TASK_TOOL_NAMES.has(toolName)) return null;
  const envelope = parseOutput(output);
  if (!envelope || envelope.ok !== true) return null;
  if (envelope.status !== 'ok') return null;
  const task = objectValue(envelope.scheduled_task);
  const rule = objectValue(task?.rule);
  if (!task || !rule || !nonempty(task.id) || !nonempty(task.title)
    || !Number.isSafeInteger(task.revision) || (task.revision as number) < 1
    || !['active', 'paused', 'exhausted', 'deleted'].includes(String(task.status))
    || !['once', 'daily'].includes(String(rule.kind))
    || !nonempty(rule.local_time) || !nonempty(rule.time_zone)) return null;
  if (rule.kind === 'once' && !nonempty(rule.local_date)) return null;
  if (task.next_run_at !== null && task.next_run_at !== undefined && !nonempty(task.next_run_at)) return null;
  return {
    id: task.id,
    title: task.title,
    rule: rule.kind === 'once'
      ? { kind: 'once', local_date: rule.local_date as string, local_time: rule.local_time, time_zone: rule.time_zone }
      : { kind: 'daily', local_time: rule.local_time, time_zone: rule.time_zone },
    nextRunAt: typeof task.next_run_at === 'string' ? task.next_run_at : null,
    status: task.status as ScheduledTaskMarkerSnapshot['status'],
    revision: task.revision as number,
  };
}

export function scheduledTaskMarkerSummary(task: ScheduledTaskMarkerSnapshot, dailyLabel: string): string {
  return task.rule.kind === 'once'
    ? `${task.rule.local_date} · ${task.rule.local_time}`
    : `${dailyLabel} · ${task.rule.local_time}`;
}

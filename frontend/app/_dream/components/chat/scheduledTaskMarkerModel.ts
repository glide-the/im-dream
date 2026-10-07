// [Input] A completed create_scheduled_task Tool part output from the live turn or persisted process detail.
// [Output] A strict, display-safe scheduled-task snapshot or null when the Tool/result contract does not match.
// [Pos] Shared scheduled-task Tool decoder for Chat markers; it does not infer tasks from assistant prose.
// [Sync] 2026-10-07: decode v3 hourly/weekly rules and render their structured cadence without prose inference.

export type ScheduledTaskMarkerRule =
  | { kind: 'once'; local_date: string; local_time: string; time_zone: string }
  | { kind: 'daily'; local_time: string; time_zone: string }
  | { kind: 'interval'; interval_minutes: number; time_zone: string }
  | { kind: 'hourly'; interval_hours: number; minute: number; time_zone: string }
  | { kind: 'weekly'; weekdays: Array<'MO' | 'TU' | 'WE' | 'TH' | 'FR' | 'SA' | 'SU'>; local_time: string; time_zone: string };

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
    || !['once', 'daily', 'interval', 'hourly', 'weekly'].includes(String(rule.kind))
    || !nonempty(rule.time_zone)) return null;
  if (rule.kind === 'once' && !nonempty(rule.local_date)) return null;
  if (['once', 'daily', 'weekly'].includes(String(rule.kind)) && !nonempty(rule.local_time)) return null;
  if (rule.kind === 'interval' && (!Number.isSafeInteger(rule.interval_minutes)
    || (rule.interval_minutes as number) < 1)) return null;
  if (rule.kind === 'hourly' && (!Number.isSafeInteger(rule.interval_hours)
    || (rule.interval_hours as number) < 1 || !Number.isSafeInteger(rule.minute)
    || (rule.minute as number) < 0 || (rule.minute as number) > 59)) return null;
  const weekdays = Array.isArray(rule.weekdays) ? rule.weekdays : [];
  if (rule.kind === 'weekly' && (weekdays.length < 1 || weekdays.length > 7
    || new Set(weekdays).size !== weekdays.length
    || weekdays.some((day) => !['MO', 'TU', 'WE', 'TH', 'FR', 'SA', 'SU'].includes(String(day))))) return null;
  if (task.next_run_at !== null && task.next_run_at !== undefined && !nonempty(task.next_run_at)) return null;
  return {
    id: task.id,
    title: task.title,
    rule: rule.kind === 'once'
      ? { kind: 'once', local_date: rule.local_date as string, local_time: rule.local_time as string, time_zone: rule.time_zone }
      : rule.kind === 'daily'
        ? { kind: 'daily', local_time: rule.local_time as string, time_zone: rule.time_zone }
        : rule.kind === 'interval'
          ? { kind: 'interval', interval_minutes: rule.interval_minutes as number, time_zone: rule.time_zone }
          : rule.kind === 'hourly'
            ? { kind: 'hourly', interval_hours: rule.interval_hours as number, minute: rule.minute as number, time_zone: rule.time_zone }
            : { kind: 'weekly', weekdays: weekdays as Extract<ScheduledTaskMarkerRule, { kind: 'weekly' }>['weekdays'],
                local_time: rule.local_time as string, time_zone: rule.time_zone },
    nextRunAt: typeof task.next_run_at === 'string' ? task.next_run_at : null,
    status: task.status as ScheduledTaskMarkerSnapshot['status'],
    revision: task.revision as number,
  };
}

export function scheduledTaskMarkerSummary(task: ScheduledTaskMarkerSnapshot, dailyLabel: string,
  intervalLabel: (count: number) => string, hourlyLabel: (count: number, minute: number) => string,
  weeklyLabel: (days: string[], time: string) => string): string {
  return task.rule.kind === 'once'
    ? `${task.rule.local_date} · ${task.rule.local_time}`
    : task.rule.kind === 'daily' ? `${dailyLabel} · ${task.rule.local_time}`
      : task.rule.kind === 'interval' ? intervalLabel(task.rule.interval_minutes)
        : task.rule.kind === 'hourly' ? hourlyLabel(task.rule.interval_hours, task.rule.minute)
          : weeklyLabel(task.rule.weekdays, task.rule.local_time);
}

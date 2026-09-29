// [Input] Raw Tool names and output envelopes from live or persisted Chat messages.
// [Output] Regression coverage for strict successful scheduled-task marker decoding.
// [Pos] Provider-free scheduled-task Chat marker contract test.
// [Sync] 2026-09-29: cover the production top-level Tool receipt in structured/string form and reject the former synthetic nested fixture.

import { expect, test } from '@playwright/test';
import { decodeScheduledTaskMarker } from '../scheduledTaskMarkerModel';

const success = {
  ok: true,
  status: 'ok',
  scheduled_task: {
    id: 'st_1', title: '晨间复盘', status: 'active', revision: 2,
    next_run_at: '2026-09-30T01:00:00Z',
    rule: { kind: 'daily', local_time: '09:00', time_zone: 'Asia/Shanghai' },
  },
};

test('decodes only the exact successful create_scheduled_task envelope', () => {
  expect(decodeScheduledTaskMarker('create_scheduled_task', success)).toEqual({
    id: 'st_1', title: '晨间复盘', status: 'active', revision: 2,
    nextRunAt: '2026-09-30T01:00:00Z',
    rule: { kind: 'daily', local_time: '09:00', time_zone: 'Asia/Shanghai' },
  });
  expect(decodeScheduledTaskMarker('create_scheduled_task', JSON.stringify(success))?.id).toBe('st_1');
  expect(decodeScheduledTaskMarker('mcp__user__create_scheduled_task', success)?.id).toBe('st_1');
});

test('fails closed for prose, another tool, failed envelopes, and malformed rules', () => {
  expect(decodeScheduledTaskMarker('Read', success)).toBeNull();
  expect(decodeScheduledTaskMarker('mcp__attacker__create_scheduled_task', success)).toBeNull();
  expect(decodeScheduledTaskMarker('create_scheduled_task', 'created st_1')).toBeNull();
  expect(decodeScheduledTaskMarker('create_scheduled_task', { ...success, ok: false })).toBeNull();
  expect(decodeScheduledTaskMarker('create_scheduled_task', {
    ok: true, result: { status: 'ok', scheduled_task: success.scheduled_task },
  })).toBeNull();
  expect(decodeScheduledTaskMarker('create_scheduled_task', {
    ...success, scheduled_task: { ...success.scheduled_task, rule: { kind: 'monthly' } },
  })).toBeNull();
});

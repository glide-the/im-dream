// [Input] Story Workspace workflow polling hook and API client source.
// [Output] Guard the REST-only run snapshot transport while run-scoped SSE is unavailable.
// [Pos] Story Workspace workflow run transport contract test.

// @ts-expect-error Playwright has Node built-ins; the browser app tsconfig intentionally omits Node types.
import { readFileSync } from 'node:fs';

import { expect, test } from '@playwright/test';

const source = readFileSync(new URL('../useWorkflowEvents.ts', import.meta.url), 'utf8');
const apiSource = readFileSync(new URL('../../api/storyWorkspaceApi.ts', import.meta.url), 'utf8');

test('workflow run transport polls the authoritative snapshot without probing an unavailable SSE route', () => {
  expect(source).not.toContain('new EventSource');
  expect(source).not.toContain('workflowRunEventsUrl');
  expect(apiSource).not.toContain('/workflow-runs/${encodeURIComponent(workflowRunId)}/events');

  const initialPoll = source.indexOf('void pollSnapshot();');
  const scheduledPoll = source.indexOf('window.setInterval');
  expect(initialPoll).toBeGreaterThan(-1);
  expect(scheduledPoll).toBeGreaterThan(initialPoll);
  expect(source).toContain("setConnectionState('polling')");
});

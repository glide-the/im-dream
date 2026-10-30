// [Sync] 2026-10-29: reuse original public Reflections fixture and current bulk catalog DTO; assertions remain.
// [Sync] 2026-10-23: verify persisted diary scope/read counts, legacy and Notion-only reports across locales and widths.
// [Sync] 2026-10-23: verify on-demand copy, inline rerun controls and return position after keyboard focus.
// [Sync] 2026-10-15: freeze today rerun fixture at its actual analysis creation day.
// [Sync] 2026-10-14: preserve original timeline geometry while inserting task recap records and reusing earlier-days loading.
// [Input] Authenticated Story Workspace Reflections route and public Reflections task/content DTOs.
// [Output] Provider-free browser journeys for source selection, task SSE/recovery, report persistence,
//          idempotent creation retry, partial failure, Notion source states, and responsive keyboard UI.
// [Pos] Technical isolated browser validation; no normal account, model, database, migration, or service write.
// [Sync] 2026-10-13: add analysis-content source and task lifecycle coverage through the production UI/API seams.
// [Sync] 2026-10-13: prepared tasks remain idle on load and start only from explicit continuation.
// [Sync] 2026-10-13: definite Notion body-read failures clear preparing state without creating or starting a task.
// [Sync] 2026-10-14: cover Chat-origin section deep links, report focus, query consumption and browser return.
// [Sync] 2026-10-14: classify Chat/Analysis route teardown aborts as expected request cleanup.
//
// Business scope: the Project, Episode, canonical Story artifacts, Run-private .dream publication, and after-turn
// Hook are out of scope. The Reflections task is the changed business fact; its public task/report DTOs and visible
// Analysis page are the consumers. The fixture owns only public API responses and protocol events.

import { expect, test, type Page } from '@playwright/test';
import { installFixtures, isReflectionHistoryCancellation, isReflectionHistoryNavigationCancellation, WEB_BASE } from './fixtures/calendarHarness';

test.use({ channel: 'chrome' });
test.setTimeout(60_000);
// Fixture report dates stay inside the original Timeline window as calendar time advances.
test.beforeEach(async({page})=>{await page.clock.setFixedTime(new Date('2026-10-14T12:00:00Z'));});

import {TASK_ID,CONNECTOR_ID,DECK_ID,AGENT_ID,PAGE_ID,ECHO_RESULT_ID,TRAIT_RESULT_ID,PATTERN_RESULT_ID,SNAPSHOT_VERSION,BODY_HASH,resultFor,contentSummary,makeTask,makeReport,candidateResponse,event,installReflectionFixtures} from './fixtures/reflectionsHarness';
import type {Section,TaskStatus,CandidateStatus,FixtureResult,SectionState,FixtureTask,FixtureReport,FixtureState} from './fixtures/reflectionsHarness';

async function openAnalysis(page: Page, viewport = { width: 1440, height: 900 }) {
  await page.setViewportSize(viewport);
  await page.goto(`${WEB_BASE}/story-workspace/analysis`);
  await expect(page).toHaveURL(`${WEB_BASE}/story-workspace/analysis`);
  await expect(page.getByRole('heading', { name: 'Reflections', exact: true })).toBeVisible();
}

for (const scenario of [
  { name: 'selected', width: 1440, zh: false, notion: true, diaryIds: ['first', 'second'], expectedDiary: 2 },
  { name: 'selected', width: 375, zh: true, notion: true, diaryIds: ['first', 'second'], expectedDiary: 2 },
  { name: 'Notion-only', width: 375, zh: false, notion: true, diaryIds: [], expectedDiary: 0 },
  { name: 'legacy', width: 1440, zh: false, notion: false, diaryIds: null, expectedDiary: 9 },
]) test(`saved report sources show ${scenario.name} diary scope at ${scenario.width}px`, async ({ page }, testInfo) => {
  const fixture = await installReflectionFixtures(page, { seedReport: true, includeNotion: scenario.notion });
  const saved = fixture.reports[0];
  saved.report_data.stats.entries = 9;
  saved.report_data.analysis_content = scenario.name === 'legacy' ? null : {
    ...contentSummary(scenario.notion, true), diary_session_ids: scenario.diaryIds,
  };
  if (scenario.zh) await page.addInitScript(() => localStorage.setItem('ink-language', 'zh'));
  await page.setViewportSize({ width: scenario.width, height: 812 });
  const openSaved = async () => {
    await page.goto(`${WEB_BASE}/story-workspace/analysis`);
    await page.locator('[data-analysis-report-id="9001"]').click();
  };
  await openSaved();
  const sources = page.getByRole('region', { name: scenario.zh ? '本次分析来源' : 'Analysis sources', exact: true });
  const diaryLabel = scenario.zh ? `日记范围 · ${scenario.expectedDiary} 篇` : `Diary scope · ${scenario.expectedDiary} entries`;
  await expect(sources.getByText(diaryLabel, { exact: true })).toBeVisible();
  if (scenario.notion) {
    await sources.locator('summary').click();
    await expect(sources.locator('summary')).toHaveText(scenario.zh ? 'Notion · 已读取 1 个页面' : 'Notion · Pages read: 1');
    await expect(sources.getByRole('link', { name: 'Weekly notes' })).toHaveAttribute('href', 'https://www.notion.so/reflection-page');
  } else await expect(sources.locator('details')).toHaveCount(0);
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth)).toBe(true);
  await page.screenshot({ path: testInfo.outputPath(`report-sources-${scenario.name}-${scenario.width}.png`) });
  await page.reload();
  await page.locator('[data-analysis-report-id="9001"]').click();
  await expect(sources.getByText(diaryLabel, { exact: true })).toBeVisible();
  expect(fixture.createRequests).toEqual([]);
  expect(fixture.startRequests).toEqual([]);
  expect(fixture.errors).toEqual([]);
  expect(fixture.base.getUnexpected()).toEqual([]);
});

test('Chat-origin section navigation opens the matching saved report once and restores clean history', async ({ page }) => {
  const fixture = await installReflectionFixtures(page, { seedReport: true });
  for (let index = 0; index < 12; index += 1) fixture.reports.unshift({
    ...fixture.reports[0],
    id: 9002 + index,
    created_at: '2026-10-14T03:00:05Z',
    report_data: {
      ...fixture.reports[0].report_data,
      task_id: `40000000-0000-4000-8000-${String(index).padStart(12, '0')}`,
      echoes: [], patterns: [],
    },
  });
  await page.setViewportSize({ width: 375, height: 812 });
  await page.goto(`${WEB_BASE}/story-workspace/chat`);
  await expect(page.getByRole('button', { name: 'Chat', exact: true })).toBeVisible();
  // AnalysisView loads these three resources on route entry. The analysis-content
  // and deck endpoints are intentionally lazy and only run after the user opens
  // the Analysis content control, so they are not part of this deep-link read set.
  const waitForAnalysisReads = () => Promise.all([
    page.waitForResponse(response => new URL(response.url()).pathname === '/api/sessions/aggregate'),
    page.waitForResponse(response => new URL(response.url()).pathname === '/api/reports/history'),
    page.waitForResponse(response => new URL(response.url()).pathname === '/api/reflections/latest'),
  ]);
  const firstReads = waitForAnalysisReads();
  await page.evaluate((href) => {
    window.history.pushState({ inkDreamView: 'story-workspace' }, '', href);
    window.dispatchEvent(new PopStateEvent('popstate'));
  }, '/story-workspace/analysis?section=patterns');
  await firstReads;

  const patterns = page.locator('[data-reflection-section="patterns"]');
  await expect(patterns).toBeVisible();
  await expect(patterns).toHaveAttribute('aria-pressed', 'true');
  await expect(patterns).toBeFocused();
  await expect(page.getByText('Review loop', { exact: true })).toBeVisible();
  expect(fixture.historyRequests.some(query => new URLSearchParams(query).has('before_id'))).toBe(true);
  await expect(page).toHaveURL(`${WEB_BASE}/story-workspace/analysis`);

  await page.goBack();
  await expect(page).toHaveURL(`${WEB_BASE}/story-workspace/chat`);
  const restoredReads = waitForAnalysisReads();
  await page.goForward();
  await restoredReads;
  await expect(page).toHaveURL(`${WEB_BASE}/story-workspace/analysis`);
  await expect(page.getByRole('heading', { name: 'Reflections', exact: true })).toBeVisible();
  await expect(page.locator('[data-reflection-section="patterns"]')).toHaveCount(0);
  expect(fixture.unexpectedReflectionRequests).toEqual([]);
  expect(fixture.errors).toEqual([]);
  expect(fixture.base.getUnexpected()).toEqual([]);
});

test('default and Notion+Agent analysis create through SSE, save retry, reload, and open the persisted report', async ({ page }) => {
  const fixture = await installReflectionFixtures(page, { reportSaveFailureOnce: true });
  await openAnalysis(page);

  const contentButton = page.getByRole('button', { name: 'Analysis content', exact: false });
  await contentButton.click();
  const contentRegion = page.getByRole('region', { name: 'Analysis content options' });
  await expect(contentRegion).toBeVisible();
  await expect(contentRegion.getByText('Read from 1 linked pages as needed.')).toBeVisible();
  const includeNotion = contentRegion.getByRole('checkbox', { name: 'Include Notion in analysis' });
  await expect(includeNotion).toBeEnabled();
  await expect(includeNotion).not.toBeChecked();
  await expect(contentRegion.getByRole('button', { name: 'Analysis Agent' })).toContainText('Default analysis');
  await includeNotion.check();
  await contentRegion.getByRole('button', { name: 'Analysis Agent' }).press('Enter');
  await expect(page.getByRole('listbox')).toBeVisible();
  await page.getByRole('listbox').getByRole('option', { name: /Reflective analyst/ }).click();
  await expect(contentRegion.getByRole('button', { name: 'Analysis Agent' })).toContainText('Reflective analyst');

  await page.getByRole('button', { name: 'Generate New Analysis', exact: true }).click();
  await expect.poll(() => fixture.createRequests.length).toBe(1);
  expect(fixture.createRequests[0].analysis_content).toMatchObject({ include_notion: true, connector_id: CONNECTOR_ID, snapshot_version: SNAPSHOT_VERSION, deck_id: DECK_ID, agent_id: AGENT_ID });
  await expect(page.getByRole('alert').filter({ has: page.getByRole('button', { name: 'Retry save', exact: true }) })).toBeVisible();
  expect(fixture.reportRequests).toEqual([TASK_ID]);

  fixture.clearHttpError(503, `/api/reflections/tasks/${TASK_ID}/report`);
  await page.getByRole('button', { name: 'Retry save', exact: true }).click();
  await expect.poll(() => fixture.reportRequests.length).toBe(2);
  expect(fixture.reportRequests).toEqual([TASK_ID, TASK_ID]);
  await expect(page.getByRole('button', { name: 'Past Reflections', exact: false })).toBeVisible();
  await page.getByRole('button', { name: /Past Reflections/ }).click();
  await page.getByRole('button', { name: 'Analysis content', exact: false }).click();
  const nextContent = page.getByRole('region', { name: 'Analysis content options' });
  await nextContent.getByRole('checkbox', { name: 'Include Notion in analysis' }).uncheck();
  expect(fixture.createRequests[0].analysis_content).toMatchObject({ include_notion: true, snapshot_version: SNAPSHOT_VERSION, agent_id: AGENT_ID });

  await page.reload();
  await expect(page.getByRole('button', { name: 'Past Reflections', exact: false })).toBeVisible();
  await page.getByText('Latest', { exact: true }).locator('..').click();
  await expect(page.getByText('Repeated concern', { exact: true })).toBeVisible();
  expect(fixture.unexpectedReflectionRequests).toEqual([]);
  expect(fixture.errors).toEqual([]);
  expect(fixture.base.getUnexpected()).toEqual([]);
});

test('partial failure remains visible and double click locks one creation immediately', async ({ page }) => {
  const fixture = await installReflectionFixtures(page, { partial: true, holdSse: true });
  await openAnalysis(page, { width: 1440, height: 900 });
  const generate = page.getByRole('button', { name: 'Generate New Analysis', exact: true });
  await generate.dblclick();
  await expect.poll(() => fixture.createRequests.length).toBe(1);
  await expect(page.getByRole('button', { name: 'Reflecting...', exact: true })).toBeDisabled();
  await expect.poll(() => fixture.eventRequests.length).toBe(1);
  fixture.releaseSse?.();
  await expect.poll(() => fixture.taskStatus).toBe('PARTIAL_FAILED');
  await expect(page.getByRole('status').filter({ hasText: /Some sections could not finish|部分栏目未完成/ })).toBeVisible();
  await expect(page.getByText('Repeated concern', { exact: true })).toBeVisible();
  expect(fixture.startRequests).toEqual([TASK_ID]);
  expect(fixture.errors).toEqual([]);
});

test('unknown creation outcome retries with the exact same request key', async ({ page }) => {
  const fixture = await installReflectionFixtures(page, { creationUnknownOnce: true });
  await openAnalysis(page);
  const generate = page.getByRole('button', { name: 'Generate New Analysis', exact: true });
  await generate.click();
  await expect(page.getByText(/The analysis could not start\. Check the selected content and retry\./).first()).toBeVisible();
  await generate.click();
  await expect.poll(() => fixture.createRequests.length).toBe(2);
  expect(fixture.createRequests[0].request_key).toBe(fixture.createRequests[1].request_key);
  await expect(page.getByText('Repeated concern', { exact: true })).toBeVisible();
  expect(fixture.errors).toEqual([]);
});

test('created empty-input task streams FAILED with no results and keeps source recovery actionable', async ({ page }) => {
  const fixture = await installReflectionFixtures(page, { noAnalyzableInputAfterSse: true });
  await openAnalysis(page);

  await page.getByRole('button', { name: 'Analysis content', exact: false }).click();
  const initialRegion = page.getByRole('region', { name: 'Analysis content options' });
  const includeNotion = initialRegion.getByRole('checkbox', { name: 'Include Notion in analysis' });
  await expect(includeNotion).toBeEnabled();
  await includeNotion.check();
  await page.getByRole('button', { name: 'Generate New Analysis', exact: true }).click();
  await expect.poll(() => fixture.createRequests.length).toBe(1);
  expect(fixture.createRequests[0].analysis_content).toMatchObject({ include_notion: true, connector_id: CONNECTOR_ID, snapshot_version: SNAPSHOT_VERSION });
  await expect.poll(() => fixture.eventRequests.length).toBe(1);
  await expect(page.getByText('Select diary entries or Notion pages with text to analyze.', { exact: true }).first()).toBeVisible();

  const failedTask = fixture.taskResponses.find(task => task.status === 'FAILED');
  expect(failedTask).toMatchObject({
    id: TASK_ID,
    task_id: TASK_ID,
    status: 'FAILED',
    workspace_path: null,
    revision: 2,
    error_summary: 'REFLECTION_NO_ANALYZABLE_INPUT (422)',
    results: [],
  });
  expect(failedTask?.input_snapshot).toMatchObject({
    session_ids: [],
    analysis_content: {
      diary_session_ids: [],
      notion: { pages: [], empty_page_count: 1 },
      agent: null,
    },
  });
  expect(failedTask?.section_states).toHaveLength(3);
  expect(failedTask?.section_states.every(section => section.status === 'PENDING' && section.result_count === 0
    && section.revision === 1 && section.completed_at === null && section.error_summary === null)).toBe(true);
  expect(fixture.results).toEqual([]);
  expect(fixture.reportRequests).toEqual([]);
  expect(fixture.reportApiRequests.filter(request => request === 'POST /api/reports')).toEqual([]);
  await expect(page.getByText('Repeated concern', { exact: true })).toHaveCount(0);

  const contentButton = page.getByRole('button', { name: 'Analysis content', exact: false });
  await contentButton.click();
  const region = page.getByRole('region', { name: 'Analysis content options' });
  const retryNotion = region.getByRole('checkbox', { name: 'Include Notion in analysis' });
  await expect(retryNotion).toBeEnabled();
  await retryNotion.uncheck();
  await retryNotion.check();
  await expect(retryNotion).toBeChecked();
  await expect(page.getByRole('button', { name: 'Generate New Analysis', exact: true })).toBeEnabled();
  expect(fixture.errors).toEqual([]);
});

test('reconnects an existing active task after reload without creating a new task', async ({ page }) => {
  const fixture = await installReflectionFixtures(page, { activeTaskOnLoad: true });
  await page.setViewportSize({ width: 1440, height: 900 });
  await page.goto(`${WEB_BASE}/story-workspace/analysis`);
  await expect(page).toHaveURL(`${WEB_BASE}/story-workspace/analysis`);
  await expect.poll(() => fixture.eventRequests.length).toBeGreaterThan(0);
  // A recovered task with terminal results opens its existing report after the
  // resume stream settles; assert that visible consumer rather than the
  // dashboard heading that only exists before recovery completes.
  await expect(page.getByRole('button', { name: '← Past Reflections' })).toBeVisible();
  await expect(page.getByText('Repeated concern', { exact: true })).toBeVisible();
  expect(fixture.createRequests).toEqual([]);
  expect(fixture.startRequests).toEqual([]);
  expect(fixture.errors).toEqual([]);
});

test('prepared task stays idle on load and explicit continuation starts its original id', async ({ page }) => {
  const fixture = await installReflectionFixtures(page, { activeTaskOnLoad: true, taskStatus: 'CREATED', seedActiveTaskStorage: false, latestHistoricalResults: true });
  await openAnalysis(page);
  const generate = page.getByRole('button', { name: 'Generate New Analysis', exact: true });
  await expect(generate).toBeEnabled();
  const continueButton = page.getByRole('button', { name: 'Continue unstarted analysis', exact: true });
  await expect(continueButton).toBeVisible();
  expect(fixture.eventRequests).toEqual([]);
  expect(fixture.startRequests).toEqual([]);
  expect(fixture.createRequests).toEqual([]);
  await expect(page.getByText('The analysis result is available, but its report has not been saved.', { exact: true })).toHaveCount(0);
  await continueButton.click();
  await expect.poll(() => fixture.startRequests).toEqual([TASK_ID]);
  await expect.poll(() => fixture.reportRequests.length).toBeGreaterThan(0);
  expect(fixture.createRequests).toEqual([]);
  expect(fixture.errors).toEqual([]);
});

test('new analysis beside a prepared task uses the current Notion selection', async ({ page }) => {
  const fixture = await installReflectionFixtures(page, { activeTaskOnLoad: true, taskStatus: 'CREATED', holdTaskLookup: true });
  await openAnalysis(page);
  await expect.poll(() => Boolean(fixture.releaseTaskLookup)).toBe(true);
  await expect(page.getByText('42', { exact: true })).toBeVisible();
  fixture.releaseTaskLookup?.();
  await expect(page.getByRole('button', { name: 'Continue unstarted analysis', exact: true })).toBeVisible();
  await page.getByRole('button', { name: 'Analysis content', exact: false }).click();
  await page.getByRole('checkbox', { name: 'Include Notion in analysis' }).check();
  await page.getByRole('button', { name: 'Generate New Analysis', exact: true }).click();
  await expect.poll(() => fixture.createRequests.length).toBe(1);
  expect(fixture.createRequests[0].analysis_content).toMatchObject({ include_notion: true, snapshot_version: SNAPSHOT_VERSION });
  await expect.poll(() => fixture.reportRequests.length).toBeGreaterThan(0);
  expect(fixture.errors).toEqual([]);
});

test('Notion no-snapshot, empty, auth-required, and empty-body responses stay actionable', async ({ page }) => {
  const fixture = await installReflectionFixtures(page, { candidateStatus: 'no_snapshot' });
  await openAnalysis(page);
  const contentButton = page.getByRole('button', { name: 'Analysis content', exact: false });
  await contentButton.click();
  const region = page.getByRole('region', { name: 'Analysis content options' });
  await expect(region.getByText('Sync linked resources in Settings first.', { exact: true })).toBeVisible();

  fixture.candidateStatus = 'empty';
  await region.getByRole('button', { name: 'Reload', exact: true }).click();
  await expect(region.getByText('No Notion pages are linked.', { exact: true })).toBeVisible();
  fixture.candidateStatus = 'auth_required';
  await region.getByRole('button', { name: 'Reload', exact: true }).click();
  await expect(region.getByText('Reconnect Notion in Settings.', { exact: true })).toBeVisible();
  fixture.candidateStatus = 'scope_changed';
  await region.getByRole('button', { name: 'Reload', exact: true }).click();
  await expect(region.getByText('Linked resources changed. Sync them again in Settings.', { exact: true })).toBeVisible();

  fixture.candidateStatus = 'ready';
  await region.getByRole('button', { name: 'Reload', exact: true }).click();
  const includeNotion = region.getByRole('checkbox', { name: 'Include Notion in analysis' });
  await expect(includeNotion).toBeEnabled();
  await includeNotion.check();
  fixture.createError = 'REFLECTION_NO_ANALYZABLE_INPUT';
  fixture.allowHttpError(422, '/api/reflections/tasks');
  await page.getByRole('button', { name: 'Generate New Analysis', exact: true }).click();
  await expect(page.getByText('Select diary entries or Notion pages with text to analyze.', { exact: true }).first()).toBeVisible();
  fixture.clearHttpError(422, '/api/reflections/tasks');
  expect(fixture.errors).toEqual([]);
});

test('Notion read and Agent invalidation errors recover through the explicit reload path', async ({ page }) => {
  const fixture = await installReflectionFixtures(page, { notionReadFailureOnce: true, agentReadFailureOnce: true, createNotionReadFailureOnce: true });
  await openAnalysis(page);
  await page.getByRole('button', { name: 'Analysis content', exact: false }).click();
  const region = page.getByRole('region', { name: 'Analysis content options' });
  await expect(region.getByText('Notion resources could not be loaded. Retry.', { exact: true })).toBeVisible();
  fixture.agentReadFailed = true;
  await region.getByRole('button', { name: 'Reload', exact: true }).click();
  await expect(region.getByText('Analysis Agents could not be loaded. Default analysis remains available.', { exact: true })).toBeVisible();
  await region.getByRole('button', { name: 'Reload', exact: true }).click();
  await expect(region.getByRole('button', { name: 'Analysis Agent' })).toContainText('Default analysis');
  await region.getByRole('checkbox', { name: 'Include Notion in analysis' }).check();
  await page.getByRole('button', { name: 'Generate New Analysis', exact: true }).click();
  await expect.poll(() => fixture.createRequests.length).toBe(1);
  await expect(page.getByText('Notion content is temporarily unavailable. Retry the analysis later.', { exact: true }).first()).toBeVisible();
  await expect(page.getByText('task · preparing', { exact: true })).toHaveCount(0);
  expect(fixture.taskResponses).toEqual([]);
  expect(fixture.startRequests).toEqual([]);
  expect(fixture.eventRequests).toEqual([]);
  expect(fixture.reportRequests).toEqual([]);
  expect(fixture.errors).toEqual([]);
});

test('today re-analysis opens the diary picker with the current entries', async ({ page }) => {
  await page.clock.install({ time: new Date('2026-10-13T03:00:05Z') });
  const fixture = await installReflectionFixtures(page, { seedReport: true });
  await openAnalysis(page);
  await page.getByRole('button', { name: 'Generate New Analysis', exact: true }).click();
  const dialog = page.getByRole('dialog', { name: 'Today already has a Reflections analysis.' });
  await expect(dialog).toBeVisible();
  await expect(dialog.getByText('A diary entry', { exact: true })).toBeVisible();
  await expect(dialog.getByRole('checkbox', { name: 'A diary entry' })).toBeChecked();
  const content = dialog.getByRole('region', { name: 'Analysis content options' });
  await expect(content).toBeVisible();
  await expect(page.locator('#reflection-analysis-content')).toHaveCount(1);
  await expect(content.getByRole('button', { name: 'Analysis Agent' })).toBeEnabled();
  await expect(dialog.getByText('Re-running will create a new analysis. Choose the diary entries and analysis content for this run.', { exact: true })).toBeVisible();
  expect(fixture.createRequests).toEqual([]);
});

for (const width of [1440, 375]) test(`same-day rerun retains shared content choices and submits Notion-only at ${width}px`, async ({ page }, testInfo) => {
  await page.clock.install({ time: new Date('2026-10-13T03:00:05Z') });
  const fixture = await installReflectionFixtures(page, { seedReport: true });
  await openAnalysis(page, { width, height: 700 });
  const more = page.getByRole('button', { name: 'More', exact: true });
  if (width === 375 && await more.getAttribute('aria-expanded') === 'true') await more.click();
  await page.getByRole('button', { name: 'Analysis content', exact: false }).click();
  const panel = page.getByRole('region', { name: 'Analysis content options' });
  await panel.getByRole('checkbox', { name: 'Include Notion in analysis' }).check();
  await panel.getByRole('button', { name: 'Analysis Agent' }).click();
  await page.getByRole('listbox').getByRole('option', { name: /Reflective analyst/ }).click();
  await page.getByRole('button', { name: 'Analysis content', exact: false }).click();
  await expect(panel).toHaveCount(0);
  await page.getByRole('button', { name: 'Generate New Analysis', exact: true }).click();
  const dialog = page.getByRole('dialog', { name: 'Today already has a Reflections analysis.' });
  const content = dialog.getByRole('region', { name: 'Analysis content options' });
  await expect(content.getByRole('checkbox', { name: 'Include Notion in analysis' })).toBeChecked();
  await expect(content.getByRole('button', { name: 'Analysis Agent' })).toContainText('Reflective analyst');
  await expect(page.locator('#reflection-analysis-content')).toHaveCount(1);
  await dialog.getByRole('button', { name: 'Cancel', exact: true }).click();
  await expect(dialog).toHaveCount(0);
  expect(fixture.createRequests).toEqual([]);
  await page.getByRole('button', { name: 'Generate New Analysis', exact: true }).click();
  await expect(content.getByRole('checkbox', { name: 'Include Notion in analysis' })).toBeChecked();
  await dialog.getByRole('button', { name: /^Clear all/ }).click();
  const confirm = dialog.getByRole('button', { name: 'Re-analyze selected', exact: true });
  await content.getByRole('checkbox', { name: 'Include Notion in analysis' }).uncheck();
  await expect(confirm).toBeDisabled();
  await content.getByRole('checkbox', { name: 'Include Notion in analysis' }).check();
  await expect(confirm).toBeEnabled();
  await expect(confirm).toBeInViewport();
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= document.documentElement.clientWidth)).toBe(true);
  await page.screenshot({ path: testInfo.outputPath(`rerun-content-${width}.png`) });
  await confirm.click();
  await expect.poll(() => fixture.createRequests.length).toBe(1);
  expect(fixture.createRequests[0].session_ids).toEqual([]);
  expect(fixture.createRequests[0].analysis_content).toMatchObject({ include_notion: true, connector_id: CONNECTOR_ID,
    snapshot_version: SNAPSHOT_VERSION, deck_id: DECK_ID, agent_id: AGENT_ID });
  await expect.poll(() => fixture.startRequests.length).toBe(1);
  await expect.poll(() => fixture.reportRequests.length).toBe(1);
  expect(fixture.errors).toEqual([]);
  expect(fixture.unexpectedReflectionRequests).toEqual([]);
});

test('desktop and narrow content controls support keyboard selection and nested Escape ownership', async ({ page }) => {
  const fixture = await installReflectionFixtures(page);
  await openAnalysis(page, { width: 390, height: 700 });
  const contentButton = page.getByRole('button', { name: 'Analysis content', exact: false });
  await contentButton.focus();
  await contentButton.press('Enter');
  const region = page.getByRole('region', { name: 'Analysis content options' });
  await expect(region).toBeVisible();
  const agentTrigger = region.getByRole('button', { name: 'Analysis Agent' });
  await expect(agentTrigger).toBeEnabled();
  await agentTrigger.focus();
  await agentTrigger.press('Enter');
  const listbox = region.getByRole('listbox');
  await expect(listbox).toBeVisible();
  await listbox.getByRole('textbox').press('ArrowDown');
  await listbox.getByRole('textbox').press('Enter');
  await expect(agentTrigger).toContainText('Reflective analyst');
  await agentTrigger.press('Enter');
  await expect(listbox).toBeVisible();
  await listbox.getByRole('textbox').press('Escape');
  await expect(listbox).toHaveCount(0);
  await expect(region).toBeVisible();
  await contentButton.press('Escape');
  await expect(region).toHaveCount(0);
  await expect(contentButton).toBeFocused();
  const overflow = await page.evaluate(() => ({ width: document.documentElement.scrollWidth, client: document.documentElement.clientWidth }));
  expect(overflow.width).toBeLessThanOrEqual(overflow.client + 1);
  expect(fixture.errors).toEqual([]);
});


function historyFixtures(count: number): FixtureReport[] {
  return Array.from({ length: count }, (_, index) => {
    // Intentional: report saving/order differs from analysis creation and diary range.
    const created = new Date(Date.UTC(2026, 9, 13, 16, 1 - index)).toISOString();
    return { id: String(9007199254741000n + BigInt(index)), created_at: '2026-12-01T00:00:00Z',
      analysis_created_at: created, task_id: `80000000-0000-4000-8000-${String(index).padStart(12, '0')}`,
      report_data: { echoes: [{ ...resultFor('echoes'), related_session_ids: [], title: `History insight ${index}`, description: `Distinct report content ${index}` }],
        traits: [], patterns: [], stats: { days: 120, entries: 9, words: 42 }, task_id: `80000000-0000-4000-8000-${String(index).padStart(12, '0')}`, analysis_content: null } };
  });
}

async function installTimelineReads(page: Page) {
  await page.route('**/api/pictures/range*', route => route.fulfill({ json: { pictures: [] } }));
}

for (const count of [0, 1, 3, 31]) test(`history preview keeps latest three independent analyses from ${count} records`, async ({ page }) => {
  const fixture = await installReflectionFixtures(page);
  fixture.reports = historyFixtures(count);
  await installTimelineReads(page);
  await openAnalysis(page);
  const history = page.getByRole('region', { name: 'Past Reflections', exact: true });
  if (count === 0) await expect(history).toHaveCount(0);
  else {
    await expect(history.locator('[data-analysis-report-id]')).toHaveCount(Math.min(count, 3));
    expect(await history.locator('[data-analysis-report-id]').evaluateAll(nodes => nodes.map(node => node.getAttribute('data-analysis-report-id'))))
      .toEqual(fixture.reports.slice(0, 3).map(report => String(report.id)));
    const card = history.locator('[data-analysis-report-id]').first();
    await card.focus(); await page.keyboard.press('Enter');
    await expect(page.getByText('History insight 0', { exact: true })).toBeVisible();
    await expect(page.getByRole('button', { name: 'Past Reflections', exact: false })).toBeFocused();
    await page.getByRole('button', { name: 'Past Reflections', exact: false }).click();
  }
  if (count === 0) await page.getByRole('button', { name: 'Timeline', exact: true }).click();
  else await history.getByRole('button', { name: 'Past Reflections', exact: false }).click();
  await expect(page).toHaveURL(`${WEB_BASE}/story-workspace/timeline`);
  if (count === 0) {
    await expect(page.locator('[data-analysis-report-id]')).toHaveCount(0);
    await expect(page.getByText('No analysis reports yet.')).toHaveCount(0);
  }
  else await expect(page.locator(`[data-analysis-report-id="${fixture.reports[0].id}"]`)).toBeVisible();
  expect(fixture.errors).toEqual([]);
  expect(fixture.base.getUnexpected()).toEqual([]);
});

for (const width of [1440, 375]) test(`analysis history navigates and reads older reports with stable return at ${width}px`, async ({ page }, testInfo) => {
  const fixture = await installReflectionFixtures(page);
  fixture.reports = historyFixtures(31);
  // Equal creation instants require decimal-id descending order; independent same-day reports stay separate.
  fixture.reports[1].analysis_created_at = fixture.reports[0].analysis_created_at;
  fixture.reports[30].analysis_created_at = '2025-09-30T16:00:00Z';
  await installTimelineReads(page);
  await page.route('**/api/preferences', route => route.fulfill({ json: { first_login_completed: true, timezone: 'Asia/Shanghai' } }));
  await openAnalysis(page, { width, height: 812 });
  const preview = page.getByRole('region', { name: 'Past Reflections', exact: true });
  await expect(preview.locator('[data-analysis-report-id]')).toHaveCount(3);
  expect(await preview.locator('[data-analysis-report-id]').first().getAttribute('data-analysis-report-id')).toBe(String(fixture.reports[1].id));
  const entry = preview.getByRole('button', { name: 'Past Reflections', exact: false });
  await entry.focus(); await page.keyboard.press('Enter');
  await expect(page).toHaveURL(`${WEB_BASE}/story-workspace/timeline`);
  const scroll = page.getByTestId('timeline-scroll');
  await expect(page.locator(`[data-analysis-report-id="${fixture.reports[1].id}"]`)).toBeVisible();
  await expect(page.locator(`[data-analysis-id="${fixture.reports[1].id}"]`)).toHaveAttribute('data-date', '2026-10-14');
  const rows = await scroll.locator('[data-date]').evaluateAll(nodes => nodes.map(node => {
    const element = node as HTMLElement;
    return { top: Number.parseFloat(element.style.top), height: element.getBoundingClientRect().height };
  }).sort((a, b) => a.top - b.top));
  expect(rows.length).toBeGreaterThan(1);
  for (const row of rows) {
    expect(row.height).toBe(100);
    expect(row.top % 70).toBe(width === 375 ? 20 : 32);
  }
  for (let index = 1; index < rows.length; index += 1) expect(rows[index].top - rows[index - 1].top).toBe(70);
  await expect(page.getByRole('button', { name: 'Load earlier analyses' })).toHaveCount(0);
  const target = page.locator(`[data-analysis-report-id="${fixture.reports[1].id}"]`);
  await target.focus();
  const before = await scroll.evaluate(node => node.scrollTop);
  await page.keyboard.press('Space');
  const reader = page.getByRole('region', { name: 'Analysis report', exact: true });
  await expect(reader.getByText('History insight 1', { exact: true })).toBeVisible();
  await expect(reader.getByRole('button', { name: 'Timeline', exact: false })).toBeFocused();
  await reader.getByRole('button', { name: 'Timeline', exact: false }).click();
  await expect(target).toBeFocused();
  expect(await scroll.evaluate(node => node.scrollTop)).toBe(before);
  fixture.historyMoreFailureOnce = true;
  await scroll.evaluate(node => { node.scrollTop = 0; });
  const retry = page.locator('[data-analysis-history-error="true"]');
  await expect(retry).toBeVisible();
  await expect(retry).toHaveAttribute('title', 'Analysis history could not be loaded.');
  const failedCursor = fixture.historyRequests.at(-1);
  const failedRequestIndex = fixture.historyRequests.length - 1;
  await retry.click();
  await expect(retry).toHaveCount(0);
  expect(fixture.historyRequests[failedRequestIndex + 1]).toBe(failedCursor);
  // Earlier recap pages use the original timeline load action and scrolling.
  for (let index = 0; index < 4; index += 1) {
    await scroll.evaluate(node => { node.scrollTop = 0; });
    await expect(page.getByRole('button', { name: 'Loading…', exact: true })).toHaveCount(0);
    if (await page.locator(`[data-analysis-report-id="${fixture.reports[30].id}"]`).count()) break;
    await page.getByRole('button', { name: 'Load earlier days', exact: true }).click();
    await expect(page.getByRole('button', { name: 'Loading…', exact: true })).toHaveCount(0);
  }
  await expect(page.getByRole('button', { name: 'Load earlier analyses' })).toHaveCount(0);
  await scroll.evaluate(node => { node.scrollTop = 0; });
  const oldest = page.locator(`[data-analysis-report-id="${fixture.reports[30].id}"]`);
  await expect(oldest).toBeVisible();
  await expect(page.locator(`[data-analysis-id="${fixture.reports[30].id}"]`)).toHaveAttribute('data-date', '2025-10-01');
  await oldest.click();
  await reader.getByRole('button', { name: 'History insight 30', exact: false }).click();
  await expect(reader.getByText('Distinct report content 30', { exact: true })).toBeVisible();
  await reader.getByRole('button', { name: 'Timeline', exact: false }).click();
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true);
  await page.screenshot({ path: testInfo.outputPath(`analysis-timeline-${width}.png`) });
  fixture.base.beginReflectionHistoryNavigation();
  await page.reload();
  await expect(page).toHaveURL(`${WEB_BASE}/story-workspace/timeline`);
  await expect(page.locator(`[data-analysis-report-id="${fixture.reports[1].id}"]`)).toBeVisible();
  await page.goBack();
  await expect(page).toHaveURL(`${WEB_BASE}/story-workspace/analysis`);
  await expect(page.getByRole('region', { name: 'Past Reflections', exact: true }).locator('[data-analysis-report-id]')).toHaveCount(3);
  fixture.base.endReflectionHistoryNavigation();
  expect(fixture.reportRequests).toEqual([]);
  expect(fixture.createRequests).toEqual([]);
  expect(fixture.errors).toEqual([]);
  expect(fixture.base.getUnexpected()).toEqual([]);
});

test('history first-read failure retries while the original task and entry remain available', async ({ page }) => {
  const fixture = await installReflectionFixtures(page, { activeTaskOnLoad: true, taskStatus: 'CREATED', seedActiveTaskStorage: false });
  fixture.historyReadFailureUntilRetry = true;
  fixture.reports = historyFixtures(1);
  await openAnalysis(page);
  await expect(page.getByRole('alert').filter({ hasText: 'Analysis history could not be loaded.' })).toContainText('Analysis history could not be loaded.');
  await expect(page.getByRole('button', { name: 'Continue unstarted analysis', exact: false })).toBeVisible();
  fixture.historyReadFailureUntilRetry = false;
  await page.getByRole('alert').filter({ hasText: 'Analysis history could not be loaded.' }).getByRole('button', { name: 'Retry', exact: true }).click();
  await expect(page.locator('[data-analysis-report-id]')).toHaveCount(1);
  expect(fixture.startRequests).toEqual([]);
  expect(fixture.errors).toEqual([]);
});


test('visible analysis creation reaches saved preview and the same timeline report', async ({ page }) => {
  const fixture = await installReflectionFixtures(page);
  await installTimelineReads(page);
  await openAnalysis(page);
  await expect(page.getByRole('region', { name: 'Past Reflections', exact: true })).toHaveCount(0);
  await page.getByRole('button', { name: 'Generate New Analysis', exact: true }).click();
  await expect(page.getByRole('region', { name: 'Analysis report' }).getByText('Repeated concern', { exact: true })).toBeVisible();
  expect(fixture.createRequests).toHaveLength(1);
  expect(fixture.startRequests).toEqual([TASK_ID]);
  expect(fixture.eventRequests).toEqual([TASK_ID]);
  expect(fixture.reportRequests).toContain(TASK_ID);
  await page.getByRole('button', { name: 'Past Reflections', exact: false }).click();
  await expect(page.getByRole('region', { name: 'Past Reflections', exact: true }).locator('[data-analysis-report-id="9001"]')).toBeVisible();
  await page.getByRole('region', { name: 'Past Reflections', exact: true }).getByRole('button', { name: 'Past Reflections', exact: false }).click();
  await expect(page).toHaveURL(`${WEB_BASE}/story-workspace/timeline`);
  const report = page.locator('[data-analysis-report-id="9001"]');
  await expect(report).toBeVisible();
  const writesBeforeReading = fixture.reportRequests.length;
  await report.click();
  await expect(page.getByRole('region', { name: 'Analysis report' }).getByText('Repeated concern', { exact: true })).toBeVisible();
  await page.getByRole('region', { name: 'Analysis report' }).getByRole('button', { name: 'Timeline', exact: false }).click();
  await expect(report).toBeFocused();
  expect(fixture.reportRequests.length).toBe(writesBeforeReading);
  expect(fixture.errors).toEqual([]);
  expect(fixture.base.getUnexpected()).toEqual([]);
});


test('timeline diary and historical picture still open beside an analysis report', async ({ page }) => {
  const fixture = await installReflectionFixtures(page);
  fixture.reports = historyFixtures(1);
  await page.clock.install({ time: new Date('2026-10-14T01:00:00Z') });
  const pictureDate = '2026-10-13';
  const png = 'iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+a9H0AAAAASUVORK5CYII=';
  await page.route(/\/api\/sessions(?:\/range)?(?:\?|$)/, async route => {
    if (route.request().method() !== 'GET') { await route.fallback(); return; }
    await route.fulfill({ json: { sessions: [{ id: 'note_existing_qa', date_key: pictureDate,
      first_line: 'Original diary remains visible', created_at: `${pictureDate}T07:00:00Z`, updated_at: `${pictureDate}T07:00:00Z` }] } });
  });
  await page.route('**/api/pictures/range*', route => route.fulfill({ json: { pictures: [{ date: pictureDate, base64: png, prompt: 'Historical picture' }] } }));
  await page.route(`**/api/pictures/${pictureDate}/full`, route => route.fulfill({ json: { image_base64: png } }));
  await page.route('**/api/sessions/batch', route => route.fulfill({ json: { sessions: [{ id: 'note_existing_qa',
    editor_state: { cells: [], commentors: [] }, created_at: `${pictureDate}T07:00:00Z`, updated_at: `${pictureDate}T07:00:00Z` }] } }));
  await page.setViewportSize({ width: 375, height: 812 });
  await page.goto(`${WEB_BASE}/story-workspace/timeline`);
  await expect(page.getByText('Original diary remains visible', { exact: true })).toBeVisible();
  await page.getByRole('img', { name: 'Historical picture', exact: true }).click();
  await expect(page.getByText('Starred Comments', { exact: true })).toBeVisible();
  await expect(page.getByRole('img', { name: 'Generated image' })).toBeVisible();
  await expect(page.getByText('No comments for this day', { exact: true })).toBeVisible();
  await page.getByRole('button', { name: '×', exact: true }).click();
  await expect(page.getByText('Starred Comments', { exact: true })).toHaveCount(0);
  const report = page.locator(`[data-analysis-report-id="${fixture.reports[0].id}"]`);
  await report.click();
  const reader = page.getByRole('region', { name: 'Analysis report' });
  await reader.getByRole('button', { name: 'History insight 0', exact: false }).click();
  await expect(reader.getByText('Distinct report content 0', { exact: true })).toBeVisible();
  await reader.getByRole('button', { name: 'Timeline', exact: false }).click();
  await expect(page.getByText('Original diary remains visible', { exact: true })).toBeVisible();
  expect(fixture.errors).toEqual([]); expect(fixture.base.getUnexpected()).toEqual([]);
});

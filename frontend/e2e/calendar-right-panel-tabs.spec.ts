// [Sync] 2026-10-07: freeze each metadata fixture response mode before async date evaluation; recovery journeys await actual complete verification and settled two-row UI before fault injection.
// [Sync] 2026-10-07: explicit-refresh completion waits for its fourth verification and cleared error; retained old title/idle state cannot stand in for the new request completing.
// [Sync] 2026-10-07: pause the installed test clock and advance each real 60-second probe cycle without replaying unrelated App animation/SSE timers; original recovery/cooldown assertions remain.
// [Sync] 2026-10-07: exercise visible serial version discovery, strict context/failed-load recovery and compact one-count one-link public DTO journeys.
// [Sync] 2026-10-07: preserve natural paper-seam and exterior safety assertions while distinguishing sticky translation; assert month rows remain inside their shell.
// [Sync] 2026-10-06: snapshot-first, historical creation, visible-only metadata verification and preserved calendar journeys.
// [Sync] 2026-10-06: borderless three-panel/theme/four-width visuals with actual opaque/alpha contrast and original scroll owners.
// [Sync] 2026-10-06: verify rendered delete-label line rectangles in the diary journey and all long-title visual combinations.
// [Sync] 2026-10-06: record actual focus/pointer events before Modal opening and prove initial-frame readiness with a bounded test-only RAF gate.
// [Sync] 2026-10-07: verify one rounded floating workspace, natural short/empty/long heights, real exterior shadow safety and preserved full journeys.
// [Input] Production Next Calendar/Settings/navigation and public API DTOs intercepted in the shared fixture.
// [Output] Complete Calendar/diary/Notion journeys and concurrent date/auth/connector recovery receipts.
// [Pos] Provider-free technical validation in frontend/e2e; no model, real account, database or resource write.
// [Sync] 2026-10-05: cover tabs, caching, midnight, metadata, recovery, Settings/Login and measured text/icon/focus contrast.
// Project, Episode, canonical Artifact, Run-private .dream and after-turn Hook: out of scope.
// Task/diary consumers and shared Chat navigation: preserved. Calendar presentation/metadata: changes.
import { expect, test, type JSHandle, type Locator, type Page, type Route } from '@playwright/test';
import { installFixtures, openCalendar, openMore, readCalendarVisualMetrics, readFloatingPaperSafety, expectFloatingPaperSafety, WEB_BASE } from './fixtures/calendarHarness';
import { RESOURCE_CONNECTORS_CHANGED_EVENT } from '../app/_dream/api/resourceConnectorApi';
import type { NotionTodayResponse } from '../app/_dream/api/notionTodayApi';

test.use({ channel: 'chrome' });
test.describe.configure({ mode: 'default' });
test.setTimeout(60_000);
const diagnostics = new WeakMap<Page, () => string[]>();
test.afterEach(async ({ page }) => { expect(diagnostics.get(page)?.() ?? []).toEqual([]); });

function todayResponse(date = '2026-09-28', title = '今日创建的文档', connectorId = 'notion-a'): NotionTodayResponse {
  const next = new Date(`${date}T00:00:00Z`); next.setUTCDate(next.getUTCDate() + 1);
  return { connectorId, dateKey: date, timeZone: 'UTC', intervalStart: `${date}T00:00:00Z`,
    intervalEnd: next.toISOString(), observedAt: `${date}T12:00:00Z`, coverage: 'connector_snapshot',
    todayKey: '2026-09-28', snapshotVersion: 'snap-fixture', snapshotFetchedAt: `${date}T10:00:00Z`, verificationState: 'not_required',
    paginationState: 'complete', partialReasons: [], candidateCount: 2, retryAfter: null,
    counts: { created: 1, edited: 1, total: 2 }, items: [
      { pageId: 'page-created', title, url: 'https://www.notion.so/page-created', emoji: '📝',
        createdTime: `${date}T00:00:00Z`, lastEditedTime: `${date}T08:00:00Z`, group: 'created', createdOnDate: true, editedOnDate: true },
      { pageId: 'page-edited', title: '今日编辑的文档', url: null, emoji: null,
        createdTime: '2026-09-01T00:00:00Z', lastEditedTime: `${date}T09:00:00Z`, group: 'edited', createdOnDate: false, editedOnDate: true },
    ] };
}

async function setup(page: Page, options: { authEntryLifecycle?: boolean; longTitle?: boolean; taskCount?: number; diaryCount?: number } = {}) {
  const base = await installFixtures(page, { firstRunOutcome: 'success', initialTriggerStatus: 'succeeded', notionFaults: true,
    authEntryLifecycle: options.authEntryLifecycle, longTitle: options.longTitle, taskCount: options.taskCount, diaryCount: options.diaryCount });
  diagnostics.set(page, base.getUnexpected);
  const calls: string[] = [];
  let connectorId = 'notion-a';
  let auth = 'authenticated';
  let connected = true;
  let version = 'snap-fixture';
  let responseVersion: string | undefined;
  let updatedAt = '2026-09-01T00:00:00Z';
  let documentTitle: string | undefined;
  let syncStatus: 'applied' | 'syncing' | 'error' | 'disabled' = 'applied';
  let connectorFailure: { code: string; status: number; retryAfter?: string } | null = null;
  let holdConnector = false;
  const connectorHeld: Route[] = [];
  let mode: 'success' | 'noCandidates' | 'noToday' | 'partial' | 'fail' | 'hold' | 'network' = 'success';
  let code = 'NOTION_UPSTREAM_UNAVAILABLE';
  let status = 502;
  let retryAfter: string | undefined;
  let longList = false;
  let verification: 'success' | 'hold' | 'auth' | 'rate' = 'success';
  let verificationFailure: { code: string; status: number } | null = null;
  const verificationHeld: Route[] = [];
  const held: Array<{ route: Route; date: string; connector: string }> = [];
  const handle = async (route: Route) => {
    const request = route.request();
    const url = new URL(request.url());
    const verifying = url.searchParams.get('validate_remote') === 'true';
    calls.push(`${request.method()} ${url.pathname}${verifying ? '?validate_remote=true' : ''}`);
    if (url.pathname === '/api/connectors') {
      if (holdConnector) { connectorHeld.push(route); return; }
      if (connectorFailure) {
        await route.fulfill({ status: connectorFailure.status, json: { detail: { error_code: connectorFailure.code } },
          headers: connectorFailure.retryAfter ? { 'Retry-After': connectorFailure.retryAfter } : undefined }); return;
      }
      await route.fulfill({ json: { connectors: connected ? [{ id: connectorId, name: 'Notion', platform: 'notion',
        auth_status: auth, status: auth, created_at: '2026-09-01T00:00:00Z', updated_at: updatedAt, current_snapshot_version: version, config: {}, sources: [],
        sync_policy: { schema_version: 1, default: { enabled: true, interval_minutes: 15, revision: 1 },
          desired: { enabled: syncStatus !== 'disabled', interval_minutes: 15, revision: 1 },
          effective: { enabled: syncStatus !== 'disabled', interval_minutes: 15, revision: 1 }, status: syncStatus,
          allowed_interval_minutes: [15, 60, 360, 1440] } }] : [] } }); return;
    }
    if (url.pathname.endsWith('/notion/documents')) {
      const date = url.searchParams.get('date_key')!;
      const connector = url.pathname.split('/')[3];
      if (verifying && verification === 'hold') { verificationHeld.push(route); return; }
      if (verifying && verification === 'auth') { await route.fulfill({ status: 401, json: { detail: { error_code: 'NOTION_AUTH_EXPIRED' } } }); return; }
      if (verifying && verificationFailure) { await route.fulfill({ status: verificationFailure.status, json: { detail: { error_code: verificationFailure.code } } }); return; }
      if (mode === 'network') { await route.abort('internetdisconnected'); return; }
      if (mode === 'hold' && !verifying) { held.push({ route, date, connector }); return; }
      if (mode === 'fail') { await route.fulfill({ status, json: { detail: { error_code: code } },
        headers: retryAfter ? { 'Retry-After': retryAfter } : undefined }); return; }
      const responseMode = mode; // A request cannot acquire a different simulated result while awaiting its server-day observation.
      const response = todayResponse(date, documentTitle ?? (options.longTitle ? '今日创建的文档与数据库内页面的长标题：'.repeat(8) : undefined), connector);
      response.snapshotVersion = responseVersion ?? version;
      response.todayKey = await page.evaluate(() => new Date().toISOString().slice(0, 10));
      response.verificationState = date === response.todayKey ? verifying ? 'complete' : 'pending' : 'not_required';
      if (date !== response.todayKey) {
        response.items = response.items.filter((item) => item.createdOnDate);
        response.counts = { created: response.items.length, edited: 0, total: response.items.length };
      }
      if (verifying && verification === 'rate') { response.verificationState = 'partial'; response.paginationState = 'partial'; response.partialReasons = ['NOTION_RATE_LIMITED']; response.retryAfter = 3; }
      if (longList) {
        response.items = Array.from({ length: 20 }, (_, index) => ({ ...response.items[0], pageId: `scroll-${index}`, title: `滚动文档 ${index}` }));
        response.candidateCount = 20; response.counts = { created: 20, edited: 0, total: 20 };
      }
      if (responseMode !== 'success') {
        response.verificationState = 'not_required';
        response.items = []; response.counts = { created: 0, edited: 0, total: 0 };
        if (responseMode === 'noCandidates') response.candidateCount = 0;
        if (responseMode === 'partial') { response.paginationState = 'partial'; response.partialReasons = ['metadata_missing']; }
      }
      await route.fulfill({ json: response }); return;
    }
    throw new Error(`Unexpected Notion operation: ${request.method()} ${url.pathname}`);
  };
  await page.route('**/api/connectors', handle);
  await page.route('**/api/connectors/**', handle);
  return { base, calls, held, verificationHeld, connectorHeld,
    snapshot: (nextVersion: string, title?: string, actualVersion?: string) => { version = nextVersion; documentTitle = title; responseVersion = actualVersion; },
    context: (value: string) => { updatedAt = value; },
    policy: (value: typeof syncStatus) => { syncStatus = value; },
    connectorFailure: (value: typeof connectorFailure) => { connectorFailure = value; },
    holdConnector: (value: boolean) => { holdConnector = value; },
    probes: () => calls.filter((call) => call.endsWith('/api/connectors')).length,
    verifyState: (next: typeof verification) => { verification = next; },
    verifyFailure: (value: typeof verificationFailure) => { verificationFailure = value; },
    verifications: () => calls.filter((call) => call.includes('?validate_remote=true')).length,
    longList: (enabled = true) => { longList = enabled; },
    reads: () => calls.filter((call) => call.endsWith('/notion/documents')).length,
    state: (next: typeof mode) => { mode = next; },
    connection: (nextId: string, nextAuth = 'authenticated', exists = true) => { connectorId = nextId; auth = nextAuth; connected = exists; },
    failure: (nextCode: string, nextStatus: number, wait?: string) => { code = nextCode; status = nextStatus; retryAfter = wait; mode = 'fail'; },
  };
}
async function notify(page: Page) { await page.evaluate((name) => window.dispatchEvent(new Event(name)), RESOURCE_CONNECTORS_CHANGED_EVENT); }

async function pauseVersionCheckClock(page: Page) {
  // Modal focus readiness is already complete. Pause before activating Notion;
  // each fastForward below advances one explicit probe/cooldown boundary, rather
  // than replaying every unrelated animation/reconnect callback in the App.
  await page.clock.install({ time: new Date('2026-09-28T12:00:00Z') });
  await page.clock.pauseAt(new Date('2026-09-28T12:00:01Z'));
}


async function expectSingleLineAction(button: Locator) {
  const rendered = await button.evaluate((element) => {
    const range = document.createRange(); range.selectNodeContents(element);
    return { text: element.textContent?.trim(), tops: Array.from(range.getClientRects()).map((rect) => rect.top) };
  });
  expect(rendered.tops.length, `${rendered.text}: no rendered label rectangles`).toBeGreaterThan(0);
  expect(Math.max(...rendered.tops) - Math.min(...rendered.tops), `${rendered.text}: label wraps across lines`).toBeLessThanOrEqual(1);
}

async function installCalendarFocusProbe(page: Page) {
  return page.evaluateHandle(() => {
    const identities = new WeakMap<Element, number>(); let nextId = 1;
    const describe = (element: EventTarget | null) => {
      if (!(element instanceof Element)) return element === window ? { label: 'window' } : null;
      if (!identities.has(element)) identities.set(element, nextId++);
      return { node: identities.get(element), tag: element.tagName, id: element.id,
        role: element.getAttribute('role'), label: element.getAttribute('aria-label'), connected: element.isConnected };
    };
    const events: unknown[] = [];
    const checkpoint = (label: string, event?: Event) => {
      events.push({ label, time: performance.now(), hasFocus: document.hasFocus(),
        active: describe(document.activeElement), target: describe(event?.target ?? null),
        relatedTarget: describe(event && 'relatedTarget' in event ? (event as FocusEvent).relatedTarget : null),
        tabs: Array.from(document.querySelectorAll('.calendar-popup__tabs [role="tab"]')).map((element) => ({
          ...describe(element), selected: element.getAttribute('aria-selected'), tabIndex: element.getAttribute('tabindex'),
        })), tooltip: document.querySelector('.calendar-popup__tabs [role="tooltip"]')?.textContent ?? null });
    };
    const capture = (event: Event) => {
      if (event.type === 'mouseenter' || event.type === 'mouseleave') {
        if (!(event.target instanceof Element) || event.target.getAttribute('role') !== 'tab') return;
      }
      checkpoint(event.type, event);
    };
    const windowEvent = (event: Event) => checkpoint(`window-${event.type}`, event);
    const names = ['focusin', 'focusout', 'mouseenter', 'mouseleave'];
    names.forEach((name) => document.addEventListener(name, capture, true));
    window.addEventListener('focus', windowEvent); window.addEventListener('blur', windowEvent);
    const observer = new MutationObserver((mutations) => {
      const relevant = mutations.filter((mutation) => {
        if (mutation.target instanceof Element && mutation.target.closest('.calendar-popup__tabs')) return true;
        return Array.from(mutation.addedNodes).some((node) => node instanceof Element
          && (node.matches('.calendar-popup__tabs') || node.querySelector('.calendar-popup__tabs')));
      });
      if (relevant.length) checkpoint(relevant.some((mutation) => mutation.type === 'attributes') ? 'tabs-selected-attribute' : 'tabs-child-mutation');
    });
    observer.observe(document.body, { childList: true, subtree: true, attributes: true, attributeFilter: ['aria-selected'] });
    checkpoint('probe-installed');
    return { checkpoint: (label: string) => checkpoint(label), read: () => events,
      cleanup: () => { names.forEach((name) => document.removeEventListener(name, capture, true));
        window.removeEventListener('focus', windowEvent); window.removeEventListener('blur', windowEvent); observer.disconnect(); } };
  });
}

test('controlled initial Modal frame proves calendar focus readiness before tab interactions', async ({ page }, testInfo) => {
  await setup(page);
  let probe: Awaited<ReturnType<typeof installCalendarFocusProbe>> | undefined;
  let frameGate: JSHandle<{ pending: () => number; release: () => number; cleanup: () => void }> | undefined;
  let released = 0;
  try {
    const { dialog } = await openCalendar(page, undefined, {
      waitForInitialFocus: false,
      beforeOpen: async () => {
        probe = await installCalendarFocusProbe(page);
        frameGate = await page.evaluateHandle(() => {
          const requestFrame = window.requestAnimationFrame;
          const cancelFrame = window.cancelAnimationFrame;
          const queued = new Map<number, FrameRequestCallback>();
          const scheduled = new Set<number>(); let nextId = -1;
          const restore = () => { window.requestAnimationFrame = requestFrame; window.cancelAnimationFrame = cancelFrame; };
          window.requestAnimationFrame = (callback) => { const id = nextId--; queued.set(id, callback); return id; };
          window.cancelAnimationFrame = (id) => { if (!queued.delete(id)) cancelFrame.call(window, id); };
          return {
            pending: () => queued.size,
            release: () => {
              restore(); const callbacks = Array.from(queued.values()); queued.clear();
              callbacks.forEach((callback) => {
                const id = requestFrame.call(window, (time) => { scheduled.delete(id); callback(time); });
                scheduled.add(id);
              });
              return callbacks.length;
            },
            cleanup: () => { restore(); queued.clear(); scheduled.forEach((id) => cancelFrame.call(window, id)); scheduled.clear(); },
          };
        });
      },
    });
    const tasks = dialog.getByRole('tab', { name: '定时任务', exact: true });
    const diary = dialog.getByRole('tab', { name: '日记', exact: true });
    const notion = dialog.getByRole('tab', { name: 'Notion', exact: true });
    const monthPrev = dialog.getByRole('button', { name: '← 上个月', exact: true });
    await tasks.focus(); await tasks.press('ArrowRight');
    await expect(diary).toBeFocused(); await expect(dialog.getByRole('tooltip')).toHaveText('日记');
    expect(await frameGate!.evaluate((gate) => gate.pending())).toBeGreaterThan(0);
    await probe!.evaluate((capture) => capture.checkpoint('before-initial-frame-release'));
    released = await frameGate!.evaluate((gate) => gate.release());
    await expect(monthPrev).toBeFocused();
    await probe!.evaluate((capture) => capture.checkpoint('after-original-initial-focus'));
    await notion.hover(); await expect(dialog.getByRole('tooltip')).toHaveText('Notion');
    await expect(monthPrev).toBeFocused();
    await probe!.evaluate((capture) => capture.checkpoint('hover-after-late-initial-focus'));
    // The original keyboard-priority contract holds once the existing initial focus is ready.
    await tasks.focus(); await tasks.press('ArrowRight'); await notion.hover();
    await expect(diary).toBeFocused(); await expect(tasks).toHaveAttribute('aria-selected', 'true');
    await expect(dialog.getByRole('tooltip')).toHaveText('日记');
    await probe!.evaluate((capture) => capture.checkpoint('keyboard-priority-after-ready'));
  } finally {
    if (frameGate) { await frameGate.evaluate((gate) => gate.cleanup()); await frameGate.dispose(); }
    if (probe) {
      await testInfo.attach('calendar-initial-frame-focus-evidence', {
        body: Buffer.from(JSON.stringify({ releasedCallbacks: released, events: await probe.evaluate((capture) => capture.read()) }, null, 2)),
        contentType: 'application/json',
      });
      await probe.evaluate((capture) => capture.cleanup()); await probe.dispose();
    }
  }
});

test('calendar journey preserves input, exact result, keyboard focus and one panel through date and reopen', async ({ page }, testInfo) => {
  const fixture = await setup(page);
  let installedProbe: Awaited<ReturnType<typeof installCalendarFocusProbe>> | undefined;
  const { dialog } = await openCalendar(page, undefined, {
    beforeOpen: async () => { installedProbe = await installCalendarFocusProbe(page); },
  });
  const focusProbe = installedProbe!;
  const tasks = dialog.getByRole('tab', { name: '定时任务', exact: true });
  const diary = dialog.getByRole('tab', { name: '日记', exact: true });
  const notion = dialog.getByRole('tab', { name: 'Notion', exact: true });
  await expect(tasks).toHaveAttribute('aria-selected', 'true');

  try {
    await tasks.focus(); await focusProbe.evaluate((probe) => probe.checkpoint('after-tasks-focus'));
    await tasks.press('ArrowRight'); await focusProbe.evaluate((probe) => probe.checkpoint('after-arrow-right'));
    await expect(diary).toBeFocused(); await expect(tasks).toHaveAttribute('aria-selected', 'true');
    await expect(dialog.getByRole('tooltip')).toHaveText('日记');
    await focusProbe.evaluate((probe) => probe.checkpoint('before-notion-hover'));
    await notion.hover(); await focusProbe.evaluate((probe) => probe.checkpoint('after-notion-hover'));
    await expect(dialog.getByRole('tooltip')).toHaveText('日记'); await expect(diary).toBeFocused();
    await page.mouse.move(0, 0); await expect(dialog.getByRole('tooltip')).toHaveText('日记');
    await diary.press('Escape'); await expect(dialog.getByRole('tooltip')).toHaveCount(0);
    await diary.press('End'); await expect(notion).toBeFocused(); await notion.press('Home'); await expect(tasks).toBeFocused();
  } finally {
    await testInfo.attach('calendar-tooltip-focus-diagnostics', {
      body: Buffer.from(JSON.stringify(await focusProbe.evaluate((probe) => probe.read()), null, 2)), contentType: 'application/json',
    });
    await focusProbe.evaluate((probe) => probe.cleanup()); await focusProbe.dispose();
  }
  await dialog.getByPlaceholder('安排任务').fill('保留的安排输入');
  const dayReads = fixture.base.getDayReadCount(); const histories = fixture.base.getHistoryRequests().length;
  await diary.click(); await expect(dialog.getByRole('tabpanel')).toHaveCount(1);
  await expect(dialog.getByPlaceholder('安排任务')).toBeHidden();
  await tasks.click(); await expect(dialog.getByPlaceholder('安排任务')).toHaveValue('保留的安排输入');
  expect(fixture.base.getDayReadCount()).toBe(dayReads); expect(fixture.base.getHistoryRequests()).toHaveLength(histories);
  await dialog.locator('.calendar-popup__task-open').click();
  await expect(dialog.locator('.calendar-popup__task-result')).toContainText('已整理今天的笔记。');
  const messages = fixture.base.getTargetThreadRequests().length;
  await diary.click(); await tasks.click();
  await expect(dialog.locator('.calendar-popup__task-result')).toContainText('已整理今天的笔记。');
  expect(fixture.base.getTargetThreadRequests()).toHaveLength(messages);
  await dialog.getByRole('gridcell', { name: /2026.*9.*29/ }).click();
  await expect(dialog.locator('.calendar-popup__task-result')).toHaveCount(0);
  await expect(tasks).toHaveAttribute('aria-selected', 'true');
  await expect(dialog.getByPlaceholder('安排任务')).toHaveValue('保留的安排输入');
  await dialog.getByRole('button', { name: '关闭', exact: true }).click();
  await page.getByRole('button', { name: 'Calendar', exact: true }).focus(); await page.keyboard.press('Enter');
  await expect(tasks).toHaveAttribute('aria-selected', 'true');
  await expect(dialog.getByPlaceholder('安排任务')).toHaveValue('');
  await expect(dialog.getByRole('gridcell', { name: /2026.*9.*28/ })).toHaveAttribute('aria-selected', 'true');
});

test('editor trap and history retain the existing owner and close menu on tab switch', async ({ page }) => {
  await setup(page); const { dialog } = await openCalendar(page);
  const card = dialog.locator('.calendar-popup__task').first();
  await openMore(card); await dialog.getByRole('tab', { name: '日记', exact: true }).click();
  await dialog.getByRole('tab', { name: '定时任务', exact: true }).click(); await expect(card.getByRole('menu')).toHaveCount(0);
  await card.getByRole('button', { name: /编辑/ }).click();
  const editor = page.getByRole('dialog', { name: /编辑“/ });
  await editor.getByLabel('标题').fill('未保存的标题');
  for (let index = 0; index < 12; index++) {
    await page.keyboard.press('Tab');
    expect(await editor.evaluate((element) => element.contains(document.activeElement))).toBe(true);
  }
  await expect(editor.getByLabel('标题')).toHaveValue('未保存的标题');
  await page.keyboard.press('Escape'); await expect(editor).toBeHidden();
  await expect(card.getByRole('button', { name: /编辑/ })).toBeFocused();
  await openMore(card); await card.getByRole('menuitem', { name: /历史/ }).click();
  await expect(page.getByRole('dialog', { name: /执行历史/ })).toBeVisible();
  await page.keyboard.press('Escape'); await expect(card.getByRole('button', { name: /更多操作/ })).toBeFocused();
});

test('diary journey opens and returns with current marker and preserves its original delete confirmation', async ({ page }) => {
  await setup(page); let { dialog } = await openCalendar(page);
  await dialog.getByRole('tab', { name: '日记', exact: true }).click();
  await dialog.getByRole('button', { name: '打开: 普通日历笔记仍然可见' }).click();
  await expect(dialog).toBeHidden();
  await page.getByRole('button', { name: 'Calendar', exact: true }).focus(); await page.keyboard.press('Enter');
  dialog = page.getByRole('dialog', { name: '日历', exact: true });
  await dialog.getByRole('tab', { name: '日记', exact: true }).click();
  await expect(dialog.getByText('当前笔记', { exact: true })).toBeVisible();
  await expectSingleLineAction(dialog.getByRole('button', { name: '删除: 普通日历笔记仍然可见' }));
  page.once('dialog', (confirmation) => { expect(confirmation.type()).toBe('confirm'); void confirmation.accept(); });
  await dialog.getByRole('button', { name: '删除: 普通日历笔记仍然可见' }).click();
  await expect(dialog.getByText('这一天暂无记录')).toBeVisible();
});

test('Notion journey reads a snapshot, groups metadata, opens directly, refreshes and reads creation on other dates', async ({ page, context }) => {
  const fixture = await setup(page); const { dialog } = await openCalendar(page);
  await dialog.getByRole('tab', { name: 'Notion', exact: true }).click();
  const panel = dialog.getByRole('tabpanel');
  await expect(panel.locator('[data-notion-count]').filter({ hasText: '2 篇' })).toBeVisible();
  await expect(panel.getByRole('listitem')).toHaveCount(2);
  await expect(panel.getByRole('region', { name: '当日创建' }).getByRole('listitem')).toContainText('创建 00:00');
  await expect(panel.getByRole('region', { name: '当日创建' }).getByRole('listitem')).toContainText('编辑 08:00');
  await expect(panel.getByText('暂时无法打开，可刷新重试。')).toBeVisible();
  await context.route('https://www.notion.so/**', (route) => route.fulfill({ body: '<h1>Notion destination fixture</h1>', contentType: 'text/html' }));
  const popupWait = page.waitForEvent('popup'); await panel.getByRole('link', { name: /在新标签中打开/ }).click();
  const popup = await popupWait; await expect(popup).toHaveURL('https://www.notion.so/page-created'); await popup.close();
  await dialog.getByRole('tab', { name: '日记', exact: true }).click(); await dialog.getByRole('tab', { name: 'Notion', exact: true }).click();
  expect(fixture.reads()).toBe(1);
  await panel.getByRole('button', { name: '刷新', exact: true }).click();
  await expect.poll(fixture.reads).toBe(2); await expect(panel.locator('.calendar-popup__card-body')).toHaveAttribute('aria-busy', 'false');
  await dialog.getByRole('gridcell', { name: /2026.*9.*29/ }).click();
  await expect(panel.getByRole('listitem')).toHaveCount(1); await expect.poll(fixture.reads).toBe(3);
  const checks = fixture.verifications();
  await dialog.getByRole('gridcell', { name: /2026.*9.*28/ }).click(); await expect.poll(fixture.reads).toBe(4);
  await expect.poll(fixture.verifications).toBe(checks + 1);
  expect(fixture.calls.every((call) => call.startsWith('GET '))).toBe(true);
});

for (const state of ['unconnected', 'pending', 'expired', 'noCandidates', 'noToday', 'partial'] as const) {
  test(`Notion ${state} is distinct and recovers through explicit refresh or settings`, async ({ page }) => {
    const fixture = await setup(page);
    if (state === 'unconnected') fixture.connection('notion-a', 'authenticated', false);
    else if (state === 'pending') fixture.connection('notion-a', 'pending');
    else if (state === 'expired') fixture.connection('notion-a', 'expired');
    else fixture.state(state);
    const { dialog } = await openCalendar(page); await dialog.getByRole('tab', { name: 'Notion', exact: true }).click();
    const panel = dialog.getByRole('tabpanel');
    const expected = { unconnected: '连接 Notion 后可查看文档。', pending: 'Notion 连接尚未完成。', expired: 'Notion 授权已失效，请重新连接。',
      noCandidates: '当前连接器索引没有文档', noToday: '今天暂未发现新建或编辑的文档。', partial: '快照尚未同步或缺少上游时间' }[state];
    await expect(panel.getByText(expected, { exact: false })).toBeVisible();
    if (state === 'partial') {
      await expect(panel.getByText('今天暂未发现新建或编辑的文档。')).toHaveCount(0);
      await expect(panel.locator('[data-notion-count]')).toHaveText('已知 0 篇');
    }
    fixture.connection('notion-a'); fixture.state('success');
    await notify(page); await expect(panel.getByText('今日创建的文档', { exact: true })).toBeVisible();
  });
}

test('connection settings navigation closes Calendar and returning reads the restored connection', async ({ page }) => {
  const fixture = await setup(page); fixture.connection('notion-a', 'authenticated', false);
  const { dialog } = await openCalendar(page); await dialog.getByRole('tab', { name: 'Notion', exact: true }).click();
  await dialog.getByRole('button', { name: '管理连接器' }).click();
  await expect(dialog).toBeHidden(); await expect(page).toHaveURL(/\/story-workspace\/settings\/resources$/);
  fixture.connection('notion-a');
  await page.getByRole('button', { name: '返回应用', exact: true }).click();
  await expect(page).toHaveURL(/\/story-workspace\/dream$/);
  const writing = page.getByRole('button', { name: '写作', exact: true });
  if (!await writing.isVisible()) { await page.getByRole('button', { name: '更多', exact: true }).focus(); await page.keyboard.press('Enter'); }
  await writing.focus(); await page.keyboard.press('Enter'); await expect(page).toHaveURL(/\/story-workspace\/writing$/);
  await page.getByRole('button', { name: 'Calendar', exact: true }).focus(); await page.keyboard.press('Enter');
  await dialog.getByRole('tab', { name: 'Notion', exact: true }).click();
  await expect(dialog.getByText('今日创建的文档', { exact: true })).toBeVisible();
  expect(fixture.calls.every((call) => call.startsWith('GET '))).toBe(true);
});

for (const failure of [
  { code: 'INVALID_ACCESS_TOKEN', status: 401, copy: '登录后可连接 Notion', keeps: false },
  { code: 'ADMIN_PERMISSION_DENIED', status: 403, copy: '当前账户已无权访问此连接', keeps: false },
  { code: 'ADMIN_CAPABILITY_UNAVAILABLE', status: 503, copy: '暂时无法读取连接或日期设置', keeps: true },
  { code: 'NOTION_AUTH_EXPIRED', status: 401, copy: 'Notion 授权已失效，请重新连接。', keeps: false },
  { code: 'NOTION_PERMISSION_DENIED', status: 403, copy: '当前连接没有权限读取这些文档', keeps: false },
  { code: 'NOTION_UPSTREAM_UNAVAILABLE', status: 502, copy: 'Notion 暂时无法响应', keeps: true },
  { code: 'ADMIN_DATA_UNAVAILABLE', status: 503, copy: '暂时无法读取连接或日期设置', keeps: true },
] as const) {
  test(`Notion refresh ${failure.code} uses the proper recovery and old-result policy`, async ({ page }) => {
    const fixture = await setup(page); const { dialog } = await openCalendar(page);
    const isCompleteVerification = (response: import('@playwright/test').Response) => {
      const url = new URL(response.url());
      return url.pathname.endsWith('/notion/documents') && url.searchParams.get('validate_remote') === 'true' && response.status() === 200;
    };
    const initialVerification = page.waitForResponse(isCompleteVerification);
    await dialog.getByRole('tab', { name: 'Notion', exact: true }).click();
    const panel = dialog.getByRole('tabpanel'); await expect(panel.getByText('今日创建的文档', { exact: true })).toBeVisible();
    const initialResponse = await initialVerification;
    expect((await initialResponse.json() as NotionTodayResponse).verificationState).toBe('complete');
    await expect.poll(fixture.verifications).toBe(1);
    await expect(panel.locator('.calendar-popup__card-body')).toHaveAttribute('aria-busy', 'false');
    await expect(panel.getByRole('listitem')).toHaveCount(2);
    await expect(panel.getByRole('alert')).toHaveCount(0);
    fixture.failure(failure.code, failure.status); await panel.getByRole('button', { name: '刷新', exact: true }).click();
    await expect(panel.getByRole('alert')).toContainText(failure.copy);
    await expect(panel.getByRole('listitem')).toHaveCount(failure.keeps ? 2 : 0);
    if (failure.keeps) await expect(panel.getByRole('alert')).toContainText('刷新失败，仍显示上次读取的文档。');
    const recoveredVerification = page.waitForResponse(isCompleteVerification);
    fixture.state('success'); await panel.getByRole('button', { name: '刷新', exact: true }).click();
    const recoveredResponse = await recoveredVerification;
    expect((await recoveredResponse.json() as NotionTodayResponse).verificationState).toBe('complete');
    await expect.poll(fixture.verifications).toBe(2);
    await expect(panel.getByText('今日创建的文档', { exact: true })).toBeVisible();
    await expect(panel.locator('.calendar-popup__card-body')).toHaveAttribute('aria-busy', 'false');
    await expect(panel.getByRole('listitem')).toHaveCount(2);
    await expect(panel.getByRole('alert')).toHaveCount(0);
  });
}

test('Notion respects Retry-After before permitting a new request', async ({ page }) => {
  const fixture = await setup(page); fixture.failure('NOTION_RATE_LIMITED', 429, '2');
  const { dialog } = await openCalendar(page); await page.clock.install({ time: new Date('2026-09-28T12:00:00Z') });
  await dialog.getByRole('tab', { name: 'Notion', exact: true }).click(); const panel = dialog.getByRole('tabpanel');
  await expect(panel.getByRole('alert')).toContainText('Notion 请求较多');
  await expect(panel.getByRole('button', { name: '刷新', exact: true })).toBeDisabled();
  fixture.state('success'); await page.clock.runFor(2_100);
  await expect(panel.getByRole('button', { name: '刷新', exact: true })).toBeEnabled();
  await panel.getByRole('button', { name: '刷新', exact: true }).click(); await expect(panel.getByRole('listitem')).toHaveCount(2);
});

test('A to B to A and close reject late responses without invoking a write or body endpoint', async ({ page }) => {
  const fixture = await setup(page); fixture.state('hold'); const { dialog } = await openCalendar(page);
  await dialog.getByRole('tab', { name: 'Notion', exact: true }).click();
  await expect.poll(() => fixture.held.length).toBe(1);
  fixture.connection('notion-b'); await notify(page); await expect.poll(() => fixture.held.length).toBe(2);
  fixture.connection('notion-a'); await notify(page); await expect.poll(() => fixture.held.length).toBe(3);
  await fixture.held[2].route.fulfill({ json: todayResponse(undefined, '最后一轮 A') });
  await expect(dialog.getByText('最后一轮 A', { exact: true })).toBeVisible();
  await fixture.held[0].route.fulfill({ json: todayResponse(undefined, '第一轮 A') }).catch(() => undefined);
  await fixture.held[1].route.fulfill({ json: todayResponse(undefined, '过期 B', 'notion-b') }).catch(() => undefined);
  await expect(dialog.getByText('第一轮 A', { exact: true })).toHaveCount(0);
  await expect(dialog.getByText('过期 B', { exact: true })).toHaveCount(0);
  await dialog.getByRole('button', { name: '刷新', exact: true }).click(); await expect.poll(() => fixture.held.length).toBe(4);
  await dialog.getByRole('button', { name: '关闭', exact: true }).click();
  await fixture.held[3].route.fulfill({ json: todayResponse(undefined, '关闭后的文档') }).catch(() => undefined);
  await expect(page.getByText('关闭后的文档')).toHaveCount(0);
  expect(fixture.calls.every((call) => call.startsWith('GET '))).toBe(true);
});

test('hidden Notion across midnight rereads the selected date snapshot as historical creation only', async ({ page }) => {
  const fixture = await setup(page); const { dialog } = await openCalendar(page);
  await page.clock.install({ time: new Date('2026-09-28T23:59:00Z') });
  await dialog.getByRole('tab', { name: 'Notion', exact: true }).click(); await expect(dialog.getByText('今日创建的文档', { exact: true })).toBeVisible();
  await dialog.getByRole('tab', { name: '日记', exact: true }).click();
  await page.clock.setSystemTime(new Date('2026-09-29T00:01:00Z'));
  await dialog.getByRole('tab', { name: 'Notion', exact: true }).click();
  await expect(dialog.getByRole('listitem')).toHaveCount(1);
  await expect(dialog.getByText('今日创建的文档', { exact: true })).toBeVisible();
  await expect(dialog.getByRole('gridcell', { name: /2026.*9.*28/ })).toHaveAttribute('aria-selected', 'true');
  expect(fixture.reads()).toBe(2);
});

test('rapid date A to B to A restarts a cancelled read and rejects the first A response', async ({ page }) => {
  const fixture = await setup(page); fixture.state('hold'); const { dialog } = await openCalendar(page);
  await dialog.getByRole('tab', { name: 'Notion', exact: true }).click(); await expect.poll(() => fixture.held.length).toBe(1);
  await dialog.getByRole('gridcell', { name: /2026.*9.*29/ }).click();
  await expect.poll(() => fixture.held.length).toBe(2);
  await dialog.getByRole('gridcell', { name: /2026.*9.*28/ }).click(); await expect.poll(() => fixture.held.length).toBe(3);
  await fixture.held[2].route.fulfill({ json: todayResponse(undefined, '返回日期后的新扫描') });
  await expect(dialog.getByText('返回日期后的新扫描', { exact: true })).toBeVisible();
  await fixture.held[0].route.fulfill({ json: todayResponse(undefined, '换日前的旧扫描') }).catch(() => undefined);
  await fixture.held[1].route.fulfill({ json: { ...todayResponse('2026-09-29', '过期日期 B'), items: [], counts: { created: 0, edited: 0, total: 0 } } }).catch(() => undefined);
  await expect(dialog.getByText('换日前的旧扫描', { exact: true })).toHaveCount(0);
});

test('shell logout discards a held today response and returns to its original sign-in screen', async ({ page }) => {
  const fixture = await setup(page, { authEntryLifecycle: true }); fixture.state('hold');
  let release!: () => void; const pending = new Promise<void>((resolve) => { release = resolve; });
  await page.route('**/auth/logout', async (route) => { await pending; await route.fulfill({ json: { success: true } }); });
  await page.route('**/auth/options', async (route) => { await route.fulfill({ json: {
    password_action: 'https://admin.example.test/auth/dream/password',
    google_action: 'https://admin.example.test/auth/dream/google',
  } }); });
  await page.clock.setFixedTime(new Date('2026-09-28T12:00:00Z'));
  await page.goto(`${WEB_BASE}/story-workspace/writing`);
  await page.getByRole('button', { name: '打开用户菜单' }).focus(); await page.keyboard.press('Enter');
  await page.getByRole('menuitem', { name: 'Logout' }).focus(); await page.keyboard.press('Enter');
  await page.getByRole('button', { name: '打开用户菜单' }).focus(); await page.keyboard.press('Enter');
  await page.getByRole('button', { name: 'Calendar', exact: true }).focus(); await page.keyboard.press('Enter');
  const dialog = page.getByRole('dialog', { name: '日历', exact: true });
  await dialog.getByRole('tab', { name: 'Notion', exact: true }).click(); await expect.poll(() => fixture.held.length).toBe(1);
  release(); await expect(dialog).toBeHidden();
  await expect(page.getByRole('button', { name: 'Login', exact: true })).toBeVisible();
  await expect(page.getByRole('button', { name: 'Login', exact: true })).toBeEnabled();
  await fixture.held[0].route.fulfill({ json: todayResponse(undefined, '登出后的旧文档') }).catch(() => undefined);
  await expect(page.getByText('登出后的旧文档')).toHaveCount(0);
});

for (const initial of [true, false]) {
  test(`actual network abort during ${initial ? 'initial read' : 'refresh'} has explicit recovery`, async ({ page }) => {
    const fixture = await setup(page); if (initial) fixture.state('network');
    const { dialog } = await openCalendar(page); await dialog.getByRole('tab', { name: 'Notion', exact: true }).click();
    const panel = dialog.getByRole('tabpanel');
    if (!initial) {
      await expect(panel.getByRole('listitem')).toHaveCount(2); fixture.state('network');
      await panel.getByRole('button', { name: '刷新', exact: true }).click();
    }
    await expect(panel.getByRole('alert')).toContainText('暂时无法读取 Notion 文档');
    await expect(panel.getByRole('listitem')).toHaveCount(initial ? 0 : 2);
    fixture.state('success'); await panel.getByRole('button', { name: '刷新', exact: true }).click();
    await expect(panel.getByRole('listitem')).toHaveCount(2);
  });
}

for (const width of [1440, 1024, 430, 390]) {
  test(`same-day tab changes preserve the owning scroll position at ${width}px`, async ({ page }) => {
    const fixture = await setup(page); fixture.longList(); const { dialog } = await openCalendar(page, { width, height: 600 });
    await dialog.getByRole('tab', { name: 'Notion', exact: true }).click(); await expect(dialog.getByRole('listitem')).toHaveCount(20);
    const owner = width > 1024 ? dialog.getByRole('tabpanel') : dialog.locator('.calendar-popup');
    const position = await owner.evaluate((element) => { element.scrollTop = element.scrollHeight; return element.scrollTop; });
    expect(position).toBeGreaterThan(0);
    await dialog.getByRole('tab', { name: '日记', exact: true }).click();
    await dialog.getByRole('tab', { name: 'Notion', exact: true }).click();
    await expect.poll(() => owner.evaluate((element) => element.scrollTop)).toBe(position);
  });
}

function expectVisualContrast(metrics: Awaited<ReturnType<typeof readCalendarVisualMetrics>>) {
  for (const tab of metrics.tabs) {
    expect(tab.ratio, `${tab.name}: ${JSON.stringify(tab.background)}`).toBeGreaterThanOrEqual(tab.selected ? 4.5 : 3);
  }
  if (metrics.focus?.visible) {
    expect(metrics.focus.style).not.toBe('none'); expect(metrics.focus.width).toBeGreaterThan(0);
    expect(metrics.focus.ratio).toBeGreaterThanOrEqual(3);
  }
  if (metrics.tooltip) expect(metrics.tooltip.ratio).toBeGreaterThanOrEqual(4.5);
  for (const action of metrics.actions) expect(action.ratio, action.text).toBeGreaterThanOrEqual(4.5);
}

function expectFloatingGeometry(metrics: Awaited<ReturnType<typeof readCalendarVisualMetrics>>, width: number) {
  for (const surface of [metrics.surfaces.tabs, metrics.surfaces.panel]) {
    expect(surface.borders).toEqual(['0px', '0px', '0px', '0px']);
    expect(surface.shadow).toBe('none');
    expect(surface.background).not.toBe('rgba(0, 0, 0, 0)');
  }
  const radius = `${width > 1024 ? 24 : width > 640 ? 20 : 18}px`;
  expect(metrics.surfaces.workspace.borders).toEqual(['0px', '0px', '0px', '0px']);
  expect(metrics.surfaces.workspace.corners).toEqual([radius, radius, radius, radius]);
  expect(metrics.surfaces.workspace.shadow).not.toBe('none');
  expect(metrics.surfaces.workspace.background).toBe(metrics.surfaces.tabs.background);
  expect(metrics.surfaces.tabs.corners).toEqual([radius, radius, '0px', '0px']);
  expect(metrics.surfaces.panel.corners).toEqual(['0px', '0px', radius, radius]);
  expect(metrics.surfaces.tabs.background).toBe(metrics.surfaces.panel.background);
  expect(metrics.surfaces.calendar.borders[0]).not.toBe('0px');
  expect(metrics.surfaces.calendar.shadow).not.toBe('none');
  for (const row of metrics.rows) {
    expect(row.borders).toEqual(['0px', '0px', '0px', '0px']);
    expect(row.shadow).toBe('none'); expect(row.radius).toBe('0px');
  }
  expect(metrics.headingBorder).toBe('0px'); expect(metrics.paperJoin).toBeLessThanOrEqual(1);
  expect(Math.max(...metrics.alignment) - Math.min(...metrics.alignment)).toBeLessThanOrEqual(1);
  for (const box of metrics.rightRects) {
    expect(box.left).toBeGreaterThanOrEqual(0); expect(box.right).toBeLessThanOrEqual(width);
  }
  expect(metrics.scrollOwner).toBe(width > 1024 ? 'panel' : 'layout');
  expect(metrics.panelOverflow).toBe(width > 1024 ? 'auto' : 'visible');
  if (width <= 1024) {
    expect(metrics.tabsPosition).toBe('sticky');
    expect(metrics.naturalStack.gap).toBeGreaterThanOrEqual(metrics.naturalStack.expectedGap - 1);
    expect(metrics.naturalStack.calendarContentBottomGap).toBeGreaterThanOrEqual(metrics.naturalStack.calendarPaddingBottom - 1);
    expect(Math.abs(metrics.naturalStack.stickyTop - metrics.naturalStack.stickyExpectedTop)).toBeLessThanOrEqual(1);
  }
}

for (const width of [1440, 1024, 430, 390]) {
  test(`floating workspace naturally follows short empty long and hidden contexts at ${width}px`, async ({ page }, testInfo) => {
    test.setTimeout(120_000);
    const fixture = await setup(page); const { dialog } = await openCalendar(page, { width, height: 844 });
    const workspace = dialog.locator('.calendar-popup__workspace');
    const snapshots: Array<{ label: string; metrics: Awaited<ReturnType<typeof readCalendarVisualMetrics>> }> = [];
    const capture = async (label: string) => {
      const metrics = await readCalendarVisualMetrics(dialog); expectFloatingGeometry(metrics, width); expectVisualContrast(metrics);
      if (width > 1024) expect(metrics.heights.workspace).toBeLessThanOrEqual(metrics.heights.available + 1);
      snapshots.push({ label, metrics }); return metrics;
    };
    for (const theme of ['light', 'dark'] as const) {
      await page.emulateMedia({ colorScheme: theme });
      await page.evaluate((value) => document.documentElement.setAttribute('data-theme', value), theme);
      await dialog.getByRole('tab', { name: '定时任务', exact: true }).click();
      await expect(dialog.locator('.calendar-popup__task')).toHaveCount(1);
      const shortTask = await capture(`${theme}-task-short`);
      if (width > 1024) expect(shortTask.heights.workspace).toBeLessThan(shortTask.heights.calendar - 1);
      await dialog.getByPlaceholder('安排任务').fill('自然高度仍保留草稿');
      fixture.base.setTaskCount(20);
      await dialog.getByRole('gridcell', { name: /2026.*9.*29/ }).click();
      await expect(dialog.locator('.calendar-popup__task')).toHaveCount(20);
      const longTask = await capture(`${theme}-task-long`);
      expect(longTask.heights.workspace).toBeGreaterThan(shortTask.heights.workspace);
      if (width > 1024) expect(longTask.heights.panelScroll).toBeGreaterThan(longTask.heights.panelClient);
      fixture.base.setTaskCount(1);
      await dialog.getByRole('gridcell', { name: /2026.*9.*28/ }).click();
      await expect(dialog.locator('.calendar-popup__task')).toHaveCount(1);
      await expect.poll(async () => (await workspace.boundingBox())!.height).toBeLessThan(longTask.heights.workspace);
      const returnedTask = await capture(`${theme}-task-short-return`);
      expect(returnedTask.heights.workspace).toBeCloseTo(shortTask.heights.workspace, 0);
      await expect(dialog.getByPlaceholder('安排任务')).toHaveValue('自然高度仍保留草稿');
      await dialog.getByRole('tab', { name: '日记', exact: true }).click();
      await expect(dialog.locator('.calendar-popup__diary')).toHaveCount(1);
      const diaryShort = await capture(`${theme}-diary-short`);
      if (width > 1024) expect(diaryShort.heights.workspace).toBeLessThan(diaryShort.heights.calendar - 1);
      await dialog.getByRole('gridcell', { name: /2026.*9.*30/ }).click();
      await expect(dialog.locator('.calendar-popup__diary')).toHaveCount(0);
      await expect(dialog.getByText('这一天暂无记录')).toBeVisible();
      const diaryEmpty = await capture(`${theme}-diary-empty`);
      if (width > 1024) expect(diaryEmpty.heights.workspace).toBeLessThan(diaryEmpty.heights.calendar - 1);
      await dialog.getByRole('gridcell', { name: /2026.*9.*28/ }).click();
      await expect(dialog.locator('.calendar-popup__diary')).toHaveCount(1);
      expect((await capture(`${theme}-diary-short-return`)).heights.workspace).toBeCloseTo(diaryShort.heights.workspace, 0);
      await dialog.getByRole('tab', { name: 'Notion', exact: true }).click();
      await expect(dialog.getByRole('listitem')).toHaveCount(2);
      const notionShort = await capture(`${theme}-notion-short`);
      fixture.state('noToday'); await dialog.getByRole('button', { name: '刷新', exact: true }).click();
      await expect(dialog.getByRole('listitem')).toHaveCount(0);
      const notionEmpty = await capture(`${theme}-notion-empty`);
      expect(notionEmpty.heights.workspace).toBeLessThan(notionShort.heights.workspace);
      fixture.state('success'); fixture.longList(); await dialog.getByRole('button', { name: '刷新', exact: true }).click();
      await expect(dialog.getByRole('listitem')).toHaveCount(20);
      const notionLong = await capture(`${theme}-notion-long`);
      expect(notionLong.heights.workspace).toBeGreaterThan(notionShort.heights.workspace);
      if (width > 1024) expect(notionLong.heights.panelScroll).toBeGreaterThan(notionLong.heights.panelClient);
      await dialog.getByRole('tab', { name: '日记', exact: true }).click();
      expect((await capture(`${theme}-hidden-long-notion`)).heights.workspace).toBeCloseTo(diaryShort.heights.workspace, 0);
      await dialog.getByRole('tab', { name: 'Notion', exact: true }).click(); await expect(dialog.getByRole('listitem')).toHaveCount(20);
      fixture.longList(false); await dialog.getByRole('button', { name: '刷新', exact: true }).click();
      await expect(dialog.getByRole('listitem')).toHaveCount(2);
      await expect.poll(async () => (await workspace.boundingBox())!.height).toBeLessThan(notionLong.heights.workspace);
      expect((await capture(`${theme}-notion-short-return`)).heights.workspace).toBeCloseTo(notionShort.heights.workspace, 0);
      const safety = await readFloatingPaperSafety(dialog);
      expectFloatingPaperSafety(safety, width > 1024 ? { side: 36, bottom: 56 }
        : width > 640 ? { side: 20, bottom: 36 } : { side: 16, bottom: 28 });
      await testInfo.attach(`calendar-notion-${theme}-${width}-natural-short`, { body: await page.screenshot(), contentType: 'image/png' });
    }
    expect(fixture.calls.every((call) => call.startsWith('GET '))).toBe(true);
    await testInfo.attach(`calendar-${width}-natural-height-evidence`, { body: Buffer.from(JSON.stringify(snapshots, null, 2)), contentType: 'application/json' });
  });
}

test('floating workspace with borderless inner three-panel visuals covers themes widths states and long titles with measured contrast', async ({ page }, testInfo) => {
  test.setTimeout(120_000);
  await setup(page, { longTitle: true });
  const { dialog } = await openCalendar(page, { width: 1440, height: 844 });
  // The existing public diary flow sets the current marker; no DOM/state injection.
  await dialog.getByRole('tab', { name: '日记', exact: true }).click();
  await dialog.locator('.calendar-popup__diary-open').click(); await expect(dialog).toBeHidden();
  await page.getByRole('button', { name: 'Calendar', exact: true }).focus(); await page.keyboard.press('Enter');
  await expect(dialog).toBeVisible();
  for (const width of [1440, 1024, 430, 390]) {
    await page.setViewportSize({ width, height: 844 });
    for (const theme of ['light', 'dark'] as const) {
      await page.emulateMedia({ colorScheme: theme });
      await page.evaluate((value) => document.documentElement.setAttribute('data-theme', value), theme);
      for (const [tabName, slug] of [['定时任务', 'tasks'], ['日记', 'diary'], ['Notion', 'notion']] as const) {
        const selected = dialog.getByRole('tab', { name: tabName, exact: true });
        await selected.click(); await expect(dialog.getByRole('tabpanel')).toHaveCount(1);
        if (slug === 'notion') {
          await expect(dialog.getByRole('listitem')).toHaveCount(2);
          await expect(dialog.getByRole('button', { name: '刷新', exact: true })).toBeEnabled();
          await expect(dialog.locator('.calendar-popup__notion-group')).toHaveCount(2);
        }
        if (slug === 'diary') await expect(dialog.locator('.calendar-popup__diary--current')).toHaveCount(1);
        await dialog.locator('.calendar-popup').evaluate((element) => { element.scrollTop = 0; });
        await page.mouse.move(0, 0); await selected.evaluate((element) => (element as HTMLElement).blur());
        const normal = await readCalendarVisualMetrics(dialog);
        expectFloatingGeometry(normal, width); expectVisualContrast(normal);
        for (const tab of normal.tabs.filter((item) => !item.selected)) expect(tab.rawBackground).toBe('rgba(0, 0, 0, 0)');
        expect(await page.evaluate(() => document.documentElement.scrollWidth <= document.documentElement.clientWidth)).toBe(true);
        await testInfo.attach(`calendar-${slug}-${theme}-${width}-normal`, { body: await page.screenshot(), contentType: 'image/png' });
        // Select by attribute because the selected label expands but semantic names are unchanged.
        const unselected = dialog.locator('[role="tab"][aria-selected="false"]').first();
        await unselected.hover(); await expect(dialog.getByRole('tooltip')).toBeVisible();
        const hovered = await readCalendarVisualMetrics(dialog); expectVisualContrast(hovered);
        const tooltipBox = hovered.tooltip!.rect;
        expect(tooltipBox.left).toBeGreaterThanOrEqual(0); expect(tooltipBox.right).toBeLessThanOrEqual(width);
        expect(tooltipBox.top).toBeGreaterThanOrEqual(0); expect(tooltipBox.bottom).toBeLessThanOrEqual(844);
        await testInfo.attach(`calendar-${slug}-${theme}-${width}-hover`, { body: await page.screenshot(), contentType: 'image/png' });
        await selected.focus(); await selected.press('ArrowRight'); await page.keyboard.press('ArrowLeft');
        await expect(selected).toBeFocused(); await page.mouse.move(0, 0);
        const focused = await readCalendarVisualMetrics(dialog); expect(focused.focus?.visible).toBe(true); expectVisualContrast(focused);
        await unselected.focus(); await unselected.press('ArrowRight'); await page.keyboard.press('ArrowLeft');
        await expect(unselected).toBeFocused(); await expect(dialog.getByRole('tooltip')).toBeVisible();
        const iconFocused = await readCalendarVisualMetrics(dialog); expect(iconFocused.focus?.visible).toBe(true); expectVisualContrast(iconFocused);
        await testInfo.attach(`calendar-${slug}-${theme}-${width}-focus`, { body: await page.screenshot(), contentType: 'image/png' });
        const rowTarget = slug === 'tasks' ? dialog.locator('.calendar-popup__task-open').first()
          : slug === 'diary' ? dialog.locator('.calendar-popup__diary-open').first()
            : dialog.locator('.calendar-popup__notion-title').first();
        await rowTarget.hover(); const rowHovered = await readCalendarVisualMetrics(dialog); expectVisualContrast(rowHovered);
        for (const row of rowHovered.rows) { expect(row.shadow).toBe('none'); expect(row.borders).toEqual(['0px', '0px', '0px', '0px']); }
        await testInfo.attach(`calendar-${slug}-${theme}-${width}-row-hover`, { body: await page.screenshot(), contentType: 'image/png' });
        await testInfo.attach(`calendar-${slug}-${theme}-${width}-computed`, {
          body: Buffer.from(JSON.stringify({ normal, hovered, focused, iconFocused, rowHovered }, null, 2)), contentType: 'application/json',
        });
        const action = slug === 'tasks' ? dialog.locator('.calendar-popup__edit-button').first()
          : slug === 'diary' ? dialog.locator('.calendar-popup__diary-delete').first()
            : dialog.getByRole('button', { name: '刷新', exact: true });
        await action.scrollIntoViewIfNeeded(); await action.click({ trial: true });
        if (slug === 'diary') await expectSingleLineAction(action);
        const actionBox = await action.boundingBox();
        expect(actionBox && actionBox.x >= 0 && actionBox.x + actionBox.width <= width
          && actionBox.y >= 0 && actionBox.y + actionBox.height <= 844).toBeTruthy();
      }
    }
  }
});

test('long three-panel content keeps the original scroll owner and floating shadow safety at every width', async ({ page }, testInfo) => {
  test.setTimeout(120_000);
  const fixture = await setup(page, { longTitle: true, taskCount: 20, diaryCount: 20 }); fixture.longList();
  const { dialog } = await openCalendar(page, { width: 1440, height: 844 });
  for (const width of [1440, 1024, 430, 390]) {
    await page.setViewportSize({ width, height: 844 });
    for (const theme of ['light', 'dark'] as const) {
      await page.emulateMedia({ colorScheme: theme });
      await page.evaluate((value) => document.documentElement.setAttribute('data-theme', value), theme);
      for (const [name, slug, selector] of [['定时任务', 'tasks', '.calendar-popup__task'],
        ['日记', 'diary', '.calendar-popup__diary'], ['Notion', 'notion', '.calendar-popup__notion-group li']] as const) {
        await dialog.getByRole('tab', { name, exact: true }).click();
        const rows = dialog.locator(selector); await expect(rows).toHaveCount(20);
        const owner = width > 1024 ? dialog.getByRole('tabpanel') : dialog.locator('.calendar-popup');
        const calendar = dialog.locator('.calendar-popup__calendar'); const before = await calendar.boundingBox();
        const position = await owner.evaluate((element) => { element.scrollTop = element.scrollHeight; return element.scrollTop; });
        expect(position).toBeGreaterThan(0); await expect(rows.last()).toBeVisible();
        const lastBox = await rows.last().boundingBox();
        expect(lastBox && lastBox.y >= 0 && lastBox.y + lastBox.height <= 844).toBeTruthy();
        const after = await calendar.boundingBox();
        if (width > 1024) expect(Math.abs(before!.y - after!.y)).toBeLessThanOrEqual(1);
        const metrics = await readCalendarVisualMetrics(dialog); expectVisualContrast(metrics); expectFloatingGeometry(metrics, width);
        if (width > 1024) {
          expect(metrics.heights.workspace).toBeLessThanOrEqual(metrics.heights.available + 1);
          expect(metrics.heights.panelScroll).toBeGreaterThan(metrics.heights.panelClient);
        }
        const safety = await readFloatingPaperSafety(dialog);
        expectFloatingPaperSafety(safety, width > 1024 ? { side: 36, bottom: 56 }
          : width > 640 ? { side: 20, bottom: 36 } : { side: 16, bottom: 28 });
        await testInfo.attach(`calendar-${slug}-${theme}-${width}-long`, { body: await page.screenshot(), contentType: 'image/png' });
        await testInfo.attach(`calendar-${slug}-${theme}-${width}-long-computed`, {
          body: Buffer.from(JSON.stringify({ metrics, safety }, null, 2)), contentType: 'application/json',
        });
      }
    }
  }
});

test('system color preference maps to actual Calendar paper and measured tab contrast', async ({ page }, testInfo) => {
  await setup(page); const { dialog } = await openCalendar(page);
  const papers: string[] = [];
  for (const scheme of ['light', 'dark'] as const) {
    await page.emulateMedia({ colorScheme: scheme });
    await page.evaluate(() => document.documentElement.removeAttribute('data-theme'));
    await dialog.getByRole('tab', { name: 'Notion', exact: true }).click(); await expect(dialog.getByRole('listitem')).toHaveCount(2);
    await page.mouse.move(0, 0);
    const metrics = await readCalendarVisualMetrics(dialog); expectVisualContrast(metrics);
    papers.push(metrics.paperToken);
    await testInfo.attach(`calendar-notion-system-${scheme}-1440-computed`, { body: Buffer.from(JSON.stringify(metrics, null, 2)), contentType: 'application/json' });
    await testInfo.attach(`calendar-notion-system-${scheme}-1440`, { body: await page.screenshot(), contentType: 'image/png' });
  }
  expect(papers[0]).not.toBe(papers[1]);
});

test('snapshot rows and links are usable while today-update verification is slow', async ({ page }) => {
  const fixture = await setup(page); fixture.verifyState('hold');
  const { dialog } = await openCalendar(page); await dialog.getByRole('tab', { name: 'Notion', exact: true }).click();
  const panel = dialog.getByRole('tabpanel');
  await expect.poll(() => fixture.verificationHeld.length).toBe(1);
  await expect(panel.getByRole('listitem')).toHaveCount(2);
  await expect(panel.locator('.calendar-popup__card-body')).toHaveAttribute('aria-busy', 'true');
  await expect(panel.getByText(/最近同步：/)).toHaveCount(0);
  await expect(panel.locator('[data-notion-count]')).toHaveText('2 篇');
  await expect(panel.getByRole('link', { name: /在新标签中打开/ })).toHaveAttribute('href', 'https://www.notion.so/page-created');
  await expect(panel.getByRole('button', { name: '刷新', exact: true })).toBeDisabled();
  const response = todayResponse(); response.verificationState = 'complete';
  await fixture.verificationHeld[0].fulfill({ json: response });
  await expect(panel.getByRole('button', { name: '刷新', exact: true })).toBeEnabled();
  await dialog.getByRole('tab', { name: '日记', exact: true }).click();
  await dialog.getByRole('tab', { name: 'Notion', exact: true }).click();
  expect(fixture.reads()).toBe(1); expect(fixture.verifications()).toBe(1);
  expect(fixture.calls.every((call) => call.startsWith('GET '))).toBe(true);
});

test('a snapshot finishing while hidden defers its today verification until the panel returns', async ({ page }) => {
  const fixture = await setup(page); fixture.state('hold'); fixture.verifyState('hold');
  const { dialog } = await openCalendar(page); await dialog.getByRole('tab', { name: 'Notion', exact: true }).click();
  await expect.poll(() => fixture.held.length).toBe(1);
  await dialog.getByRole('tab', { name: '日记', exact: true }).click();
  const response = todayResponse(); response.verificationState = 'pending';
  await fixture.held[0].route.fulfill({ json: response });
  await expect(dialog.getByText('当前笔记', { exact: true })).toBeVisible();
  expect(fixture.verifications()).toBe(0);
  await dialog.getByRole('tab', { name: 'Notion', exact: true }).click();
  await expect.poll(() => fixture.verificationHeld.length).toBe(1);
  await expect(dialog.getByRole('listitem')).toHaveCount(2);
  await dialog.getByRole('button', { name: '关闭', exact: true }).click();
  await fixture.verificationHeld[0].fulfill({ json: { ...response, verificationState: 'complete' } }).catch(() => undefined);
  await expect(page.getByText('今日创建的文档', { exact: true })).toHaveCount(0);
});

test('verification auth loss clears the visible snapshot and recovers after connection changes', async ({ page }) => {
  const fixture = await setup(page); fixture.verifyState('auth');
  const { dialog } = await openCalendar(page); await dialog.getByRole('tab', { name: 'Notion', exact: true }).click();
  await expect(dialog.getByRole('alert')).toContainText('Notion 授权已失效');
  await expect(dialog.getByRole('listitem')).toHaveCount(0);
  fixture.verifyState('success'); await notify(page);
  await expect(dialog.getByRole('listitem')).toHaveCount(2);
  await expect(dialog.getByRole('button', { name: '刷新', exact: true })).toBeEnabled();
});

test('verification partial rate limit preserves the snapshot and disables refresh for Retry-After', async ({ page }) => {
  const fixture = await setup(page); fixture.verifyState('rate');
  const { dialog } = await openCalendar(page); await dialog.getByRole('tab', { name: 'Notion', exact: true }).click();
  await expect(dialog.getByText('部分文档未能读取，请稍后刷新。')).toBeVisible();
  await expect(dialog.getByRole('listitem')).toHaveCount(2);
  await expect(dialog.getByRole('button', { name: '刷新', exact: true })).toBeDisabled();
  expect(fixture.verifications()).toBe(1);
});


test('background V1 to V2 discovery is serial visible-only and unchanged loaded metadata stays cached', async ({ page }) => {
  const fixture = await setup(page); const { dialog } = await openCalendar(page);
  await pauseVersionCheckClock(page);
  await dialog.getByRole('tab', { name: 'Notion', exact: true }).click();
  const panel = dialog.getByRole('tabpanel');
  await expect(panel.getByRole('listitem')).toHaveCount(2); await expect(panel.locator('.calendar-popup__card-body')).toHaveAttribute('aria-busy', 'false');
  await expect(panel.locator('[data-notion-count]')).toHaveText('2 篇');
  const reads = fixture.reads(); const verifications = fixture.verifications();
  await page.clock.fastForward(60_001); await expect.poll(fixture.probes).toBeGreaterThan(1);
  expect(fixture.reads()).toBe(reads); expect(fixture.verifications()).toBe(verifications);
  fixture.holdConnector(true); await page.clock.fastForward(60_001); await expect.poll(() => fixture.connectorHeld.length).toBe(1);
  const serialProbes = fixture.probes(); await page.clock.fastForward(180_001); expect(fixture.probes()).toBe(serialProbes);
  fixture.holdConnector(false);
  await fixture.connectorHeld[0].fulfill({ json: { connectors: [{ id: 'notion-a', name: 'Notion', platform: 'notion', auth_status: 'authenticated',
    created_at: '2026-09-01T00:00:00Z', updated_at: '2026-09-01T00:00:00Z', current_snapshot_version: 'snap-fixture', config: {}, sources: [],
    sync_policy: { schema_version: 1, default: { enabled: true, interval_minutes: 15, revision: 1 },
      desired: { enabled: true, interval_minutes: 15, revision: 1 }, effective: { enabled: true, interval_minutes: 15, revision: 1 },
      status: 'error', allowed_interval_minutes: [15, 60, 360, 1440] } }] } });
  await expect(panel.getByRole('status')).toContainText('连接器同步失败。');
  await expect(panel.getByRole('status').getByRole('button', { name: '管理连接器', exact: true })).toHaveCount(1);
  fixture.snapshot('V2', '后台同步后的今日文档');
  await page.clock.fastForward(60_001); await expect(panel.getByText('后台同步后的今日文档', { exact: true })).toBeVisible();
  await expect(panel.getByRole('listitem')).toHaveCount(2); await expect(panel.locator('.calendar-popup__card-body')).toHaveAttribute('aria-busy', 'false');
  expect(fixture.reads()).toBe(reads + 1); expect(fixture.verifications()).toBe(verifications + 1);
  await dialog.getByRole('tab', { name: '日记', exact: true }).click(); const hiddenCalls = fixture.calls.length;
  fixture.snapshot('V3', '返回栏目发现的文档'); await page.clock.fastForward(120_001);
  expect(fixture.calls.length).toBe(hiddenCalls);
  await dialog.getByRole('tab', { name: 'Notion', exact: true }).click();
  await expect(panel.getByText('返回栏目发现的文档', { exact: true })).toBeVisible();
  await expect(panel.getByRole('listitem')).toHaveCount(2); await expect(panel.locator('.calendar-popup__card-body')).toHaveAttribute('aria-busy', 'false');
  const beforePageHide = fixture.calls.length;
  await page.evaluate(() => { Object.defineProperty(document, 'visibilityState', { configurable: true, value: 'hidden' }); document.dispatchEvent(new Event('visibilitychange')); });
  fixture.snapshot('V4', '恢复浏览器可见后文档'); await page.clock.fastForward(120_001); expect(fixture.calls.length).toBe(beforePageHide);
  await page.evaluate(() => { Object.defineProperty(document, 'visibilityState', { configurable: true, value: 'visible' }); document.dispatchEvent(new Event('visibilitychange')); });
  await expect(panel.getByText('恢复浏览器可见后文档', { exact: true })).toBeVisible();
  expect(fixture.calls.every((call) => call.startsWith('GET '))).toBe(true);
});

test('a probe V2 and successful actual V3 response do not reread when the next observation catches up', async ({ page }) => {
  const fixture = await setup(page); const { dialog } = await openCalendar(page);
  await pauseVersionCheckClock(page);
  await dialog.getByRole('tab', { name: 'Notion', exact: true }).click();
  const panel = dialog.getByRole('tabpanel'); await expect(panel.getByRole('listitem')).toHaveCount(2); await expect(panel.locator('.calendar-popup__card-body')).toHaveAttribute('aria-busy', 'false');
  fixture.snapshot('V2', '实际版本V3文档', 'V3');
  await page.clock.fastForward(60_001); await expect(panel.getByText('实际版本V3文档', { exact: true })).toBeVisible();
  await expect(panel.getByRole('listitem')).toHaveCount(2); await expect(panel.locator('.calendar-popup__card-body')).toHaveAttribute('aria-busy', 'false');
  const reads = fixture.reads(); const verifications = fixture.verifications(); const probes = fixture.probes();
  fixture.snapshot('V3', '实际版本V3文档'); await page.clock.fastForward(60_001);
  await expect.poll(fixture.probes).toBeGreaterThan(probes);
  expect(fixture.reads()).toBe(reads); expect(fixture.verifications()).toBe(verifications);
  await expect(panel.getByRole('listitem')).toHaveCount(2); await expect(panel.locator('.calendar-popup__card-body')).toHaveAttribute('aria-busy', 'false');
});

for (const fault of [{ code: 'NOTION_UPSTREAM_UNAVAILABLE', status: 502 }, { code: 'NOTION_SNAPSHOT_CHANGED', status: 409 }]) {
  test(`same observed version recovers ${fault.code} on the next normal cycle without a busy loop`, async ({ page }) => {
    const fixture = await setup(page); fixture.failure(fault.code, fault.status);
    const { dialog } = await openCalendar(page); await pauseVersionCheckClock(page);
    await dialog.getByRole('tab', { name: 'Notion', exact: true }).click(); const panel = dialog.getByRole('tabpanel');
    await expect(panel.getByRole('alert')).toBeVisible(); expect(fixture.reads()).toBe(1);
    fixture.state('success'); await page.clock.fastForward(59_000); expect(fixture.reads()).toBe(1);
    await page.clock.fastForward(1_001); await expect(panel.getByText('今日创建的文档', { exact: true })).toBeVisible();
    await expect(panel.getByRole('listitem')).toHaveCount(2); await expect(panel.locator('.calendar-popup__card-body')).toHaveAttribute('aria-busy', 'false');
    expect(fixture.reads()).toBe(2); expect(fixture.verifications()).toBe(1);
    fixture.snapshot('V2', '新版本恢复文档'); fixture.failure(fault.code, fault.status);
    await page.clock.fastForward(60_001); await expect(panel.getByRole('alert')).toBeVisible(); expect(fixture.reads()).toBe(3);
    fixture.state('success'); await page.clock.fastForward(60_001); await expect(panel.getByText('新版本恢复文档', { exact: true })).toBeVisible();
    await expect(panel.locator('.calendar-popup__card-body')).toHaveAttribute('aria-busy', 'false');
    expect(fixture.reads()).toBe(4); expect(fixture.verifications()).toBe(2);
    fixture.verifyFailure(fault); await panel.getByRole('button', { name: '刷新', exact: true }).click();
    await expect(panel.getByRole('alert')).toBeVisible(); expect(fixture.verifications()).toBe(3);
    await expect(panel.getByRole('listitem')).toHaveCount(fault.status === 502 ? 2 : 0);
    fixture.verifyFailure(null); await page.clock.fastForward(60_001);
    if (fault.status === 502) {
      expect(fixture.verifications()).toBe(3); await expect(panel.getByRole('alert')).toBeVisible();
      await panel.getByRole('button', { name: '刷新', exact: true }).click();
    }
    // A temporary failure keeps the same title and idle state visible. The new
    // explicit refresh must reach its own verification before those observations
    // can represent completion; keep the exact fourth-request expectation.
    await expect.poll(fixture.verifications).toBe(4);
    await expect(panel.getByRole('alert')).toHaveCount(0);
    await expect(panel.getByText('新版本恢复文档', { exact: true })).toBeVisible();
    await expect(panel.locator('.calendar-popup__card-body')).toHaveAttribute('aria-busy', 'false');
    expect(fixture.calls.every((call) => call.startsWith('GET '))).toBe(true);
  });
}

test('sync-only updatedAt changes clear old results and cancel an obsolete read even when the version is unchanged', async ({ page }) => {
  const fixture = await setup(page); const { dialog } = await openCalendar(page);
  await pauseVersionCheckClock(page);
  await dialog.getByRole('tab', { name: 'Notion', exact: true }).click(); const panel = dialog.getByRole('tabpanel');
  await expect(panel.getByRole('listitem')).toHaveCount(2); await expect(panel.locator('.calendar-popup__card-body')).toHaveAttribute('aria-busy', 'false');
  fixture.context('2026-09-28T12:01:00Z'); fixture.policy('syncing'); fixture.state('hold');
  await page.clock.fastForward(60_001); await expect.poll(() => fixture.held.length).toBe(1);
  await expect(panel.getByRole('listitem')).toHaveCount(0);
  fixture.context('2026-09-01T00:00:00Z'); fixture.policy('applied'); fixture.state('success');
  await page.clock.fastForward(60_001); await expect(panel.getByText('今日创建的文档', { exact: true })).toBeVisible();
  await expect(panel.getByRole('listitem')).toHaveCount(2); await expect(panel.locator('.calendar-popup__card-body')).toHaveAttribute('aria-busy', 'false');
  await fixture.held[0].route.fulfill({ json: todayResponse('2026-09-28', '迟到的未知上下文文档') }).catch(() => undefined);
  await expect(panel.getByText('迟到的未知上下文文档')).toHaveCount(0);
  expect(fixture.verifications()).toBe(2);
});

test('probe authorization loss and same-identity recovery discard the previous verification completion', async ({ page }) => {
  const fixture = await setup(page); const { dialog } = await openCalendar(page);
  await pauseVersionCheckClock(page);
  await dialog.getByRole('tab', { name: 'Notion', exact: true }).click(); const panel = dialog.getByRole('tabpanel');
  await expect(panel.getByRole('listitem')).toHaveCount(2); await expect(panel.locator('.calendar-popup__card-body')).toHaveAttribute('aria-busy', 'false'); expect(fixture.verifications()).toBe(1);
  fixture.connectorFailure({ code: 'INVALID_ACCESS_TOKEN', status: 401 }); await page.clock.fastForward(60_001);
  await expect(panel.getByRole('alert')).toContainText('登录后可连接 Notion'); await expect(panel.getByRole('listitem')).toHaveCount(0);
  fixture.connectorFailure(null); await page.clock.fastForward(60_001);
  await expect(panel.getByText('今日创建的文档', { exact: true })).toBeVisible();
  await expect(panel.getByRole('listitem')).toHaveCount(2); await expect(panel.locator('.calendar-popup__card-body')).toHaveAttribute('aria-busy', 'false'); expect(fixture.verifications()).toBe(2);
});

test('connector probe Retry-After suppresses all phases and an unchanged in-flight verification is not cancelled', async ({ page }) => {
  const fixture = await setup(page); fixture.verifyState('hold'); const { dialog } = await openCalendar(page);
  await pauseVersionCheckClock(page);
  await dialog.getByRole('tab', { name: 'Notion', exact: true }).click(); const panel = dialog.getByRole('tabpanel');
  await expect.poll(() => fixture.verificationHeld.length).toBe(1);
  await page.clock.fastForward(60_001); expect(fixture.reads()).toBe(1); expect(fixture.verificationHeld.length).toBe(1);
  await fixture.verificationHeld[0].fulfill({ json: { ...todayResponse(), verificationState: 'complete' } });
  await expect(panel.getByRole('listitem')).toHaveCount(2); await expect(panel.locator('.calendar-popup__card-body')).toHaveAttribute('aria-busy', 'false');
  fixture.connectorFailure({ code: 'NOTION_RATE_LIMITED', status: 429, retryAfter: '120' });
  await page.clock.fastForward(60_001); await expect(panel.getByRole('alert')).toContainText('Notion 请求较多');
  await expect(panel.getByRole('button', { name: '刷新', exact: true })).toBeDisabled();
  const calls = fixture.calls.length; fixture.connectorFailure(null); fixture.snapshot('V2', '冷却后新版本文档');
  await page.clock.fastForward(60_001); expect(fixture.calls.length).toBe(calls);
  await page.clock.fastForward(60_001); await expect(panel.getByText('冷却后新版本文档', { exact: true })).toBeVisible();
  expect(fixture.calls.every((call) => call.startsWith('GET '))).toBe(true);
});

test('compact Notion content shows one true count one title link nonempty groups and necessary sync recovery', async ({ page }) => {
  const fixture = await setup(page); const { dialog } = await openCalendar(page); await dialog.getByRole('tab', { name: 'Notion', exact: true }).click();
  const panel = dialog.getByRole('tabpanel'); await expect(panel.getByRole('listitem')).toHaveCount(2); await expect(panel.locator('.calendar-popup__card-body')).toHaveAttribute('aria-busy', 'false');
  await expect(panel.locator('[data-notion-count]')).toHaveCount(1); await expect(panel.locator('[data-notion-count]')).toHaveText('2 篇');
  await expect(panel.locator('.calendar-popup__notion-group h4')).toHaveText(['当日创建', '今天编辑']);
  await expect(panel.getByRole('link')).toHaveCount(1); await expect(panel.getByRole('link')).toHaveAccessibleName('在新标签中打开 Notion 文档：今日创建的文档');
  await expect(panel.getByText(/最近同步|列表来自当前连接器|在 Notion 中打开/)).toHaveCount(0);
  await dialog.getByRole('gridcell', { name: /2026.*9.*29/ }).click();
  await expect(panel.locator('.calendar-popup__notion-group')).toHaveCount(1); await expect(panel.locator('[data-notion-count]')).toHaveText('1 篇');
  fixture.state('partial'); fixture.policy('syncing'); await panel.getByRole('button', { name: '刷新', exact: true }).click();
  await expect(panel.locator('[data-notion-count]')).toHaveText('已知 0 篇'); await expect(panel.locator('.calendar-popup__notion-group')).toHaveCount(0);
  await expect(panel.getByRole('status')).toHaveCount(1); await expect(panel.getByRole('button', { name: '管理连接器', exact: true })).toHaveCount(1);
  await expect(panel.getByText('该日没有创建的文档。')).toHaveCount(0);
});

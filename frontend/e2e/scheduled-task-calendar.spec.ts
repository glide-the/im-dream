// [Sync] 2026-10-07: edit v3 repeat presets, custom cadence, Chat mode and model through the production task DTO.
// [Sync] 2026-10-07: make the canonical Chat Thread handoff phase explicit before checking its scoped navigation cancellation.
// [Input] Production Calendar and shared API-boundary fixture.
// [Output] Complete provider-free task lifecycle regression with mutually exclusive tabs.
// [Pos] Calendar technical browser journey in frontend/e2e.
// [Sync] 2026-10-05: preserve task journeys while checking one visible paper, original diary access and scroll ownership.
// [Sync] 2026-10-06: distinguish the unchanged month border/shadow from the borderless active right paper and RESULT spacing.
import { expect, test } from '@playwright/test';
import { installFixtures, openCalendar, openMore, readFloatingPaperSafety, expectFloatingPaperSafety, TARGET_THREAD_ID, TASK_ID } from './fixtures/calendarHarness';
import type { TaskRule } from './fixtures/calendarHarness';
test.use({ channel: 'chrome' });
test.describe.configure({ mode: 'serial' });

test('desktop journey follows the reviewed task-before-diary lifecycle', async ({ page }, testInfo) => {
  const fixture = await installFixtures(page, { firstRunOutcome: 'server_error' });
  const { dialog } = await openCalendar(page);

  const workspace = dialog.locator('.calendar-popup__workspace');
  const stack = workspace.locator('.calendar-popup__workspace-scroll');
  const taskSection = stack.locator(':scope > .calendar-popup__task-section');
  const diarySection = stack.locator(':scope > .calendar-popup__diary-section');
  await expect(taskSection.locator('.calendar-popup__card-count')).toHaveText('1 项');
  await expect(diarySection).toBeHidden();
  await expect(dialog.getByRole('tabpanel')).toHaveCount(1);
  await dialog.getByRole('tab', { name: '日记', exact: true }).click();
  await expect(diarySection.locator('.calendar-popup__card-count')).toHaveText('1 篇');
  await expect(dialog.getByText('普通日历笔记仍然可见')).toBeVisible();
  await dialog.getByRole('tab', { name: '定时任务', exact: true }).click();
  await expect(dialog.getByText('晨间复盘')).toBeVisible();
  await expect(dialog.locator('.calendar-popup__date-summary')).toHaveCount(0);
  const closeBox = await dialog.getByRole('button', { name: '关闭' }).boundingBox();
  const paperBoxes = await Promise.all([
    dialog.locator('.calendar-popup__calendar').boundingBox(), workspace.boundingBox(),
  ]);
  expect(closeBox && paperBoxes.every((paper) => paper && (
    closeBox.x + closeBox.width <= paper.x || paper.x + paper.width <= closeBox.x
    || closeBox.y + closeBox.height <= paper.y || paper.y + paper.height <= closeBox.y
  ))).toBeTruthy();
  const surfaces = await dialog.evaluate((element) => {
    const dialogStyle = getComputedStyle(element);
    const workspaceElement = element.querySelector('.calendar-popup__workspace');
    if (!(workspaceElement instanceof HTMLElement)) throw new Error('calendar workspace is missing');
    const workspaceStyle = getComputedStyle(workspaceElement);
    const papers = Array.from(element.querySelectorAll('.calendar-popup__calendar, .calendar-popup__section:not([hidden])')).map((paper) => {
      const style = getComputedStyle(paper);
      return { month: paper.classList.contains('calendar-popup__calendar'), borderWidth: style.borderTopWidth,
        background: style.backgroundColor, boxShadow: style.boxShadow, radius: style.borderRadius, corners: [style.borderTopLeftRadius, style.borderTopRightRadius, style.borderBottomRightRadius, style.borderBottomLeftRadius] };
    });
    const task = element.querySelector('.calendar-popup__task');
    return {
      dialog: {
        borderWidth: dialogStyle.borderTopWidth,
        background: dialogStyle.backgroundColor,
        boxShadow: dialogStyle.boxShadow,
      },
      workspace: {
        borderWidth: workspaceStyle.borderTopWidth,
        background: workspaceStyle.backgroundColor,
        boxShadow: workspaceStyle.boxShadow,
      },
      papers,
      task: task ? {
        borderWidth: getComputedStyle(task).borderTopWidth,
        background: getComputedStyle(task).backgroundColor,
        boxShadow: getComputedStyle(task).boxShadow,
      } : null,
    };
  });
  expect(surfaces.dialog).toEqual({ borderWidth: '0px', background: 'rgba(0, 0, 0, 0)', boxShadow: 'none' });
  expect(surfaces.workspace.borderWidth).toBe('0px');
  expect(surfaces.workspace.background).not.toBe('rgba(0, 0, 0, 0)'); expect(surfaces.workspace.boxShadow).not.toBe('none');
  expect(surfaces.papers).toHaveLength(2);
  const monthSurface = surfaces.papers.find((paperStyle) => paperStyle.month)!;
  expect(monthSurface.borderWidth).not.toBe('0px'); expect(monthSurface.boxShadow).not.toBe('none');
  const rightSurface = surfaces.papers.find((paperStyle) => !paperStyle.month)!;
  expect(rightSurface).toMatchObject({ borderWidth: '0px', boxShadow: 'none', corners: ['0px', '0px', '24px', '24px'] });
  expect(rightSurface.background).not.toBe('rgba(0, 0, 0, 0)');
  expect(surfaces.task).toEqual({ borderWidth: '0px', background: 'rgba(0, 0, 0, 0)', boxShadow: 'none' });
  const hiddenTitle = await dialog.locator('.modal-title--default').evaluate((element) => {
    const style = getComputedStyle(element);
    return { position: style.position, width: style.width, height: style.height, clip: style.clip };
  });
  expect(hiddenTitle).toEqual({ position: 'absolute', width: '1px', height: '1px', clip: 'rect(0px, 0px, 0px, 0px)' });
  const desktopSafety = await readFloatingPaperSafety(dialog);
  expect(desktopSafety.scrollOwner).toBe('stack');
  expect(desktopSafety.fixedCalendarDelta).toBeLessThanOrEqual(1);
  expectFloatingPaperSafety(desktopSafety, { side: 36, bottom: 56 });
  await expect(dialog.getByRole('gridcell', { name: /2026.*9.*29/ })).not.toHaveClass(/calendar-popup__day--has-entry/);

  const card = dialog.locator('.calendar-popup__task').first();
  await expect(taskSection.getByPlaceholder('安排任务')).toBeVisible();
  const editButton = card.getByRole('button', { name: /编辑/ });
  await editButton.click();
  const editor = page.getByRole('dialog', { name: /编辑“/ });
  await editor.getByLabel('标题').fill('新的每日复盘');
  await editor.getByLabel('执行提示词').fill('整理新的笔记');
  await editor.getByRole('button', { name: '保存' }).click();
  await expect(editor.getByRole('alert').filter({ hasText: '最新已生效配置' })).toContainText('服务端更新后的复盘');
  await expect(editor.getByLabel('标题')).toHaveValue('新的每日复盘');
  await editor.getByRole('button', { name: '保存' }).click();
  await expect(editor).toBeHidden();
  await expect(editButton).toBeFocused();
  await expect(card).toContainText('新的每日复盘');
  expect(fixture.getDefinitionRequests().slice(0, 2)).toEqual([
    { action: 'edit', revision: 1 }, { action: 'edit', revision: 2 },
  ]);

  await openMore(card);
  await card.getByRole('menuitem', { name: '暂停' }).click();
  await expect(card).toContainText('已暂停');
  await openMore(card);
  await card.getByRole('menuitem', { name: '恢复' }).click();
  await expect(card).toContainText('9月30日');

  await openMore(card);
  await card.getByRole('menuitem', { name: '立即运行' }).click();
  await expect(card.getByRole('alert').filter({ hasText: '任务更新失败' })).toBeVisible();
  await openMore(card);
  await card.getByRole('menuitem', { name: '立即运行' }).click();
  expect(fixture.getManualRequestKeys()).toHaveLength(2);
  expect(fixture.getManualRequestKeys()[1]).not.toBe(fixture.getManualRequestKeys()[0]);

  await openMore(card);
  await card.getByRole('menuitem', { name: /历史/ }).click();
  const historyDialog = page.getByRole('dialog', { name: /执行历史/ });
  await expect(historyDialog).toContainText('手动执行');
  await expect(historyDialog.getByRole('button', { name: /打开会话/ })).toBeVisible();
  await historyDialog.getByRole('button', { name: '关闭面板' }).click();
  await expect(card.getByRole('button', { name: /更多操作/ })).toBeFocused();

  await openMore(card);
  await card.getByRole('menuitem', { name: /删除/ }).click();
  const undo = dialog.locator('.calendar-popup__undo-row');
  await expect(undo).toContainText('已删除“新的每日复盘”');
  await undo.getByRole('button', { name: /撤销删除/ }).click();
  const restored = dialog.locator('.calendar-popup__task').first();
  await expect(restored.getByLabel('已启用')).toBeVisible();
  await testInfo.attach('calendar-floating-wide', {
    body: await page.screenshot({ fullPage: true }), contentType: 'image/png',
  });

  await restored.locator('.calendar-popup__task-open').click();
  await expect(dialog.getByRole('heading', { name: '定时任务执行完成' })).toBeVisible();
  await expect(dialog.getByText('已整理今天的笔记。')).toBeVisible();
  await expect(dialog.locator('.calendar-popup__task-result > header')).toHaveCSS('border-bottom-width', '0px');
  await expect(dialog.locator('.calendar-popup__task-result > footer')).toHaveCSS('border-top-width', '0px');
  await expect(dialog.getByText('这是一条更晚的普通回复，不能作为定时任务结果。')).toHaveCount(0);
  fixture.beginThreadHandoff();
  await dialog.getByRole('button', { name: '打开会话' }).click();
  await expect(page).toHaveURL(/\/story-workspace\/chat$/);
  await expect(dialog).toBeHidden();
  await expect.poll(() => fixture.getTargetThreadRequests().some((item) => item.includes(TARGET_THREAD_ID))).toBe(true);
  const handoffAborts = fixture.getThreadHandoffAborts();
  await testInfo.attach('calendar-thread-handoff-abort-evidence', {
    body: Buffer.from(JSON.stringify({ count: handoffAborts.length, handoffAborts }, null, 2)),
    contentType: 'application/json',
  });
  for (const abort of handoffAborts) {
    expect(abort).toMatchObject({ method: 'GET', path: '/api/claude-agent/threads', query: '?limit=21',
      error: 'net::ERR_ABORTED', pagePath: '/story-workspace/chat', refererPath: '/story-workspace/chat' });
  }
  fixture.endThreadHandoff();
  expect(fixture.getUnexpected()).toEqual([]);
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= document.documentElement.clientWidth + 1)).toBeTruthy();
});

test('mobile exhausted state keeps unknown execution safe and menu keyboard-operable', async ({ page }, testInfo) => {
  const fixture = await installFixtures(page, {
    taskStatus: 'exhausted', initialTriggerStatus: 'state_unknown', initialTriggerHasThread: true,
    firstRunOutcome: 'success',
  });
  const { dialog } = await openCalendar(page, { width: 390, height: 844 });
  const card = dialog.locator('.calendar-popup__task').first();

  await expect(card.getByRole('button', { name: /编辑/ })).toHaveCount(0);
  const attention = dialog.getByRole('button', { name: '有 1 项需处理' });
  await attention.click();
  await expect(card).toBeFocused();

  const more = card.getByRole('button', { name: /更多操作/ });
  await more.click();
  const openItem = card.getByRole('menuitem', { name: /打开会话/ });
  const historyItem = card.getByRole('menuitem', { name: /历史/ });
  await expect(openItem).toBeFocused();
  await page.keyboard.press('ArrowDown');
  await expect(historyItem).toBeFocused();
  await historyItem.click();
  const historyDialog = page.getByRole('dialog', { name: /执行历史/ });
  await expect(historyDialog.getByRole('button', { name: /打开会话/ })).toBeVisible();
  await page.keyboard.press('Escape');
  await expect(historyDialog).toBeHidden();
  await expect(more).toBeFocused();

  const calendarBox = await dialog.locator('.calendar-popup__calendar').boundingBox();
  const taskBox = await dialog.locator('.calendar-popup__task-section').boundingBox();
  expect(calendarBox && taskBox && taskBox.y > calendarBox.y + calendarBox.height).toBeTruthy();
  await expect(dialog.getByRole('tabpanel')).toHaveCount(1);
  const mobileSafety = await readFloatingPaperSafety(dialog);
  expect(mobileSafety.scrollOwner).toBe('layout');
  expectFloatingPaperSafety(mobileSafety, { side: 16, bottom: 28 });
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= document.documentElement.clientWidth + 1)).toBeTruthy();
  await testInfo.attach('calendar-floating-mobile', {
    body: await page.screenshot({ fullPage: true }), contentType: 'image/png',
  });
  expect(fixture.getUnexpected()).toEqual([]);
});

test('tablet breakpoint keeps one scroll owner and switches cleanly to two columns', async ({ page }, testInfo) => {
  const fixture = await installFixtures(page, { firstRunOutcome: 'success' });
  const { dialog } = await openCalendar(page, { width: 1024, height: 768 });
  const calendar = dialog.locator('.calendar-popup__calendar');
  const taskSection = dialog.locator('.calendar-popup__task-section');
  const singleColumnBoxes = await Promise.all([calendar.boundingBox(), taskSection.boundingBox()]);
  expect(singleColumnBoxes[0] && singleColumnBoxes[1]
    && singleColumnBoxes[1].y > singleColumnBoxes[0].y + singleColumnBoxes[0].height).toBeTruthy();
  const closeBox = await dialog.getByRole('button', { name: '关闭' }).boundingBox();
  expect(closeBox && singleColumnBoxes.every((paper) => paper && (
    closeBox.x + closeBox.width <= paper.x || paper.x + paper.width <= closeBox.x
    || closeBox.y + closeBox.height <= paper.y || paper.y + paper.height <= closeBox.y
  ))).toBeTruthy();
  const scrollOwners = await dialog.evaluate((element) => {
    const content = element.querySelector(':scope > .modal-content--default');
    const layout = element.querySelector('.calendar-popup');
    const stack = element.querySelector('.calendar-popup__workspace-scroll');
    if (!(content instanceof HTMLElement) || !(layout instanceof HTMLElement) || !(stack instanceof HTMLElement)) {
      throw new Error('calendar scroll structure is incomplete');
    }
    return {
      content: getComputedStyle(content).overflowY,
      layout: getComputedStyle(layout).overflowY,
      stack: getComputedStyle(stack).overflowY,
    };
  });
  expect(scrollOwners).toEqual({ content: 'hidden', layout: 'auto', stack: 'visible' });
  const tabletSafety = await readFloatingPaperSafety(dialog);
  expect(tabletSafety.scrollOwner).toBe('layout');
  expectFloatingPaperSafety(tabletSafety, { side: 20, bottom: 36 });

  await page.setViewportSize({ width: 1025, height: 768 });
  const twoColumnBoxes = await Promise.all([calendar.boundingBox(), taskSection.boundingBox()]);
  expect(twoColumnBoxes[0] && twoColumnBoxes[1]
    && twoColumnBoxes[1].x > twoColumnBoxes[0].x + twoColumnBoxes[0].width
    && twoColumnBoxes[1].y > twoColumnBoxes[0].y).toBeTruthy();
  const desktopScrollOwners = await dialog.evaluate((element) => ({
    layout: getComputedStyle(element.querySelector('.calendar-popup') as HTMLElement).overflowY,
    stack: getComputedStyle(element.querySelector('.calendar-popup__task-section') as HTMLElement).overflowY,
  }));
  expect(desktopScrollOwners).toEqual({ layout: 'hidden', stack: 'auto' });
  const contentFits = await dialog.locator('.calendar-popup').evaluate((element) =>
    element.scrollWidth <= element.clientWidth + 1);
  expect(contentFits).toBeTruthy();
  await testInfo.attach('calendar-floating-tablet-boundary', {
    body: await page.screenshot({ fullPage: true }), contentType: 'image/png',
  });

  await page.setViewportSize({ width: 1440, height: 480 });
  const shortViewportDialogBox = await dialog.boundingBox();
  const shortViewportCalendarTop = (await calendar.boundingBox())?.y;
  const monthScroll = await calendar.evaluate((element) => {
    element.scrollTop = element.scrollHeight;
    return {
      overflowY: getComputedStyle(element).overflowY,
      maxScrollTop: element.scrollHeight - element.clientHeight,
      reachedBottom: Math.abs(element.scrollTop - (element.scrollHeight - element.clientHeight)) <= 1,
    };
  });
  expect(monthScroll.overflowY).toBe('auto');
  expect(monthScroll.maxScrollTop).toBeGreaterThan(0);
  expect(monthScroll.reachedBottom).toBe(true);
  await expect(calendar.getByRole('gridcell', { name: /2026.*9.*30/ })).toBeVisible();
  expect((await calendar.boundingBox())?.y).toBeCloseTo(shortViewportCalendarTop ?? 0, 0);
  expect(shortViewportDialogBox && shortViewportDialogBox.height <= 416 + 1).toBeTruthy();
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= document.documentElement.clientWidth + 1)).toBeTruthy();
  expect(fixture.getUnexpected()).toEqual([]);
});

test('unknown manual-run response reuses one request key before creating a second run', async ({ page }) => {
  const fixture = await installFixtures(page, { firstRunOutcome: 'network_unknown' });
  const { dialog } = await openCalendar(page);
  const card = dialog.locator('.calendar-popup__task').first();

  await openMore(card);
  await card.getByRole('menuitem', { name: '立即运行' }).click();
  await expect(card.getByRole('alert').filter({ hasText: '正在确认是否已创建本次执行' })).toBeVisible();
  await card.getByRole('button', { name: '核查运行请求' }).click();
  expect(fixture.getManualRequestKeys()).toHaveLength(2);
  expect(fixture.getManualRequestKeys()[1]).toBe(fixture.getManualRequestKeys()[0]);
  expect(fixture.getUnexpected()).toEqual([]);
});

test('task-free date keeps an independent empty task card beside diary content', async ({ page }) => {
  const fixture = await installFixtures(page, { empty: true, firstRunOutcome: 'success' });
  const { dialog } = await openCalendar(page);
  const taskSection = dialog.locator('.calendar-popup__task-section');
  await expect(taskSection).toHaveCount(1);
  await expect(taskSection.getByRole('heading', { name: '今天的定时任务' })).toBeVisible();
  await expect(taskSection.locator('.calendar-popup__card-count')).toHaveText('0 项');
  await expect(taskSection.getByText('这一天没有定时任务。')).toBeVisible();
  await dialog.getByRole('tab', { name: '日记', exact: true }).click();
  await expect(dialog.getByRole('heading', { name: '今天的日记' })).toBeVisible();
  await expect(dialog.getByText('普通日历笔记仍然可见')).toBeVisible();
  expect(fixture.getUnexpected()).toEqual([]);
});

test('arrange task hands an editable unsent draft to a fresh canonical Chat', async ({ page }) => {
  const fixture = await installFixtures(page, { firstRunOutcome: 'success' });
  const { dialog } = await openCalendar(page);
  await dialog.getByPlaceholder('安排任务').fill('每天早上九点整理昨天的日记');
  await dialog.getByRole('button', { name: '在 Chat 中继续' }).click();
  await expect(page).toHaveURL(/\/story-workspace\/chat$/);
  await expect(page.getByRole('textbox', { name: '聊天输入' })).toHaveText('每天早上九点整理昨天的日记');
  await expect(page.locator('[data-chat-scroll-region="messages"]').getByText('每天早上九点整理昨天的日记', { exact: true })).toHaveCount(0);
  expect(fixture.getUnexpected()).toEqual([]);
});

test('task read failure stays inside its card while diary remains actionable', async ({ page }) => {
  const fixture = await installFixtures(page, {
    dayStartsUnavailable: true,
    firstRunOutcome: 'success',
  });
  const { dialog } = await openCalendar(page);
  const taskSection = dialog.locator('.calendar-popup__task-section');
  const diarySection = dialog.locator('.calendar-popup__diary-section');
  await expect(taskSection.getByRole('alert')).toContainText('任务暂不可用。');
  await dialog.getByRole('tab', { name: '日记', exact: true }).click();
  await expect(diarySection.getByText('普通日历笔记仍然可见')).toBeVisible();
  await expect(diarySection.getByRole('button', { name: '打开: 普通日历笔记仍然可见' })).toBeEnabled();
  await expect(diarySection.getByRole('button', { name: '删除: 普通日历笔记仍然可见' })).toBeEnabled();
  await dialog.getByRole('tab', { name: '定时任务', exact: true }).click();
  fixture.allowDayReads();
  await taskSection.getByRole('button', { name: '重试' }).click();
  await expect(taskSection.getByText('晨间复盘')).toBeVisible();
  await dialog.getByRole('tab', { name: '日记', exact: true }).click();
  await expect(diarySection.getByText('普通日历笔记仍然可见')).toBeVisible();
  expect(fixture.getUnexpected()).toEqual([]);
});

test('active execution refreshes to a terminal result and history loads older pages by cursor', async ({ page }) => {
  const fixture = await installFixtures(page, {
    initialTriggerStatus: 'running', initialTriggerHasThread: true,
    historyCount: 21, firstRunOutcome: 'success',
  });
  const { dialog } = await openCalendar(page);
  const card = dialog.locator('.calendar-popup__task').first();

  await expect(card).toContainText('执行中');
  fixture.completeRunningOnNextDayRead();
  await expect(card).toHaveClass(/calendar-popup__task--succeeded/, { timeout: 7_000 });
  expect(fixture.getDayReadCount()).toBeGreaterThanOrEqual(2);
  const settledReadCount = fixture.getDayReadCount();
  await page.waitForTimeout(2_300);
  expect(fixture.getDayReadCount()).toBe(settledReadCount);

  await openMore(card);
  await card.getByRole('menuitem', { name: /历史/ }).click();
  const history = page.getByRole('dialog', { name: /执行历史/ }).locator('.calendar-popup__history');
  await expect(history.getByRole('listitem')).toHaveCount(20);
  await history.getByRole('button', { name: /加载更早记录/ }).click();
  await expect(history.getByRole('listitem')).toHaveCount(21);
  await expect(history.getByRole('button', { name: /加载更早记录/ })).toHaveCount(0);
  const safety = await readFloatingPaperSafety(dialog);
  // History is rendered in its own modal; this short fixture does not need to
  // overflow the underlying task/diary stack to prove cursor pagination.
  expect(safety.maxScrollTop).toBeGreaterThanOrEqual(0);
  expect(safety.scrollOwner).toBe('stack');
  expect(safety.fixedCalendarDelta).toBeLessThanOrEqual(1);
  expectFloatingPaperSafety(safety, { side: 36, bottom: 56 });
  expect(fixture.getHistoryRequests().some((search) => search.includes('before_created_at='))).toBe(true);
  expect(fixture.getUnexpected()).toEqual([]);
});

test('edit keeps the desired draft and explains repeated or missing daylight-saving times', async ({ page }) => {
  const fixture = await installFixtures(page, {
    firstEditConflict: false,
    editErrorCodes: ['SCHEDULE_OFFSET_REQUIRED', 'SCHEDULE_LOCAL_TIME_MISSING'],
    firstRunOutcome: 'success',
  });
  const { dialog } = await openCalendar(page);
  const card = dialog.locator('.calendar-popup__task').first();

  await card.getByRole('button', { name: /编辑/ }).click();
  const editor = page.getByRole('dialog', { name: /编辑/ });
  await editor.getByLabel('重复').selectOption('custom');
  await editor.getByRole('button', { name: /高级日程/ }).click();
  let ruleEditor = page.getByRole('dialog', { name: '高级日程' });
  await ruleEditor.getByLabel('自定义日程').selectOption('once');
  await ruleEditor.getByLabel('日期').fill('2026-11-01');
  await ruleEditor.getByLabel('时间').fill('01:30');
  await ruleEditor.getByLabel('时区').fill('America/New_York');
  await ruleEditor.getByRole('button', { name: '应用' }).click();
  await editor.getByRole('button', { name: '保存' }).click();
  await expect(editor.getByRole('alert')).toContainText('该当地时间因时钟调整会出现两次');
  await editor.getByRole('button', { name: /高级日程/ }).click();
  ruleEditor = page.getByRole('dialog', { name: '高级日程' });
  await expect(ruleEditor.getByLabel('时间')).toHaveValue('01:30');

  await ruleEditor.getByLabel('日期').fill('2026-03-08');
  await ruleEditor.getByLabel('时间').fill('02:30');
  await ruleEditor.getByRole('button', { name: '应用' }).click();
  await editor.getByRole('button', { name: '保存' }).click();
  await expect(editor.getByRole('alert')).toContainText('这个当地时间因时钟调整而不存在');
  await editor.getByRole('button', { name: /高级日程/ }).click();
  ruleEditor = page.getByRole('dialog', { name: '高级日程' });
  await expect(ruleEditor.getByLabel('时间')).toHaveValue('02:30');

  await ruleEditor.getByLabel('时间').fill('03:30');
  await ruleEditor.getByRole('button', { name: '应用' }).click();
  await editor.getByRole('button', { name: '保存' }).click();
  await expect(editor).toBeHidden();
  await expect(card).toContainText('2026-03-08 · 03:30');
  expect(fixture.getEditBodies().slice(0, 2).map((body) => (body.rule as TaskRule).kind === 'once'
    ? (body.rule as Extract<TaskRule, { kind: 'once' }>).selected_offset_minutes : 'daily')).toEqual([null, null]);
  expect(fixture.getUnexpected()).toEqual([]);
});

test('edit changes a task to every ten minutes through the production DTO', async ({ page }) => {
  const fixture = await installFixtures(page, { firstEditConflict: false, firstRunOutcome: 'success' });
  const { dialog } = await openCalendar(page);
  const card = dialog.locator('.calendar-popup__task').first();

  await card.getByRole('button', { name: /编辑/ }).click();
  const editor = page.getByRole('dialog', { name: /编辑/ });
  await editor.getByLabel('重复').selectOption('custom');
  await editor.getByRole('button', { name: /高级日程/ }).click();
  const ruleEditor = page.getByRole('dialog', { name: '高级日程' });
  await ruleEditor.getByLabel('自定义日程').selectOption('interval');
  await ruleEditor.getByLabel('每隔（分钟）').fill('10');
  await ruleEditor.getByRole('button', { name: '应用' }).click();
  await editor.getByRole('button', { name: '保存' }).click();

  await expect(editor).toBeHidden();
  await expect(card).toContainText('每隔 10 分钟');
  expect(fixture.getEditBodies().at(-1)?.rule).toEqual({
    kind: 'interval', interval_minutes: 10, time_zone: 'UTC',
  });
  expect(fixture.getUnexpected()).toEqual([]);
});

test('repeat presets and advanced Chat/model choices submit the v3 production DTO', async ({ page }) => {
  const fixture = await installFixtures(page, { firstEditConflict: false, firstRunOutcome: 'success' });
  const { dialog } = await openCalendar(page);
  const card = dialog.locator('.calendar-popup__task').first();

  await card.getByRole('button', { name: /编辑/ }).click();
  let editor = page.getByRole('dialog', { name: /编辑/ });
  const repeat = editor.getByLabel('重复');
  await expect(repeat.locator('option')).toHaveText(['每小时', '每天', '工作日', '每周', '自定义']);
  await repeat.selectOption('hourly');
  await editor.getByRole('button', { name: '高级', exact: true }).click();
  await editor.getByLabel(/每次运行时都开启新聊天/).check();
  await editor.getByLabel('模型').selectOption('dream-fast');
  await editor.getByRole('button', { name: '保存' }).click();
  await expect(editor).toBeHidden();
  expect(fixture.getEditBodies().at(-1)).toMatchObject({
    rule: { kind: 'hourly', interval_hours: 1, minute: 0, time_zone: 'UTC' },
    run_thread_mode: 'new_thread_each_run', model_alias: 'dream-fast',
  });

  await card.getByRole('button', { name: /编辑/ }).click();
  editor = page.getByRole('dialog', { name: /编辑/ });
  await editor.getByLabel('重复').selectOption('workdays');
  await editor.getByRole('button', { name: '保存' }).click();
  expect(fixture.getEditBodies().at(-1)).toMatchObject({
    rule: { kind: 'weekly', weekdays: ['MO', 'TU', 'WE', 'TH', 'FR'], local_time: '09:00', time_zone: 'UTC' },
    run_thread_mode: 'new_thread_each_run', model_alias: 'dream-fast',
  });

  await card.getByRole('button', { name: /编辑/ }).click();
  editor = page.getByRole('dialog', { name: /编辑/ });
  await editor.getByLabel('重复').selectOption('weekly');
  await editor.getByRole('button', { name: '保存' }).click();
  expect(fixture.getEditBodies().at(-1)?.rule).toEqual({
    kind: 'weekly', weekdays: ['MO'], local_time: '09:00', time_zone: 'UTC',
  });
  expect(fixture.getUnexpected()).toEqual([]);
});


for (const width of [1440, 390]) {
  test(`floating task menu remains reachable on short and last long rows at ${width}px`, async ({ page }, testInfo) => {
    test.setTimeout(120_000);
    const fixture = await installFixtures(page, { firstRunOutcome: 'success', firstEditConflict: false, initialTriggerStatus: 'succeeded' });
    const publicActions: string[] = [];
    page.on('request', (request) => {
      const url = new URL(request.url());
      if (request.method() === 'POST' && url.pathname.startsWith('/api/claude-agent/scheduled-tasks/')) publicActions.push(`${request.method()} ${url.pathname}`);
    });
    const { dialog } = await openCalendar(page, { width, height: 844 });
    const workspace = dialog.locator('.calendar-popup__workspace');
    const heights: unknown[] = [];
    for (const theme of ['light', 'dark'] as const) {
      await page.emulateMedia({ colorScheme: theme });
      await page.evaluate((value) => document.documentElement.setAttribute('data-theme', value), theme);
      for (const count of [1, 20]) {
        fixture.setTaskCount(count);
        await dialog.getByRole('gridcell', { name: count === 1 ? /2026.*9.*28/ : /2026.*9.*29/ }).click();
        const rows = dialog.locator('.calendar-popup__task'); await expect(rows).toHaveCount(count);
        const card = rows.last(); const more = card.getByRole('button', { name: /更多操作/ });
        await card.locator('.calendar-popup__task-open').focus(); await page.keyboard.press('Tab');
        await expect(card.getByRole('button', { name: /编辑/ })).toBeFocused();
        await page.keyboard.press('Tab'); await expect(more).toBeFocused();
        const hitBefore = await more.boundingBox(); expect(hitBefore!.width).toBeGreaterThanOrEqual(42); expect(hitBefore!.height).toBeGreaterThanOrEqual(42);
        const closedHeight = (await workspace.boundingBox())!.height;
        await openMore(card); const menu = card.getByRole('menu'); await expect(menu).toHaveCSS('position', 'static');
        await expect(menu.getByRole('menuitem', { name: '立即运行', exact: true })).toBeFocused();
        expect(await menu.evaluate((element) => element.contains(document.activeElement))).toBe(true);
        expect(await card.evaluate((element) => {
          const menu = element.querySelector('[role=menu]'); return Boolean(menu && element.querySelector('.calendar-popup__more-wrap')?.contains(menu));
        })).toBe(true);
        const openHeight = (await workspace.boundingBox())!.height;
        if (count === 1) expect(openHeight).toBeGreaterThan(closedHeight);
        const hitOpen = await more.boundingBox(); expect(hitOpen!.width).toBeCloseTo(hitBefore!.width, 0); expect(hitOpen!.height).toBeCloseTo(hitBefore!.height, 0);
        await menu.getByRole('menuitem', { name: '立即运行', exact: true }).press('End');
        const remove = menu.getByRole('menuitem', { name: '删除', exact: true }); await expect(remove).toBeFocused();
        const removeBox = await remove.boundingBox();
        expect(removeBox && removeBox.x >= 0 && removeBox.x + removeBox.width <= width
          && removeBox.y >= 0 && removeBox.y + removeBox.height <= 844).toBeTruthy();
        await testInfo.attach(`calendar-tasks-${theme}-${width}-${count}-menu-open`, { body: await page.screenshot(), contentType: 'image/png' });
        await page.keyboard.press('Escape'); await expect(menu).toHaveCount(0); await expect(more).toBeFocused();
        await expect.poll(async () => (await workspace.boundingBox())!.height).toBeCloseTo(closedHeight, 0);
        await openMore(card); await card.getByRole('menuitem', { name: /历史/ }).click();
        const history = page.getByRole('dialog', { name: /执行历史/ }); await expect(history).toBeVisible();
        await page.keyboard.press('Escape'); await expect(history).toBeHidden(); await expect(more).toBeFocused();
        await card.getByRole('button', { name: /编辑/ }).click(); const editor = page.getByRole('dialog', { name: /编辑“/ });
        await expect(editor.getByLabel('标题')).toBeFocused(); await page.keyboard.press('Escape');
        await expect(editor).toBeHidden(); await expect(card.getByRole('button', { name: /编辑/ })).toBeFocused();
        // The last actual menu item invokes the existing public mutation DTO, then the existing undo entry restores it.
        await openMore(card); await card.getByRole('menuitem', { name: '删除', exact: true }).click();
        await expect(dialog.locator('.calendar-popup__undo-row')).toHaveCount(1);
        expect(publicActions).toContain(`POST /api/claude-agent/scheduled-tasks/${TASK_ID}/delete`);
        await dialog.getByRole('button', { name: /撤销删除/ }).click(); await expect(rows).toHaveCount(count);
        expect(publicActions).toContain(`POST /api/claude-agent/scheduled-tasks/${TASK_ID}/restore`);
        heights.push({ theme, count, closedHeight, openHeight, finalHeight: (await workspace.boundingBox())!.height });
        const safety = await readFloatingPaperSafety(dialog);
        expectFloatingPaperSafety(safety, width > 1024 ? { side: 36, bottom: 56 } : { side: 16, bottom: 28 });
      }
    }
    expect(fixture.getUnexpected()).toEqual([]);
    await testInfo.attach(`calendar-tasks-${width}-menu-height-evidence`, {
      body: Buffer.from(JSON.stringify({ heights, publicActions }, null, 2)), contentType: 'application/json',
    });
  });
}

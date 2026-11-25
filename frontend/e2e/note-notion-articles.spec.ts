// [Input] Actual Writing route, installed Chrome, isolated session/connector HTTP fixtures.
// [Output] Actual card/input geometry, explicit Calendar confirmation, cancellation and title-to-link identity across two articles, clipboard, undo and narrow-screen evidence.
// Changes only an intercepted journal DTO. Project/Episode artifacts, Run, Hook, model and real accounts are outside this journey.
// [Pos] Provider-free browser journeys. All writes terminate at the fixture boundary.
import {test, expect, type Locator, type Page} from '@playwright/test';
import {installFixtures} from './fixtures/calendarHarness';

test.use({channel: 'chrome'});
const base = process.env.E2E_WEB_BASE;
if (!base) throw Error('E2E_WEB_BASE_REQUIRED');
const pageId = '40b30b7547c380cd9930c384ab35023c';
const article = `https://app.notion.com/p/${pageId}?v=40b30b7547c380f18b8c000c207f918f&source=copy_link#42130b7547c3800aad38daaa6f003a8a`;
const before = '会议资料', after = '下周讨论';
const original = before + article + after;
const source = 'current-session';
const date = '2026-09-28T12:00:00Z';

async function openWriting(page: Page, initial: string, width = 1220) {
  await installFixtures(page);
  const pageErrors: string[] = [];
  page.on('pageerror', error => pageErrors.push(error.stack ?? error.message));
  await page.addInitScript(() => {
    localStorage.setItem('ink-language', 'zh');
    sessionStorage.setItem('ink-dream-web-oauth', JSON.stringify({refresh_token: 'isolated-writing-refresh'}));
  });
  await page.route('**/auth/refresh', route => route.fulfill({json: {
    access_token: 'writing-test', refresh_token: 'isolated-writing-refresh', expires_at: Date.UTC(2035, 0, 1),
  }}));
  await page.route('**/auth/session', route => route.fulfill({json: {user: {
    id: '20260929', email: 'writing@example.test', display_name: 'Writing', avatar_url: null,
    role: 'user', created_at: date,
  }}}));
  await page.route('**/api/preferences', route => route.fulfill({json: {
    selected_state: 'happy', timezone: 'UTC', first_login_completed: true,
  }}));
  const entry = {id: source, createdAt: date, selectedState: 'happy',
    cells: [{id: 'old-text', type: 'text', content: initial}], commentors: [], tasks: [],
    weightPath: [], overlappedPhrases: [], notFoundPhrases: []};
  let saved = entry;
  const writes: typeof entry[] = [];
  let rejectSave = false;
  const note = {id: source, created_at: date, updated_at: date, labels: []};
  await page.route(/\/api\/sessions(?:\?.*)?$/, route => {
    if (route.request().method() === 'POST') {
      const body = route.request().postDataJSON();
      expect(body.session_id).toBe(source);
      if (rejectSave) return route.fulfill({status:503, json:{detail:'temporary save failure'}});
      saved = body.editor_state;
      writes.push(saved);
      return route.fulfill({json: {success: true}});
    }
    return route.fulfill({json: {sessions: [note]}});
  });
  await page.route('**/api/sessions/' + source, route => route.fulfill({json: {...note, editor_state: saved}}));
  const reads: string[] = [];
  let failure = '';
  await page.route('**/api/connectors/notion/articles/*', route => {
    const path = new URL(route.request().url()).pathname;
    reads.push(path);
    expect(path).toBe('/api/connectors/notion/articles/' + pageId);
    expect(route.request().headers().authorization).toBe('Bearer writing-test');
    if (failure) return route.fulfill({status: failure === 'NOTION_RESOURCE_NOT_SELECTED' ? 403 : 502,
      json: {detail: {error_code: failure}}});
    return route.fulfill({json: {pageId, title: '会议材料', markdown: '## 议程\n\n第一项是下周的会议。'}});
  });
  await page.clock.setFixedTime(new Date(date));
  await page.setViewportSize({width, height: 840});
  await page.goto(base + '/story-workspace/writing');
  const editor = page.locator('.notebook-lines textarea.writing-prose').first();
  await expect(editor).toHaveValue(initial);
  return {editor, writes, reads, pageErrors, rejectSave: (reject: boolean) => {rejectSave = reject;}, failWith: (code: string) => {failure = code;}};
}

for (const width of [1220, 360]) {
  test.describe(`standalone article at ${width}px`, () => {
    test.describe.configure({timeout: 60_000}); // Initial route compile and two full session reloads.
    test.use({hasTouch: width === 360});

    test('click blank paper and type directly on a new line, then reopen', async ({page}, testInfo) => {
      const url = `https://www.notion.so/2026-11-24-${pageId}?source=copy_link#42130b7547c3800aad38daaa6f003a8a`;
      const {editor, writes, reads, pageErrors} = await openWriting(page, url, width);
      const card = page.locator('.note-article');
      const paper = page.locator('.notebook-lines');
      const clickPaper = (x: number, y: number) => width === 360
        ? page.touchscreen.tap(x, y) : page.mouse.click(x, y);

      await expect(card).toContainText('2026 11 24');
      const bounds = (await card.boundingBox())!;
      await clickPaper(bounds.x + bounds.width + 12, bounds.y + bounds.height / 2);
      const row = page.getByRole('textbox', {name: '日记第 2 行'});
      await expect(row).toBeFocused();
      await expect(row).toHaveValue('');
      await expect(card).toBeVisible();
      expect((await row.boundingBox())!.y).toBeGreaterThanOrEqual(bounds.y + bounds.height - 1);
      expect((await card.boundingBox())!.y).toBeCloseTo(bounds.y, 0);
      await expect(paper).toHaveCSS('background-image','none');
      await expect(row).toHaveCSS('background-image','none');
      await page.keyboard.insertText('下周讨论');
      const updated = url + '\n下周讨论';
      await expect(row).toHaveValue('下周讨论');
      await testInfo.attach(`focused-row-${width}`, {body: await paper.screenshot(), contentType: 'image/png'});
      await expect(card).toBeVisible();
      await expect.poll(() => writes.at(-1)?.cells[0].content).toBe(updated);

      await page.reload();
      await expect(card.getByRole('link')).toHaveAttribute('href', url);
      await expect(page.locator('.note-article-prose')).toHaveText('下周讨论');
      await testInfo.attach(`article-new-line-${width}`, {body: await paper.screenshot(), contentType: 'image/png'});
      const sheet = (await paper.boundingBox())!;
      await clickPaper(sheet.x + sheet.width / 2, sheet.y + sheet.height - 22);
      await expect(page.getByRole('textbox', {name: '日记第 3 行'})).toBeFocused();
      await expect(editor).toHaveValue(updated + '\n');
      await clickPaper(sheet.x + sheet.width / 2, sheet.y + sheet.height - 22);
      await expect(editor).toHaveValue(updated + '\n');
      await page.keyboard.insertText('周五确认');
      await expect.poll(() => writes.at(-1)?.cells[0].content).toBe(updated + '\n周五确认');

      await page.reload();
      const resume = page.getByRole('button', {name: '另起一行'});
      if (width === 360) await resume.tap();
      else await resume.click();
      await expect(page.getByRole('textbox', {name: '日记第 4 行'})).toBeFocused();
      await page.keyboard.insertText('带上纪要');
      await expect(editor).toHaveValue(updated + '\n周五确认\n带上纪要');
      await expect(card).toHaveCount(1);
      expect(reads).toHaveLength(0);
      expect(pageErrors).toEqual([]);
    });
  });
}

test('paste into a note, continue, undo, save and reopen the same source twice', async ({page, context}, testInfo) => {
  const {editor, reads, writes, pageErrors} = await openWriting(page, before);
  await context.grantPermissions(['clipboard-read', 'clipboard-write'], {origin: new URL(base!).origin});
  await editor.focus();
  await editor.press('End');
  await page.evaluate(text => navigator.clipboard.writeText(text), article);
  await editor.press('ControlOrMeta+v');
  const card = page.locator('.note-article');
  await expect(card).toHaveCount(1);
  await expect(editor).toBeFocused();
  expect(await editor.evaluate(el => (el as HTMLTextAreaElement).selectionStart)).toBe(before.length + article.length);
  await page.keyboard.insertText(after);
  await expect(editor).toHaveValue(original);
  await expect(card).toHaveCount(1);
  // Remove the address using the native selection, then undo the single edit.
  await editor.evaluate((el, offsets) => (el as HTMLTextAreaElement).setSelectionRange(...offsets),
    [before.length, before.length + article.length] as [number, number]);
  await editor.press('Backspace');
  await expect(editor).toHaveValue(before + after);
  await expect(card).toHaveCount(0);
  await editor.press('ControlOrMeta+z');
  await expect(editor).toHaveValue(original);
  await expect(card).toHaveCount(1);
  await expect.poll(() => writes.at(-1)?.cells).toEqual([{id: 'old-text', type: 'text', content: original}]);
  for (let i = 0; i < 2; i++) {
    await page.reload();
    await expect(card).toHaveCount(1);
    await expect(editor).toHaveValue(original);
    const projection = page.locator('.note-article-row').first();
    expect(await projection.evaluate(el => [el.firstChild?.textContent, el.lastChild?.textContent])).toEqual([before, after]);
    await expect(card.getByRole('link')).toHaveAttribute('href', article);
  }
  await testInfo.attach('writing-article', {body: await page.screenshot(), contentType: 'image/png'});
  expect(reads).toHaveLength(0);
  await context.route('https://app.notion.com/p/**', route => route.fulfill({contentType: 'text/html', body: '<title>Original article</title>'}));
  const [originalTab] = await Promise.all([page.waitForEvent('popup'), card.getByRole('link').click()]);
  await expect(originalTab).toHaveURL(article);
  await originalTab.close();
  await card.getByRole('button').click();
  const reader = page.getByRole('dialog', {name: '会议材料'});
  await expect(reader.locator('.notion .notion-h')).toContainText('议程');
  await expect(reader.locator('.notion .notion-text')).toContainText('第一项是下周的会议。');
  await testInfo.attach('article-reader', {body: await page.screenshot(), contentType: 'image/png'});
  await expect(reader.getByRole('link', {name: '打开原文'})).toHaveAttribute('href', article);
  await reader.getByRole('button', {name: '关闭页面预览'}).click();
  await expect(editor).toBeFocused();
  expect(await editor.evaluate(el => (el as HTMLTextAreaElement).selectionStart)).toBe(before.length + article.length);
  await page.keyboard.insertText('，');
  await expect(editor).toHaveValue(before + article + '，' + after);
  expect(reads).toHaveLength(1);
  expect(pageErrors).toEqual([]);
});

test('type a standalone link without interruption, then see the original and recover after a failed read', async ({page}, testInfo) => {
  const ordinary = `https://example.test/${pageId} https://notion.so.example.test/${pageId}`;
  const {editor, reads, failWith, pageErrors} = await openWriting(page, ordinary + '\n', 360);
  const card = page.locator('.note-article');
  await expect(card).toHaveCount(0);
  await editor.focus();
  await editor.evaluate(el => {
    const textarea = el as HTMLTextAreaElement;
    textarea.setSelectionRange(textarea.value.length, textarea.value.length);
  });
  await page.keyboard.type(article);
  await expect(card).toHaveCount(0);
  await editor.press('Enter');
  await expect(card).toHaveCount(1);
  await page.keyboard.insertText(after);
  const body = ordinary + '\n' + article + '\n' + after;
  await expect(editor).toHaveValue(body);
  expect(reads).toHaveLength(0);
  const inputBox = (await editor.boundingBox())!;
  const cardBox = (await card.boundingBox())!;
  expect(cardBox.y).toBeGreaterThanOrEqual(inputBox.y + inputBox.height - 1);
  expect(cardBox.x + cardBox.width).toBeLessThanOrEqual(360);
  await testInfo.attach('narrow-writing', {body: await page.screenshot(), contentType: 'image/png'});
  failWith('NOTION_RESOURCE_NOT_SELECTED');
  await card.getByRole('button').click();
  const dialog = page.getByRole('dialog');
  await expect(dialog.getByRole('alert')).toContainText('选择此页面');
  await expect(dialog.getByRole('link', {name: '打开原文'})).toHaveAttribute('href', article);
  failWith('NOTION_UPSTREAM_UNAVAILABLE');
  await dialog.getByRole('button', {name: '重试'}).click();
  await expect(dialog.getByRole('alert')).toContainText('暂时无法读取');
  failWith('');
  await dialog.getByRole('button', {name: '重试'}).click();
  await expect(dialog.locator('.notion-text')).toContainText('第一项');
  await page.keyboard.press('Escape');
  await expect(editor).toBeFocused();
  await expect(editor).toHaveValue(body);
  await page.keyboard.insertText('！');
  await expect(editor).toHaveValue(body + '！');
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true);
  expect(pageErrors).toEqual([]);
});

test('open an existing plain-text reference, edit the block anchor and undo without touching adjacent prose', async ({page}) => {
  const {editor, reads} = await openWriting(page, original);
  const card = page.locator('.note-article');
  const compact = page.locator('.note-article-projection');
  await expect(card).toHaveCount(1);
  await expect(compact.locator('.note-article-prose')).toHaveText([before, after]);
  await compact.locator('.note-article-prose').last().click();
  await expect(editor).toBeFocused();
  const start = before.length + article.indexOf('#') + 1;
  await editor.evaluate((el, position) => (el as HTMLTextAreaElement).setSelectionRange(position, position + 32), start);
  await page.keyboard.insertText(pageId);
  await editor.press('ArrowRight');
  const updated = article.slice(0, article.indexOf('#') + 1) + pageId;
  await expect(editor).toHaveValue(before + updated + after);
  await expect(card.getByRole('link')).toHaveAttribute('href', updated);
  await editor.press('ControlOrMeta+z');
  await expect(editor).toHaveValue(original);
  await expect(card.getByRole('link')).toHaveAttribute('href', article);
  expect(reads).toHaveLength(0);
});

for (const failFirst of [false, true]) test(`calendar article insertion, first save ${failFirst ? 'fails' : 'succeeds'}`, async ({page}, testInfo) => {
  const {editor, writes, reads, rejectSave} = await openWriting(page, '正在编辑的日记', failFirst ? 360 : 1220);
  const chosen = failFirst ? '2026-09-28' : '2026-09-27';
  const following = failFirst ? '2026-09-29' : '2026-09-28';
  const policy = {enabled: true, interval_minutes: 15, revision: 1};
  await page.route('**/api/connectors', route => route.fulfill({json: {connectors: [{
    id: 'notion-journal', name: 'Notion', platform: 'notion', auth_status: 'authenticated', status: 'authenticated',
    created_at: date, updated_at: date, current_snapshot_version: 'snapshot-journal', config: {}, sources: [],
    sync_policy: {schema_version: 1, default: policy, desired: policy, effective: policy, status: 'applied', allowed_interval_minutes: [15]},
  }]}}));
  await page.route('**/api/connectors/notion-journal/notion/documents?**', route => route.fulfill({json: {
    connectorId: 'notion-journal', dateKey:chosen, todayKey:'2026-09-28', timeZone:'UTC',
    intervalStart:chosen + 'T00:00:00Z', intervalEnd:following + 'T00:00:00Z', observedAt:date,
    coverage:'connector_snapshot', paginationState:'complete', snapshotVersion:'snapshot-journal', snapshotFetchedAt:date,
    verificationState:'complete', partialReasons:[], candidateCount:2, retryAfter:null, counts:{created:2,edited:0,total:2},
    items:[{pageId:'42230b7547c3802e8cb4cde06b73d2ae', title:'上一份记录', url:null}, {pageId, title:'设计会议', url:article}].map(item => ({
      ...item, emoji:null, createdTime:chosen + 'T12:00:00Z', lastEditedTime:chosen + 'T12:00:00Z', group:'created', createdOnDate:true, editedOnDate:true,
    })),
  }}));
  await page.getByRole('button',{name:'Calendar',exact:true}).click();
  const dialog = page.locator('.calendar-popup-modal');
  if (!failFirst) await dialog.getByRole('gridcell').filter({hasText:/^27$/}).click();
  await dialog.getByRole('tab',{name:'Notion',exact:true}).click();
  const insert = dialog.getByRole('button',{name:'将《设计会议》插入当前日记',exact:true});
  const other = dialog.getByRole('button',{name:'将《上一份记录》插入当前日记',exact:true});
  const confirmation = (name: string) => dialog.getByRole('dialog',{name:`将《${name}》插入当前日记？`,exact:true});
  const choice = confirmation('设计会议');
  const confirm = choice.getByRole('button',{name:'确认插入'});
  async function expectTipAtButton(tip: Locator, button = insert) {
    await expect(tip).toBeInViewport({ratio:1});
    const rect = (await button.boundingBox())!;
    const hint = (await tip.boundingBox())!;
    if (await tip.getAttribute('role') === 'dialog') {
      const centerY = rect.y + rect.height / 2;
      expect(centerY).toBeGreaterThan(hint.y);
      expect(centerY).toBeLessThan(hint.y + hint.height);
      const gap = Math.max(rect.x - hint.x - hint.width, hint.x - rect.x - rect.width);
      expect(gap).toBeGreaterThanOrEqual(0);
      expect(gap).toBeLessThanOrEqual(12);
      return;
    }
    const center = rect.x + rect.width / 2;
    expect(center).toBeGreaterThan(hint.x);
    expect(center).toBeLessThan(hint.x + hint.width);
    const gap = Math.max(rect.y - hint.y - hint.height, hint.y - rect.y - rect.height);
    expect(gap).toBeGreaterThanOrEqual(0);
    expect(gap).toBeLessThanOrEqual(12);
  }
  const original = '正在编辑的日记';
  let finishSave!: () => void;
  let attempts = 0;
  const pendingSave = new Promise<void>(resolve => {finishSave = resolve;});
  await page.route('**/api/sessions', async route => {
    if (route.request().method() === 'POST') {attempts++; await pendingSave;}
    await route.fallback();
  });
  await other.click();
  await expectTipAtButton(confirmation('上一份记录'), other);
  await insert.click();
  await expect(confirmation('上一份记录')).toHaveCount(0);
  await expectTipAtButton(choice);
  await other.click();
  await expect(choice).toHaveCount(0);
  await expectTipAtButton(confirmation('上一份记录'), other);
  await insert.click();
  await expectTipAtButton(choice);
  await expect(editor).toHaveValue(original);
  await testInfo.attach(failFirst ? 'article-confirm-narrow' : 'article-confirm-desktop', {body: await page.screenshot(), contentType:'image/png'});
  await choice.getByRole('button',{name:'取消'}).click();
  await expect(choice).toHaveCount(0);
  await expect(insert).toBeFocused();
  await insert.press('Enter');
  await expect(choice).toBeVisible();
  await page.keyboard.press('Escape');
  await expect(choice).toHaveCount(0);
  await expect(dialog).toBeVisible();
  await expect(editor).toHaveValue(original);
  expect(attempts).toBe(0);

  await insert.click();
  rejectSave(failFirst);
  await confirm.click();
  try {
    await expectTipAtButton(dialog.getByRole('status').filter({hasText:'正在保存到当前日记'}));
    await expect(insert).toBeDisabled();
  } finally {
    finishSave();
  }
  if (failFirst) {
    await expectTipAtButton(dialog.getByRole('alert').filter({hasText:'暂时未能保存到当前日记'}));
    rejectSave(false);
    await insert.click();
    await confirm.click();
  }
  const savedTip = dialog.getByRole('status').filter({hasText:failFirst ? '当前日记已包含《设计会议》' : '已将《设计会议》插入当前日记'});
  await expectTipAtButton(savedTip);
  await testInfo.attach(failFirst ? 'calendar-tip-narrow' : 'calendar-tip-desktop', {body: await page.screenshot(), contentType: 'image/png'});
  const first = original + '\n' + article;
  await expect.poll(() => writes.at(-1)?.cells[0].content).toBe(first);
  await insert.click();
  await confirm.click();
  const duplicateTip = dialog.getByRole('status').filter({hasText:'当前日记已包含《设计会议》'});
  await expectTipAtButton(duplicateTip);
  await expect(duplicateTip).toBeHidden();
  await other.click();
  await confirmation('上一份记录').getByRole('button',{name:'确认插入'}).click();
  await expectTipAtButton(dialog.getByRole('status').filter({hasText:'已将《上一份记录》插入当前日记'}), other);
  const otherId = '42230b7547c3802e8cb4cde06b73d2ae';
  const otherHref = 'https://www.notion.so/' + otherId;
  const expected = first + '\n' + otherHref;
  await expect.poll(() => writes.at(-1)?.cells[0].content).toBe(expected);
  await page.keyboard.press('Escape');
  await page.reload();
  await expect(editor).toHaveValue(expected);
  const cards = page.locator('.note-article');
  await expect(cards).toHaveCount(2);
  await expect(cards.nth(0).getByRole('button')).toHaveAccessibleName('预览设计会议');
  await expect(cards.nth(0).getByRole('link')).toHaveAttribute('href',article);
  await expect(cards.nth(1).getByRole('button')).toHaveAccessibleName('预览上一份记录');
  await expect(cards.nth(1).getByRole('link')).toHaveAttribute('href',otherHref);
  expect(reads).toEqual([]);
  await page.route('**/api/connectors/notion/articles/*', route => {
    const id = new URL(route.request().url()).pathname.split('/').pop();
    const title = id === pageId ? '设计会议' : '上一份记录';
    return route.fulfill({json:{pageId:id, title, markdown:'## ' + title + '正文'}});
  });
  for (const name of ['设计会议','上一份记录']) {
    await page.getByRole('button',{name:'预览' + name,exact:true}).click();
    const reader = page.getByRole('dialog',{name,exact:true});
    await expect(reader.locator('.notion-text, .notion-h2').filter({hasText:name+'正文'}).first()).toBeVisible();
    await reader.getByRole('button',{name:'关闭页面预览'}).click();
  }
});

test('insert between two existing journal lines and reuse the empty row', async ({page}) => {
  const other = article.replace(pageId,'aae712be97ca4074beb365c30bb3c8ad');
  const {writes, reads} = await openWriting(page, [before, article, '已有后文', other].join('\n'));
  const rows = page.locator('.note-article-row');
  const card = rows.nth(1).locator('.note-article');
  const box = (await card.boundingBox())!;
  const clickAfterCard = () => page.mouse.click(box.x + box.width + 15, box.y + box.height / 2);
  await clickAfterCard();
  const field = page.getByRole('textbox', {name:'日记第 3 行'});
  await expect(field).toBeFocused();
  await clickAfterCard();
  await expect(rows).toHaveCount(5);
  await page.keyboard.insertText('第一段');
  await page.keyboard.press('Enter');
  const next = page.getByRole('textbox',{name:'日记第 4 行'});
  await expect(next).toBeFocused();
  await page.keyboard.insertText('修改');
  await page.keyboard.press('ControlOrMeta+z');
  await expect(next).toHaveValue('');
  await page.keyboard.insertText('第二段');
  const expected = [before, article, '第一段','第二段','已有后文',other].join('\n');
  await expect.poll(() => writes.at(-1)?.cells[0].content).toBe(expected);
  await page.reload();
  await expect(rows).toHaveCount(6);
  await expect(rows.nth(2)).toHaveText('第一段');
  await expect(rows.nth(4)).toHaveText('已有后文');
  await expect(rows.nth(5).getByRole('link')).toHaveAttribute('href',other);
  expect(reads).toEqual([]);
});

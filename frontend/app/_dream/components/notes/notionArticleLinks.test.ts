// [Sync] 2026-11-25: verify named reference round trips and recovery of a rejected draft.
// [Sync] 2026-11-25: cover Calendar page identity, URL preservation and canonical fallback.
// [Input] Note prose with page links, UTF-16 offsets, query parameters and block fragments.
// [Output] Deterministic source-preserving recognition and hostname/shape exclusions.
// [Pos] Provider-free Writing link contract.
import assert from 'node:assert/strict';
import test from 'node:test';
import {EditorEngine} from '../../engine/EditorEngine.ts';
import {calendarArticleHref, findNotionArticleLinks, formatNotionArticleLink, recoverNotionArticleDraft} from './notionArticleLinks.ts';

const id = '40b30b7547c380cd9930c384ab35023c';
const dashed = '40b30b75-47c3-80cd-9930-c384ab35023c';
const block = '42130b7547c3800aad38daaa6f003a8a';
const sample = `https://app.notion.com/p/${id}?v=${id}&source=copy_link#${block}`;

test('full source ranges survive inline prose, standalone links and repeated occurrences', () => {
  assert.equal(findNotionArticleLinks(`Read (${sample}).`)[0].href, sample);
  const text = `📝会议资料${sample}下周讨论${sample}\n${sample}`;
  const links = findNotionArticleLinks(text);
  assert.equal(links.length, 3);
  for (const link of links) {
    assert.equal(link.pageId, id);
    assert.equal(text.slice(link.start, link.end), sample);
    assert.equal(link.href, sample);
  }
});

test('page routes, decoded title, query page target and literal query spelling', () => {
  for (const host of ['notion.so', 'www.notion.so', 'workplace.notion.site', 'notion.site']) {
    const href = `https://${host}/team/%E4%BC%9A%E8%AE%AE-${dashed}?x=%2F&y=hi!`;
    const [page] = findNotionArticleLinks(href);
    assert.deepEqual([page.href, page.label, page.pageId], [href, '会议', id]);
  }
  const href = `https://www.notion.so/${id}?v=${id}&p=${block}#${id}`;
  assert.equal(findNotionArticleLinks(`(${href})`)[0].pageId, block);
  assert.equal(findNotionArticleLinks(`(${href})`)[0].href, href);
});

test('ordinary, lookalike, embedded, malformed and incomplete addresses stay plain', () => {
  const ignored = ['https://example.com/', 'http://notion.so/', 'https://notion.so.evil.test/',
    'https://notion.site.example/', 'https://user@notion.so/', 'https://@notion.so/',
    'https:///user@notion.so/', 'https://notion.so:8080/', 'https://example.com/?next=https://www.notion.so/'];
  for (const prefix of ignored) assert.deepEqual(findNotionArticleLinks(prefix + id), []);
  for (const tail of ['help', 'abc123', id + 'x', id + '?p=invalid'])
    assert.deepEqual(findNotionArticleLinks('https://www.notion.so/' + tail), []);
});

test('calendar preserves the exact selected page address or builds one from its page ID', () => {
  assert.equal(calendarArticleHref(dashed, sample), sample);
  assert.equal(calendarArticleHref(id, null), `https://www.notion.so/${id}`);
  assert.equal(calendarArticleHref(id, `https://www.notion.so/${block}`), `https://www.notion.so/${id}`);
  assert.equal(calendarArticleHref(id, 'https://example.test/article'), `https://www.notion.so/${id}`);
  assert.equal(calendarArticleHref('incomplete', sample), null);
});

test('named Calendar links preserve source ranges, punctuation, escaped titles and distinct URLs', () => {
  const title = '阅读 [A] \\ ' + sample;
  const href = sample.split('#')[0] + '&filter=a(b)';
  const named = formatNotionArticleLink(href, title);
  const text = '资料' + named + '下周\n' + sample;
  const [a, b] = findNotionArticleLinks(text);
  assert.deepEqual([a.href, a.label, text.slice(a.start, a.end)], [href, title, named]);
  assert.equal(b.href, sample);
  assert.equal(text.slice(b.start, b.end), sample);
  assert.equal(findNotionArticleLinks(text).length, 2);
  assert.deepEqual(findNotionArticleLinks('[普通](<https://notion.so.invalid/' + id + '>)'), []);
});

test('retrying a rejected draft preserves the prose, link fragment and distinct Calendar title using the published cell fields', () => {
  const cell = {id:'note', type:'text' as const, content:'会议资料\n' + sample + '\n下周讨论'};
  assert.equal(recoverNotionArticleDraft(cell), cell);
  const previous = {...cell, notionArticleTitles:{[sample]:'设计会议'}};
  const recovered = recoverNotionArticleDraft(previous);
  assert.deepEqual(recovered, {...cell, content:'会议资料\n[设计会议](<' + sample + '>)\n下周讨论'});
  assert.equal(recoverNotionArticleDraft(recovered), recovered);
  assert.equal(previous.content, cell.content);
});

test('confirming a reference already present in user prose keeps every original character', () => {
  const engine = new EditorEngine('journal');
  const content = '资料（' + sample + '），下周讨论';
  const cell = {id:'prose', type:'text' as const, content};
  engine.loadState({...engine.getState(), cells:[cell]});
  assert.equal(engine.insertNotionArticle(sample, '设计会议'), 'present');
  assert.deepEqual(engine.getState().cells, [{id:'prose', type:'text', content}]);
});

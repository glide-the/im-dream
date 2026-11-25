// [Sync] 2026-11-25: cover Calendar page identity, URL preservation and canonical fallback.
// [Input] Note prose with page links, UTF-16 offsets, query parameters and block fragments.
// [Output] Deterministic source-preserving recognition and hostname/shape exclusions.
// [Pos] Provider-free Writing link contract.
import assert from 'node:assert/strict';
import test from 'node:test';
import {calendarArticleHref, findNotionArticleLinks} from './notionArticleLinks.ts';

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

// [Sync] 2026-11-18: regress Read numbering, source identity and prose-first card excerpts.
// [Input] Existing Notion Read JSON and tool DTO boundaries.
// [Output] Deterministic matching, identity, incomplete-result and error regressions.
// [Pos] Provider-free Chat presentation contracts.
// [Sync] 2026-11-18: cover objects, strings, numbered Read output and safe generic fallbacks.
import {expect, test} from '@playwright/test';
import type {DynamicToolUIPart} from 'ai';
import {notionPreviewExcerpt, resolveNotionWorkspacePreview} from '../notionPreviewProjection';
const pageId = '41b30b75-47c3-803a-9079-e5c84adc127d';
const payload = {ok: true, page_id: pageId, title: '观察记录', markdown: '# 观察记录\n\n今天的观察。', snapshot: {version: 1}};
function part(output: unknown = payload, path = `.notion/pages/${pageId}.json`, toolName = 'Read'): DynamicToolUIPart {
  return {type: 'dynamic-tool', toolName, toolCallId: 'notion-read', state: 'output-available', input: {file_path: path}, output};
}
test('matches existing object/string payload and page identity across UUID formatting', () => {
  for (const output of [payload, JSON.stringify(payload)]) expect(resolveNotionWorkspacePreview(part(output))).toMatchObject({state: 'ready', title: '观察记录', markdown: payload.markdown, payload});
  expect(resolveNotionWorkspacePreview(part(payload, `/workspace/.notion/pages/${pageId.replaceAll('-', '').toUpperCase()}.json`))).not.toBeNull();
});
test('decodes exact numbered Read JSON and the existing private redirect path', () => {
  const numbered = JSON.stringify(payload, null, 2).split('\n').map((line, i) => `     ${i + 1}→${line}`).join('\n') + '\n<system-reminder>tool reminder</system-reminder>';
  expect(resolveNotionWorkspacePreview(part(numbered, '/workspace/thread/.claude-tmp/notion-read-ab_12.json'))?.payload).toEqual(payload);
  expect(resolveNotionWorkspacePreview(part(numbered.replace('     1→', '     2→')))).toBeNull();
});
test('decodes actual tab-numbered page success and error receipts with the trailing reminder', () => {
  const reminder = '\n\n<system-reminder>tool reminder</system-reminder>';
  for (const value of [payload, {ok: false, page_id: pageId, code: 'NOTION_PERMISSION_DENIED'}]) {
    const output = '1\t' + JSON.stringify(value) + reminder;
    expect(resolveNotionWorkspacePreview(part(output))?.payload).toEqual(value);
  }
  const numbered = JSON.stringify(payload, null, 2).split('\n').map((line, index) => `${index}\t${line}`).join('\r\n') + reminder;
  expect(resolveNotionWorkspacePreview(part(numbered))?.payload).toEqual(payload);
});
test('rejects truncated, skipped, duplicated and mixed-delimiter numbered JSON', () => {
  const numbered = JSON.stringify(payload, null, 2).split('\n').map((line, index) => `${index}\t${line}`).join('\n');
  for (const output of [numbered.replace(/^0\t/, '2\t'), numbered.replace('1\t', '3\t'), numbered.replace('1\t', '0\t'), numbered.replace('1\t', '1→'), numbered.slice(0, -1)]) {
    expect(resolveNotionWorkspacePreview(part(output))).toBeNull();
  }
});
test('preserves empty success and maps actual hook failure codes', () => {
  expect(resolveNotionWorkspacePreview(part({...payload, markdown: ''}))).toMatchObject({state: 'ready', markdown: ''});
  for (const [code, failure] of [['NOTION_AUTH_REQUIRED', 'access'], ['NOTION_PERMISSION_DENIED', 'access'], ['NOTION_RESOURCE_NOT_SELECTED', 'scope'], ['NOTION_CAPABILITY_UNAVAILABLE', 'failed'], ['NOTION_REQUEST_FAILED', 'failed']]) {
    expect(resolveNotionWorkspacePreview(part({ok: false, page_id: pageId, code}))).toMatchObject({state: 'error', failure, markdown: ''});
  }
});
test('keeps unrelated tools/files, mismatched identifiers and partial results in the original renderer', () => {
  for (const candidate of [part(payload, 'files/page.json'), part(payload, `.notion/pages/${pageId}.json`, 'Bash'), part(payload, `.notion/pages/${'a'.repeat(32)}.json`), part({...payload, page_id: 'invalid'}), part({...payload, ok: 'true'}), part({...payload, markdown: undefined}), part('{"ok":true'), part(JSON.stringify(payload).slice(1)), part(payload, `../.notion/pages/${pageId}.json`), {...part(), state: 'input-available', output: undefined} as DynamicToolUIPart, {...part(), state: 'output-error', errorText: 'failed'} as DynamicToolUIPart]) expect(resolveNotionWorkspacePreview(candidate)).toBeNull();
});
test('limits the collapsed text excerpt and keeps the full payload intact', () => {
  const markdown = '# 标题\n\n[文字](https://example.test) **强调** ' + '正文'.repeat(10000);
  const preview = resolveNotionWorkspacePreview(part({...payload, markdown}));
  expect(notionPreviewExcerpt(markdown)).toContain('标题 文字 强调');
  expect(notionPreviewExcerpt(markdown).length).toBeLessThanOrEqual(280);
  expect(preview?.markdown).toBe(markdown);
});
test('uses prose for card excerpts and preserves a fallback for code-only pages', () => {
  const markdown = '# 观察记录\n\n今天的观察。\n\n| 时间 | 事件 |\n| --- | --- |\n| 上午 | 河流 |\n\n```json\n{"long":"detail"}\n```\n\n明天继续观察。';
  expect(notionPreviewExcerpt(markdown, '观察记录')).toBe('今天的观察。 明天继续观察。');
  expect(notionPreviewExcerpt('```json\n{"key":"value"}\n```')).toContain('key');
});

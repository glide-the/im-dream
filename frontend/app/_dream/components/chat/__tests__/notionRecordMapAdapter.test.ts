// [Input] Synthetic saved enhanced Markdown and the production RecordMap adapter.
// [Output] Block-order, reference, literal-code and URL-boundary regression evidence.
// [Pos] Provider-free data-format contracts; no Notion API or account access.
// [Sync] 2026-11-18: qualify data consumed by the actual react-notion-x browser journey.
import {expect, test} from '@playwright/test';
import type {Block} from 'notion-types';
import {createNotionRecordMap, notionPreviewUrl} from '../notionRecordMapAdapter';
import {notionPreviewExcerpt} from '../notionPreviewProjection';
const pageId = '41b30b75-47c3-803a-9079-e5c84adc127d';
function blocks(markdown: string): Block[] {
  return Object.values(createNotionRecordMap({pageId, title: '观察', markdown}).block).map(box => 'type' in box.value ? box.value : box.value.value);
}
test('maps attachments and references using saved labels and URLs without fabricating target pages', () => {
  const result = blocks('<file src="https://files.example.test/report.pdf?signature=secret">观察附件</file>\n\n<mention-page url="https://www.notion.so/abc">观察页面</mention-page> 与 <mention-database url="https://www.notion.so/def">记录库</mention-database>');
  expect(result.map(block => block.type)).toEqual(['page', 'file', 'text']);
  expect(result[1].properties).toMatchObject({title: [['观察附件']], source: [['https://files.example.test/report.pdf?signature=secret']]});
  expect(result[2].properties.title).toEqual([['观察页面', [['a', 'https://www.notion.so/abc']]], [' 与 '], ['记录库', [['a', 'https://www.notion.so/def']]]]);
});
test('shows a self-closing link-preview from the real source format as a labeled original link', () => {
  const result = blocks('<link-preview url="https://github.com/NotionX/react-notion-x" source="github"/>');
  expect(result[1].properties.title).toEqual([['github.com', [['a', 'https://github.com/NotionX/react-notion-x']]]]);
});
test('preserves nested callouts, toggles, columns and enhanced table headers in source order', () => {
  const result = blocks('<callout icon="💡">\n\t提示正文\n\t<details><summary>更多观察</summary>\n\t\t折叠正文\n\t</details>\n</callout>\n<columns><column>左侧</column><column>右侧</column></columns>\n<table header-row="true"><tr><td>时间</td><td>事件</td></tr><tr><td>上午</td><td>**观察**</td></tr></table>');
  expect(result.map(block => block.type)).toEqual(['page', 'callout', 'text', 'toggle', 'text', 'column_list', 'column', 'text', 'column', 'text', 'table', 'table_row', 'table_row']);
  expect(result[1].format.page_icon).toBe('💡');
  expect(result[4].parent_id).toBe(result[3].id);
  expect(result[6].format.column_ratio).toBe(.5);
  expect(result[10].format.table_block_column_header).toBe(true);
  expect(result[12].properties.column1).toEqual([['观察', [['b']]]]);
});
test('leaves fenced, inline and escaped enhanced tags as literal code or text', () => {
  const source = '<callout>\n```xml\n<file src="https://files.example.test/a">代码</file>\n```\n\n`<mention-page url="https://www.notion.so/a">行内代码</mention-page>`\n\n\\<file src="https://files.example.test/a">转义文字\\</file>\n</callout>';
  const result = blocks(source);
  expect(result.filter(block => block.type === 'file')).toHaveLength(0);
  expect(result.find(block => block.type === 'code')?.properties.title).toEqual([['<file src="https://files.example.test/a">代码</file>']]);
  expect(JSON.stringify(result)).toContain('行内代码');
  expect(JSON.stringify(result)).toContain('转义文字');
});
test('converts Markdown formatting, tables, lists and the existing paired Chat math syntax', () => {
  const result = blocks('# 标题\n\n**粗体** [链接](https://example.test) 与 \\(x^2\\)\n\n- [x] 完成\n- [ ] 待办\n\n| 时间 | 事件 |\n| --- | --- |\n| 上午 | 观察 |\n\n$$x^2+y^2$$');
  expect(result.map(block => block.type)).toEqual(['page', 'header', 'text', 'to_do', 'to_do', 'table', 'table_row', 'table_row', 'equation']);
  expect(result[2].properties.title).toContainEqual(['⁍', [['e', 'x^2']]]);
  expect(result[3].properties.checked).toEqual([['Yes']]);
  expect(result.at(-1)?.properties.title).toEqual([['x^2+y^2']]);
});
test('rejects script, credential and unsupported URL schemes while retaining readable content', () => {
  for (const url of ['javascript:alert(1)', 'data:text/html,test', 'file:///private/a', 'https://user:password@example.test/a', '//example.test/a']) expect(notionPreviewUrl(url)).toBeUndefined();
  const result = blocks('<file src="javascript:alert(1)">不可用附件</file>\n<mention-page url="javascript:alert(1)">页面名</mention-page>\n<script>alert(1)</script>');
  expect(result.map(block => block.type)).not.toContain('file');
  expect(JSON.stringify(result)).not.toContain('javascript:');
  expect(JSON.stringify(result)).toContain('不可用附件');
  expect(result.filter(block => block.type === 'text').map(block => block.properties.title.flat().join('')).join('')).toContain('<script>');
});
test('keeps blank blocks, line breaks, dates and decoded filenames without exposing signature text', () => {
  const source = '<empty-block/>\n第一行<br/>第二行 <mention-date start="2026-11-18"/>\n<file src="https://files.example.test/%E8%A7%82%E5%AF%9F.pdf?signature=secret"/>';
  const result = blocks(source);
  expect(result[1].properties.title).toEqual([['\u00a0']]);
  expect(result[2].properties.title).toEqual([['第一行'], ['\n'], ['第二行 2026-11-18']]);
  expect(result[3].properties.title).toEqual([['观察.pdf']]);
  expect(notionPreviewExcerpt('前文 ![](https://files.example.test/image.png?signature=' + 'secret'.repeat(400) + ') 后文 <file src="https://files.example.test/a?signature=secret">附件</file>')).toBe('前文 后文 附件');
});

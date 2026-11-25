// [Sync] 2026-11-24: expose the page data consumed by both reading surfaces.
// [Input] One saved Notion enhanced-Markdown result; no API, authentication or persistence access.
// [Output] Ordered ExtendedRecordMap for react-notion-x, with validated URLs and literal code preserved.
// [Pos] Presentation-only format adapter; NotionRenderer owns block DOM and layout.
// [Sync] 2026-11-18: reuse mdast/GFM and Chat math syntax; parse enhanced tags without injecting HTML.
import {parseDocument} from 'htmlparser2';
import {fromMarkdown} from 'mdast-util-from-markdown';
import {gfmFromMarkdown} from 'mdast-util-gfm';
import {gfm} from 'micromark-extension-gfm';
import type {RootContent, PhrasingContent} from 'mdast';
import type {BaseBlock, Block, BlockType, Decoration, ExtendedRecordMap, SubDecoration} from 'notion-types';
import {chatMathFromMarkdown, chatMathSyntax} from './remarkChatMath';

type MarkupNode = ReturnType<typeof parseDocument>['children'][number];
type Tag = Extract<MarkupNode, {attribs: Record<string, string>}>;
const isTag = (node: MarkupNode): node is Tag => 'name' in node && 'attribs' in node;
const escapeMarkup = (text: string) => text.replaceAll('&', '&amp;').replaceAll('<', '&lt;').replaceAll('>', '&gt;');
const escapeLabel = (text: string) => text.replace(/[\\[\]`*_]/g, '\\$&');
const parseMarkdown = (text: string) => fromMarkdown(text, {extensions: [gfm(), chatMathSyntax], mdastExtensions: [gfmFromMarkdown(), chatMathFromMarkdown]});

export function notionPreviewUrl(value: string | undefined): string | undefined {
  if (!value) return undefined;
  try {
    const url = new URL(value);
    if ((url.protocol === 'https:' || url.protocol === 'http:') && !url.username && !url.password) return url.href;
  } catch { /* Missing or unsupported URLs remain readable labels. */ }
  return undefined;
}

function fileLabel(url: string | undefined, fallback: string): string {
  if (!url) return fallback;
  try {return decodeURIComponent(new URL(url).pathname.split('/').filter(Boolean).at(-1) || fallback);} catch {return fallback;}
}

/** Mask markup before locating Markdown code: an opening XML tag must not swallow a following fence. */
function protectLiterals(source: string): string {
  const masked = source.replace(/<\/?[a-zA-Z][^>]*>/g, value => value.replace(/[^\n\r]/g, ' '));
  const ranges: [number, number][] = [];
  function visit(node: {type: string; position?: {start: {offset?: number}; end: {offset?: number}}; children?: unknown[]}) {
    const start = node.position?.start.offset, end = node.position?.end.offset;
    if (start !== undefined && end !== undefined && (node.type === 'inlineCode' || node.type === 'code' && /^\s*(`{3,}|~{3,})/.test(source.slice(start, end)))) ranges.push([start, end]);
    else if (node.children) for (const child of node.children) visit(child as Parameters<typeof visit>[0]);
  }
  visit(parseMarkdown(masked));
  // Backslash-escaped tags also remain literal through the markup parser.
  for (const match of source.matchAll(/(\\+)(<\/?[a-zA-Z][^>]*>)/g)) {
    if (match[1].length % 2 && !ranges.some(([start, end]) => match.index >= start && match.index < end)) ranges.push([match.index + match[1].length, match.index + match[0].length]);
  }
  ranges.sort((a, b) => a[0] - b[0]);
  let end = 0, output = '';
  for (const [start, next] of ranges) {
    if (start < end) continue;
    output += source.slice(end, start) + escapeMarkup(source.slice(start, next)); end = next;
  }
  return output + source.slice(end);
}

function rawText(nodes: MarkupNode[]): string {
  return nodes.map(node => node.type === 'text' ? node.data : isTag(node) ? rawText(node.children) : '').join('');
}
function markupText(node: MarkupNode): string {
  if (node.type === 'text') return node.data;
  if (!isTag(node)) return '';
  const label = rawText(node.children).trim() || node.attribs.title || node.attribs.name;
  const url = notionPreviewUrl(node.attribs.url || node.attribs.href);
  if (/^(mention-(page|database|data-source|user|agent)|page|database|link-preview|a)$/.test(node.name)) {
    const title = label || (url ? node.name === 'link-preview' ? new URL(url).hostname : fileLabel(url, node.name) : node.name);
    return url ? `[${escapeLabel(title)}](<${url}>)` : escapeLabel(title);
  }
  if (node.name === 'mention-date') return escapeLabel(label || [node.attribs.start, node.attribs.end].filter(Boolean).join(' – '));
  const text = node.children.map(markupText).join('');
  if (node.name === 'br') return '  \n';
  if (node.name === 'strong' || node.name === 'b') return `**${text}**`;
  if (node.name === 'em' || node.name === 'i') return `*${text}*`;
  if (node.name === 's' || node.name === 'del') return `~~${text}~~`;
  if (node.name === 'span' || node.name === 'u') return text;
  // Unknown markup stays visible as source; no HTML or attributes enter the DOM.
  return `<${node.name}>${text}</${node.name}>`;
}
const STRUCTURAL = new Set(['file', 'pdf', 'audio', 'video', 'image', 'empty-block', 'callout', 'details', 'columns', 'table', 'hr']);
function dedent(text: string): string {
  const lines = text.replace(/^\n/, '').replace(/\n[\t ]*$/, '').split('\n');
  const indentation = Math.min(...lines.filter(line => line.trim()).map(line => /^[\t ]*/.exec(line)![0].length));
  return Number.isFinite(indentation) && indentation > 0 ? lines.map(line => line.slice(indentation)).join('\n') : lines.join('\n');
}

export interface NotionDocumentData {pageId: string; title: string; markdown: string}

export function createNotionRecordMap({pageId, title, markdown}: NotionDocumentData): ExtendedRecordMap {
  const map: ExtendedRecordMap = {block: {}, collection: {}, collection_view: {}, notion_user: {}, collection_query: {}, signed_urls: {}};
  const blocks = new Map<string, BaseBlock>();
  let sequence = 0;
  function add(type: BlockType, parent: string, properties: Record<string, unknown> = {}, format: Record<string, unknown> = {}): BaseBlock {
    // Local sequential identity only; no synthetic Notion resource is fetched or persisted.
    const id = sequence++ === 0 ? pageId : `${pageId.replaceAll('-', '')}-${sequence}`;
    const block: BaseBlock = {id, type, parent_id: parent, parent_table: 'block', version: 1, alive: true,
      created_time: 0, last_edited_time: 0, created_by_table: 'notion_user', created_by_id: '', last_edited_by_table: 'notion_user', last_edited_by_id: '',
      properties, format, content: []};
    // The builder supplies type-specific fields below; this union assertion stays at the format boundary.
    map.block[id] = {role: 'reader', value: block as Block};
    blocks.set(id, block);
    blocks.get(parent)?.content?.push(id);
    return block;
  }
  const root = add('page', '', {title: [[title]]});
  Object.assign(root, {permissions: [{role: 'reader', type: 'space_permission'}]});

  function rich(nodes: PhrasingContent[], decorations: SubDecoration[] = []): Decoration[] {
    const result: Decoration[] = [];
    const push = (text: string, marks = decorations) => {if (text) result.push(marks.length ? [text, marks] : [text]);};
    for (const node of nodes) {
      if (node.type === 'text') push(node.value);
      else if (node.type === 'break') push('\n');
      else if (node.type === 'inlineCode') {
        const props = node.data?.hProperties;
        if (props?.dataMathSource && props.dataMathClosed === 'true') result.push(['⁍', [...decorations, ['e', node.value.slice(2, -2)]]]);
        else push(node.value, [...decorations, ['c']]);
      } else if (node.type === 'link') {
        const url = notionPreviewUrl(node.url);
        result.push(...rich(node.children, url ? [...decorations, ['a', url]] : decorations));
      } else if (node.type === 'strong' || node.type === 'emphasis' || node.type === 'delete') result.push(...rich(node.children, [...decorations, [node.type === 'strong' ? 'b' : node.type === 'emphasis' ? 'i' : 's']]));
      else if (node.type === 'image') push(node.alt || fileLabel(notionPreviewUrl(node.url), 'image'));
      else if ('value' in node) push(String(node.value));
      else if ('children' in node) result.push(...rich(node.children as PhrasingContent[], decorations));
    }
    return result;
  }
  const richMarkdown = (text: string) => {
    const nodes = parseMarkdown(text).children;
    return nodes.flatMap(node => 'children' in node ? rich(node.children as PhrasingContent[]) : 'value' in node ? [[String(node.value)] as Decoration] : []);
  };
  function asset(type: string, source: string | undefined, caption: string, parent: string) {
    const url = notionPreviewUrl(source), label = caption || fileLabel(url, type);
    if (!url) {add('text', parent, {title: [[label]]}); return;}
    // PDF has an accessible attachment link; no extra PDF worker or credentials.
    if (type === 'file' || type === 'pdf') add('file', parent, {title: richMarkdown(label), source: [[url]], size: []});
    else add(type as 'image' | 'audio' | 'video', parent, {source: [[url]], caption: richMarkdown(caption), alt_text: [[caption || label]]});
  }
  function table(rows: Decoration[][][], parent: string, header: boolean, rowHeader = false) {
    const columns = Array.from({length: Math.max(0, ...rows.map(row => row.length))}, (_, index) => `column${index}`);
    const block = add('table', parent, {}, {table_block_column_order: columns, table_block_column_header: header, table_block_row_header: rowHeader});
    for (const row of rows) add('table_row', block.id, Object.fromEntries(columns.map((column, i) => [column, row[i] || []])));
  }
  function md(nodes: RootContent[], parent: string) {
    for (const node of nodes) {
      if (node.type === 'paragraph' || node.type === 'heading') {
        if (node.type === 'paragraph' && node.children.some(child => child.type === 'image')) {
          let text: PhrasingContent[] = [];
          for (const child of node.children) {
            if (child.type === 'image') {if (text.length) add('text', parent, {title: rich(text)}); text = []; asset('image', child.url, child.alt || '', parent);}
            else text.push(child);
          }
          if (text.length) add('text', parent, {title: rich(text)});
        } else if (node.type === 'paragraph' && node.children.length === 1 && node.children[0].type === 'inlineCode' && node.children[0].data?.hProperties?.dataMathDisplay === 'true') {
          const math = node.children[0];
          add(math.data?.hProperties?.dataMathClosed === 'true' ? 'equation' : 'text', parent, {title: [[math.data?.hProperties?.dataMathClosed === 'true' ? math.value.slice(2, -2) : math.value]]});
        } else add(node.type === 'heading' ? node.depth === 1 ? 'header' : node.depth === 2 ? 'sub_header' : 'sub_sub_header' : 'text', parent, {title: rich(node.children)});
      } else if (node.type === 'list') {
        for (const item of node.children) {
          const [first, ...rest] = item.children;
          const block = add(item.checked !== null && item.checked !== undefined ? 'to_do' : node.ordered ? 'numbered_list' : 'bulleted_list', parent,
            {title: first?.type === 'paragraph' ? rich(first.children) : [], ...(item.checked === null || item.checked === undefined ? {} : {checked: [[item.checked ? 'Yes' : 'No']]})});
          md(first?.type === 'paragraph' ? rest : item.children, block.id);
        }
      } else if (node.type === 'blockquote') {
        const [first, ...rest] = node.children;
        const quote = add('quote', parent, {title: first?.type === 'paragraph' ? rich(first.children) : []});
        md(first?.type === 'paragraph' ? rest : node.children, quote.id);
      } else if (node.type === 'code') add('code', parent, {title: [[node.value]], language: [[node.lang || 'plain text']], caption: []});
      else if (node.type === 'thematicBreak') add('divider', parent);
      else if (node.type === 'table') table(node.children.map(row => row.children.map(cell => rich(cell.children))), parent, true);
      else if (node.type === 'html') add('text', parent, {title: [[node.value]]});
      else if (node.type !== 'definition' && 'children' in node) md(node.children as RootContent[], parent);
    }
  }
  function markup(nodes: MarkupNode[], parent: string) {
    let text = '';
    const flush = () => {if (text.trim()) md(parseMarkdown(dedent(text)).children, parent); text = '';};
    for (const node of nodes) {
      if (!isTag(node) || !STRUCTURAL.has(node.name)) {text += markupText(node); continue;}
      flush();
      const name = node.name, attrs = node.attribs;
      if (['file', 'pdf', 'audio', 'video', 'image'].includes(name)) asset(name, attrs.src || attrs.url, rawText(node.children).trim() || attrs.alt || '', parent);
      else if (name === 'empty-block') add('text', parent, {title: [['\u00a0']]});
      else if (name === 'hr') add('divider', parent);
      else if (name === 'callout') {
        const block = add('callout', parent, {title: []}, {page_icon: attrs.icon && !/[:/]/.test(attrs.icon) ? attrs.icon : undefined});
        markup(node.children, block.id);
      } else if (name === 'details') {
        const summary = node.children.find(child => isTag(child) && child.name === 'summary');
        const block = add('toggle', parent, {title: summary && isTag(summary) ? richMarkdown(rawText(summary.children)) : []});
        markup(node.children.filter(child => child !== summary), block.id);
      } else if (name === 'columns') {
        const columns = node.children.filter(child => isTag(child) && child.name === 'column') as Tag[];
        const block = add('column_list', parent);
        for (const column of columns) markup(column.children, add('column', block.id, {}, {column_ratio: 1 / columns.length}).id);
      } else if (name === 'table') {
        const rows: Tag[] = [];
        function findRows(children: MarkupNode[]) {for (const child of children) if (isTag(child)) {if (child.name === 'tr') rows.push(child); else findRows(child.children);}}
        findRows(node.children);
        table(rows.map(row => row.children.filter(child => isTag(child) && (child.name === 'td' || child.name === 'th')).map(cell => richMarkdown((cell as Tag).children.map(markupText).join('')))), parent,
          attrs['header-row'] === 'true' || attrs['header-row'] === '' || rows[0]?.children.some(child => isTag(child) && child.name === 'th') || false,
          attrs['header-column'] === 'true' || attrs['header-column'] === '');
      }
    }
    flush();
  }
  const source = protectLiterals(markdown).replace(/<(br|hr)\s*\/?\s*>/gi, '<$1/>');
  markup(parseDocument(source, {xmlMode: true, decodeEntities: true, recognizeSelfClosing: true}).children, root.id);
  return map;
}

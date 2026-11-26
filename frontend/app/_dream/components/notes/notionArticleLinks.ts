// [Sync] 2026-11-25: encode Calendar titles as Markdown links inside the supported text-cell content.
// [Sync] 2026-11-25: resolve the selected Calendar page to an insertable article URL.
// [Input] Unmodified Writing TextCell prose.
// [Output] Ordered source ranges, original URLs and page identities for inline Notion articles.
// [Pos] Local presentation only. The connector owns page authorization.
import type {TextCell} from '../../engine/EditorEngine';

export interface NotionArticleLink {
  start: number;
  end: number;
  href: string;
  pageId: string;
  label: string;
}

const uuid = '[a-f0-9]{8}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{12}|[a-f0-9]{32}';
const pageSegment = new RegExp(`^(?:(.+)-)?(${uuid})$`, 'i');
const pageParameter = new RegExp(`^(?:${uuid})$`, 'i');
const adjacentProse = new RegExp(`((?:${uuid}))(?=[\\p{Script=Han}\\p{Script=Hiragana}\\p{Script=Katakana}\\p{Script=Hangul}])`, 'iu');
// A block UUID is complete before surrounding sentence punctuation.
const blockWithPunctuation = new RegExp(`(#(?:${uuid}))[.,!;:'\\])]+$`, 'i');
const articleHosts = new Set(['notion.so', 'www.notion.so', 'app.notion.com', 'notion.site']);

function findBareLinks(text: string): NotionArticleLink[] {
  if (!text.includes('://')) return [];
  const links: NotionArticleLink[] = [];
  // Consume ordinary URLs as a whole so a Notion URL inside their query is still ordinary text.
  const tokens = /(?<![a-z\d+.-])[a-z][a-z\d+.-]*:\/\/[^\s<>"`“”‘’【】《》。，！？；：（）]+/giu;
  let match: RegExpExecArray | null;
  while ((match = tokens.exec(text)) !== null) {
    const candidate = match[0];
    const authority = /^https:\/\/([^/?#]+)/i.exec(candidate)?.[1];
    if (!authority || authority.includes('@') || candidate.includes('\\')) continue;
    // A compact page or block ID may directly precede unspaced CJK prose.
    const boundary = adjacentProse.exec(candidate);
    const token = boundary ? candidate.slice(0, boundary.index + boundary[0].length) : candidate;
    let href = token;
    const block = blockWithPunctuation.exec(token);
    if (block) href = token.slice(0, block.index + block[1].length);
    else if (!/[?#]/.test(token)) href = token.replace(/[.,!;:'\])]+$/, '');
    else if ((text[match.index - 1] === '(' && token.endsWith(')'))
      || (text[match.index - 1] === '[' && token.endsWith(']'))) href = token.slice(0, -1);
    let url: URL;
    try { url = new URL(href); } catch { continue; }
    if ((!articleHosts.has(url.hostname) && !/^(?:[a-z0-9-]+\.)+notion\.site$/i.test(url.hostname))
      || url.port) continue;
    const segments = url.pathname.split('/').filter(Boolean);
    if (!segments.length || segments.length > 2) continue;
    const segment = pageSegment.exec(segments[segments.length - 1]);
    if (!segment) continue;
    const target = url.searchParams.get('p');
    if (target !== null && !pageParameter.test(target)) continue;
    const pageId = (target ?? segment[2]).replaceAll('-', '').toLowerCase();
    let title = target ? '' : segment[1] ?? '';
    try { title = decodeURIComponent(title).replaceAll('-', ' '); } catch { /* Keep source spelling. */ }
    if (boundary) tokens.lastIndex = match.index + href.length;
    links.push({start: match.index, end: match.index + href.length, href, pageId, label: title || `Notion · ${pageId.slice(-8)}`});
  }
  return links;
}

/** Angle-bracket destinations keep the original query and fragment, including literal parentheses. */
export function formatNotionArticleLink(href: string, title: string): string {
  const label = title.replace(/[\r\n]+/g, ' ').replace(/[\\[\]]/g, '\\$&');
  return `[${label}](<${href}>)`;
}

export function findNotionArticleLinks(text: string): NotionArticleLink[] {
  if (!text.includes('](<')) return findBareLinks(text);
  const links: NotionArticleLink[] = [];
  let cursor = 0;
  function appendBare(end: number) {
    for (const link of findBareLinks(text.slice(cursor, end))) {
      links.push({...link, start: cursor + link.start, end: cursor + link.end});
    }
  }
  const named = /\[((?:\\[^\r\n]|[^\\[\]\r\n])+)\]\(<([^<>\s]+)>\)/g;
  for (const match of text.matchAll(named)) {
    const href = match[2];
    const [link] = findBareLinks(href);
    if (link?.href !== href) continue;
    appendBare(match.index);
    cursor = match.index + match[0].length;
    links.push({...link, start: match.index, end: cursor, label: match[1].replace(/\\([\\[\]])/g, '$1')});
  }
  appendBare(text.length);
  return links;
}

/** Recover a draft from the client that put article titles outside the published Session schema. */
export function recoverNotionArticleDraft(cell: TextCell): TextCell {
  if (!('notionArticleTitles' in cell)) return cell;
  const {notionArticleTitles, ...restored} = cell;
  if (notionArticleTitles && typeof notionArticleTitles === 'object') {
    const titles = notionArticleTitles as Record<string, unknown>;
    for (const link of findNotionArticleLinks(cell.content).reverse()) {
      const title = titles[link.href];
      if (typeof title !== 'string' || !title.trim()) continue;
      restored.content = restored.content.slice(0, link.start) + formatNotionArticleLink(link.href, title) + restored.content.slice(link.end);
    }
  }
  return restored;
}

/** Keep a matching original URL; a selected page without one can still use its canonical page ID. */
export function calendarArticleHref(pageId: string, url: string | null): string | null {
  if (!pageParameter.test(pageId)) return null;
  const id = pageId.replaceAll('-', '').toLowerCase();
  const original = url ? findNotionArticleLinks(url)[0] : undefined;
  return original?.pageId === id && original.href === url ? url : `https://www.notion.so/${id}`;
}

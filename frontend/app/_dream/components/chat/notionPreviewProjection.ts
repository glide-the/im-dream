// [Sync] 2026-11-18: preserve Read identity/numbering and prefer readable prose in document-card excerpts.
// [Input] Original Read tool DTO and notion_read_hook.py page JSON, including Claude line-numbered text.
// [Output] A display-only page projection or null for unrelated, partial and identity-conflicting results.
// [Pos] Chat Notion result matcher; server Read/index checks retain authorization ownership.
// [Sync] 2026-11-18: recognize existing page/redirect paths without fetching or executing tools.
import type {DynamicToolUIPart, ToolUIPart} from 'ai';
import {resolveToolName} from './toolConfirmation';
import {readToolInput} from './toolPartPresentation';

type JsonObject = Record<string, unknown>;
export interface NotionWorkspacePreviewData {
  pageId: string;
  title: string;
  markdown: string;
  state: 'ready' | 'error';
  failure: 'access' | 'scope' | 'failed';
  payload: JsonObject | null;
}
// Mirrors the existing Notion Read hook path contract, not a configurable filesystem location.
const PAGE_ID = '[0-9a-fA-F]{32}|[0-9a-fA-F]{8}(?:-[0-9a-fA-F]{4}){3}-[0-9a-fA-F]{12}';
const PAGE_PATH = new RegExp(`(?:^|/)\\.notion/pages/(${PAGE_ID})\\.json$`);
const REDIRECT_PATH = /(?:^|\/)\.claude-tmp\/notion-read-[\w-]+\.json$/;
const pageIdentity = (value: string) => value.replaceAll('-', '').toLowerCase();
const object = (value: unknown): value is JsonObject => Boolean(value && typeof value === 'object' && !Array.isArray(value));

function readPayload(output: unknown): JsonObject | null {
  if (object(output)) return output;
  if (typeof output !== 'string') return null;
  let text = output.trim();
  try { const parsed: unknown = JSON.parse(text); return object(parsed) ? parsed : null; } catch { /* Read adds line numbers. */ }
  const lines = text.split(/\r?\n/);
  const body: string[] = [];
  let nextLine: number | undefined;
  let separator: string | undefined;
  for (const line of lines) {
    const numbered = /^[ \t]*(\d+)(→|\t)(.*)$/.exec(line);
    if (numbered) {
      const lineNumber = Number(numbered[1]);
      if (nextLine === undefined) {
        if (lineNumber !== 0 && lineNumber !== 1) return null;
        nextLine = lineNumber;
        separator = numbered[2];
      }
      if (lineNumber !== nextLine || numbered[2] !== separator) return null;
      nextLine += 1;
      body.push(numbered[3]);
    } else if (body.length && line.startsWith('<system-reminder>')) break;
    else if (line.trim()) return null;
  }
  if (!body.length) return null;
  text = body.join('\n');
  try { const parsed: unknown = JSON.parse(text); return object(parsed) ? parsed : null; } catch { return null; }
}

export function resolveNotionWorkspacePreview(part: ToolUIPart | DynamicToolUIPart): NotionWorkspacePreviewData | null {
  if (resolveToolName(part) !== 'Read') return null;
  const input = readToolInput(part);
  if (!object(input) || typeof input.file_path !== 'string') return null;
  const path = input.file_path;
  if (path.split('/').some(segment => segment === '..' || segment === '.') || path.includes('\\')) return null;
  const match = PAGE_PATH.exec(path);
  if (!match && !REDIRECT_PATH.test(path)) return null;
  const complete = part.state === 'output-available' || part.state === 'output-error';
  if (!complete) return null;
  const payload = readPayload('output' in part ? part.output : undefined);
  if (!payload || typeof payload.page_id !== 'string' || !new RegExp(`^(?:${PAGE_ID})$`).test(payload.page_id)) return null;
  if (match && pageIdentity(match[1]) !== pageIdentity(payload.page_id)) return null;
  if (typeof payload.ok !== 'boolean' || (payload.ok && (part.state === 'output-error' || typeof payload.markdown !== 'string'))) return null;
  if (!payload.ok && typeof payload.code !== 'string') return null;
  const markdown = payload.ok ? payload.markdown as string : '';
  const title = typeof payload.title === 'string' ? payload.title.trim() : '';
  const code = typeof payload.code === 'string' ? payload.code : '';
  return {pageId: payload.page_id, title, markdown, payload, state: payload.ok ? 'ready' : 'error',
    failure: /AUTH|PERMISSION|CREDENTIAL/.test(code) ? 'access' : code === 'NOTION_RESOURCE_NOT_SELECTED' ? 'scope' : 'failed'};
}

// Local presentation budget keeps collapsed cards small; it does not limit page data or downloads.
const EXCERPT_CHARACTERS = 280;
export function notionPreviewExcerpt(markdown: string, title?: string): string {
  // Remove complete resource markup before truncation so a long signed URL cannot leak into the excerpt.
  const lines = markdown.trim().split('\n');
  if (title && /^#{1,6}\s+/.test(lines[0]) && lines[0].replace(/^#{1,6}\s+/, '').trim() === title.trim()) lines.shift();
  const source = lines.join('\n');
  // Prefer prose in a collapsed card; code/table-only pages keep their readable text fallback.
  const prose = source.replace(/^[ \t]*(`{3,}|~{3,})[^\n]*\n[\s\S]*?^[ \t]*\1[ \t]*\r?$/gm, ' ')
    .replace(/^[ \t]*\|[^\n]*\|[ \t]*\r?$/gm, ' ');
  const plain = (text: string) => text.replace(/!\[([^\]]*)\]\([^)]*\)/g, '$1').replace(/\[([^\]]+)\]\([^)]*\)/g, '$1')
    .replace(/<[^>]*>/g, '').replace(/https?:\/\/[^\s<>"']+/g, '')
    .replace(/[#*`_>|]/g, '').replace(/\s+/g, ' ').trim();
  return (plain(prose) || plain(source)).slice(0, EXCERPT_CHARACTERS);
}

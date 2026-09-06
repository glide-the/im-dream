// [Input] Hook-published character/scene Markdown documents with optional YAML frontmatter.
// [Output] Presentation-only metadata rows and Markdown body for the Execution focus reader.
// [Pos] Story Workspace asset document rendering seam; canonical files remain unchanged.

import { parse } from 'yaml';

export interface StoryWorkspaceAssetMetadataRow {
  readonly key: string;
  readonly label: string;
  readonly value: string;
}

export interface StoryWorkspaceAssetDocumentViewModel {
  readonly body: string;
  readonly metadata: readonly StoryWorkspaceAssetMetadataRow[];
  readonly metadataFallback: string | null;
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === 'object' && value !== null && !Array.isArray(value);
}

function scalarText(value: unknown): string | null {
  if (value === null) return '—';
  if (typeof value === 'string') return value;
  if (typeof value === 'number' || typeof value === 'boolean') return String(value);
  return null;
}

function appendMetadataRows(
  value: unknown,
  path: readonly string[],
  rows: StoryWorkspaceAssetMetadataRow[],
): void {
  const scalar = scalarText(value);
  if (scalar !== null) {
    const label = path.length > 0 ? path.join(' / ') : '值';
    rows.push({ key: path.join('.'), label, value: scalar });
    return;
  }

  if (Array.isArray(value)) {
    const scalarItems = value.map(scalarText);
    if (scalarItems.every((item) => item !== null)) {
      const label = path.length > 0 ? path.join(' / ') : '值';
      rows.push({
        key: path.join('.'),
        label,
        value: scalarItems.length > 0 ? scalarItems.join('、') : '—',
      });
      return;
    }
    value.forEach((item, index) => appendMetadataRows(item, [...path, String(index + 1)], rows));
    return;
  }

  if (isRecord(value)) {
    Object.entries(value).forEach(([key, item]) => appendMetadataRows(item, [...path, key], rows));
  }
}

function splitFrontmatter(content: string): { body: string; frontmatter: string | null } {
  const normalized = content.replaceAll('\r\n', '\n');
  const lines = normalized.split('\n');
  if (lines[0]?.trim() !== '---') return { body: normalized, frontmatter: null };

  const closingIndex = lines.findIndex((line, index) => index > 0 && line.trim() === '---');
  if (closingIndex < 0) return { body: normalized, frontmatter: null };
  return {
    body: lines.slice(closingIndex + 1).join('\n').trim(),
    frontmatter: lines.slice(1, closingIndex).join('\n'),
  };
}

/**
 * Keep YAML out of the Markdown parser so document separators cannot become
 * headings. Unknown nested fields remain visible through generic flattened rows.
 */
export function storyWorkspaceBuildAssetDocumentViewModel(
  content: string,
): StoryWorkspaceAssetDocumentViewModel {
  const { body, frontmatter } = splitFrontmatter(content);
  if (frontmatter === null) return { body, metadata: [], metadataFallback: null };

  try {
    const rows: StoryWorkspaceAssetMetadataRow[] = [];
    appendMetadataRows(parse(frontmatter, { maxAliasCount: 0 }), [], rows);
    return {
      body,
      metadata: rows,
      metadataFallback: rows.length > 0 ? null : frontmatter,
    };
  } catch {
    return { body, metadata: [], metadataFallback: frontmatter };
  }
}

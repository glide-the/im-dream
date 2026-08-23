// [Input] Untrusted Markdown URL strings emitted by Chat users or Agents.
// [Output] Parse exact workspace://files/... references into canonical Thread-workspace-relative paths without network access.
// [Pos] workspace URI protocol parser in frontend/src/components/chat
// [Sync] 2026-08-22: initial strict parser for decoded Unicode/space paths, traversal and repeated-encoding rejection, and image type classification.

export const WORKSPACE_URI_PREFIX = 'workspace://';

const PERCENT_ENCODED_SEPARATOR = /%(?:2f|5c)/i;
const PERCENT_ESCAPE = /%[0-9a-f]{2}/i;
const WINDOWS_DRIVE_SEGMENT = /^[a-z]:$/i;
const INLINE_IMAGE_EXTENSIONS = new Set(['.gif', '.jpeg', '.jpg', '.png', '.webp']);

export type WorkspaceUriErrorCode =
  | 'not_workspace_uri'
  | 'empty_path'
  | 'absolute_path'
  | 'encoded_separator'
  | 'malformed_encoding'
  | 'repeated_encoding'
  | 'unsupported_syntax'
  | 'invalid_segment'
  | 'unsupported_namespace';

export type WorkspaceUriParseResult =
  | {
      readonly ok: true;
      readonly path: string;
      readonly fileName: string;
      readonly canPreviewImage: boolean;
    }
  | {
      readonly ok: false;
      readonly code: WorkspaceUriErrorCode;
    };

export function isWorkspaceUri(value: string | null | undefined): value is string {
  return typeof value === 'string' && value.startsWith(WORKSPACE_URI_PREFIX);
}

function invalid(code: WorkspaceUriErrorCode): WorkspaceUriParseResult {
  return { ok: false, code };
}

function containsControlCharacter(value: string): boolean {
  return [...value].some((character) => {
    const codePoint = character.codePointAt(0) ?? 0;
    return codePoint <= 0x1f || codePoint === 0x7f;
  });
}

export function parseWorkspaceUri(value: string): WorkspaceUriParseResult {
  if (!isWorkspaceUri(value)) return invalid('not_workspace_uri');

  const encodedPath = value.slice(WORKSPACE_URI_PREFIX.length);
  if (!encodedPath) return invalid('empty_path');
  if (encodedPath.startsWith('/')) return invalid('absolute_path');
  if (encodedPath.includes('?') || encodedPath.includes('#')) return invalid('unsupported_syntax');
  if (PERCENT_ENCODED_SEPARATOR.test(encodedPath)) return invalid('encoded_separator');

  let decodedPath: string;
  try {
    decodedPath = decodeURIComponent(encodedPath);
  } catch {
    return invalid('malformed_encoding');
  }

  if (PERCENT_ESCAPE.test(decodedPath)) return invalid('repeated_encoding');
  if (decodedPath.startsWith('/')) return invalid('absolute_path');
  if (
    decodedPath.includes('\\')
    || decodedPath.includes('?')
    || decodedPath.includes('#')
    || containsControlCharacter(decodedPath)
  ) {
    return invalid('unsupported_syntax');
  }

  const segments = decodedPath.split('/');
  if (
    segments.length < 2
    || segments.some((segment) => !segment || segment === '.' || segment === '..')
    || WINDOWS_DRIVE_SEGMENT.test(segments[0])
  ) {
    return invalid('invalid_segment');
  }
  if (segments[0] !== 'files') return invalid('unsupported_namespace');

  const path = segments.join('/');
  const fileName = segments.at(-1) ?? '';
  const lowerName = fileName.toLocaleLowerCase('en-US');
  const extension = [...INLINE_IMAGE_EXTENSIONS].find((candidate) => lowerName.endsWith(candidate));
  return {
    ok: true,
    path,
    fileName,
    canPreviewImage: extension !== undefined,
  };
}

// [Input] Unknown values thrown by browser APIs and backend response parsing.
// [Output] A safe user-facing error string without assuming the thrown value shape.
// [Pos] Shared frontend error normalization boundary.

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === 'object' && value !== null;
}

function readMessage(value: unknown): string | null {
  if (typeof value === 'string' && value.length > 0) return value;
  if (!isRecord(value)) return null;

  for (const key of ['error_description', 'error', 'message']) {
    const candidate = value[key];
    if (typeof candidate === 'string' && candidate.length > 0) return candidate;
  }
  return null;
}

export function getErrorMessage(error: unknown, fallback: string): string {
  if (error instanceof Error && error.message.length > 0) return error.message;
  if (!isRecord(error)) return fallback;
  return readMessage(error.detail) ?? readMessage(error) ?? fallback;
}

// [Input] Original Writing EditorState and a public text-only snapshot DTO.
// [Output] Ordered prose projection and matching SHA-256 for server-side saved-content checks.
// [Pos] Note sharing projection; editor identities, widgets and Agent state stay private.
export interface NoteSnapshot {title: string; created_at: string | null; paragraphs: string[]}
export interface NoteShareSource {sessionId: string; snapshot: NoteSnapshot}
export function projectNote(state: {id: string; createdAt?: string; cells: {type: string; content?: string}[]}): NoteShareSource {
  const paragraphs = state.cells.filter(cell => cell.type === 'text').map(cell => cell.content ?? '');
  const title = Array.from(paragraphs.join('\n\n').split('\n').map(line => line.trim()).find(Boolean) ?? '').slice(0, 100).join('');
  return {sessionId: state.id, snapshot: {title, created_at: state.createdAt ?? null, paragraphs}};
}
export async function noteContentDigest(note: NoteSnapshot): Promise<string> {
  const bytes = new TextEncoder().encode(note.paragraphs.join('\n\n'));
  const digest = await crypto.subtle.digest('SHA-256', bytes);
  return Array.from(new Uint8Array(digest), byte => byte.toString(16).padStart(2, '0')).join('');
}

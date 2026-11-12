// [Input] Frozen note prose, expected digest and stable publication request key.
// [Output] Admin-owned immutable share publication through the original authenticated route.
// [Pos] Note adapter to the unified external-share API.
import {publishShare} from './externalShareApi';
import {noteContentDigest, type NoteShareSource} from '../components/notes/noteShare';
export async function createNoteShare(source: NoteShareSource, signal: AbortSignal, requestKey: string, transport: typeof fetch = fetch) {
  const digest = await noteContentDigest(source.snapshot);
  return publishShare(`/api/sessions/${encodeURIComponent(source.sessionId)}/share`, {content_sha256: digest, request_key: requestKey}, transport, signal);
}

// [Input] Validated public account ID, original composer state and iOS Settings.
// [Output] Account-scoped Thread selection, unsent text and completed attachment references.
// [Pos] Native Chat restoration adapter; task state and ownership stay with the original server reads.
// [Sync] 2026-11-02: retain only restorable input metadata; selection changes retire old composer writers.
// [Sync] 2026-11-02: retain one main-owned side pointer and verify the original Writing source through its existing GET.
import {Platform,Settings} from 'react-native';
import {z} from 'zod';
import {BackendRuntimeManager} from '../../../../src/runtime/BackendRuntimeManager';
import type {ComposerDraftSnapshot} from './useComposerDraft';
import {browserRequestHeaders} from '../../lib/browserSession';
import {apiUrl} from '../../lib/apiBase';
import type {EditorJumpToCellDetail} from './editorWriteTools';

const key='ink-native-chat-recovery';
const fileSchema=z.strictObject({
  id:z.string().min(1),name:z.string(),mimeType:z.string(),size:z.number().finite().nonnegative(),storageKey:z.string().min(1),
  workspacePath:z.string().optional(),savedAt:z.string().optional(),hash:z.string().optional(),uploadSource:z.enum(['click','paste','drag']).optional(),
});
const composerSchema=z.strictObject({query:z.string(),uploadedFiles:z.array(fileSchema),toolChoice:z.enum(['auto','none','manual']),interruptedFiles:z.array(z.string())});
const sideChatSchema=z.strictObject({threadId:z.string().min(1),writingSessionId:z.string().min(1).optional()});
const slotSchema=z.strictObject({threadId:z.string().min(1).nullable(),composer:composerSchema.optional(),sideChat:sideChatSchema.optional()});
const recordSchema=z.strictObject({ownerId:z.string().min(1),slots:z.record(z.string(),slotSchema)});
type Slot=z.infer<typeof slotSchema>;
export type NativeSideChatPointer=z.infer<typeof sideChatSchema>;

export function createNativeChatRecovery(ownerId:string,initialThreadId?:string) {
  if(!ownerId)throw Error('NATIVE_CHAT_OWNER_REQUIRED');
  const scope=initialThreadId?`thread:${initialThreadId}`:'main';
  let composerRevision=0;
  function record() {
    const empty={ownerId,slots:{} as Record<string,Slot>};
    try {
      if(Platform.OS!=='ios')return empty;
      const raw:unknown=Settings.get(key);
      if(typeof raw!=='string'||!raw)return empty;
      let value:unknown;
      try {value=JSON.parse(raw);} catch {BackendRuntimeManager.recordError('recovery',Error('NATIVE_CHAT_RECOVERY_JSON_INVALID'));return empty;}
      const parsed=recordSchema.safeParse(value);
      if(!parsed.success){BackendRuntimeManager.recordError('recovery',Error('NATIVE_CHAT_RECOVERY_SCHEMA_INVALID'));return empty;}
      if(parsed.data.ownerId===ownerId)return parsed.data;
    } catch {BackendRuntimeManager.recordError('recovery',Error('NATIVE_CHAT_RECOVERY_READ_FAILED'));}
    return empty;
  }
  function read():Slot {
    const slot=record().slots[scope];
    if(initialThreadId&&slot?.threadId!==initialThreadId)return {threadId:initialThreadId};
    return slot??{threadId:initialThreadId??null};
  }
  function write(patch:Partial<Slot>) {
    try {
      if(Platform.OS!=='ios')return;
      const next=record();next.slots[scope]={...(next.slots[scope]??{threadId:initialThreadId??null}),...patch};
      Settings.set({[key]:JSON.stringify(next)});
    } catch {BackendRuntimeManager.recordError('recovery',Error('NATIVE_CHAT_RECOVERY_WRITE_FAILED'));}
  }
  return {
    read,
    // User navigation resets the original input instance. Late effects from that instance cannot restore it.
    selectThread(threadId:string|null) {composerRevision++;write({threadId,composer:undefined,...(!initialThreadId?{sideChat:undefined}:{})});},
    rememberThread(threadId:string) {write({threadId});},
    readSideChat():NativeSideChatPointer|null {return initialThreadId?null:read().sideChat??null;},
    rememberSideChat(pointer:NativeSideChatPointer) {if(!initialThreadId)write({sideChat:{threadId:pointer.threadId,...(pointer.writingSessionId?{writingSessionId:pointer.writingSessionId}:{})}});},
    clearSideChat(expected?:NativeSideChatPointer) {
      if(initialThreadId)return;
      const current=read().sideChat;
      if(!current)return;
      if(expected&&(current.threadId!==expected.threadId||current.writingSessionId!==expected.writingSessionId))return;
      write({sideChat:undefined});
    },
    async readWritingTarget(pointer:NativeSideChatPointer,transport:typeof fetch,signal?:AbortSignal):Promise<EditorJumpToCellDetail> {
      if(initialThreadId||!pointer.writingSessionId)throw Error('NATIVE_CHAT_WRITING_SOURCE_UNAVAILABLE');
      try {
        const response=await transport(apiUrl(`/api/sessions/${encodeURIComponent(pointer.writingSessionId)}`),{headers:browserRequestHeaders(),signal});
        if(!response.ok)throw Error('NATIVE_CHAT_WRITING_SOURCE_UNAVAILABLE');
        const source=z.object({id:z.string(),editor_state:z.object({id:z.string(),writingThreadId:z.string(),cells:z.array(z.object({id:z.string().min(1)}))})}).safeParse(await response.json());
        if(!source.success||source.data.id!==pointer.writingSessionId||source.data.editor_state.id!==pointer.writingSessionId||source.data.editor_state.writingThreadId!==pointer.threadId||!source.data.editor_state.cells[0])throw Error('NATIVE_CHAT_WRITING_SOURCE_UNAVAILABLE');
        return {editorSessionId:pointer.writingSessionId,cellId:source.data.editor_state.cells[0].id};
      } catch {
        if(!signal?.aborted)BackendRuntimeManager.recordError('recovery',Error('NATIVE_CHAT_WRITING_SOURCE_UNAVAILABLE'));
        throw Error('NATIVE_CHAT_WRITING_SOURCE_UNAVAILABLE');
      }
    },
    composer() {
      const revision=composerRevision;
      return {initial:read().composer,write(draft:ComposerDraftSnapshot) {
        if(revision!==composerRevision)return;
        const uploadedFiles=draft.uploadedFiles.filter(file=>!file.isUploading&&file.storageKey).map(file=>({
          id:file.id,name:file.name,mimeType:file.mimeType,size:file.size,storageKey:file.storageKey!,
          workspacePath:file.workspacePath,savedAt:file.savedAt,hash:file.hash,uploadSource:file.uploadSource,
        }));
        write({composer:{query:draft.query,uploadedFiles,toolChoice:draft.toolChoice,
          interruptedFiles:draft.uploadedFiles.filter(file=>file.isUploading||!file.storageKey).map(file=>file.name)}});
      }};
    },
  };
}
export type NativeChatRecovery=ReturnType<typeof createNativeChatRecovery>;

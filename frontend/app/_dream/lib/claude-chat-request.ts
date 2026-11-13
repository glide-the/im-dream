// [Sync] 2026-11-13: serialize copied per-message tools through the shared Web/native request builder.
// [Input] Original ChatPanel context, pending attachments/tool choice and the outgoing UIMessage.
// [Output] The public Claude Chat request body with explicit per-message tools shared by Web and native callers.
// [Pos] DTO construction only; no submission, runtime, credentials or permission-policy ownership.
import type {UIMessage} from 'ai';
import type {ChatApiSchemaRequestBody,ChatToolDescriptor,ToolChoice} from './chat-schema';
import type {Attachment} from '../components/chat/AIInputDock.helpers';
import {toFileProxyUrl} from './toFileProxyUrl';
export interface ClaudeChatRequestContext {
  deckId?:string;voiceId?:string;voiceSystemPrompt?:string;settingsSystemPrompt?:string;
  editorState?:Record<string,unknown>|null;imFullAccessEnabled:boolean;currentToolChoice:ToolChoice;
  tools?:readonly ChatToolDescriptor[];
}
export function buildClaudeChatRequest({id,message,context,attachments=[],toolChoice}:{id:string;message:UIMessage;context:ClaudeChatRequestContext;attachments?:readonly Attachment[];toolChoice?:ToolChoice}):ChatApiSchemaRequestBody {
  return {id,...(context.deckId?{deckId:context.deckId}:{}),...(context.voiceId?{voiceId:context.voiceId}:{}),resume:true,message,
    toolChoice:context.imFullAccessEnabled?'auto':toolChoice ?? context.currentToolChoice,
    tools:(context.tools??[]).map(tool=>({...tool})),
    allowedAppDefaultToolkit:[],allowedMcpServers:{},
    attachments:attachments.filter(file=>file.storageKey).map(file=>({type:'file',url:toFileProxyUrl(file.storageKey!),storageKey:file.storageKey,mediaType:file.type,filename:file.name,size:file.size,workspacePath:file.workspacePath,savedAt:file.savedAt,hash:file.hash})),
    systemPrompt:context.voiceSystemPrompt ?? context.settingsSystemPrompt,
    ...(context.editorState!=null?{editor_state:context.editorState}:{}),
  };
}

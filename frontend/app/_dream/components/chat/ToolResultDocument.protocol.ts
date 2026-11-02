// [Sync] 2026-10-31: bind explicit document disposal and acknowledgement to the same document/Thread/tool/request identity.
// [Input] Original tool parts, selected Thread and fixed local document events.
// [Output] Tool/document-bound state, one-message Chat requests and editor confirmation notifications.
// [Pos] Specific DOM tool adapter; credentials, tool permissions and HTTP retain their existing owners.
import {isToolUIPart,type DynamicToolUIPart,type ToolUIPart} from 'ai';
import {z} from 'zod';
import {composerDocumentUrl} from './MarkdownInputDocument.protocol';
import {MCP_APPS_SANDBOX_PATH} from './mcp-apps/host-policy';
import {parseEditorJumpToCellDetail} from './editorWriteTools';
export type ToolPart=DynamicToolUIPart|ToolUIPart;
const id=z.string().min(1);
const binding={documentId:id,threadId:id,toolCallId:id};
const part=z.custom<ToolPart>(value=>Boolean(value&&typeof value==='object'&&'type' in value&&typeof value.type==='string'&&isToolUIPart(value as ToolPart)&&typeof (value as ToolPart).toolCallId==='string'));
const state=z.strictObject({type:z.literal('state'),...binding,revision:z.number().int().nonnegative(),part,
  presentation:z.enum(['app-only','editor']),editorCompleted:z.boolean(),settledToolCallIds:z.array(id),active:z.boolean(),theme:z.enum(['light','dark','system']),language:z.string()})
  .refine(value=>value.toolCallId===value.part.toolCallId);
const dispose=z.strictObject({type:z.literal('dispose'),...binding,requestId:id});
const result=z.strictObject({type:z.literal('result'),...binding,requestId:id,accepted:z.boolean()});
const text=z.strictObject({type:z.literal('text'),text:z.string().refine(value=>Boolean(value.trim()))});
const jump=z.custom<NonNullable<ReturnType<typeof parseEditorJumpToCellDetail>>>(value=>parseEditorJumpToCellDetail(value)!==null);
const event=z.discriminatedUnion('type',[
  z.strictObject({type:z.literal('ready'),documentId:id}),
  z.strictObject({type:z.literal('disposed'),...binding,requestId:id}),
  z.strictObject({type:z.literal('height'),...binding,height:z.number().positive().finite()}),
  z.strictObject({type:z.literal('session-expired'),...binding}),
  z.strictObject({type:z.literal('user-message'),...binding,requestId:id,message:z.strictObject({role:z.literal('user'),parts:z.array(text).min(1)})}),
  z.strictObject({type:z.literal('tool-result'),...binding,tool:z.string(),output:z.strictObject({approved:z.boolean()})}),
  z.strictObject({type:z.literal('confirmation-settled'),...binding}),
  z.strictObject({type:z.literal('editor-confirmed'),...binding}),
  z.strictObject({type:z.literal('editor-jump'),...binding,detail:jump}),
]);
export type ToolResultState=z.infer<typeof state>;
export type ToolResultDispose=z.infer<typeof dispose>;
export type ToolResultReply=z.infer<typeof result>;
export type ToolResultEvent=z.infer<typeof event>;
export const TOOL_RESULT_DOCUMENT_PATH='/native/tool-result';
export function toolResultDocumentUrl(origin:string):string {composerDocumentUrl(origin);return origin.replace(/\/$/,'')+TOOL_RESULT_DOCUMENT_PATH;}
export function readToolResultState(value:unknown):ToolResultState|null {const parsed=state.safeParse(value);return parsed.success?parsed.data:null;}
export function readToolResultDispose(value:unknown):ToolResultDispose|null {const parsed=dispose.safeParse(value);return parsed.success?parsed.data:null;}
export function readToolResultReply(value:unknown):ToolResultReply|null {const parsed=result.safeParse(value);return parsed.success?parsed.data:null;}
export function readToolResultEvent(raw:string):ToolResultEvent|null {try{const parsed=event.safeParse(JSON.parse(raw));return parsed.success?parsed.data:null;}catch{return null;}}
export function toolResultNavigationAllowed(url:string,isTopFrame:boolean|undefined,origin:string):boolean {
  if(url===toolResultDocumentUrl(origin))return true;
  if(isTopFrame!==false)return false;
  return url==='about:blank'||url==='about:srcdoc'||url.startsWith(origin.replace(/\/$/,'')+MCP_APPS_SANDBOX_PATH+'?');
}

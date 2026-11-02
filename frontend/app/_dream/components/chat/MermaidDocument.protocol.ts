// [Input] One Mermaid source revision and fixed local-document events.
// [Output] Document/revision-matched diagram, clipboard, preview and PNG operation messages.
// [Pos] Mermaid-only DOM adapter; no HTTP, account, tool or arbitrary file operation.
import {z} from 'zod';
import {composerDocumentUrl} from './MarkdownInputDocument.protocol';
const id=z.string().min(1),revision=z.number().int().nonnegative().safe();
const binding={documentId:id,revision};
const state=z.strictObject({type:z.literal('state'),...binding,chart:z.string(),expanded:z.boolean(),theme:z.enum(['light','dark','system']),language:z.string()});
const reply=z.strictObject({type:z.literal('result'),...binding,requestId:id,accepted:z.boolean()});
const request={...binding,requestId:id};
const events=z.discriminatedUnion('type',[
  z.strictObject({type:z.literal('ready'),documentId:id}),
  z.strictObject({type:z.literal('height'),...binding,height:z.number().positive().finite()}),
  z.strictObject({type:z.literal('preview'),...binding,open:z.boolean()}),
  z.strictObject({type:z.literal('copy'),...request,text:z.string()}),
  z.strictObject({type:z.literal('png'),...request,name:z.string().regex(/^mermaid-diagram-[0-9]+\.png$/),base64:z.string().startsWith('iVBORw0KGgo').regex(/^[A-Za-z0-9+/]+={0,2}$/)}),
]);
export type MermaidDocumentState=z.infer<typeof state>;
export type MermaidDocumentReply=z.infer<typeof reply>;
export type MermaidDocumentEvent=z.infer<typeof events>;
export function mermaidDocumentUrl(origin:string):string {composerDocumentUrl(origin);return origin.replace(/\/$/,'')+'/native/mermaid';}
export function readMermaidState(raw:unknown):MermaidDocumentState|null {const value=state.safeParse(raw);return value.success?value.data:null;}
export function readMermaidReply(raw:unknown):MermaidDocumentReply|null {const value=reply.safeParse(raw);return value.success?value.data:null;}
export function readMermaidEvent(raw:string):MermaidDocumentEvent|null {try{const value=events.safeParse(JSON.parse(raw));return value.success?value.data:null;}catch{return null;}}

// [Input] Original projected export DTOs and a fixed loopback document address.
// [Output] Document/job/delivery-matched image rendering events and opaque PNG handoff metadata.
// [Pos] Share-only protocol; no login, business mutation, arbitrary URL or filesystem commands.
import {z} from 'zod';
import {composerDocumentUrl} from './MarkdownInputDocument.protocol';
const identity=z.string().regex(/^[A-Za-z0-9_-]{1,128}$/);
const count=z.number().int().min(0).max(Number.MAX_SAFE_INTEGER),positive=count.min(1);
const optionalText=z.string().optional();
const tool=z.strictObject({kind:z.literal('tool'),toolName:z.string(),title:optionalText,summary:optionalText,status:z.enum(['executing','completed','error']),pendingLabel:optionalText,terminalLabel:optionalText,command:optionalText,output:optionalText,outputTruncated:z.boolean().optional(),exitCode:z.string().nullable().optional(),statusLabel:optionalText,isEditorWrite:z.boolean().optional()});
const question=z.strictObject({question:z.string(),required:z.boolean().optional(),description:optionalText,options:z.array(z.strictObject({label:z.string(),description:optionalText}))});
const pending=z.strictObject({kind:z.enum(['confirm','askuser','sandbox-network','reject-only']),title:z.string(),badge:z.string(),detail:optionalText,infoRows:z.array(z.string()).optional(),questions:z.array(question).optional(),primaryActionLabel:z.string(),secondaryActionLabel:z.string()});
const options=z.strictObject({threadId:identity,title:z.string(),messages:z.array(z.strictObject({role:z.enum(['user','assistant']),blocks:z.array(z.union([z.strictObject({kind:z.literal('text'),text:z.string()}),z.strictObject({kind:z.literal('reasoning'),text:z.string()}),tool])),files:z.array(z.string())})).min(1),labels:z.strictObject({you:z.string(),assistant:z.string(),footer:z.string(),thinking:z.string(),truncated:z.string(),workspaceImageUnavailable:z.string()}),pendingConfirmation:pending.nullable().optional()});
const png=z.strictObject({name:z.string().min(1).refine(value=>/\.png$/i.test(value)&&!/[\/\\\0\r\n]/.test(value)),base64:z.string().min(1).regex(/^(?:[A-Za-z0-9+/]{4})*(?:[A-Za-z0-9+/]{2}==|[A-Za-z0-9+/]{3}=)?$/),size:positive,width:positive,height:positive}).refine(value=>value.base64.startsWith('iVBORw0KGgo')&&value.base64.length/4*3-(value.base64.endsWith('==')?2:value.base64.endsWith('=')?1:0)===value.size);
const command=z.discriminatedUnion('type',[
 z.strictObject({type:z.literal('render'),documentId:identity,requestId:identity,options,language:z.string(),theme:z.enum(['light','dark','system'])}),
 z.strictObject({type:z.literal('prepare'),documentId:identity,requestId:identity,deliveryId:identity}),
 z.strictObject({type:z.literal('clear'),documentId:identity,requestId:identity}),
 z.strictObject({type:z.literal('workspaceImageResult'),documentId:identity,requestId:identity,imageId:identity,image:z.strictObject({type:z.string().regex(/^image\/[A-Za-z0-9.+-]+$/),base64:z.string().regex(/^(?:[A-Za-z0-9+/]{4})*(?:[A-Za-z0-9+/]{2}==|[A-Za-z0-9+/]{3}=)?$/)}).nullable()}),
]);
const event=z.discriminatedUnion('type',[
 z.strictObject({type:z.literal('ready'),documentId:identity}),
 z.strictObject({type:z.literal('progress'),documentId:identity,requestId:identity,done:count,total:positive}).refine(value=>value.done<=value.total),
 z.strictObject({type:z.literal('preview'),documentId:identity,requestId:identity,partial:z.boolean(),fileName:z.string(),images:z.array(png).min(1)}),
 z.strictObject({type:z.literal('prepared'),documentId:identity,requestId:identity,deliveryId:identity,images:z.array(png).min(1)}),
 z.strictObject({type:z.literal('workspaceImage'),documentId:identity,requestId:identity,imageId:identity,uri:z.string()}),
 z.strictObject({type:z.literal('failed'),documentId:identity,requestId:identity,deliveryId:identity.optional()}),
]);
export type ChatImageCommand=z.infer<typeof command>;
export type ChatImageEvent=z.infer<typeof event>;
export type ChatImagePNG=z.infer<typeof png>;
export function readChatImageCommand(value:unknown):ChatImageCommand|null {const result=command.safeParse(value);return result.success?result.data:null;}
export function readChatImageEvent(raw:string):ChatImageEvent|null {try{const result=event.safeParse(JSON.parse(raw));return result.success?result.data:null;}catch{return null;}}
export const CHAT_IMAGE_DOCUMENT_PATH='/native/chat-export';
export function chatImageDocumentUrl(origin:string):string {composerDocumentUrl(origin);return origin.replace(/\/$/,'')+CHAT_IMAGE_DOCUMENT_PATH;}

// [Input] Local sketch document events and the existing attachment-size rule.
// [Output] Document/request-matched PNG handoff and upload acknowledgement; no business commands or arbitrary paths.
// [Pos] Narrow adapter for the existing browser sketch component and native attachment owner.
import {MAX_UPLOAD_FILE_SIZE_BYTES} from './AIInputDock.helpers';
import {composerDocumentUrl} from './MarkdownInputDocument.protocol';
export const SKETCH_DOCUMENT_PATH='/native/sketch';
export interface SketchDocumentState {type:'state';documentId:string;revision:number;open:boolean;disabled:boolean;theme:'light'|'dark'|'system';language:string;}
export interface SketchDocumentResult {type:'result';documentId:string;requestId:string;accepted:boolean;}
export type SketchDocumentEvent={type:'ready'|'close';documentId:string}|{type:'add';documentId:string;requestId:string;name:string;size:number;base64:string};
const identity=(value:unknown):value is string=>typeof value==='string' && /^[\da-f]{8}-(?:[\da-f]{4}-){3}[\da-f]{12}$/i.test(value);
export function readSketchState(value:unknown):SketchDocumentState|null {
  if(!value || typeof value!=='object')return null;const state=value as Record<string,unknown>;
  return state.type==='state' && identity(state.documentId) && Number.isSafeInteger(state.revision) && (state.revision as number)>=0
    && typeof state.open==='boolean' && typeof state.disabled==='boolean' && ['light','dark','system'].includes(state.theme as string)
    && typeof state.language==='string' ? state as unknown as SketchDocumentState : null;
}
export function readSketchResult(value:unknown):SketchDocumentResult|null {
  if(!value || typeof value!=='object')return null;const result=value as Record<string,unknown>;
  return result.type==='result' && identity(result.documentId) && identity(result.requestId) && typeof result.accepted==='boolean' ? result as unknown as SketchDocumentResult : null;
}
export function readSketchEvent(raw:string):SketchDocumentEvent|null {
  if(raw.length>Math.ceil(MAX_UPLOAD_FILE_SIZE_BYTES/3)*4+8192)return null;
  let event:Record<string,unknown>;try {event=JSON.parse(raw);}catch{return null;}
  if(!event || typeof event!=='object' || !identity(event.documentId))return null;
  if(event.type==='ready' || event.type==='close')return event as SketchDocumentEvent;
  if(event.type!=='add' || !identity(event.requestId) || typeof event.name!=='string' || !event.name.toLowerCase().endsWith('.png')
    || /[\/\\\0\r\n]/.test(event.name) || typeof event.size!=='number' || !Number.isSafeInteger(event.size) || event.size<=0 || event.size>MAX_UPLOAD_FILE_SIZE_BYTES
    || typeof event.base64!=='string' || !event.base64.length || event.base64.length>Math.ceil(MAX_UPLOAD_FILE_SIZE_BYTES/3)*4
    || !/^(?:[A-Za-z0-9+/]{4})*(?:[A-Za-z0-9+/]{2}==|[A-Za-z0-9+/]{3}=)?$/.test(event.base64))return null;
  const size=event.base64.length/4*3-(event.base64.endsWith('==')?2:event.base64.endsWith('=')?1:0);
  return size===event.size ? event as SketchDocumentEvent : null;
}
export function sketchDocumentUrl(origin:string):string {composerDocumentUrl(origin);return origin.replace(/\/$/,'')+SKETCH_DOCUMENT_PATH;}

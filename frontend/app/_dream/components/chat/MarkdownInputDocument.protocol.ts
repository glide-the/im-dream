// [Input] State for the existing MarkdownInputEditor and document-local editing events.
// [Output] Narrow editor messages with document identity and monotonic edit acknowledgements.
// [Pos] Local rich-editor adapter only; no HTTP, credentials, tools or business submission implementation.
// [Sync] 2026-10-28: add optional Skill-menu state and bounded keyboard intent; original document events remain valid.
export const COMPOSER_DOCUMENT_PATH = '/native/composer';
export interface ComposerDocumentState {
  type:'state';documentId:string;revision:number;eventCount:number;
  value:string;placeholder:string;ariaLabel:string;disabled:boolean;theme:'light'|'dark'|'system';
  skillMenuOpen?:boolean;
}
export type ComposerDocumentEvent =
  | {type:'ready';documentId:string}
  | {type:'change';documentId:string;eventCount:number;value:string}
  | {type:'height';documentId:string;height:number}
  | {type:'keydown';documentId:string;key:'ArrowDown'|'ArrowUp'|'Enter'|'Tab'|'Escape'}
  | {type:'focus'|'blur'|'submit';documentId:string};
type WithoutIdentity<T> = T extends unknown ? Omit<T,'documentId'> : never;
export type ComposerDocumentPayload = WithoutIdentity<ComposerDocumentEvent>;
const count = (value:unknown):value is number => Number.isSafeInteger(value) && (value as number) >= 0;
export function readComposerState(value:unknown):ComposerDocumentState|null {
  if (!value || typeof value !== 'object') return null;
  const state=value as Record<string,unknown>;
  return state.type === 'state' && typeof state.documentId === 'string' && count(state.revision) && count(state.eventCount)
    && typeof state.value === 'string' && typeof state.placeholder === 'string' && typeof state.ariaLabel === 'string'
    && typeof state.disabled === 'boolean' && (state.skillMenuOpen===undefined || typeof state.skillMenuOpen==='boolean') && ['light','dark','system'].includes(state.theme as string) ? state as unknown as ComposerDocumentState : null;
}
export function readComposerEvent(raw:string):ComposerDocumentEvent|null {
  let event:Record<string,unknown>;
  try {event=JSON.parse(raw);} catch {return null;}
  if (!event || typeof event !== 'object' || typeof event.documentId !== 'string') return null;
  if (['ready','focus','blur','submit'].includes(event.type as string)) return event as ComposerDocumentEvent;
  if (event.type === 'change' && count(event.eventCount) && typeof event.value === 'string') return event as ComposerDocumentEvent;
  if (event.type === 'height' && typeof event.height === 'number' && Number.isFinite(event.height) && event.height > 0) return event as ComposerDocumentEvent;
  if (event.type === 'keydown' && ['ArrowDown','ArrowUp','Enter','Tab','Escape'].includes(event.key as string))return event as ComposerDocumentEvent;
  return null;
}
export function composerDocumentUrl(origin:string):string {
  // RN 0.81's URL polyfill does not implement hostname/origin; accept only the runtime's loopback origin form.
  const match=/^http:\/\/(localhost|127\.0\.0\.1|\[::1\])(?::([0-9]+))?\/?$/.exec(origin);
  if (!match || (match[2] && (Number(match[2]) < 1 || Number(match[2]) > 65535))) throw new Error('COMPOSER_ORIGIN_INVALID');
  return origin.replace(/\/$/,'')+COMPOSER_DOCUMENT_PATH;
}

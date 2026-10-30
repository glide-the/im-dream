// [Input] Relative BFF URLs and the native HTTP/Cookie adapter.
// [Output] HTTP heads, incremental UTF-8 chunks and response-compatible JSON reads.
// [Pos] Native transport; cookie values stay in iOS/Android platform storage.
// [Sync] 2026-10-28: share the original read/cancel/buffer adapter with file-upload response heads.
// [Sync] 2026-10-28: register cancellation before waiting for headers using the existing native request-ID owner.
// [Sync] 2026-10-29: retain safe Content-Type/Retry-After response metadata for the original resource error/cooldown contract.
import {NativeModules} from 'react-native';
const runtime = NativeModules.InkRuntime;
let requestSequence=0;
export type OpenResponse = {status: number; headers?:Headers; chunks: AsyncIterable<string>; cancel: () => void};
export function nativeResponseStream(head:{id:string;status:number;headers?:Record<string,string>},signal?:AbortSignal):OpenResponse {
  const cancel=()=>{void runtime.cancelRequest(head.id);};
  const abort=()=>cancel();signal?.addEventListener('abort',abort,{once:true});if(signal?.aborted)cancel();
  async function* chunks() {
    try {while(true){const next=await runtime.readResponse(head.id);if(next.text)yield next.text as string;if(next.done)break;}}
    finally {signal?.removeEventListener('abort',abort);cancel();}
  }
  return {status:head.status,headers:new Headers(head.headers),chunks:chunks(),cancel};
}
export async function openResponse(path: string, init: RequestInit = {}): Promise<OpenResponse> {
  if (init.signal?.aborted) throw new Error('HTTP_ABORTED');
  const headers = Object.fromEntries(new Headers(init.headers).entries());
  const id=`http_${Date.now().toString(36)}_${(++requestSequence).toString(36)}`;
  const cancelPending=()=>{void runtime.cancelRequest(id);};
  init.signal?.addEventListener('abort',cancelPending,{once:true});
  try {
    const head = await runtime.openRequest({id,path, method: init.method ?? 'GET', headers, body: init.body ?? null});
    if(init.signal?.aborted){void runtime.cancelRequest(head.id);throw new Error('HTTP_ABORTED');}
    return nativeResponseStream(head,init.signal ?? undefined);
  } catch(error) {
    if(init.signal?.aborted)throw new Error('HTTP_ABORTED');
    throw error;
  } finally {init.signal?.removeEventListener('abort',cancelPending);}
}
export async function bufferNativeResponse(response:OpenResponse):Promise<Response> {
  let body='';for await(const text of response.chunks)body+=text;
  return new Response([204,205,304].includes(response.status)?null:body,{status:response.status,headers:response.headers});
}
export const clientFetch = (async (input: RequestInfo | URL, init?: RequestInit) => {
  const path = typeof input === 'string' ? input : input instanceof URL ? input.href : input.url;
  return bufferNativeResponse(await openResponse(path,init));
}) as typeof fetch;

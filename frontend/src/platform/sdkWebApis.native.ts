// [Input] Hermes global Web API availability and locked UTF-8/stream constructors required by the original SDK.
// [Output] Missing encoding and basic stream constructors before the original AI SDK is imported.
// [Pos] Native bootstrap compatibility only; Web globals, HTTP, SSE projection and third-party SDK code remain unchanged.
import {TextDecoder,TextEncoder} from 'text-encoding-utf-8';
import {ReadableStream,WritableStream,TransformStream} from 'web-streams-polyfill';
export function installNativeSdkWebApis(host:{TextDecoder?:unknown;TextEncoder?:unknown;ReadableStream?:unknown;WritableStream?:unknown;TransformStream?:unknown}=globalThis):void {
  if(typeof host.TextDecoder!=='function')host.TextDecoder=TextDecoder;
  if(typeof host.TextEncoder!=='function')host.TextEncoder=TextEncoder;
  if(typeof host.ReadableStream!=='function')host.ReadableStream=ReadableStream;
  if(typeof host.WritableStream!=='function')host.WritableStream=WritableStream;
  if(typeof host.TransformStream!=='function')host.TransformStream=TransformStream;
}
installNativeSdkWebApis();

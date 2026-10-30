// [Input] Production native bootstrap registration and the exact locked UTF-8/Stream constructors.
// [Output] Unicode decoding, stream pipeline/error propagation and existing-global-preservation receipts.
// [Pos] Native compatibility contract tests; no browser globals are removed and no service/provider is called.
import {test,expect} from '@playwright/test';
import {TextDecoder as UTF8Decoder,TextEncoder as UTF8Encoder} from 'text-encoding-utf-8';
import {ReadableStream,WritableStream,TransformStream} from 'web-streams-polyfill';
import {installNativeSdkWebApis} from '../src/platform/sdkWebApis.native';
function nativeHost(){const host:NonNullable<Parameters<typeof installNativeSdkWebApis>[0]>={};installNativeSdkWebApis(host);return {host,Decoder:host.TextDecoder as typeof UTF8Decoder,Encoder:host.TextEncoder as typeof UTF8Encoder};}
test('registers UTF-8 constructors only when missing and retains platform-provided implementations',()=>{
  const {host}=nativeHost();expect(host.TextDecoder).toBe(UTF8Decoder);expect(host.TextEncoder).toBe(UTF8Encoder);
  expect(host.ReadableStream).toBe(ReadableStream);expect(host.WritableStream).toBe(WritableStream);expect(host.TransformStream).toBe(TransformStream);
  const provided={TextDecoder:globalThis.TextDecoder,TextEncoder:globalThis.TextEncoder,ReadableStream:globalThis.ReadableStream,WritableStream:globalThis.WritableStream,TransformStream:globalThis.TransformStream};
  installNativeSdkWebApis(provided);for(const key of Object.keys(provided) as (keyof typeof provided)[])expect(provided[key]).toBe(globalThis[key]);
});
test('round-trips ASCII, Chinese, emoji, combining marks and null bytes without a Node Buffer',()=>{
  const {Decoder,Encoder}=nativeHost(),text='Ink 中文 🖋️ e\u0301\0 end';expect(new Decoder().decode(new Encoder().encode(text))).toBe(text);
});
test('retains split UTF-8 code points and consumes the initial BOM once across stream chunks',()=>{
  const {Decoder,Encoder}=nativeHost(),text='中文🙂Tail',bytes=new Uint8Array([239,187,191,...new Encoder().encode(text)]),decoder=new Decoder();let result='';
  for(const byte of bytes)result+=decoder.decode(new Uint8Array([byte]),{stream:true});result+=decoder.decode();expect(result).toBe(text);
});
test('preserves view offsets and explicit ignoreBOM behavior',()=>{
  const {Decoder,Encoder}=nativeHost(),bytes=new Encoder().encode('x中文y');expect(new Decoder().decode(bytes.subarray(1,bytes.length-1))).toBe('中文');
  expect(new Decoder('utf-8',{ignoreBOM:true}).decode(new Uint8Array([239,187,191,65]))).toBe('\uFEFFA');
});
test('invalid or unfinished sequences use replacement or fatal errors according to the original options',()=>{
  const {Decoder}=nativeHost();expect(new Decoder().decode(new Uint8Array([255]))).toBe('\uFFFD');expect(()=>new Decoder('utf-8',{fatal:true}).decode(new Uint8Array([255]))).toThrow();
  const decoder=new Decoder();expect(decoder.decode(new Uint8Array([240,159]),{stream:true})).toBe('');expect(decoder.decode()).toBe('\uFFFD');
});
test('installed constructors carry split Unicode through a readable-transform-writable pipeline',async()=>{
  const {host,Decoder,Encoder}=nativeHost(),Source=host.ReadableStream as typeof ReadableStream,Transform=host.TransformStream as typeof TransformStream,Sink=host.WritableStream as typeof WritableStream;
  const text='Dream 中文🙂 stream',bytes=new Encoder().encode(text),decoder=new Decoder(),output:string[]=[];
  const source=new Source<Uint8Array>({start(controller){for(const byte of bytes)controller.enqueue(new Uint8Array([byte]));controller.close();}});
  const transform=new Transform<Uint8Array,string>({transform(chunk,controller){controller.enqueue(decoder.decode(chunk,{stream:true}));},flush(controller){controller.enqueue(decoder.decode());}});
  await source.pipeThrough(transform).pipeTo(new Sink<string>({write(chunk){output.push(chunk);}}));expect(output.join('')).toBe(text);
});
test('a transform failure cancels its source and aborts its sink with the original error',async()=>{
  const {host}=nativeHost(),Source=host.ReadableStream as typeof ReadableStream,Transform=host.TransformStream as typeof TransformStream,Sink=host.WritableStream as typeof WritableStream;
  const failure=new Error('fixture-transform-failure');let canceled:unknown,aborted:unknown;
  const source=new Source<number>({pull(controller){controller.enqueue(1);},cancel(reason){canceled=reason;}});
  const result=source.pipeThrough(new Transform<number,number>({transform(){throw failure;}})).pipeTo(new Sink<number>({abort(reason){aborted=reason;}}));
  await expect(result).rejects.toBe(failure);expect(canceled).toBe(failure);expect(aborted).toBe(failure);
});

// [Input] Locked text-encoding-utf-8 package API.
// [Output] Types for its UTF-8-only constructor, stream, BOM and error behavior.
// [Pos] Narrow dependency declarations; Web Encoding Streams and encodeInto are outside this package API.
declare module 'text-encoding-utf-8' {
  export class TextDecoder {
    constructor(encoding?:string,options?:{fatal?:boolean;ignoreBOM?:boolean});
    readonly encoding:'utf-8';readonly fatal:boolean;readonly ignoreBOM:boolean;
    decode(input?:ArrayBuffer|ArrayBufferView,options?:{stream?:boolean}):string;
  }
  export class TextEncoder {
    constructor(encoding?:string);
    readonly encoding:'utf-8';
    encode(input?:string):Uint8Array;
  }
}

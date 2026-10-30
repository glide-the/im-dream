// [Input] Explicit native Settings fixture device and browser crypto at a test-only module boundary.
// [Output] Existing RNW/Settings facade plus a deterministic observable native UUID call.
// [Pos] Harness only; Foundation UUID and UserDefaults require device-level acceptance.
export * from './appearance-platform-web-boundary';
import {Platform as WebPlatform} from 'react-native-web';
export const Platform={...WebPlatform,OS:'ios',select:(values:Record<string,unknown>)=>values.ios??values.native??values.default};
export const NativeModules={InkRuntime:{randomUUID:async()=>{const id=crypto.randomUUID();(window as any).__settingsFixture.uuidCalls.push(id);return id;}}};

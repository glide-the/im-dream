// [Input] iOS application-owned embedded runtime module.
// [Output] One shared startup promise and public readiness facts across RN remounts.
// [Pos] RN runtime coordinator; Python/Node ownership stays in the native singleton.
import {NativeModules} from 'react-native';

export type RuntimeFacts = {state: 'ready'; localWebOrigin: string};
let startup: Promise<RuntimeFacts> | undefined;

export const BackendRuntimeManager = {
  ensureStarted(): Promise<RuntimeFacts> {
    startup ??= NativeModules.InkRuntime.ensureStarted().catch((error: unknown) => {
      startup = undefined;
      throw error;
    });
    return startup!;
  },
};

// [Sync] 2026-11-02: adopt display-only Kastention naming; existing behavior and technical identities remain.
// [Sync] 2026-11-02: retain native Chat restoration errors in the existing per-source diagnostics.
// [Sync] 2026-11-02: connect original account failures to runtime diagnostics and align the packaged native callback.
// [Input] iOS application-owned embedded runtime module.
// [Sync] 2026-11-03: project bounded on-demand performance samples into the existing diagnostics snapshot without changing startup or recovery.
// [Output] Shared startup facts and the original error returned by each observed source.
// [Pos] RN runtime coordinator; Python/Node ownership stays in the native singleton.
// [Sync] 2026-11-01: retain original errors without redaction, one latest error per source in process memory.
import { BRAND_NAME } from '../../app/_dream/constants/brand';
import {NativeModules} from 'react-native';
import {createPerformanceMonitor,type PerformanceState} from './runtimePerformance';

export type RuntimeFacts = {state: 'ready'; localWebOrigin: string};
export type SessionReadState = 'reading' | 'available' | 'signed_out' | 'unavailable';
export type RuntimeErrorSource = 'startup' | 'session' | 'config' | 'catalog' | 'login' | 'registration' | 'google' | 'recovery';
export type RuntimeErrorRecord = Readonly<{source: RuntimeErrorSource; at: number; text: string}>;
export type RuntimeSnapshot = Readonly<{
  state: 'idle' | 'starting' | 'ready' | 'failed';
  startedAt?: number;
  finishedAt?: number;
  elapsedMs?: number;
  updatedAt?: number;
  errorCode?: string;
  sessionRead?: Readonly<{state: SessionReadState; updatedAt: number}>;
  errors?: Readonly<Partial<Record<RuntimeErrorSource, RuntimeErrorRecord>>>;
  performance?: PerformanceState;
}>;
let startup: Promise<RuntimeFacts> | undefined;
let snapshot: RuntimeSnapshot = Object.freeze({state: 'idle'});
const listeners = new Set<() => void>();

function publish(value: RuntimeSnapshot) {
  snapshot = Object.freeze(value);
  for (const listener of listeners) {
    // Observation must not change the original startup result.
    try { listener(); } catch { /* A detached observer cannot fail runtime startup. */ }
  }
}

const performanceMonitor=createPerformanceMonitor({
  available:()=>typeof NativeModules.InkRuntime?.readPerformanceSample==='function',
  read:async()=>{
    const value:unknown=await NativeModules.InkRuntime.readPerformanceSample();
    if(snapshot.state==='starting'&&snapshot.startedAt!==undefined&&value&&typeof value==='object'&&'activities' in value&&Array.isArray(value.activities)) {
      return {...value,activities:[...value.activities,{id:`runtime:startup:${snapshot.startedAt}`,kind:'runtime',label:'本地启动与初始化',phase:'starting'}]};
    }
    return value;
  },
  changed:performance=>publish({...snapshot,performance}),
});

export function formatRuntimeError(error: unknown): string {
  if (typeof error === 'string') return error;
  try {
    const seen = new WeakSet<object>();
    const detail = JSON.stringify(error, (_key, value: unknown) => {
      if (typeof value === 'bigint') return value.toString();
      if (value !== null && typeof value === 'object') {
        if (seen.has(value)) return '[Circular]';
        seen.add(value);
        if (value instanceof Error) return Object.fromEntries(Object.getOwnPropertyNames(value).map(key => [key, (value as unknown as Record<string, unknown>)[key]]));
      }
      return value;
    }, 2) ?? String(error);
    // The bridge preserves NSError.userInfo even when its top-level message is generic.
    const nativeMessage = error && typeof error === 'object' && 'userInfo' in error
      && error.userInfo && typeof error.userInfo === 'object' && 'NSLocalizedDescription' in error.userInfo
      ? error.userInfo.NSLocalizedDescription : undefined;
    return typeof nativeMessage === 'string' ? `${nativeMessage}\n\n${detail}` : detail;
  } catch { return String(error); }
}

function withError(source: RuntimeErrorSource, error: unknown) {
  return Object.freeze({...snapshot.errors, [source]: Object.freeze({source, at: Date.now(), text: formatRuntimeError(error)})});
}

export function formatRuntimeDiagnostics(value: RuntimeSnapshot): string {
  const date = (time?: number) => time === undefined ? '未观测' : new Date(time).toISOString();
  return [
    `${BRAND_NAME} 启动诊断`,
    `启动状态: ${value.state}`,
    `开始时间: ${date(value.startedAt)}`,
    `结束时间: ${date(value.finishedAt)}`,
    `总耗时: ${value.elapsedMs === undefined ? '尚未完成' : `${value.elapsedMs} ms`}`,
    `最后更新时间: ${date(value.updatedAt)}`,
    `启动错误码: ${value.errorCode ?? '无'}`,
    `原会话读取: ${value.sessionRead?.state ?? '未观测'}`,
    `会话观测时间: ${date(value.sessionRead?.updatedAt)}`,
    '公网连接: 未单独观测',
    '错误日志（各来源最近一次）:',
    ...Object.values(value.errors ?? {}).sort((a, b) => b.at - a.at).map(item => `${date(item.at)} [${item.source}]\n${item.text}`),
  ].join('\n');
}

export const BackendRuntimeManager = {
  observePerformance:(active:boolean)=>performanceMonitor.acquire(active),
  pausePerformance:(paused:boolean)=>performanceMonitor.setPaused(paused),
  getSnapshot: (): RuntimeSnapshot => snapshot,
  subscribe(listener: () => void): () => void {
    listeners.add(listener);
    return () => { listeners.delete(listener); };
  },
  recordSessionRead(state: SessionReadState) {
    publish({...snapshot, sessionRead: Object.freeze({state, updatedAt: Date.now()})});
  },
  recordError(source: RuntimeErrorSource, error: unknown) {
    publish({...snapshot, errors: withError(source, error)});
  },
  ensureStarted(): Promise<RuntimeFacts> {
    if (startup) return startup;
    const startedAt = Date.now(), startedTick = performance.now();
    // Assign before notifying observers; reentrant callers share this same operation.
    startup = Promise.resolve().then(() => NativeModules.InkRuntime.ensureStarted()).then((facts: RuntimeFacts) => {
      const finishedAt = Date.now();
      publish({...snapshot, state: 'ready', finishedAt, updatedAt: finishedAt,
        elapsedMs: Math.max(0, Math.round(performance.now() - startedTick))});
      return facts;
    }, (error: unknown) => {
      startup = undefined;
      const code = error && typeof error === 'object' && 'code' in error ? error.code : undefined;
      const errorCode = typeof code === 'string' || typeof code === 'number' ? String(code) : undefined;
      const finishedAt = Date.now();
      publish({...snapshot, state: 'failed', finishedAt, updatedAt: finishedAt, errorCode,
        elapsedMs: Math.max(0, Math.round(performance.now() - startedTick)), errors: withError('startup', error)});
      throw error;
    });
    publish({state: 'starting', startedAt, updatedAt: startedAt, errors: snapshot.errors, performance:snapshot.performance});
    return startup;
  },
};

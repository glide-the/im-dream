// [Input] Canonical Dream React root and the native host startup response.
// [Output] Shared application after local-service readiness, or one readable startup failure with retry.
// [Pos] Mobile resource entry; business pages remain in app/_dream.
// [Sync] 2026-10-24: keep a local startup timer and remove technical capability panels and speculative recovery subscriptions.

import { StrictMode, useEffect, useState } from 'react';
import { createRoot } from 'react-dom/client';

import DreamRoot from '../app/_dream/DreamRoot';
import {
  getMobileBridge,
  requiredApplicationCapabilityNames,
  type MobileAppInfo,
  type MobileRuntimeCapabilities,
} from '../app/_dream/platform/mobileBridge';
import { installMobileRuntimeFetch } from '../app/_dream/platform/mobileRuntimeTransport';
import './mobile-shell.css';

const startupTimeoutMs = 10_000;
type StartupState =
  | { phase: 'loading' }
  | { phase: 'ready'; info: MobileAppInfo }
  | { phase: 'failed'; message: string };

function MobileStartup() {
  const [state, setState] = useState<StartupState>({ phase: 'loading' });
  const [attempt, setAttempt] = useState(0);

  useEffect(() => {
    setState({ phase: 'loading' });
    const bridge = getMobileBridge();
    if (!bridge) {
      setState({ phase: 'failed', message: '应用启动失败，请重新打开应用。' });
      return;
    }
    const abort = new AbortController();
    let restoreFetch: (() => void) | undefined;
    const timer = window.setTimeout(() => {
      abort.abort();
      setState({ phase: 'failed', message: '本机服务未响应，请重试。' });
    }, startupTimeoutMs);

    void (async () => {
      try {
        const [info, runtime] = await Promise.all([
          bridge.call<MobileAppInfo>('app.getInfo', {}, { signal: abort.signal }),
          bridge.call<MobileRuntimeCapabilities>('runtime.getCapabilities', {}, { signal: abort.signal }),
        ]);
        if (abort.signal.aborted) return;
        if (requiredApplicationCapabilityNames.some((name) => runtime.capabilities[name]?.state !== 'available')) {
          setState({ phase: 'failed', message: '此版本尚未完成本机服务接入，工作区暂时无法打开。' });
          return;
        }
        restoreFetch = installMobileRuntimeFetch(bridge);
        setState({ phase: 'ready', info });
      } catch {
        if (!abort.signal.aborted) setState({ phase: 'failed', message: '本机服务启动失败，请重试。' });
      } finally {
        window.clearTimeout(timer);
      }
    })();

    return () => {
      window.clearTimeout(timer);
      abort.abort();
      restoreFetch?.();
    };
  }, [attempt]);

  if (state.phase === 'ready') {
    return <DreamRoot frontendVersion={`mobile-${state.info.platform}-${state.info.appVersion}`} />;
  }
  return (
    <main className="mobile-startup-shell">
      <section className="mobile-startup-card" aria-live="polite">
        <p className="mobile-startup-kicker">Ink &amp; Memory</p>
        <h1>{state.phase === 'loading' ? '正在打开工作区' : '工作区暂时无法打开'}</h1>
        <p>{state.phase === 'loading' ? '正在启动本机服务…' : state.message}</p>
        {state.phase === 'failed' ? (
          <button type="button" onClick={() => setAttempt((value) => value + 1)}>重试</button>
        ) : null}
      </section>
    </main>
  );
}

const root = document.getElementById('root');
if (!root) throw new Error('mobile root element is missing');
createRoot(root).render(<StrictMode><MobileStartup /></StrictMode>);


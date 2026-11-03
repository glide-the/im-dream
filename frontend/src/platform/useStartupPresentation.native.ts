// [Input] Existing AppState transitions and whether the entry screen is unobscured.
// [Output] One second of visible foreground presentation on launch and each background return.
// [Pos] Presentation-only timing; SessionGate retains startup/session ownership.
// [Sync] 2026-11-03: count active visible time, cancel on departure, and preserve the mounted account view.
import {useCallback, useEffect, useRef, useState} from 'react';
import {AppState, type AppStateStatus} from 'react-native';
import {STARTUP_PRESENTATION_DURATION_MS} from '../components/startupPresentation';

export default function useStartupPresentation(unobscured: boolean) {
  const [visible, setVisible] = useState(true);
  const state = useRef(AppState.currentState);
  const blocked = useRef(!unobscured);
  const pending = useRef(true);
  const remaining = useRef(STARTUP_PRESENTATION_DURATION_MS);
  const startedAt = useRef<number | null>(null);
  const timer = useRef<ReturnType<typeof setTimeout> | null>(null);

  const pause = useCallback(() => {
    if (timer.current !== null) clearTimeout(timer.current);
    timer.current = null;
    if (startedAt.current !== null) remaining.current = Math.max(0, remaining.current - (performance.now() - startedAt.current));
    startedAt.current = null;
  }, []);
  const resume = useCallback(() => {
    if (!pending.current || blocked.current || state.current !== 'active' || timer.current !== null) return;
    startedAt.current = performance.now();
    timer.current = setTimeout(() => {
      timer.current = null;
      startedAt.current = null;
      remaining.current = 0;
      pending.current = false;
      setVisible(false);
    }, remaining.current);
  }, []);
  const onAppState = useCallback((next: AppStateStatus) => {
    pause();
    if (next === 'background' && state.current !== 'background') {
      remaining.current = STARTUP_PRESENTATION_DURATION_MS;
      pending.current = true;
      setVisible(true);
    }
    state.current = next;
    resume();
  }, [pause, resume]);

  useEffect(() => {
    pause();
    state.current = AppState.currentState;
    blocked.current = !unobscured;
    resume();
    return pause;
  }, [pause, resume, unobscured]);

  return {visible, onAppState};
}

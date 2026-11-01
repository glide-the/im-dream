// [Input] Local detail height, handle position and the measured available reading area.
// [Output] Bounded drag height and nearest-stop settling shared by Web and native report readers.
// [Pos] Reflections presentation state only; report selection, tasks and persistence stay with their owners.
// [Sync] 2026-11-01: add handle-only resize without taking over the detail content scroll gesture.
import {useCallback, useRef, useState} from 'react';

const STOPS = [0.45, 0.7, 0.9] as const;
const clamp = (value: number) => Math.max(STOPS[0], Math.min(STOPS[2], value));
const nearest = (value: number) => STOPS.reduce<number>((best, stop) => Math.abs(stop - value) < Math.abs(best - value) ? stop : best, STOPS[0]);

export default function useReflectionDetailSheet() {
  const [fraction, setFraction] = useState<number>(STOPS[1]);
  const current = useRef(fraction);
  const drag = useRef<{y: number; height: number; fraction: number} | null>(null);
  const update = useCallback((value: number) => {
    current.current = clamp(value);
    setFraction(current.current);
  }, []);
  const begin = useCallback((y: number, height: number) => {
    if (height > 0) drag.current = {y, height, fraction: current.current};
  }, []);
  const move = useCallback((y: number) => {
    const start = drag.current;
    if (start) update(start.fraction + (start.y - y) / start.height);
  }, [update]);
  const finish = useCallback((cancelled = false) => {
    const start = drag.current;
    if (!start) return;
    drag.current = null;
    update(cancelled ? start.fraction : nearest(current.current));
  }, [update]);
  const adjust = useCallback((direction: 'up' | 'down' | 'min' | 'max') => {
    if (direction === 'min' || direction === 'max') return update(direction === 'min' ? STOPS[0] : STOPS[2]);
    const stops = direction === 'up' ? STOPS : [...STOPS].reverse();
    const next = stops.find(stop => direction === 'up' ? stop > current.current + 0.001 : stop < current.current - 0.001);
    if (next !== undefined) update(next);
  }, [update]);
  return {fraction, minPercent: STOPS[0] * 100, maxPercent: STOPS[2] * 100, begin, move, finish, adjust};
}

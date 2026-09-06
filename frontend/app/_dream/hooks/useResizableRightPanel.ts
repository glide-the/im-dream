// [Input] Right-panel width bounds, persistence key, pointer/keyboard resize events, and optional container width.
// [Output] Shared accessible resize state and handlers for right-side workspace panels.
// [Pos] Frontend layout hook reused by Chat subagent details and Story Workspace writing Chat.
// [Sync] 2026-08-31: extract the proven Subagent resize contract for reusable right-side panels.
import {
  useCallback,
  useEffect,
  useRef,
  useState,
  type KeyboardEvent as ReactKeyboardEvent,
  type PointerEvent as ReactPointerEvent,
} from 'react';

export interface ResizableRightPanelBounds {
  min: number;
  max: number;
}

export interface UseResizableRightPanelOptions {
  defaultWidth: number;
  minWidth: number;
  maxWidth: number;
  minSiblingWidth: number;
  storageKey: string;
  getAvailableWidth?: () => number;
}

export function getResizableRightPanelBounds(
  availableWidth: number,
  minWidth: number,
  maxWidth: number,
  minSiblingWidth: number,
): ResizableRightPanelBounds {
  const safeAvailableWidth = Number.isFinite(availableWidth) && availableWidth > 0
    ? availableWidth
    : minWidth + minSiblingWidth;
  const responsiveMin = Math.min(
    minWidth,
    Math.max(280, safeAvailableWidth - minSiblingWidth),
  );
  const responsiveMax = Math.max(
    responsiveMin,
    Math.min(maxWidth, safeAvailableWidth - minSiblingWidth),
  );
  return { min: responsiveMin, max: responsiveMax };
}

export function clampResizableRightPanelWidth(
  value: number,
  bounds: ResizableRightPanelBounds,
): number {
  return Math.min(bounds.max, Math.max(bounds.min, value));
}

export function useResizableRightPanel({
  defaultWidth,
  minWidth,
  maxWidth,
  minSiblingWidth,
  storageKey,
  getAvailableWidth,
}: UseResizableRightPanelOptions) {
  const optionsRef = useRef({
    defaultWidth,
    minWidth,
    maxWidth,
    minSiblingWidth,
    getAvailableWidth,
  });
  optionsRef.current = {
    defaultWidth,
    minWidth,
    maxWidth,
    minSiblingWidth,
    getAvailableWidth,
  };

  const readBounds = useCallback(() => {
    const options = optionsRef.current;
    const availableWidth = options.getAvailableWidth?.()
      ?? (typeof window === 'undefined'
        ? options.maxWidth + options.minSiblingWidth
        : window.innerWidth);
    return getResizableRightPanelBounds(
      availableWidth,
      options.minWidth,
      options.maxWidth,
      options.minSiblingWidth,
    );
  }, []);

  const clampWidth = useCallback((value: number) => (
    clampResizableRightPanelWidth(value, readBounds())
  ), [readBounds]);

  const readInitialWidth = () => {
    if (typeof window === 'undefined') return clampWidth(defaultWidth);
    try {
      const stored = Number(window.localStorage.getItem(storageKey));
      return clampWidth(Number.isFinite(stored) && stored > 0 ? stored : defaultWidth);
    } catch {
      return clampWidth(defaultWidth);
    }
  };

  const [width, setWidth] = useState(readInitialWidth);
  const [isResizing, setIsResizing] = useState(false);
  const [resizeRailActive, setResizeRailActive] = useState(false);
  const widthRef = useRef(width);
  const resizeStartRef = useRef<{ clientX: number; width: number } | null>(null);
  const bodyStyleRef = useRef<{ cursor: string; userSelect: string } | null>(null);

  useEffect(() => {
    widthRef.current = width;
  }, [width]);

  const persistWidth = useCallback((nextWidth: number) => {
    try {
      window.localStorage.setItem(storageKey, String(Math.round(nextWidth)));
    } catch {
      // Storage can be unavailable in hardened/private browser contexts.
    }
  }, [storageKey]);

  const finishResize = useCallback(() => {
    if (!resizeStartRef.current) return;
    resizeStartRef.current = null;
    setIsResizing(false);
    persistWidth(widthRef.current);
    if (bodyStyleRef.current) {
      document.body.style.cursor = bodyStyleRef.current.cursor;
      document.body.style.userSelect = bodyStyleRef.current.userSelect;
      bodyStyleRef.current = null;
    }
  }, [persistWidth]);

  const handleResizePointerDown = useCallback((event: ReactPointerEvent<HTMLDivElement>) => {
    if (event.button !== 0) return;
    event.preventDefault();
    resizeStartRef.current = { clientX: event.clientX, width: widthRef.current };
    bodyStyleRef.current = {
      cursor: document.body.style.cursor,
      userSelect: document.body.style.userSelect,
    };
    document.body.style.cursor = 'col-resize';
    document.body.style.userSelect = 'none';
    event.currentTarget.setPointerCapture(event.pointerId);
    setIsResizing(true);
  }, []);

  const handleResizePointerMove = useCallback((event: ReactPointerEvent<HTMLDivElement>) => {
    const start = resizeStartRef.current;
    if (!start) return;
    const nextWidth = clampWidth(start.width + start.clientX - event.clientX);
    widthRef.current = nextWidth;
    setWidth(nextWidth);
  }, [clampWidth]);

  const handleResizePointerEnd = useCallback((event: ReactPointerEvent<HTMLDivElement>) => {
    if (event.currentTarget.hasPointerCapture(event.pointerId)) {
      event.currentTarget.releasePointerCapture(event.pointerId);
    }
    finishResize();
  }, [finishResize]);

  const resetWidth = useCallback(() => {
    const nextWidth = clampWidth(optionsRef.current.defaultWidth);
    widthRef.current = nextWidth;
    setWidth(nextWidth);
    persistWidth(nextWidth);
  }, [clampWidth, persistWidth]);

  const reclampWidth = useCallback(() => {
    const nextWidth = clampWidth(widthRef.current);
    widthRef.current = nextWidth;
    setWidth(nextWidth);
  }, [clampWidth]);

  const handleResizeKeyDown = useCallback((event: ReactKeyboardEvent<HTMLDivElement>) => {
    const bounds = readBounds();
    const step = event.shiftKey ? 32 : 16;
    let nextWidth: number | null = null;
    if (event.key === 'ArrowLeft') nextWidth = widthRef.current + step;
    if (event.key === 'ArrowRight') nextWidth = widthRef.current - step;
    if (event.key === 'Home') nextWidth = bounds.min;
    if (event.key === 'End') nextWidth = bounds.max;
    if (nextWidth == null) return;
    event.preventDefault();
    const clampedWidth = clampResizableRightPanelWidth(nextWidth, bounds);
    widthRef.current = clampedWidth;
    setWidth(clampedWidth);
    persistWidth(clampedWidth);
  }, [persistWidth, readBounds]);

  useEffect(() => {
    window.addEventListener('resize', reclampWidth);
    return () => window.removeEventListener('resize', reclampWidth);
  }, [reclampWidth]);

  useEffect(() => () => {
    resizeStartRef.current = null;
    if (bodyStyleRef.current) {
      document.body.style.cursor = bodyStyleRef.current.cursor;
      document.body.style.userSelect = bodyStyleRef.current.userSelect;
      bodyStyleRef.current = null;
    }
  }, []);

  return {
    bounds: readBounds(),
    finishResize,
    handleResizeKeyDown,
    handleResizePointerDown,
    handleResizePointerEnd,
    handleResizePointerMove,
    isResizing,
    reclampWidth,
    resetWidth,
    resizeRailActive,
    setResizeRailActive,
    width,
  };
}

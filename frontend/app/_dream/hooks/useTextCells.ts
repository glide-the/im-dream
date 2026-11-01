// [Sync] 2026-11-01: optionally recompute mobile textarea geometry after committed text, font and width changes without editor writes.
// [Input] EditorEngine text Cells, textarea events, IME state, and Agent dropdown state.
// [Output] Manage local TextCell mirrors, composition, paste, key handling, and textarea refs without model side effects.
// [Pos] Text Cell interaction hook in frontend/app/_dream/hooks.
// [Sync] 2026-09-01: remove the inspiration callback so every prose edit remains model-request-free.

import { useState, useCallback, useRef, useEffect, useLayoutEffect } from 'react';
import type { RefObject, Dispatch, SetStateAction } from 'react';
import type { EditorEngine, EditorState, TextCell } from '../engine/EditorEngine';

export interface UseTextCellsOptions {
  engineRef: RefObject<EditorEngine | null>;
  state: EditorState | null;
  dropdownVisible?: boolean;
  dropdownTriggerCellId?: string | null;
  onDropdownClose?: () => void;
  trackLayout?: boolean;
  scrollContainerRef?: RefObject<HTMLDivElement | null>;
}

export interface UseTextCellsReturn {
  localTexts: Map<string, string>;
  setLocalTexts: React.Dispatch<React.SetStateAction<Map<string, string>>>;
  composingCells: Set<string>;
  textareaRefs: React.MutableRefObject<Map<string, HTMLTextAreaElement>>;
  refsReady: number;
  refsReadyTriggered: React.MutableRefObject<boolean>;
  setRefsReady: Dispatch<SetStateAction<number>>;
  handleTextChange: (cellId: string, newText: string) => void;
  handleCompositionStart: (cellId: string) => void;
  handleCompositionEnd: (cellId: string, e: React.CompositionEvent<HTMLTextAreaElement>) => void;
  handlePaste: (cellId: string, e: React.ClipboardEvent<HTMLTextAreaElement>) => void;
  handleKeyDown: (cellId: string, e: React.KeyboardEvent<HTMLTextAreaElement>) => void;
  createTextareaRef: (cellId: string) => (el: HTMLTextAreaElement | null) => void;
}

// @@@ Text cell management hook: tracks local text, IME composition, and textarea refs
export function useTextCells({
  engineRef,
  state,
  dropdownVisible,
  dropdownTriggerCellId,
  onDropdownClose,
  trackLayout = false,
  scrollContainerRef,
}: UseTextCellsOptions): UseTextCellsReturn {
  const [localTexts, setLocalTexts] = useState<Map<string, string>>(new Map());
  const [composingCells, setComposingCells] = useState<Set<string>>(new Set());

  const textareaRefs = useRef<Map<string, HTMLTextAreaElement>>(new Map());
  const [refsReady, setRefsReady] = useState(0);
  const refsReadyTriggered = useRef(false);

  useEffect(() => {
    if (state) {
      setLocalTexts(prev => {
        const next = new Map(prev);
        state.cells.filter(c => c.type === 'text').forEach(cell => {
          const textCell = cell as TextCell;
          if (!composingCells.has(cell.id)) {
            next.set(cell.id, textCell.content || '');
          }
        });
        return next;
      });
    }
  }, [state, composingCells]);

  const resizeTextareas = useCallback(() => {
    const container = scrollContainerRef?.current;
    const scrollTop = container?.scrollTop ?? 0;
    const focused = document.activeElement;
    const anchor = focused instanceof HTMLTextAreaElement && Array.from(textareaRefs.current.values()).includes(focused) ? focused : null;
    const before = anchor?.getBoundingClientRect().top;
    textareaRefs.current.forEach(textarea => {
      textarea.style.height = 'auto';
      textarea.style.height = `${textarea.scrollHeight}px`;
    });
    if (container) container.scrollTop = scrollTop + (anchor && before !== undefined ? anchor.getBoundingClientRect().top - before : 0);
  }, [scrollContainerRef]);

  useLayoutEffect(() => {
    if (trackLayout) resizeTextareas();
  }, [trackLayout, localTexts, refsReady, resizeTextareas]);

  useEffect(() => {
    if (!trackLayout) return;
    let frame = 0, disposed = false, previous = '';
    const schedule = () => {
      if (disposed || frame) return;
      frame = requestAnimationFrame(() => {frame = 0; if (!disposed) resizeTextareas();});
    };
    const changed = () => {
      const first = textareaRefs.current.values().next().value as HTMLTextAreaElement | undefined;
      const style = first ? getComputedStyle(first) : null;
      const signature = `${first?.clientWidth}/${style?.fontSize}/${style?.lineHeight}/${style?.fontFamily}`;
      if (signature !== previous) {previous = signature; schedule();}
    };
    const observer = new ResizeObserver(changed);
    textareaRefs.current.forEach(textarea => observer.observe(textarea));
    if (scrollContainerRef?.current) observer.observe(scrollContainerRef.current);
    void document.fonts.ready.then(schedule);
    document.fonts.addEventListener('loadingdone', schedule);
    window.addEventListener('resize', changed);
    window.visualViewport?.addEventListener('resize', changed);
    changed();
    return () => {
      disposed = true;
      if (frame) cancelAnimationFrame(frame);
      observer.disconnect();
      document.fonts.removeEventListener('loadingdone', schedule);
      window.removeEventListener('resize', changed);
      window.visualViewport?.removeEventListener('resize', changed);
    };
  }, [trackLayout, refsReady, state?.cells.length, scrollContainerRef, resizeTextareas]);

  const handleTextChange = useCallback((cellId: string, newText: string) => {
    setLocalTexts(prev => {
      const next = new Map(prev);
      next.set(cellId, newText);
      return next;
    });

    const textarea = textareaRefs.current.get(cellId);
    if (textarea) {
      textarea.style.height = 'auto';
      textarea.style.height = textarea.scrollHeight + 'px';
    }

    if (dropdownVisible && dropdownTriggerCellId === cellId && !newText.includes('@')) {
      onDropdownClose?.();
    }

    if (!composingCells.has(cellId) && engineRef.current) {
      engineRef.current.updateTextCell(cellId, newText);
    }

  }, [
    composingCells,
    dropdownVisible,
    dropdownTriggerCellId,
    onDropdownClose,
    engineRef
  ]);

  const handleCompositionStart = useCallback((cellId: string) => {
    setComposingCells(prev => new Set(prev).add(cellId));
  }, []);

  const handleCompositionEnd = useCallback((cellId: string, e: React.CompositionEvent<HTMLTextAreaElement>) => {
    setComposingCells(prev => {
      const next = new Set(prev);
      next.delete(cellId);
      return next;
    });

    const newText = e.currentTarget.value;
    setLocalTexts(prev => {
      const next = new Map(prev);
      next.set(cellId, newText);
      return next;
    });

    if (engineRef.current) {
      engineRef.current.updateTextCell(cellId, newText);
    }
  }, [engineRef]);

  const handlePaste = useCallback((cellId: string, e: React.ClipboardEvent<HTMLTextAreaElement>) => {
    const textarea = e.currentTarget;
    setTimeout(() => {
      const newText = textarea.value;
      setLocalTexts(prev => {
        const next = new Map(prev);
        next.set(cellId, newText);
        return next;
      });
      if (engineRef.current) {
        engineRef.current.updateTextCell(cellId, newText);
      }
    }, 0);
  }, [engineRef]);

  const handleKeyDown = useCallback((cellId: string, e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Escape' && dropdownVisible) {
      onDropdownClose?.();
    }

    if (e.key === '@' && composingCells.has(cellId)) {
      e.preventDefault();
    }
  }, [composingCells, dropdownVisible, onDropdownClose]);

  const createTextareaRef = useCallback((cellId: string) => {
    return (el: HTMLTextAreaElement | null) => {
      if (el) {
        const wasEmpty = textareaRefs.current.size === 0;
        textareaRefs.current.set(cellId, el);
        if (wasEmpty && !refsReadyTriggered.current) {
          refsReadyTriggered.current = true;
          setRefsReady(prev => prev + 1);
        }
      } else {
        textareaRefs.current.delete(cellId);
      }
    };
  }, []);

  return {
    localTexts,
    setLocalTexts,
    composingCells,
    textareaRefs,
    refsReady,
    refsReadyTriggered,
    setRefsReady,
    handleTextChange,
    handleCompositionStart,
    handleCompositionEnd,
    handlePaste,
    handleKeyDown,
    createTextareaRef,
  };
}

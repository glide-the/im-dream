// [Input] User-selected text and an optional platform clipboard writer.
// [Output] Existing copied feedback after the clipboard operation succeeds.
// [Pos] Shared copy state; Web defaults to navigator.clipboard, native documents supply their existing system operation.
// [Sync] 2026-10-30: accept a concrete clipboard writer for local Mermaid documents; ordinary Web behavior remains.
import { useCallback, useEffect, useRef, useState } from 'react';

const writeClipboard = (text: string): Promise<void> => navigator.clipboard.writeText(text);

export function useCopy(resetDelay = 2000, writeText = writeClipboard) {
  const [copied, setCopied] = useState(false);
  const timerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const active = useRef(true);
  useEffect(() => { active.current = true; return () => { active.current = false; if (timerRef.current) clearTimeout(timerRef.current); }; }, []);

  const copy = useCallback(
    (text: string) => {
      writeText(text).then(() => {
        if (!active.current) return;
        setCopied(true);
        if (timerRef.current) {
          clearTimeout(timerRef.current);
        }
        timerRef.current = setTimeout(() => setCopied(false), resetDelay);
      }).catch(() => { if (active.current) setCopied(false); });
    },
    [resetDelay, writeText],
  );

  return { copied, copy };
}

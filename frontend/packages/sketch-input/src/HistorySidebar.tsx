// [Input] Source paper-fragment HistorySidebar layout and controlled action previews/cursor.
// [Output] Local snapshot restoration and history clear without dropping current layer contents.
// [Pos] History UI module of the charcoal component package, not Chat message history.
// [Sync] 2026-10-13: preserve left drawer and paper thumbnails with keyboard-accessible buttons.

import { useEffect, useRef } from 'react';
import { LuClock, LuEraser, LuImage, LuPenTool, LuRotateCcw, LuTrash2, LuX } from 'react-icons/lu';
import type { SketchDocument } from './history';
import type { SketchEditorLabels } from './SketchEditor';

interface Props {
  document: SketchDocument; open: boolean; labels: SketchEditorLabels; blocked: boolean;
  onClose: () => void; onRestore: (cursor: number) => void; onClear: () => void;
}
export function HistorySidebar({ document, open, labels, blocked, onClose, onRestore, onClear }: Props) {
  const closeRef = useRef<HTMLButtonElement>(null);
  useEffect(() => { if (open) closeRef.current?.focus(); }, [open]);
  return <aside className="ink-sketch__history" hidden={!open} aria-label={labels.history}>
    <header><div><h3>{labels.history}</h3><p>{labels.fragments}</p></div>
      <button ref={closeRef} type="button" aria-label={labels.closeHistory} title={labels.closeHistory} onClick={onClose}><LuX /></button></header>
    <div className="ink-sketch__history-list">
      {!document.actions.length ? <p className="ink-sketch__history-empty"><LuClock />{labels.noHistory}</p> : null}
      {[...document.actions].map((action, index) => ({ action, index })).reverse().map(({ action, index }, order) => {
        const description = action.kind === 'pen' ? labels.pen : action.kind === 'eraser' ? labels.eraser : action.kind === 'image' ? labels.importImage : labels.clear;
        return <button type="button" className="ink-sketch__fragment" key={index} disabled={blocked}
          aria-current={document.cursor === index + 1 ? 'step' : undefined}
          aria-label={`${labels.restore} ${index + 1}: ${description}`} onClick={() => onRestore(index + 1)}
          style={{ transform: `rotate(${(order % 3 - 1) * 1.5}deg)` }}>
          {action.preview ? <img src={action.preview} alt={`${labels.fragments} ${index + 1}`} /> : null}
          <span>{action.kind === 'pen' ? <LuPenTool /> : action.kind === 'eraser' ? <LuEraser /> : action.kind === 'image' ? <LuImage /> : <LuTrash2 />}
            {description}<LuRotateCcw className="ink-sketch__restore-icon" /></span>
          {action.timestamp ? <time>{new Date(action.timestamp).toLocaleTimeString()}</time> : null}
        </button>;
      })}
    </div>
    <button type="button" className="ink-sketch__history-clear" disabled={blocked || !document.actions.length} onClick={onClear}>
      <LuTrash2 />{labels.clearHistory}</button>
    <div className="ink-sketch__history-binding" aria-hidden="true" />
  </aside>;
}

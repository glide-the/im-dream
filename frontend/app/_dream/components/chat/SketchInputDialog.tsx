// [Input] Modal, sketchDrawing canvas helpers, translated copy and AIInputDock's existing upload callback.
// [Output] Local hand-drawn PNG input with reversible edits, retained unsent drawing and upload retry.
// [Pos] Chat sketch editor dialog; no Agent, Gateway or image-model execution.
// [Sync] 2026-10-09: add white-paper pen/eraser drawing with fixed-ratio pointer mapping.

import { useEffect, useRef, useState, type PointerEvent } from 'react';
import { useTranslation } from 'react-i18next';
import Modal from './Modal';
import {
  drawSketchStroke, exportSketch, renderSketch, sketchHasInk,
  SKETCH_HEIGHT, SKETCH_WIDTH, type SketchAction, type SketchPoint, type SketchStroke,
} from './sketchDrawing';
import './SketchInputDialog.css';

interface SketchInputDialogProps {
  open: boolean;
  disabled?: boolean;
  onClose: () => void;
  onAdd: (file: File) => Promise<boolean>;
}

export default function SketchInputDialog({ open, disabled = false, onClose, onAdd }: SketchInputDialogProps) {
  const { t } = useTranslation();
  const [actions, setActions] = useState<SketchAction[]>([]);
  const [cursor, setCursor] = useState(0);
  const [tool, setTool] = useState<'pen' | 'eraser'>('pen');
  const [hasInk, setHasInk] = useState(false);
  const [drawing, setDrawing] = useState(false);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const penRef = useRef<HTMLButtonElement>(null);
  const activeStroke = useRef<{ pointerId: number; stroke: SketchStroke } | null>(null);
  const savingRef = useRef(false);
  const blocked = disabled || saving;

  useEffect(() => {
    if (open && canvasRef.current) renderSketch(canvasRef.current, actions.slice(0, cursor));
  }, [open, actions, cursor]);

  function applyHistory(nextActions: SketchAction[], nextCursor: number) {
    setActions(nextActions);
    setCursor(nextCursor);
    setError(null);
    if (canvasRef.current) {
      renderSketch(canvasRef.current, nextActions.slice(0, nextCursor));
      setHasInk(sketchHasInk(canvasRef.current));
    }
  }

  function point(event: PointerEvent<HTMLCanvasElement>): SketchPoint {
    const bounds = event.currentTarget.getBoundingClientRect();
    return {
      x: Math.max(0, Math.min(SKETCH_WIDTH, (event.clientX - bounds.left) / bounds.width * SKETCH_WIDTH)),
      y: Math.max(0, Math.min(SKETCH_HEIGHT, (event.clientY - bounds.top) / bounds.height * SKETCH_HEIGHT)),
    };
  }

  function close() {
    if (savingRef.current) return;
    activeStroke.current = null;
    setDrawing(false);
    onClose();
  }

  function finishStroke(event: PointerEvent<HTMLCanvasElement>, cancelled: boolean) {
    const active = activeStroke.current;
    if (!active || active.pointerId !== event.pointerId) return;
    activeStroke.current = null;
    setDrawing(false);
    if (event.currentTarget.hasPointerCapture(event.pointerId)) event.currentTarget.releasePointerCapture(event.pointerId);
    if (cancelled) {
      renderSketch(event.currentTarget, actions.slice(0, cursor));
      return;
    }
    active.stroke.points.push(point(event));
    const next = [...actions.slice(0, cursor), active.stroke];
    applyHistory(next, next.length);
  }

  async function add() {
    if (!canvasRef.current || !hasInk || drawing || blocked || savingRef.current) return;
    savingRef.current = true;
    setSaving(true);
    setError(null);
    try {
      const blob = await exportSketch(canvasRef.current);
      const file = new File([blob], t('chat.inputDock.sketch.filename'), { type: 'image/png' });
      if (!await onAdd(file)) {
        setError(t('chat.inputDock.sketch.addFailed'));
        return;
      }
      applyHistory([], 0);
      setTool('pen');
      onClose();
    } catch {
      setError(t('chat.inputDock.sketch.addFailed'));
    } finally {
      savingRef.current = false;
      setSaving(false);
    }
  }

  return (
    <div onPaste={event => event.stopPropagation()} onDragOver={event => {
      event.preventDefault();
      event.stopPropagation();
    }} onDrop={event => {
      event.preventDefault();
      event.stopPropagation();
    }}>
    <Modal open={open} title={t('chat.inputDock.sketch.title')} onClose={close}
      closeLabel={t('chat.inputDock.sketch.return')} initialFocusRef={penRef} surfaceClassName="sketch-input-dialog">
      <div className="sketch-input__toolbar" role="group" aria-label={t('chat.inputDock.sketch.tools')}>
        {(['pen', 'eraser'] as const).map(value => (
          <button ref={value === 'pen' ? penRef : undefined} type="button" key={value}
            aria-pressed={tool === value} disabled={blocked || drawing} onClick={() => setTool(value)}>
            {t(`chat.inputDock.sketch.${value}`)}
          </button>
        ))}
        <span className="sketch-input__toolbar-divider" aria-hidden="true" />
        <button type="button" disabled={blocked || drawing || cursor === 0} onClick={() => applyHistory(actions, cursor - 1)}>{t('chat.inputDock.sketch.undo')}</button>
        <button type="button" disabled={blocked || drawing || cursor === actions.length} onClick={() => applyHistory(actions, cursor + 1)}>{t('chat.inputDock.sketch.redo')}</button>
        <button type="button" disabled={blocked || drawing || !hasInk} onClick={() => {
          const next: SketchAction[] = [...actions.slice(0, cursor), { kind: 'clear' }];
          applyHistory(next, next.length);
        }}>{t('chat.inputDock.sketch.clear')}</button>
      </div>
      <canvas ref={canvasRef} width={SKETCH_WIDTH} height={SKETCH_HEIGHT}
        className="sketch-input__canvas" aria-label={t('chat.inputDock.sketch.canvas')}
        aria-disabled={blocked} data-tool={tool}
        onPointerDown={event => {
          if (blocked || activeStroke.current || event.button !== 0) return;
          event.preventDefault();
          event.currentTarget.setPointerCapture(event.pointerId);
          const stroke: SketchStroke = { kind: tool, points: [point(event)] };
          activeStroke.current = { pointerId: event.pointerId, stroke };
          setDrawing(true);
          const context = event.currentTarget.getContext('2d');
          if (context) drawSketchStroke(context, stroke);
        }}
        onPointerMove={event => {
          const active = activeStroke.current;
          if (!active || active.pointerId !== event.pointerId) return;
          event.preventDefault();
          const previous = active.stroke.points.at(-1)!;
          const next = point(event);
          active.stroke.points.push(next);
          const context = event.currentTarget.getContext('2d');
          if (context) drawSketchStroke(context, { kind: active.stroke.kind, points: [previous, next] });
        }}
        onPointerUp={event => finishStroke(event, false)}
        onPointerCancel={event => finishStroke(event, true)}
        onLostPointerCapture={event => finishStroke(event, true)}
      />
      {error ? <p className="sketch-input__error" role="alert">{error}</p> : null}
      <div className="sketch-input__footer">
        <button type="button" disabled={saving} onClick={close}>{t('chat.inputDock.sketch.return')}</button>
        <button type="button" className="sketch-input__add" disabled={blocked || drawing || !hasInk}
          onClick={() => { void add(); }}>
          {t(saving ? 'chat.inputDock.sketch.adding' : 'chat.inputDock.sketch.add')}
        </button>
      </div>
      {saving ? <span className="sketch-input__status" role="status">{t('chat.inputDock.sketch.adding')}</span> : null}
    </Modal>
    </div>
  );
}

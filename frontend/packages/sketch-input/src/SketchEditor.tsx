'use client';
// [Input] Host-owned draft, labels, size policy and PNG-add/close callbacks.
// [Output] Local charcoal/image editor with stable history and retryable PNG output.
// [Pos] React view of sketch-input; Modal/auth/upload remain host-owned.
// [Sync] 2026-10-13: preserve source tools/layers/gestures; closing the snapshot drawer restores trigger focus.

import { useCallback, useEffect, useRef, useState, type PointerEvent, type RefObject } from 'react';
import { DRAWING, exportSketch, renderSketch, sketchHasInk, sketchHistoryPreview, snapshotSketchLayers } from './drawing';
import { appendSketchAction, createSketchDocument, type SketchAction, type SketchDocument, type SketchLayer, type SketchPoint, type SketchStroke } from './history';
import { decodeSketchImage, ImageInputError } from './imageInput';
import { CharcoalToolbar } from './CharcoalToolbar';
import { ToolkitDashboard } from './ToolkitDashboard';
import { HistorySidebar } from './HistorySidebar';
import { GestureController } from './gestures';
import { LuPenTool } from 'react-icons/lu';

export interface SketchEditorLabels {
  tools: string; pen: string; eraser: string; pan: string; undo: string; redo: string; clear: string;
  canvas: string; back: string; add: string; adding: string; filename: string; addFailed: string;
  importImage: string; importing: string; importFailed: string; imageTooLarge: string;
  eraserSize: string; zoomIn: string; zoomOut: string; resetView: string; zoom: string;
  layeredCanvas: string; layers: string; history: string; toolkit: string; sketchLayer: string; imageLayer: string;
  eraseTarget: string; eraseSketch: string; eraseImage: string; closeHistory: string; clearHistory: string;
  restore: string; fragments: string; noHistory: string; layerHidden: string;
}
export interface SketchEditorProps {
  document: SketchDocument;
  onDocumentChange: (document: SketchDocument) => void;
  labels: SketchEditorLabels;
  maxFileBytes: number;
  disabled?: boolean;
  initialFocusRef?: RefObject<HTMLButtonElement | null>;
  onClose: () => void;
  onAdd: (file: File) => Promise<boolean>;
  onSavingChange: (saving: boolean) => void;
}

export function SketchEditor({ document, onDocumentChange, labels, maxFileBytes, disabled = false,
  initialFocusRef, onClose, onAdd, onSavingChange }: SketchEditorProps) {
  const [tool, setTool] = useState<'pen' | 'eraser' | 'pan'>('pen');
  const [eraserSize, setEraserSize] = useState<number>(DRAWING.eraserDefault);
  const [hasContent, setHasContent] = useState(false);
  const [hasImage, setHasImage] = useState(false);
  const [layersOpen, setLayersOpen] = useState(false);
  const [historyOpen, setHistoryOpen] = useState(false);
  const [target, setTarget] = useState<SketchLayer>('sketch');
  const [cursorPoint, setCursorPoint] = useState<SketchPoint | null>(null);
  const [drawing, setDrawing] = useState(false);
  const [saving, setSaving] = useState(false);
  const [importing, setImporting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [zoom, setZoom] = useState(1);
  const [offset, setOffset] = useState<SketchPoint>({ x: 0, y: 0 });
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const viewportRef = useRef<HTMLDivElement>(null);
  const gestures = useRef(new GestureController());
  const inputRef = useRef<HTMLInputElement>(null);
  const historyRef = useRef<HTMLButtonElement>(null);
  const documentRef = useRef(document);
  const strokeRef = useRef<{ pointerId: number; stroke: SketchStroke } | null>(null);
  const panRef = useRef<{ pointerId: number; point: SketchPoint } | null>(null);
  const savingRef = useRef(false);
  const importRef = useRef<AbortController | null>(null);
  const importSequence = useRef(0);
  const mounted = useRef(false);
  const blocked = disabled || saving || importing;
  const editingBlocked = blocked || drawing;
  const targetVisible = tool === 'pan' || document.layers[tool === 'pen' ? 'sketch' : target].visible;
  const cancelImport = useCallback(() => {
    importSequence.current++;
    importRef.current?.abort();
  }, []);

  useEffect(() => {
    mounted.current = true;
    return () => { mounted.current = false; cancelImport(); };
  }, [cancelImport]);
  useEffect(() => {
    documentRef.current = document;
    if (canvasRef.current) {
      const imageVisible = renderSketch(canvasRef.current, document.actions.slice(0, document.cursor), document.layers, document.baseline);
      setHasContent(imageVisible || sketchHasInk(canvasRef.current));
      setHasImage(snapshotSketchLayers(canvasRef.current, document).hasImage);
    }
  }, [document]);

  function apply(next: SketchDocument) {
    documentRef.current = next;
    onDocumentChange(next);
    setError(null);
    if (canvasRef.current) {
      const imageVisible = renderSketch(canvasRef.current, next.actions.slice(0, next.cursor), next.layers, next.baseline);
      setHasContent(imageVisible || sketchHasInk(canvasRef.current));
      setHasImage(snapshotSketchLayers(canvasRef.current, next).hasImage);
    }
  }
  function commit(action: SketchAction) {
    const next = appendSketchAction(documentRef.current, action);
    if (canvasRef.current) {
      renderSketch(canvasRef.current, next.actions, next.layers, next.baseline);
      next.actions = [...next.actions.slice(0, -1), { ...action, preview: sketchHistoryPreview(canvasRef.current), timestamp: Date.now(), layers: next.layers }];
    }
    apply(next);
  }
  function toggleLayer(layer: SketchLayer) {
    apply({ ...document, layers: { ...document.layers, [layer]: { ...document.layers[layer], visible: !document.layers[layer].visible } } });
  }
  function clearHistory() {
    if (!canvasRef.current) return;
    apply({ ...document, actions: [], cursor: 0, baseline: snapshotSketchLayers(canvasRef.current, document) });
  }
  function closeHistory() {
    setHistoryOpen(false);
    historyRef.current?.focus();
  }
  function restore(cursor: number) {
    apply({ ...document, cursor, layers: document.actions[cursor - 1].layers ?? document.layers });
    closeHistory();
  }
  function point(event: PointerEvent<HTMLCanvasElement>): SketchPoint {
    const rect = event.currentTarget.getBoundingClientRect(); // Includes CSS transform, as in CanvasManager.
    return {
      x: Math.max(0, Math.min(DRAWING.width, (event.clientX - rect.left) / rect.width * DRAWING.width)),
      y: Math.max(0, Math.min(DRAWING.height, (event.clientY - rect.top) / rect.height * DRAWING.height)),
    };
  }
  function finish(event: PointerEvent<HTMLCanvasElement>, cancelled: boolean) {
    gestures.current.end(event.pointerId);
    const active = strokeRef.current;
    if (panRef.current?.pointerId === event.pointerId) panRef.current = null;
    if (!active || active.pointerId !== event.pointerId) return;
    strokeRef.current = null;
    setDrawing(false);
    if (event.currentTarget.hasPointerCapture(event.pointerId)) event.currentTarget.releasePointerCapture(event.pointerId);
    if (cancelled) renderSketch(event.currentTarget, documentRef.current.actions.slice(0, documentRef.current.cursor), documentRef.current.layers, documentRef.current.baseline);
    else {
      active.stroke.points.push(point(event));
      commit(active.stroke);
    }
  }
  async function importImage(file: File | undefined) {
    if (!file || blocked || drawing || savingRef.current) return;
    importRef.current?.abort();
    const abort = new AbortController();
    importRef.current = abort;
    const sequence = ++importSequence.current;
    setImporting(true);
    setError(null);
    try {
      const image = await decodeSketchImage(file, maxFileBytes, abort.signal);
      if (!mounted.current || abort.signal.aborted || sequence !== importSequence.current) return;
      commit({ kind: 'image', image });
    } catch (failure) {
      if (!mounted.current || abort.signal.aborted || sequence !== importSequence.current) return;
      setError(failure instanceof ImageInputError && failure.code === 'size' ? labels.imageTooLarge : labels.importFailed);
    } finally {
      if (mounted.current && sequence === importSequence.current) setImporting(false);
    }
  }
  async function add() {
    const canvas = canvasRef.current;
    if (!canvas || !hasContent || editingBlocked || savingRef.current) return;
    savingRef.current = true;
    onSavingChange(true);
    setSaving(true);
    setError(null);
    try {
      const blob = await exportSketch(canvas);
      if (!mounted.current) return;
      const success = await onAdd(new File([blob], labels.filename, { type: 'image/png' }));
      if (!mounted.current) return;
      if (!success) { setError(labels.addFailed); return; }
      apply(createSketchDocument());
      savingRef.current = false;
      onSavingChange(false); // Release the host's Modal close guard before closing.
      setSaving(false);
      onClose();
    } catch {
      if (mounted.current) setError(labels.addFailed);
    } finally {
      savingRef.current = false;
      if (mounted.current) { setSaving(false); onSavingChange(false); }
    }
  }

  return <div className="ink-sketch" onKeyDown={event => {
    const target = event.target as HTMLElement;
    if (target.matches('input, textarea') || target.isContentEditable || event.ctrlKey || event.metaKey || event.altKey) return;
    if (event.key === 'Escape' && historyOpen) { event.stopPropagation(); closeHistory(); return; }
    if (editingBlocked) return;
    if (event.key.toLowerCase() === 'b') setTool('pen');
    else if (event.key.toLowerCase() === 'e') setTool('eraser');
    else if (event.key.toLowerCase() === 'h') setHistoryOpen(value => !value);
    else if (event.key === '0') { setZoom(1); setOffset({ x: 0, y: 0 }); }
    else if (event.key === '+' || event.key === '=') setZoom(value => Math.min(DRAWING.zoomMax, value + DRAWING.zoomStep));
    else if (event.key === '-') setZoom(value => Math.max(DRAWING.zoomMin, value - DRAWING.zoomStep));
    else return;
    event.preventDefault();
  }} onPaste={event => {
    event.stopPropagation();
    if (event.clipboardData.files.length) { event.preventDefault(); void importImage(event.clipboardData.files[0]); }
  }} onDragOver={event => { event.preventDefault(); event.stopPropagation(); }}
    onDrop={event => { event.preventDefault(); event.stopPropagation(); void importImage(event.dataTransfer.files[0]); }}>
    <header className="ink-sketch__brand"><LuPenTool /><div><h3>CHARCOAL NARRATIVE</h3><p>{labels.layeredCanvas}</p></div></header>
    <div className="ink-sketch__controls">
      <CharcoalToolbar labels={labels} blocked={editingBlocked} tool={tool} zoom={zoom} penRef={initialFocusRef} historyRef={historyRef}
        layersOpen={layersOpen} historyOpen={historyOpen} canUndo={document.cursor > 0}
        canRedo={document.cursor < document.actions.length} canClear={hasContent}
        onTool={setTool} onLayers={() => setLayersOpen(value => !value)} onHistory={() => setHistoryOpen(value => !value)}
        onImport={() => inputRef.current?.click()} onUndo={() => apply({ ...document, cursor: document.cursor - 1 })}
        onRedo={() => apply({ ...document, cursor: document.cursor + 1 })} onClear={() => commit({ kind: 'clear' })}
        onZoom={direction => setZoom(value => Math.min(DRAWING.zoomMax, Math.max(DRAWING.zoomMin, value + direction * DRAWING.zoomStep)))}
        onReset={() => { setZoom(1); setOffset({ x: 0, y: 0 }); }} />
      <ToolkitDashboard labels={labels} layers={document.layers} layersOpen={layersOpen} erasing={tool === 'eraser'}
        target={target} size={eraserSize} blocked={editingBlocked} hasImage={hasImage}
        onLayer={toggleLayer} onTarget={setTarget} onSize={setEraserSize} />
    </div>
    <input ref={inputRef} type="file" hidden accept="image/*" disabled={editingBlocked} aria-label={labels.importImage}
      onChange={event => { const file = event.target.files?.[0]; event.target.value = ''; void importImage(file); }} />
    <div className="ink-sketch__viewport" ref={viewportRef}>
      <canvas ref={canvasRef} width={DRAWING.width} height={DRAWING.height} className="ink-sketch__canvas"
        aria-label={labels.canvas} aria-disabled={blocked || !targetVisible} data-tool={tool} tabIndex={0}
        style={{ transform: `translate(${offset.x}px, ${offset.y}px) scale(${zoom})` }}
        onPointerDown={event => {
          if (blocked || !targetVisible || event.button !== 0) return;
          event.preventDefault();
          event.currentTarget.focus({ preventScroll: true });
          if (event.pointerType === 'touch') {
            gestures.current.start(event.pointerId, { x: event.clientX, y: event.clientY });
            if (gestures.current.active) {
              strokeRef.current = null; panRef.current = null; setDrawing(false);
              renderSketch(event.currentTarget, documentRef.current.actions.slice(0, documentRef.current.cursor), documentRef.current.layers, documentRef.current.baseline);
              event.currentTarget.setPointerCapture(event.pointerId);
              return;
            }
          }
          if (strokeRef.current || panRef.current) return;
          event.currentTarget.setPointerCapture(event.pointerId);
          if (tool === 'pan') { panRef.current = { pointerId: event.pointerId, point: { x: event.clientX, y: event.clientY } }; return; }
          const seed = crypto.getRandomValues(new Uint32Array(1))[0];
          const stroke: SketchStroke = { kind: tool, points: [point(event)], seed, size: eraserSize, target };
          strokeRef.current = { pointerId: event.pointerId, stroke };
          setDrawing(true);
          renderSketch(event.currentTarget, [...documentRef.current.actions.slice(0, documentRef.current.cursor), stroke], documentRef.current.layers, documentRef.current.baseline);
        }}
        onPointerLeave={() => setCursorPoint(null)}
        onPointerMove={event => {
          const rect = viewportRef.current?.getBoundingClientRect();
          if (rect && event.pointerType !== 'touch') setCursorPoint({ x: event.clientX - rect.left, y: event.clientY - rect.top });
          if (event.pointerType === 'touch') {
            const gesture = gestures.current.move(event.pointerId, { x: event.clientX, y: event.clientY });
            if (gesture) {
              setZoom(value => Math.min(DRAWING.zoomMax, Math.max(DRAWING.zoomMin, value * gesture.scale)));
              setOffset(value => ({ x: value.x + gesture.dx, y: value.y + gesture.dy }));
              return;
            }
          }
          const pan = panRef.current;
          if (pan?.pointerId === event.pointerId) {
            event.preventDefault();
            const dx = event.clientX - pan.point.x, dy = event.clientY - pan.point.y;
            pan.point = { x: event.clientX, y: event.clientY };
            setOffset(previous => ({ x: previous.x + dx, y: previous.y + dy }));
            return;
          }
          const active = strokeRef.current;
          if (!active || active.pointerId !== event.pointerId) return;
          event.preventDefault();
          active.stroke.points.push(point(event));
          renderSketch(event.currentTarget, [...documentRef.current.actions.slice(0, documentRef.current.cursor), active.stroke], documentRef.current.layers, documentRef.current.baseline);
        }}
        onPointerUp={event => finish(event, false)} onPointerCancel={event => finish(event, true)}
        onLostPointerCapture={event => finish(event, true)} />
      {cursorPoint && targetVisible && !blocked && tool !== 'pan' ? <span className={`ink-sketch__cursor ink-sketch__cursor--${tool}`} aria-hidden="true"
        style={{ left: cursorPoint.x, top: cursorPoint.y, width: tool === 'eraser' ? eraserSize * zoom : undefined, height: tool === 'eraser' ? eraserSize * zoom : undefined }}>
        {tool === 'pen' ? <LuPenTool /> : null}
      </span> : null}
    </div>
    <HistorySidebar document={document} open={historyOpen} labels={labels} blocked={editingBlocked}
      onClose={closeHistory} onRestore={restore} onClear={clearHistory} />
    {!targetVisible ? <p className="ink-sketch__layer-hint">{labels.layerHidden}</p> : null}
    {error ? <p className="ink-sketch__error" role="alert">{error}</p> : null}
    <div className="ink-sketch__footer">
      <button type="button" disabled={saving} onClick={onClose}>{labels.back}</button>
      <button type="button" className="ink-sketch__add" disabled={editingBlocked || !hasContent}
        onClick={() => { void add(); }}>{saving ? labels.adding : labels.add}</button>
    </div>
    {saving || importing ? <span className="ink-sketch__status" role="status">{saving ? labels.adding : labels.importing}</span> : null}
  </div>;
}

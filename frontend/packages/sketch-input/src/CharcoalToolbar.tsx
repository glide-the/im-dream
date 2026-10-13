// [Input] Editor state/callbacks and labels; source EraToggle floating glass layout.
// [Output] Original-style icon tool groups, view controls, layers/history and local image entry.
// [Pos] Toolbar module of the complete charcoal component; no generation placeholders.
// [Sync] 2026-10-13: preserve floating tools and the history trigger for keyboard focus restoration.

import { LuEraser, LuHand, LuHistory, LuImagePlus, LuLayers, LuPenTool, LuRedo2, LuRotateCcw, LuTrash2, LuUndo2, LuZoomIn, LuZoomOut } from 'react-icons/lu';
import type { RefObject } from 'react';
import { DRAWING } from './drawing';
import type { SketchEditorLabels } from './SketchEditor';

interface Props {
  labels: SketchEditorLabels; blocked: boolean; tool: 'pen' | 'eraser' | 'pan'; zoom: number;
  layersOpen: boolean; historyOpen: boolean; canUndo: boolean; canRedo: boolean; canClear: boolean;
  penRef?: RefObject<HTMLButtonElement | null>;
  historyRef: RefObject<HTMLButtonElement | null>;
  onTool: (tool: 'pen' | 'eraser' | 'pan') => void;
  onLayers: () => void; onHistory: () => void; onImport: () => void;
  onZoom: (direction: -1 | 1) => void; onReset: () => void;
  onUndo: () => void; onRedo: () => void; onClear: () => void;
}

export function CharcoalToolbar(props: Props) {
  const { labels, blocked, tool, zoom } = props;
  return <div className="ink-sketch__toolbar" role="group" aria-label={labels.tools}>
    <button type="button" title={labels.layers} aria-label={labels.layers} aria-expanded={props.layersOpen}
      aria-pressed={props.layersOpen} onClick={props.onLayers} disabled={blocked}><LuLayers /></button>
    <button ref={props.historyRef} type="button" title={labels.history} aria-label={labels.history} aria-expanded={props.historyOpen}
      onClick={props.onHistory} disabled={blocked}><LuHistory /></button>
    <span className="ink-sketch__divider" />
    <div className="ink-sketch__tool-group">
      <button type="button" title={labels.zoomOut} aria-label={labels.zoomOut} disabled={blocked || zoom <= DRAWING.zoomMin}
        onClick={() => props.onZoom(-1)}><LuZoomOut /></button>
      <output aria-label={labels.zoom}>{Math.round(zoom * 100)}%</output>
      <button type="button" title={labels.zoomIn} aria-label={labels.zoomIn} disabled={blocked || zoom >= DRAWING.zoomMax}
        onClick={() => props.onZoom(1)}><LuZoomIn /></button>
    </div>
    <span className="ink-sketch__divider" />
    <div className="ink-sketch__tool-group">
      <button type="button" title={labels.pen} aria-label={labels.pen} aria-pressed={tool === 'pen'} ref={props.penRef}
        disabled={blocked} onClick={() => props.onTool('pen')}><LuPenTool /></button>
      <button type="button" title={labels.eraser} aria-label={labels.eraser} aria-pressed={tool === 'eraser'}
        disabled={blocked} onClick={() => props.onTool('eraser')}><LuEraser /></button>
      <button type="button" title={labels.pan} aria-label={labels.pan} aria-pressed={tool === 'pan'}
        disabled={blocked} onClick={() => props.onTool('pan')}><LuHand /></button>
    </div>
    <span className="ink-sketch__divider" />
    <button type="button" title={labels.importImage} aria-label={labels.importImage} disabled={blocked} onClick={props.onImport}><LuImagePlus /></button>
    <button type="button" title={labels.undo} aria-label={labels.undo} disabled={blocked || !props.canUndo} onClick={props.onUndo}><LuUndo2 /></button>
    <button type="button" title={labels.redo} aria-label={labels.redo} disabled={blocked || !props.canRedo} onClick={props.onRedo}><LuRedo2 /></button>
    <button type="button" title={labels.clear} aria-label={labels.clear} disabled={blocked || !props.canClear} onClick={props.onClear}><LuTrash2 /></button>
    <button type="button" title={labels.resetView} aria-label={labels.resetView} disabled={blocked} onClick={props.onReset}><LuRotateCcw /></button>
  </div>;
}

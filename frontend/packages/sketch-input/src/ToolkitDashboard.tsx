// [Input] Source ToolkitDashboard/LayerControls/EraserToolbox structure and controlled layer/tool state.
// [Output] Floating image/sketch visibility and explicit eraser-target/size controls.
// [Pos] Layer/toolbox module in the complete charcoal component package.
// [Sync] 2026-10-13: preserve both layer targets; labels describe uploaded image rather than simulated AI.

import { LuEraser, LuImage, LuPenTool } from 'react-icons/lu';
import { DRAWING } from './drawing';
import type { SketchLayer, SketchLayers } from './history';
import type { SketchEditorLabels } from './SketchEditor';

interface Props {
  labels: SketchEditorLabels; layers: SketchLayers; layersOpen: boolean; erasing: boolean;
  target: SketchLayer; size: number; blocked: boolean; hasImage: boolean;
  onLayer: (layer: SketchLayer) => void; onTarget: (target: SketchLayer) => void; onSize: (size: number) => void;
}
export function ToolkitDashboard(props: Props) {
  const { labels, layers, blocked } = props;
  if (!props.layersOpen && !props.erasing) return null;
  return <div className="ink-sketch__toolkit" role="group" aria-label={labels.toolkit}>
    {props.layersOpen ? <div className="ink-sketch__tool-group" role="group" aria-label={labels.layers}>
      <button type="button" title={labels.sketchLayer} aria-label={labels.sketchLayer} aria-pressed={layers.sketch.visible}
        disabled={blocked} onClick={() => props.onLayer('sketch')}><LuPenTool /><span>{labels.sketchLayer}</span></button>
      <button type="button" title={labels.imageLayer} aria-label={labels.imageLayer} aria-pressed={layers.render.visible}
        disabled={blocked || !props.hasImage} onClick={() => props.onLayer('render')}><LuImage /><span>{labels.imageLayer}</span></button>
    </div> : null}
    {props.layersOpen && props.erasing ? <span className="ink-sketch__divider" /> : null}
    {props.erasing ? <>
      <div className="ink-sketch__tool-group" role="group" aria-label={labels.eraseTarget}>
        <button type="button" title={labels.eraseSketch} aria-label={labels.eraseSketch} aria-pressed={props.target === 'sketch'}
          disabled={blocked} onClick={() => props.onTarget('sketch')}><LuPenTool /></button>
        <button type="button" title={labels.eraseImage} aria-label={labels.eraseImage} aria-pressed={props.target === 'render'}
          disabled={blocked || !props.hasImage} onClick={() => props.onTarget('render')}><LuImage /></button>
      </div>
      <label className="ink-sketch__size"><LuEraser aria-hidden="true" /><span>{labels.eraserSize}</span>
        <input type="range" min={DRAWING.eraserMin} max={DRAWING.eraserMax} value={props.size}
          disabled={blocked} onChange={event => props.onSize(Number(event.target.value))} /><output>{props.size}</output>
      </label>
    </> : null}
  </div>;
}

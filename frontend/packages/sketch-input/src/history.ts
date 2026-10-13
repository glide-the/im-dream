// [Input] Local decoded image and pointer actions; no application state or persistence.
// [Output] Controlled sketch document and reversible action history with branch replacement.
// [Pos] History module of the single sketch-input component package.
// [Sync] 2026-10-13: retain source layer state and snapshot history; clearing history keeps two-layer pixels.

export type SketchPoint = { x: number; y: number };
export type SketchLayer = 'sketch' | 'render';
export type SketchLayers = Record<SketchLayer, { visible: boolean; opacity: number }>;
export type SketchStroke = { kind: 'pen' | 'eraser'; points: SketchPoint[]; seed: number; size: number; target?: SketchLayer };
export type SketchAction = (SketchStroke | { kind: 'clear' } | { kind: 'image'; image: HTMLImageElement }) & {
  preview?: string; timestamp?: number; layers?: SketchLayers;
};
export type SketchLayerBuffers = { sketch: HTMLCanvasElement; render: HTMLCanvasElement; hasImage: boolean };
export type SketchDocument = { actions: readonly SketchAction[]; cursor: number; layers: SketchLayers; baseline?: SketchLayerBuffers };

export function createSketchLayers(): SketchLayers {
  return { sketch: { visible: true, opacity: 1 }, render: { visible: true, opacity: 1 } };
}

export function createSketchDocument(): SketchDocument {
  return { actions: [], cursor: 0, layers: createSketchLayers() };
}

export function appendSketchAction(document: SketchDocument, action: SketchAction): SketchDocument {
  const actions = [...document.actions.slice(0, document.cursor), action];
  return { ...document, actions, cursor: actions.length };
}

// [Input] history.ts actions and Canvas 2D; CharcoalNarrative CanvasManager/CharcoalScene algorithms.
// [Output] Seeded charcoal, two erase targets, visible-layer composition, history baseline/preview and PNG.
// [Pos] Drawing module of sketch-input; no zoom, uploads, credentials or model calls.
// [Sync] 2026-10-13: preserve reference layers/targets/history with stable replay and existing 900x600 output.

import { createSketchLayers, type SketchAction, type SketchDocument, type SketchLayerBuffers, type SketchLayers, type SketchPoint, type SketchStroke } from './history';

// Geometry is presentation, not a product quota. Dimensions retain the existing Chat PNG contract;
// charcoal values and eraser controls come from the readonly reference component.
export const DRAWING = {
  width: 900, height: 600, paper: '#ffffff', charcoal: '#1A1A1A',
  grainSpacing: 1.2, grains: 8, spread: 5, opacityRange: .6, opacityBase: .15,
  radiusRange: 1.8, radiusBase: .6, eraserDefault: 28, eraserMin: 10, eraserMax: 120,
  zoomMin: .5, zoomMax: 3, zoomStep: .1,
  previewWidth: 240, previewHeight: 160,
} as const;

const canvasLayers = new WeakMap<HTMLCanvasElement, SketchLayerBuffers>();

function seededRandom(seed: number) {
  let value = seed >>> 0;
  return () => {
    value += 0x6D2B79F5;
    let mixed = Math.imul(value ^ value >>> 15, 1 | value);
    mixed ^= mixed + Math.imul(mixed ^ mixed >>> 7, 61 | mixed);
    return ((mixed ^ mixed >>> 14) >>> 0) / 4294967296;
  };
}

export function drawSketchStroke(context: CanvasRenderingContext2D, stroke: SketchStroke) {
  if (!stroke.points.length) return;
  context.save();
  context.lineCap = context.lineJoin = 'round';
  if (stroke.kind === 'eraser') {
    context.globalCompositeOperation = 'destination-out';
    context.globalAlpha = 1;
    context.lineWidth = stroke.size;
    context.beginPath();
    if (stroke.points.length === 1) {
      context.arc(stroke.points[0].x, stroke.points[0].y, stroke.size / 2, 0, Math.PI * 2);
      context.fill();
    } else {
      context.moveTo(stroke.points[0].x, stroke.points[0].y);
      stroke.points.slice(1).forEach(point => context.lineTo(point.x, point.y));
      context.stroke();
    }
  } else {
    const random = seededRandom(stroke.seed);
    context.globalCompositeOperation = 'source-over';
    context.fillStyle = DRAWING.charcoal;
    const dab = (point: SketchPoint) => {
      for (let j = 0; j < DRAWING.grains; j++) {
        const x = point.x + (random() - .5) * DRAWING.spread;
        const y = point.y + (random() - .5) * DRAWING.spread;
        context.globalAlpha = random() * DRAWING.opacityRange + DRAWING.opacityBase;
        context.beginPath();
        context.arc(x, y, random() * DRAWING.radiusRange + DRAWING.radiusBase, 0, Math.PI * 2);
        context.fill();
      }
    };
    dab(stroke.points[0]);
    for (let i = 1; i < stroke.points.length; i++) {
      const from = stroke.points[i - 1], to = stroke.points[i];
      const steps = Math.max(1, Math.floor(Math.hypot(to.x - from.x, to.y - from.y) / DRAWING.grainSpacing));
      for (let j = 1; j <= steps; j++) dab({ x: from.x + (to.x - from.x) * j / steps, y: from.y + (to.y - from.y) * j / steps });
    }
  }
  context.restore();
}

export function renderSketchLayers(canvas: HTMLCanvasElement, actions: readonly SketchAction[], baseline?: SketchLayerBuffers): SketchLayerBuffers {
  let buffers = canvasLayers.get(canvas);
  if (!buffers) {
    buffers = { sketch: canvas.ownerDocument.createElement('canvas'), render: canvas.ownerDocument.createElement('canvas'), hasImage: false };
    canvasLayers.set(canvas, buffers);
  }
  for (const layer of [buffers.sketch, buffers.render]) { layer.width = canvas.width; layer.height = canvas.height; }
  const inkContext = buffers.sketch.getContext('2d');
  const imageContext = buffers.render.getContext('2d');
  if (!inkContext || !imageContext) throw new Error('Canvas 2D is unavailable');
  buffers.hasImage = baseline?.hasImage ?? false;
  if (baseline) {
    inkContext.drawImage(baseline.sketch, 0, 0);
    imageContext.drawImage(baseline.render, 0, 0);
  }
  for (const action of actions) {
    if (action.kind === 'clear') {
      buffers.hasImage = false;
      inkContext.clearRect(0, 0, canvas.width, canvas.height);
      imageContext.clearRect(0, 0, canvas.width, canvas.height);
    } else if (action.kind === 'image') {
      buffers.hasImage = true;
      imageContext.clearRect(0, 0, canvas.width, canvas.height);
      const ratio = Math.min(canvas.width / action.image.naturalWidth, canvas.height / action.image.naturalHeight);
      const width = action.image.naturalWidth * ratio, height = action.image.naturalHeight * ratio;
      imageContext.drawImage(action.image, (canvas.width - width) / 2, (canvas.height - height) / 2, width, height);
    } else drawSketchStroke(action.kind === 'eraser' && action.target === 'render' ? imageContext : inkContext, action);
  }
  return buffers;
}

export function renderSketch(canvas: HTMLCanvasElement, actions: readonly SketchAction[], layers: SketchLayers = createSketchLayers(), baseline?: SketchLayerBuffers): boolean {
  const context = canvas.getContext('2d');
  if (!context) throw new Error('Canvas 2D is unavailable');
  const buffers = renderSketchLayers(canvas, actions, baseline);
  context.save();
  context.globalCompositeOperation = 'source-over';
  context.globalAlpha = 1;
  context.fillStyle = DRAWING.paper;
  context.fillRect(0, 0, canvas.width, canvas.height);
  for (const key of ['render', 'sketch'] as const) {
    if (layers[key].visible) {
      context.globalAlpha = layers[key].opacity;
      context.drawImage(buffers[key], 0, 0);
    }
  }
  context.restore();
  return buffers.hasImage && layers.render.visible;
}

export function snapshotSketchLayers(canvas: HTMLCanvasElement, document: SketchDocument): SketchLayerBuffers {
  const current = renderSketchLayers(canvas, document.actions.slice(0, document.cursor), document.baseline);
  const copy = (source: HTMLCanvasElement) => {
    const result = canvas.ownerDocument.createElement('canvas');
    result.width = source.width; result.height = source.height;
    result.getContext('2d')!.drawImage(source, 0, 0);
    return result;
  };
  return { render: copy(current.render), sketch: copy(current.sketch), hasImage: current.hasImage };
}

export function sketchHistoryPreview(canvas: HTMLCanvasElement): string {
  const preview = canvas.ownerDocument.createElement('canvas');
  preview.width = DRAWING.previewWidth; preview.height = DRAWING.previewHeight;
  preview.getContext('2d')!.drawImage(canvas, 0, 0, preview.width, preview.height);
  return preview.toDataURL('image/png');
}

export function sketchHasInk(canvas: HTMLCanvasElement): boolean {
  const context = canvas.getContext('2d');
  if (!context) return false;
  const pixels = context.getImageData(0, 0, canvas.width, canvas.height).data;
  for (let i = 0; i < pixels.length; i += 4) {
    if (pixels[i] < 255 || pixels[i + 1] < 255 || pixels[i + 2] < 255) return true;
  }
  return false;
}

export function exportSketch(canvas: HTMLCanvasElement): Promise<Blob> {
  return new Promise((resolve, reject) => {
    canvas.toBlob(blob => blob ? resolve(blob) : reject(new Error('PNG export failed')), 'image/png');
  });
}

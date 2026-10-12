// [Input] Canvas 2D context and ordered pen/eraser/clear operations from SketchInputDialog.
// [Output] Fixed-ratio stroke rendering, visible-ink detection and PNG export without network calls.
// [Pos] Pure canvas helpers for Chat hand-drawn image input.
// [Sync] 2026-10-09: add local drawing primitives; no media or message protocol changes.

export const SKETCH_WIDTH = 900;
export const SKETCH_HEIGHT = 600;
export type SketchPoint = { x: number; y: number };
export type SketchStroke = { kind: 'pen' | 'eraser'; points: SketchPoint[] };
export type SketchAction = SketchStroke | { kind: 'clear' };

export function drawSketchStroke(context: CanvasRenderingContext2D, stroke: SketchStroke) {
  if (!stroke.points.length) return;
  const width = stroke.kind === 'pen' ? 4 : 28;
  context.strokeStyle = context.fillStyle = stroke.kind === 'pen' ? '#222222' : '#ffffff';
  context.lineWidth = width;
  context.lineCap = context.lineJoin = 'round';
  context.beginPath();
  if (stroke.points.length === 1) {
    context.arc(stroke.points[0].x, stroke.points[0].y, width / 2, 0, Math.PI * 2);
    context.fill();
  } else {
    context.moveTo(stroke.points[0].x, stroke.points[0].y);
    stroke.points.slice(1).forEach(point => context.lineTo(point.x, point.y));
    context.stroke();
  }
}

export function renderSketch(canvas: HTMLCanvasElement, actions: readonly SketchAction[]) {
  const context = canvas.getContext('2d');
  if (!context) throw new Error('Canvas 2D is unavailable');
  context.fillStyle = '#ffffff';
  context.fillRect(0, 0, canvas.width, canvas.height);
  for (const action of actions) {
    if (action.kind === 'clear') {
      context.fillStyle = '#ffffff';
      context.fillRect(0, 0, canvas.width, canvas.height);
    } else drawSketchStroke(context, action);
  }
}

export function sketchHasInk(canvas: HTMLCanvasElement): boolean {
  const context = canvas.getContext('2d');
  if (!context) return false;
  const pixels = context.getImageData(0, 0, canvas.width, canvas.height).data;
  for (let index = 0; index < pixels.length; index += 4) {
    if (pixels[index] < 255 || pixels[index + 1] < 255 || pixels[index + 2] < 255) return true;
  }
  return false;
}

export function exportSketch(canvas: HTMLCanvasElement): Promise<Blob> {
  return new Promise((resolve, reject) => {
    canvas.toBlob(blob => blob ? resolve(blob) : reject(new Error('PNG export failed')), 'image/png');
  });
}

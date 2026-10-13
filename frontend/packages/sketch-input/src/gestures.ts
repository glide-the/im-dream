// [Input] Pointer IDs/client coordinates, corresponding to the reference GestureController TouchList.
// [Output] Two-pointer midpoint pan and relative zoom without drawing/history mutation.
// [Pos] Local gesture module within the single charcoal component package.
// [Sync] 2026-10-13: preserve reference two-finger view interaction using Pointer Events.

import type { SketchPoint } from './history';

export class GestureController {
  private points = new Map<number, SketchPoint>();
  private previous: { midpoint: SketchPoint; distance: number } | null = null;
  get active() { return this.points.size >= 2; }
  start(id: number, point: SketchPoint) { this.points.set(id, point); this.previous = this.measure(); }
  end(id: number) { this.points.delete(id); this.previous = null; }
  move(id: number, point: SketchPoint) {
    if (!this.points.has(id)) return null;
    this.points.set(id, point);
    const current = this.measure(), previous = this.previous;
    this.previous = current;
    if (!current || !previous) return null;
    return { dx: current.midpoint.x - previous.midpoint.x, dy: current.midpoint.y - previous.midpoint.y,
      scale: previous.distance > 0 ? current.distance / previous.distance : 1 };
  }
  private measure() {
    const [first, second] = [...this.points.values()];
    if (!first || !second) return null;
    return { midpoint: { x: (first.x + second.x) / 2, y: (first.y + second.y) / 2 },
      distance: Math.hypot(first.x - second.x, first.y - second.y) };
  }
}

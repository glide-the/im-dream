// [Input] SketchEditor and the controlled history module.
// [Output] The single browser component package API; styles are an explicit subpath.
// [Pos] Public sketch-input entry; never imports the host application.
// [Sync] 2026-10-13: expose a local editor and draft contract with no service dependencies.

export { SketchEditor, type SketchEditorLabels, type SketchEditorProps } from './SketchEditor';
export { createSketchDocument, type SketchDocument } from './history';

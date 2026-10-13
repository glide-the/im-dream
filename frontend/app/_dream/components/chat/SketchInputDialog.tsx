// [Input] @ink-dream/sketch-input, shared Modal, i18n and AIInputDock original upload callback/policy.
// [Output] Thread-owned draft and thin editor adapter; PNG upload remains in AIInputDock.
// [Pos] Chat sketch dialog adapter, without a second drawing engine.
// [Sync] 2026-10-13: use one workspace package and retain shared Modal behavior.

import { useCallback, useRef, useState } from 'react';
import { useTranslation } from 'react-i18next';
import { createSketchDocument, SketchEditor, type SketchEditorLabels } from '@ink-dream/sketch-input';
import '@ink-dream/sketch-input/styles.css';
import Modal from './Modal';
import './SketchInputDialog.css';

interface SketchInputDialogProps {
  open: boolean;
  disabled?: boolean;
  maxFileBytes: number;
  onClose: () => void;
  onAdd: (file: File) => Promise<boolean>;
}

export default function SketchInputDialog({ open, disabled = false, maxFileBytes, onClose, onAdd }: SketchInputDialogProps) {
  const { t } = useTranslation();
  const [document, setDocument] = useState(createSketchDocument);
  const penRef = useRef<HTMLButtonElement>(null);
  const savingRef = useRef(false);
  const onSavingChange = useCallback((saving: boolean) => { savingRef.current = saving; }, []);
  const close = () => { if (!savingRef.current) onClose(); };
  const text = (key: string) => t(`chat.inputDock.sketch.${key}`);
  const labels: SketchEditorLabels = {
    tools: text('tools'), pen: text('pen'), eraser: text('eraser'), pan: text('pan'),
    undo: text('undo'), redo: text('redo'), clear: text('clear'), canvas: text('canvas'),
    back: text('return'), add: text('add'), adding: text('adding'), filename: text('filename'), addFailed: text('addFailed'),
    importImage: text('importImage'), importing: text('importing'), importFailed: text('importFailed'), imageTooLarge: text('imageTooLarge'),
    layeredCanvas: text('layeredCanvas'), layers: text('layers'), history: text('history'), toolkit: text('toolkit'),
    sketchLayer: text('sketchLayer'), imageLayer: text('imageLayer'), eraseTarget: text('eraseTarget'),
    eraseSketch: text('eraseSketch'), eraseImage: text('eraseImage'), closeHistory: text('closeHistory'), clearHistory: text('clearHistory'),
    restore: text('restore'), fragments: text('fragments'), noHistory: text('noHistory'), layerHidden: text('layerHidden'),
    eraserSize: text('eraserSize'), zoomIn: text('zoomIn'), zoomOut: text('zoomOut'), resetView: text('resetView'), zoom: text('zoom'),
  };
  return <Modal open={open} title={text('title')} onClose={close} closeLabel={text('return')}
    initialFocusRef={penRef} surfaceClassName="sketch-input-dialog">
    <SketchEditor document={document} onDocumentChange={setDocument} labels={labels} maxFileBytes={maxFileBytes}
      disabled={disabled} initialFocusRef={penRef} onClose={close} onAdd={onAdd} onSavingChange={onSavingChange} />
  </Modal>;
}

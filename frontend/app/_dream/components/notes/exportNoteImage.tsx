// [Input] Frozen prose snapshot and capture progress callback.
// [Output] Full-resolution PNG parts using the existing Chat capture and download owners.
// [Pos] Offscreen note renderer; all created DOM and React roots are released after capture.
import {flushSync} from 'react-dom';
import {createRoot} from 'react-dom/client';
import {BRAND_FILE_PREFIX} from '../../constants/brand';
import {capturePartBlobs, type RenderedThreadImage} from '../chat/exportThreadImage';
import NoteContent from './NoteContent';
import type {NoteSnapshot} from './noteShare';
export async function exportNoteImage(note: NoteSnapshot, onProgress: (value: {done: number; total: number}) => void): Promise<RenderedThreadImage> {
  const host = document.createElement('div');
  host.style.cssText = 'position:fixed;left:-100000px;top:0;pointer-events:none;';
  document.body.appendChild(host);
  const root = createRoot(host);
  try {
    flushSync(() => root.render(<NoteContent note={note} exporting/>));
    await document.fonts.ready;
    const node = host.firstElementChild as HTMLElement;
    const blobs = await capturePartBlobs(node, host, {onProgress});
    if (!blobs.length) throw new Error('NOTE_EXPORT_EMPTY');
    const title = note.title.replace(/[^\w一-龥-]+/g, '-').slice(0, 48) || 'note';
    return {images: blobs.map(blob => URL.createObjectURL(blob)), fileName: `${BRAND_FILE_PREFIX}-${title}.png`};
  } finally { root.unmount(); host.remove(); }
}

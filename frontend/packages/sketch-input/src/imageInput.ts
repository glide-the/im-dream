// [Input] Browser-local File, host upload-size policy and AbortSignal.
// [Output] Decoded local image or classified error; object URLs always released.
// [Pos] Image input module of sketch-input; performs no network upload.
// [Sync] 2026-10-13: decode before committing history and cancel on editor close/unmount.

export class ImageInputError extends Error {
  constructor(public readonly code: 'type' | 'size' | 'decode') {
    super(`Image input failed: ${code}`);
  }
}

export async function decodeSketchImage(file: File, maxFileBytes: number, signal: AbortSignal): Promise<HTMLImageElement> {
  if (signal.aborted) throw new DOMException('Image import cancelled', 'AbortError');
  if (!file.type.startsWith('image/')) throw new ImageInputError('type');
  if (file.size > maxFileBytes) throw new ImageInputError('size');
  const url = URL.createObjectURL(file);
  const image = new Image();
  try {
    await new Promise<void>((resolve, reject) => {
      const abort = () => {
        image.src = '';
        reject(new DOMException('Image import cancelled', 'AbortError'));
      };
      const cleanup = () => signal.removeEventListener('abort', abort);
      image.onload = () => {
        cleanup();
        if (image.naturalWidth && image.naturalHeight) resolve();
        else reject(new ImageInputError('decode'));
      };
      image.onerror = () => { cleanup(); reject(new ImageInputError('decode')); };
      signal.addEventListener('abort', abort, { once: true });
      image.src = url;
      if (signal.aborted) abort();
    });
    return image;
  } finally {
    image.onload = image.onerror = null;
    URL.revokeObjectURL(url);
  }
}

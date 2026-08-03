// [Input] Same-width PNG data URLs (the export slices/parts, produced by canvas.toDataURL).
// [Output] A single merged PNG as a Blob — stitched vertically at the binary level:
//          IDAT inflate (DecompressionStream) → per-row PNG unfiltering → rows re-emitted
//          with filter 0 → deflate (CompressionStream) → new IHDR/IDAT/IEND with CRC32.
//          No canvas involved, so the browser canvas edge/area limits do not apply and the
//          merged image can be arbitrarily tall. Rows stream through; memory stays bounded.
// [Pos] binary PNG stitching utility node in frontend/src/lib
// [Sync] 2026-08-03: created for the share long-image export — replaces canvas-based
//                    stitching so very long conversations still merge into one big PNG.

const PNG_SIGNATURE = new Uint8Array([0x89, 0x50, 0x4e, 0x47, 0x0d, 0x0a, 0x1a, 0x0a]);
const IDAT_TYPE = new Uint8Array([0x49, 0x44, 0x41, 0x54]); // 'IDAT'
const BYTES_PER_PIXEL = 4; // 8-bit RGBA (color type 6) — what canvas.toDataURL emits
const INFLATE_WRITE_CHUNK = 4 * 1024 * 1024;

interface PngPart {
  width: number;
  height: number;
  idat: Uint8Array;
}

// ---------- CRC32 (PNG chunk integrity) ----------

const CRC_TABLE = (() => {
  const table = new Uint32Array(256);
  for (let n = 0; n < 256; n += 1) {
    let c = n;
    for (let k = 0; k < 8; k += 1) {
      c = c & 1 ? 0xedb88320 ^ (c >>> 1) : c >>> 1;
    }
    table[n] = c >>> 0;
  }
  return table;
})();

/** Incremental CRC32 — feed chunks in order; initial state 0xffffffff, finalize with ~state. */
function crc32Update(state: number, bytes: Uint8Array): number {
  let c = state;
  for (let i = 0; i < bytes.length; i += 1) {
    c = CRC_TABLE[(c ^ bytes[i]) & 0xff] ^ (c >>> 8);
  }
  return c;
}

// ---------- PNG parsing ----------

function readU32(bytes: Uint8Array, offset: number): number {
  return ((bytes[offset] << 24) | (bytes[offset + 1] << 16) | (bytes[offset + 2] << 8) | bytes[offset + 3]) >>> 0;
}

function writeU32(target: Uint8Array, offset: number, value: number): void {
  target[offset] = (value >>> 24) & 0xff;
  target[offset + 1] = (value >>> 16) & 0xff;
  target[offset + 2] = (value >>> 8) & 0xff;
  target[offset + 3] = value & 0xff;
}

function concatBytes(chunks: Uint8Array[]): Uint8Array {
  const total = chunks.reduce((sum, chunk) => sum + chunk.length, 0);
  const out = new Uint8Array(total);
  let cursor = 0;
  for (const chunk of chunks) {
    out.set(chunk, cursor);
    cursor += chunk.length;
  }
  return out;
}

async function dataUrlToBytes(dataUrl: string): Promise<Uint8Array> {
  const response = await fetch(dataUrl);
  return new Uint8Array(await response.arrayBuffer());
}

/** Parse a canvas-produced PNG (8-bit RGBA, non-interlaced). Throws on any other layout. */
function parsePng(bytes: Uint8Array): PngPart {
  for (let i = 0; i < PNG_SIGNATURE.length; i += 1) {
    if (bytes[i] !== PNG_SIGNATURE[i]) throw new Error('not a PNG file');
  }
  let offset = PNG_SIGNATURE.length;
  let width = 0;
  let height = 0;
  const idatChunks: Uint8Array[] = [];
  while (offset + 8 <= bytes.length) {
    const length = readU32(bytes, offset);
    const type = String.fromCharCode(bytes[offset + 4], bytes[offset + 5], bytes[offset + 6], bytes[offset + 7]);
    const dataStart = offset + 8;
    const dataEnd = dataStart + length;
    if (dataEnd + 4 > bytes.length) throw new Error('truncated PNG chunk');
    if (type === 'IHDR') {
      width = readU32(bytes, dataStart);
      height = readU32(bytes, dataStart + 4);
      const bitDepth = bytes[dataStart + 8];
      const colorType = bytes[dataStart + 9];
      const interlace = bytes[dataStart + 12];
      if (bitDepth !== 8 || colorType !== 6 || interlace !== 0) {
        throw new Error('unsupported PNG layout (need 8-bit RGBA, non-interlaced)');
      }
    } else if (type === 'IDAT') {
      idatChunks.push(bytes.subarray(dataStart, dataEnd));
    } else if (type === 'IEND') {
      break;
    }
    offset = dataEnd + 4;
  }
  if (!width || !height || idatChunks.length === 0) throw new Error('invalid PNG structure');
  return { width, height, idat: concatBytes(idatChunks) };
}

// ---------- PNG scanline unfiltering ----------

function paethPredictor(a: number, b: number, c: number): number {
  const p = a + b - c;
  const pa = Math.abs(p - a);
  const pb = Math.abs(p - b);
  const pc = Math.abs(p - c);
  if (pa <= pb && pa <= pc) return a;
  if (pb <= pc) return b;
  return c;
}

/** Reverse one PNG filter in place (bpp = 4). prevRow is null for the first row. */
function unfilterRow(filterType: number, row: Uint8Array, prevRow: Uint8Array | null): void {
  const bpp = BYTES_PER_PIXEL;
  switch (filterType) {
    case 0:
      return;
    case 1: // Sub
      for (let i = bpp; i < row.length; i += 1) row[i] = (row[i] + row[i - bpp]) & 0xff;
      return;
    case 2: // Up
      if (!prevRow) return;
      for (let i = 0; i < row.length; i += 1) row[i] = (row[i] + prevRow[i]) & 0xff;
      return;
    case 3: // Average
      for (let i = 0; i < row.length; i += 1) {
        const a = i >= bpp ? row[i - bpp] : 0;
        const b = prevRow ? prevRow[i] : 0;
        row[i] = (row[i] + ((a + b) >> 1)) & 0xff;
      }
      return;
    case 4: // Paeth
      for (let i = 0; i < row.length; i += 1) {
        const a = i >= bpp ? row[i - bpp] : 0;
        const b = prevRow ? prevRow[i] : 0;
        const c = i >= bpp && prevRow ? prevRow[i - bpp] : 0;
        row[i] = (row[i] + paethPredictor(a, b, c)) & 0xff;
      }
      return;
    default:
      throw new Error(`unknown PNG filter type ${filterType}`);
  }
}

/** Inflate an IDAT stream and yield raw scanlines (filter byte + pixel bytes) one by one. */
async function processRows(
  idat: Uint8Array,
  rowLength: number,
  onRow: (rawRow: Uint8Array) => Promise<void>,
): Promise<void> {
  const stream = new DecompressionStream('deflate');
  const writePromise = (async () => {
    const writer = stream.writable.getWriter();
    try {
      for (let offset = 0; offset < idat.length; offset += INFLATE_WRITE_CHUNK) {
        await writer.write(idat.subarray(offset, offset + INFLATE_WRITE_CHUNK));
      }
      await writer.close();
    } finally {
      writer.releaseLock();
    }
  })();

  const reader = stream.readable.getReader();
  let pending = new Uint8Array(0);
  try {
    for (;;) {
      const { done, value } = await reader.read();
      if (value && value.length > 0) {
        pending = pending.length > 0 ? concatBytes([pending, value]) : value.slice();
      }
      while (pending.length >= rowLength) {
        const row = pending.slice(0, rowLength);
        pending = pending.slice(rowLength);
        await onRow(row);
      }
      if (done) break;
    }
  } finally {
    reader.releaseLock();
  }
  await writePromise;
}

// ---------- PNG assembly ----------

function makeChunk(type: string, data: Uint8Array): Uint8Array {
  const chunk = new Uint8Array(8 + data.length + 4);
  writeU32(chunk, 0, data.length);
  for (let i = 0; i < 4; i += 1) chunk[4 + i] = type.charCodeAt(i);
  chunk.set(data, 8);
  let crc = 0xffffffff;
  crc = crc32Update(crc, chunk.subarray(4, 8));
  crc = crc32Update(crc, data);
  writeU32(chunk, 8 + data.length, ~crc >>> 0);
  return chunk;
}

/**
 * Stitch same-width PNG data URLs into one tall PNG Blob — binary-level, no canvas,
 * no browser size ceiling. Throws when the input layout is unsupported; callers
 * should fall back to per-part downloads.
 */
export async function stitchPngPartsToBlob(dataUrls: string[]): Promise<Blob> {
  if (typeof DecompressionStream === 'undefined' || typeof CompressionStream === 'undefined') {
    throw new Error('CompressionStream API unavailable');
  }
  const parts: PngPart[] = [];
  for (const dataUrl of dataUrls) {
    parts.push(parsePng(await dataUrlToBytes(dataUrl)));
  }
  const width = parts[0].width;
  if (parts.some((part) => part.width !== width)) {
    throw new Error('PNG parts have mismatched widths');
  }
  const totalHeight = parts.reduce((sum, part) => sum + part.height, 0);

  // Re-encode: rows stream in with filter 0 and deflate on the fly; the CRC over
  // 'IDAT' + compressed bytes accumulates incrementally so nothing is buffered twice.
  const stream = new CompressionStream('deflate');
  const compressedChunks: Uint8Array[] = [];
  let idatCrc = crc32Update(0xffffffff, IDAT_TYPE);
  const readPromise = (async () => {
    const reader = stream.readable.getReader();
    try {
      for (;;) {
        const { done, value } = await reader.read();
        if (value && value.length > 0) {
          compressedChunks.push(value);
          idatCrc = crc32Update(idatCrc, value);
        }
        if (done) break;
      }
    } finally {
      reader.releaseLock();
    }
  })();

  const writer = stream.writable.getWriter();
  const rowLength = 1 + width * BYTES_PER_PIXEL;
  let prevRow: Uint8Array | null = null;
  try {
    for (const part of parts) {
      await processRows(part.idat, rowLength, async (rawRow) => {
        const row = rawRow.slice(1);
        unfilterRow(rawRow[0], row, prevRow);
        const out = new Uint8Array(rowLength);
        out.set(row, 1); // filter byte 0 (None)
        await writer.write(out);
        prevRow = row;
      });
    }
    await writer.close();
  } finally {
    writer.releaseLock();
  }
  await readPromise;

  const ihdr = new Uint8Array(13);
  writeU32(ihdr, 0, width);
  writeU32(ihdr, 4, totalHeight);
  ihdr[8] = 8; // bit depth
  ihdr[9] = 6; // color type RGBA
  const ihdrChunk = makeChunk('IHDR', ihdr);
  const iendChunk = makeChunk('IEND', new Uint8Array(0));

  const idatLength = compressedChunks.reduce((sum, chunk) => sum + chunk.length, 0);
  const idatHeader = new Uint8Array(8);
  writeU32(idatHeader, 0, idatLength);
  idatHeader.set(IDAT_TYPE, 4);
  const idatCrcBytes = new Uint8Array(4);
  writeU32(idatCrcBytes, 0, ~idatCrc >>> 0);

  return new Blob(
    [PNG_SIGNATURE, ihdrChunk, idatHeader, ...compressedChunks, idatCrcBytes, iendChunk],
    { type: 'image/png' },
  );
}

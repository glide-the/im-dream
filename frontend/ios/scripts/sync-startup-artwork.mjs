// [Input] Shared startup vector paths and existing native light/dark text tokens.
// [Output] Transparent standalone SVG and matching iOS appearance variants, or a drift check.
// [Pos] Build-time artwork serialization; the RN renderer consumes the same path JSON.
// [Sync] 2026-11-02: replace paper-backed raster startup artwork with shared transparent vectors.
import fs from 'node:fs';
import path from 'node:path';
import {fileURLToPath} from 'node:url';

const frontend = fileURLToPath(new URL('../../', import.meta.url));
const artwork = JSON.parse(fs.readFileSync(path.join(frontend, 'src/assets/startup-artwork.json'), 'utf8'));
const tokens = fs.readFileSync(path.join(frontend, 'src/components/inkColors.ts'), 'utf8');
const palette = name => {
  const block = tokens.split(name === 'light' ? 'const light = {' : 'const dark: InkColors = {')[1]?.split('};')[0];
  const ink = block?.match(/'color-text-primary'\s*:\s*'([^']+)'/)?.[1];
  if (!ink) throw Error(`Missing existing ${name} ink token`);
  return ink;
};
function svg(ink) {
  const paths = artwork.paths.map(p => `  <path d="${p.d}" fill="${p.fill === 'currentColor' ? ink : p.fill}" stroke="${p.stroke === 'currentColor' ? ink : p.stroke}" stroke-width="${p.strokeWidth}"/>`).join('\n');
  return `<?xml version="1.0" encoding="UTF-8"?>\n<!-- Shared path source: frontend/src/assets/startup-artwork.json. Transparent face and canvas. -->\n<svg xmlns="http://www.w3.org/2000/svg" width="1254" height="1254" viewBox="${artwork.viewBox}" fill="none" stroke-linecap="round" stroke-linejoin="round">\n${paths}\n</svg>\n`;
}
const outputs = new Map([
  ['src/assets/startup.svg', svg('currentColor')],
  ['ios/InkMemory/Assets.xcassets/StartupArtwork.imageset/startup.svg', svg(palette('light'))],
  ['ios/InkMemory/Assets.xcassets/StartupArtwork.imageset/startup-dark.svg', svg(palette('dark'))],
]);
if (!['--write', '--check'].includes(process.argv[2])) throw Error('Use --write or --check');
for (const [relative, content] of outputs) {
  const target = path.join(frontend, relative);
  if (process.argv[2] === '--write') fs.writeFileSync(target, content);
  else if (!fs.existsSync(target) || fs.readFileSync(target, 'utf8') !== content) throw Error(`Startup vector drift: ${relative}`);
}
console.log(`Startup vectors ${process.argv[2] === '--write' ? 'written' : 'match'}: ${outputs.size}; no raster image or background shape.`);

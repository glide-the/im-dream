// [Input] Generated mobile Web resource directory and its asset-manifest.json.
// [Output] Exact file-inventory, byte-count, and SHA-256 verification receipt.
// [Pos] Platform-neutral packaged-resource integrity check; it does not build or sign an application.
// [Sync] 2026-10-24: verify both native hosts consume an intact canonical React resource set.

import { createHash } from 'node:crypto';
import { readFile, readdir, stat } from 'node:fs/promises';
import { resolve } from 'node:path';

const directory = resolve(process.argv[2] ?? 'frontend/shared/build/web');
const manifestPath = resolve(directory, 'asset-manifest.json');
const manifest = JSON.parse(await readFile(manifestPath, 'utf8'));
if (manifest.formatVersion !== 1 || manifest.entry !== 'index.html' || !Array.isArray(manifest.files)) {
  throw new Error('mobile asset manifest shape is invalid');
}

async function inventory(root, relative = '') {
  const files = [];
  for (const name of (await readdir(root)).sort()) {
    const absolute = resolve(root, name);
    const child = relative ? `${relative}/${name}` : name;
    const details = await stat(absolute);
    if (details.isDirectory()) files.push(...await inventory(absolute, child));
    else if (child !== 'asset-manifest.json') {
      const content = await readFile(absolute);
      files.push({ path: child, bytes: content.byteLength, sha256: createHash('sha256').update(content).digest('hex') });
    }
  }
  return files;
}

const actual = await inventory(directory);
if (JSON.stringify(actual) !== JSON.stringify(manifest.files)) {
  throw new Error('mobile asset inventory or digest does not match asset-manifest.json');
}

process.stdout.write(`mobile-assets-check: ${actual.length} files verified at ${directory}\n`);

// [Input] Canonical Dream React source, mobile entry HTML, public assets, and an explicit output directory.
// [Output] One local WebView resource bundle and hash manifest shared by the iOS and Android native hosts.
// [Pos] Mobile resource build adapter inside the sole frontend workspace; Next remains the Web build owner.
// [Sync] 2026-10-25: preserve original visual resources; packaging only rewrites local asset locations.
// [Sync] 2026-10-24: guard cleanup ownership, keep public URLs local, and emit hashes.

import { build } from 'esbuild';
import { createHash } from 'node:crypto';
import { cp, lstat, mkdir, readFile, readdir, rm, stat, writeFile } from 'node:fs/promises';
import { basename, dirname, parse, relative, resolve, sep } from 'node:path';
import { homedir } from 'node:os';
import { fileURLToPath } from 'node:url';

const frontendRoot = resolve(dirname(fileURLToPath(import.meta.url)), '..');
const repositoryRoot = resolve(frontendRoot, '..');
const argumentIndex = process.argv.indexOf('--outdir');
const outputArgument = argumentIndex >= 0 ? process.argv[argumentIndex + 1] : undefined;
if (argumentIndex >= 0 && !outputArgument) throw new Error('--outdir requires a path');
const outdir = resolve(frontendRoot, outputArgument ?? '../mobile/shared/build/web');
const outputMarker = '.ink-mobile-assets-output';
const outputMarkerValue = 'ink-memory-mobile-assets-v1\n';

function contains(parent, child) {
  const candidate = relative(parent, child);
  return candidate === '' || (!candidate.startsWith(`..${sep}`) && candidate !== '..' && !candidate.startsWith(sep));
}

function assertOwnedOutputDirectory(directory) {
  const filesystemRoot = parse(directory).root;
  for (const protectedPath of [filesystemRoot, homedir(), repositoryRoot, frontendRoot]) {
    if (contains(directory, protectedPath)) {
      throw new Error(`refusing to clean protected output directory: ${directory}`);
    }
  }

  if (contains(repositoryRoot, directory)) {
    const mobileRoot = resolve(repositoryRoot, 'mobile');
    const segments = relative(mobileRoot, directory).split(sep);
    if (!contains(mobileRoot, directory) || !segments.includes('build')) {
      throw new Error(`repository output must be a generated directory below mobile/**/build: ${directory}`);
    }
    return;
  }

  if (!['app', 'web', 'WebAssets'].includes(basename(directory))) {
    throw new Error(`external output must use a dedicated app, web, or WebAssets directory: ${directory}`);
  }
}

assertOwnedOutputDirectory(outdir);

const existingOutput = await lstat(outdir).catch((error) => {
  if (error?.code === 'ENOENT') return null;
  throw error;
});
if (existingOutput) {
  if (!existingOutput.isDirectory() || existingOutput.isSymbolicLink()) {
    throw new Error(`refusing to replace non-directory output: ${outdir}`);
  }
  const marker = await readFile(resolve(outdir, outputMarker), 'utf8').catch(() => null);
  const existingEntries = await readdir(outdir);
  if (existingEntries.length > 0 && marker !== outputMarkerValue) {
    throw new Error(`refusing to clean output without Ink & Memory ownership marker: ${outdir}`);
  }
}

await rm(outdir, { recursive: true, force: true });
await mkdir(resolve(outdir, 'assets'), { recursive: true });
await writeFile(resolve(outdir, outputMarker), outputMarkerValue);

await build({
  absWorkingDir: frontendRoot,
  entryPoints: ['mobile/entry.tsx'],
  outdir,
  bundle: true,
  format: 'esm',
  platform: 'browser',
  target: ['safari16.4', 'chrome109'],
  minify: true,
  legalComments: 'eof',
  entryNames: 'assets/app',
  assetNames: 'assets/[name]-[hash]',
  loader: {
    '.png': 'file', '.jpg': 'file', '.jpeg': 'file', '.gif': 'file', '.svg': 'file',
    '.woff': 'file', '.woff2': 'file', '.ttf': 'file',
  },
  alias: { '@': resolve(frontendRoot, 'app') },
  plugins: [{
    name: 'public-root-urls',
    setup(buildContext) {
      buildContext.onResolve({ filter: /^\// }, (args) => args.kind === 'url-token'
        ? { path: args.path, external: true }
        : undefined);
    },
  }],
  define: {
    'process.env.NODE_ENV': '"production"',
    'process.env.NEXT_PUBLIC_WS_BASE_URL': 'undefined',
  },
  logLevel: 'info',
});

const html = await readFile(resolve(frontendRoot, 'mobile/index.html'), 'utf8');
await writeFile(resolve(outdir, 'index.html'), html);
const cssPath = resolve(outdir, 'assets/app.css');
const css = (await readFile(cssPath, 'utf8')).replace(/url\((['"]?)\/([^)'"\s]+)\1\)/g, 'url($1../$2$1)');
await writeFile(cssPath, css);
await cp(resolve(frontendRoot, 'public'), outdir, { recursive: true, force: true });

async function inventory(directory, relative = '') {
  const entries = await readdir(directory);
  const files = [];
  for (const name of entries.sort()) {
    const absolute = resolve(directory, name);
    const childRelative = relative ? `${relative}/${name}` : name;
    const details = await stat(absolute);
    if (details.isDirectory()) files.push(...await inventory(absolute, childRelative));
    else if (childRelative !== 'asset-manifest.json') {
      const content = await readFile(absolute);
      files.push({ path: childRelative, bytes: content.byteLength, sha256: createHash('sha256').update(content).digest('hex') });
    }
  }
  return files;
}

const files = await inventory(outdir);
await writeFile(resolve(outdir, 'asset-manifest.json'), `${JSON.stringify({ formatVersion: 1, entry: 'index.html', files }, null, 2)}\n`);

process.stdout.write(`mobile-assets: ${outdir} (${files.length} files)\n`);

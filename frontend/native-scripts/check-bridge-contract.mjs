// [Input] Versioned bridge manifest plus TypeScript, Swift, Kotlin, and Python protocol sources.
// [Output] Deterministic protocol inventory and cross-language name-drift validation.
// [Pos] Mobile bridge validation entry; it performs no build, network, or service operation.
// [Sync] 2026-10-24: leave the local startup timer outside the shared method/event contract.
// [Sync] 2026-10-24: compare exact method/event inventories and identifier patterns across language mirrors.

import { readFile } from 'node:fs/promises';
import { dirname, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';

const mobileRoot = resolve(dirname(fileURLToPath(import.meta.url)), '..');
const repositoryRoot = resolve(mobileRoot, '..');
const manifestPath = resolve(mobileRoot, 'shared/bridge/contract.json');
const manifest = JSON.parse(await readFile(manifestPath, 'utf8'));

const fail = (message) => {
  process.stderr.write(`bridge-contract: ${message}\n`);
  process.exitCode = 1;
};

if (!/^\d+\.\d+$/.test(manifest.protocolVersion ?? '')) {
  fail('protocolVersion must use major.minor form');
}

const methodNames = manifest.methods?.map((entry) => entry.name) ?? [];
const eventNames = manifest.events?.map((entry) => entry.name) ?? [];
const errorCodes = manifest.errorCodes ?? [];

for (const [label, values] of [['method', methodNames], ['event', eventNames], ['error', errorCodes]]) {
  if (new Set(values).size !== values.length) fail(`${label} names must be unique`);
}

for (const method of manifest.methods ?? []) {
  if (!/^[a-z][a-zA-Z0-9]*(\.[a-z][a-zA-Z0-9]*)+$/.test(method.name ?? '')) fail(`invalid method name: ${method.name}`);
  if (!['native', 'python'].includes(method.owner)) fail(`invalid owner for ${method.name}`);
  if (typeof method.purpose !== 'string' || method.purpose.trim().length < 12) fail(`missing purpose for ${method.name}`);
}

const unsafeNames = ['shell.execute', 'native.invoke', 'file.readPath', 'eval.execute', 'secret.read'];
for (const name of unsafeNames) if (methodNames.includes(name)) fail(`unsafe generic capability is forbidden: ${name}`);

const sources = [
  {
    path: resolve(repositoryRoot, 'frontend/app/_dream/platform/mobileBridge.ts'),
    methods: [/mobileBridgeMethodNames\s*=\s*\[([\s\S]*?)\]\s*as const/],
    events: [/mobileBridgeEventNames\s*=\s*\[([\s\S]*?)\]\s*as const/],
  },
  {
    path: resolve(repositoryRoot, 'backend/mobile_runtime/contract.py'),
    methods: [/MOBILE_BRIDGE_METHODS\s*=\s*frozenset\([\s\S]*?\{([\s\S]*?)\}[\s\S]*?\)/],
    events: [/MOBILE_BRIDGE_EVENTS\s*=\s*frozenset\([\s\S]*?\{([\s\S]*?)\}[\s\S]*?\)/],
  },
  {
    path: resolve(mobileRoot, 'ios/InkMemory/MobileBridgeContract.swift'),
    methods: [/static let methods[^=]*=\s*\[([\s\S]*?)\]/],
    events: [/static let events[^=]*=\s*\[([\s\S]*?)\]/],
  },
  {
    path: resolve(mobileRoot, 'android/app/src/main/java/com/inkmemory/mobile/bridge/MobileBridgeContract.kt'),
    methods: [/val methods[^=]*=\s*setOf\(([\s\S]*?)\n\s*\)/],
    events: [/val events[^=]*=\s*setOf\(([\s\S]*?)\n\s*\)/],
  },
];

function parseInventory(text, patterns, label, source) {
  const match = patterns.map((pattern) => text.match(pattern)).find(Boolean);
  if (!match) {
    fail(`${label} inventory cannot be parsed: ${source}`);
    return [];
  }
  return [...match[1].matchAll(/["']([a-z][a-zA-Z0-9]*(?:\.[a-z][a-zA-Z0-9]*)+)["']/g)].map((entry) => entry[1]);
}

function compareInventory(expected, actual, label, source) {
  const expectedSet = new Set(expected);
  const actualSet = new Set(actual);
  const missing = expected.filter((name) => !actualSet.has(name));
  const extra = actual.filter((name) => !expectedSet.has(name));
  if (missing.length || extra.length || actualSet.size !== actual.length) {
    fail(`${label} inventory drift in ${source}; missing=[${missing.join(',')}], extra=[${extra.join(',')}]`);
  }
}

for (const source of sources) {
  let text;
  try {
    text = await readFile(source.path, 'utf8');
  } catch {
    fail(`missing protocol source: ${source.path}`);
    continue;
  }
  if (!text.includes(manifest.protocolVersion)) fail(`protocol version drift: ${source.path}`);
  if (!text.includes(manifest.requestIdPattern) || !text.includes(manifest.pageGenerationPattern)) {
    fail(`identifier pattern drift: ${source.path}`);
  }
  compareInventory(methodNames, parseInventory(text, source.methods, 'method', source.path), 'method', source.path);
  compareInventory(eventNames, parseInventory(text, source.events, 'event', source.path), 'event', source.path);
}

if (!process.exitCode) {
  process.stdout.write(`bridge-contract: ${methodNames.length} methods, ${eventNames.length} events, ${errorCodes.length} errors\n`);
}

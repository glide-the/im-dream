// [Input] Original iOS host startWeb function and explicit synthetic application environments.
// [Output] Worker environment, callback preservation and existing lifecycle rejection evidence.
// [Pos] Provider-free host qualification; executes the production function without sockets, credentials or an application.
// [Sync] 2026-10-31: keep the synthetic workerData aligned with the host's Admin HTTP adapter module.
import assert from 'node:assert/strict';
import fs from 'node:fs';
import path from 'node:path';
import vm from 'node:vm';
import {fileURLToPath} from 'node:url';

const hostPath = fileURLToPath(new URL('../runtime/host.cjs', import.meta.url));
const host = fs.readFileSync(hostPath, 'utf8');
const start = host.indexOf('function startWeb(backendOrigin) {');
const end = host.indexOf('\nconst server = ', start);
assert(start >= 0 && end > start, 'Original host startWeb function was not found');
let cases = 0;
for (const configured of [undefined, 'http://localhost:5173/auth/callback', 'com.example.ink.auth:/auth/callback', '']) {
  const instances = [];
  class WorkerFixture {
    constructor(url, options) {
      instances.push({url, options});
      this.stdout = {on() {}};
      this.stderr = {on() {}};
    }
    on() {}
  }
  const applicationEnvironment = {INK_ADMIN_DREAM_SERVICE_CLIENT_ID: 'original-client', INK_DREAM_BFF_COOKIE_SECRET: 'synthetic-value'};
  if (configured !== undefined) applicationEnvironment.INK_DREAM_BFF_REDIRECT_URI = configured;
  const before = {...applicationEnvironment};
  const context = vm.createContext({URL, path, Worker: WorkerFixture, applicationEnvironment,
    webOrigin: new URL('http://localhost:5173'), workerURL: new URL('data:text/javascript,'),
    nextEntry: '/synthetic/app/next/server.js', processBoundaryURL: 'file:///synthetic/boundary.mjs',
    adminHTTPURL: 'file:///synthetic/ios-admin-http.mjs',
    endpointFile: '/synthetic/data/endpoint.json', process: {env: {}, pid: 123},
    webWorker: undefined, webFailure: undefined, webListening: false, boundBackendOrigin: undefined});
  vm.runInContext(host.slice(start, end), context, {filename: hostPath});
  const result = vm.runInContext('startWeb("http://127.0.0.1:5199")', context);
  assert.equal(result.type, 'web_started');
  assert.equal(instances.length, 1);
  const environment = instances[0].options.env;
  assert.equal(environment.INK_DREAM_BFF_REDIRECT_URI, configured ?? 'http://localhost:5173/auth/callback');
  assert.equal(environment.INK_ADMIN_DREAM_SERVICE_CLIENT_ID, before.INK_ADMIN_DREAM_SERVICE_CLIENT_ID);
  assert.equal(environment.INK_DREAM_BFF_COOKIE_SECRET, before.INK_DREAM_BFF_COOKIE_SECRET);
  assert.equal(environment.INK_DREAM_PUBLIC_ORIGIN, 'http://localhost:5173');
  assert.equal(environment.INK_BACKEND_INTERNAL_URL, 'http://127.0.0.1:5199');
  assert.equal(instances[0].options.workerData.adminHTTPURL, 'file:///synthetic/ios-admin-http.mjs');
  assert.deepEqual(applicationEnvironment, before);
  cases++;
  vm.runInContext('startWeb("http://127.0.0.1:5199")', context);
  assert.equal(instances.length, 1); cases++;
  assert.throws(() => vm.runInContext('startWeb("http://127.0.0.1:5200")', context), /IOS_NEXT_BACKEND_ALREADY_BOUND/); cases++;
  assert.throws(() => vm.runInContext('startWeb("https://example.com")', context), /IOS_BACKEND_ORIGIN_INVALID/); cases++;
}
console.log(JSON.stringify({cases, failures: 0, networkRequests: 0, accountCredentialsUsed: false}));

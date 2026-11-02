// [Input] Original iOS host startWeb function and explicit synthetic application environments.
// [Output] Worker environment, callback preservation and original startup error propagation evidence.
// [Pos] Provider-free host qualification; executes the production function without sockets, credentials or an application.
// [Sync] 2026-10-31: keep the synthetic workerData aligned with the host's Admin HTTP adapter module.
// [Sync] 2026-11-01: qualify original Next console errors, failure status and unchanged console forwarding.
import assert from 'node:assert/strict';
import fs from 'node:fs';
import path from 'node:path';
import vm from 'node:vm';
import {fileURLToPath} from 'node:url';
import {format} from 'node:util';

const hostPath = fileURLToPath(new URL('../runtime/host.cjs', import.meta.url));
const host = fs.readFileSync(hostPath, 'utf8');
const start = host.indexOf('function webStatus() {');
const end = host.indexOf('\nconst server = ', start);
assert(start >= 0 && end > start, 'Original host startWeb function was not found');
let cases = 0;
for (const configured of [undefined, 'http://localhost:5173/auth/callback', 'com.example.ink.auth:/auth/callback', '']) {
  const instances = [];
  class WorkerFixture {
    constructor(url, options) {
      this.events = new Map();
      instances.push({url, options, worker: this});
      this.stdout = {on() {}};
      this.stderr = {on() {}};
    }
    on(event, callback) { this.events.set(event, callback); }
  }
  const applicationEnvironment = {INK_ADMIN_DREAM_SERVICE_CLIENT_ID: 'original-client', INK_DREAM_BFF_COOKIE_SECRET: 'synthetic-value'};
  if (configured !== undefined) applicationEnvironment.INK_DREAM_BFF_REDIRECT_URI = configured;
  const before = {...applicationEnvironment};
  const context = vm.createContext({URL, path, Worker: WorkerFixture, applicationEnvironment,
    webOrigin: new URL('http://localhost:5173'), workerURL: new URL('data:text/javascript,'),
    nextEntry: '/synthetic/app/next/server.js', processBoundaryURL: 'file:///synthetic/boundary.mjs',
    adminHTTPURL: 'file:///synthetic/ios-admin-http.mjs',
    endpointFile: '/synthetic/data/endpoint.json', process: {env: {}, pid: 123},
    webWorker: undefined, webFailure: undefined, webError: undefined, webListening: false, boundBackendOrigin: undefined});
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
  const original = 'Error: listen EADDRINUSE: address already in use ::1:5173\n/private/next/server.js:12';
  instances[0].worker.events.get('message')({type:'next_error',error:original});
  // An observed console error alone does not change the existing readiness state.
  assert.equal(vm.runInContext('webStatus().state', context), 'starting');
  instances[0].worker.events.get('exit')(1);
  assert.equal(vm.runInContext('webStatus().error', context), original);
  assert.equal(vm.runInContext('webStatus().code', context), 'IOS_NEXT_WORKER_STOPPED');
  assert.throws(() => vm.runInContext('startWeb("http://127.0.0.1:5199")', context), error => error.message === original); cases++;
}

const workerPath = fileURLToPath(new URL('../runtime/worker.mjs', import.meta.url));
const worker = fs.readFileSync(workerPath, 'utf8');
const captureStart = worker.indexOf('const originalConsoleError =');
const captureEnd = worker.indexOf('const { installIOSAdminHTTP }', captureStart);
assert(captureStart >= 0 && captureEnd > captureStart);
for (const observationFails of [false, true]) {
  const forwarded = [], observed = [];
  const context = vm.createContext({format, console:{error:(...args)=>forwarded.push(args)},
    parentPort:{postMessage:message=>{if(observationFails)throw Error('detached');observed.push(message);}}});
  vm.runInContext(worker.slice(captureStart, captureEnd), context, {filename:workerPath});
  vm.runInContext('console.error("Original %s", "EADDRINUSE")', context);
  assert.equal(forwarded[0][0], 'Original %s');
  assert.equal(forwarded[0][1], 'EADDRINUSE');
  if (!observationFails) assert.equal(observed[0].error, 'Original EADDRINUSE');
  cases++;
}
console.log(JSON.stringify({cases, failures: 0, networkRequests: 0, accountCredentialsUsed: false}));

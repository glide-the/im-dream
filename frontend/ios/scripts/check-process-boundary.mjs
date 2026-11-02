// [Input] The original iOS process-boundary module and this script's isolated Node worker.
// [Output] Mechanical receipts for missing-boundary rejection, immutable bindings and async/sync ENOSYS.
// [Pos] Explicit provider-free validation; fixture platform metadata never enters application resources.
import assert from 'node:assert/strict';
import { Worker, workerData, isMainThread, parentPort } from 'node:worker_threads';
import { once } from 'node:events';

if (isMainThread) {
  const worker = new Worker(new URL(import.meta.url), { workerData: { fixture: 'ios-command-boundary' } });
  const [receipt] = await once(worker, 'message');
  assert.equal(receipt.nativeProcessBlocked, true);
  assert.equal(receipt.missingBoundaryRejected, true);
  assert.equal(receipt.tamperRejected, true);
  const [exitCode] = await once(worker, 'exit');
  assert.equal(exitCode, 0);
  process.stdout.write(JSON.stringify(receipt) + '\n');
} else {
  assert.equal(workerData.fixture, 'ios-command-boundary');
  // This isolated desktop fixture exercises native binding mechanics. Actual
  // iOS support is separately qualified by app-hosted original SDK tests.
  Object.defineProperty(process, 'platform', { value: 'ios' });
  const boundary = await import('../runtime/ios-process-boundary.mjs');
  const childProcess = await import('node:child_process');
  assert.throws(boundary.assertIOSProcessBoundary, /IOS_RUNTIME_PROCESS_BOUNDARY_UNQUALIFIED/);
  boundary.installIOSProcessBoundary();
  const bindings = process.binding('process_wrap');
  assert.throws(() => { bindings.Process.prototype.spawn = () => 0; }, TypeError);
  assert.throws(() => { bindings.Process.prototype = {}; }, TypeError);
  assert.throws(() => { bindings.Process = function () {}; }, TypeError);
  assert.throws(() => { delete bindings.Process.prototype.spawn; }, TypeError);
  assert.throws(() => { process.binding('spawn_sync').spawn = () => ({}); }, TypeError);
  boundary.assertIOSProcessBoundary();
  assert.throws(boundary.rejectIOSCommand, error => error.code === 'ENOSYS');
  const syncResult = childProcess.spawnSync(process.execPath, ['-e', 'process.exit(0)']);
  assert.equal(syncResult.error.code, 'ENOSYS');
  assert.throws(() => childProcess.spawn(process.execPath, ['-e', 'process.exit(0)']),
    error => error.code === 'ENOSYS');
  parentPort.postMessage({ fixture: 'native-binding-mechanics', targetIOS: false,
    missingBoundaryRejected: true, tamperRejected: true, nativeProcessBlocked: true });
}

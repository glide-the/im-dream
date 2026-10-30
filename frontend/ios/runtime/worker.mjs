// [Input] App-owned Runtime entry and one session's SDK arguments/environment.
// [Output] Original Runtime JSONL/control or original Next standalone HTTP in one application worker.
// [Pos] Node worker entry; isolates module state without launching an OS process.
// [Sync] 2026-10-25: Runtime commands use the bundled interpreter; Next retains command denial and no Mac execution.
// [Sync] 2026-10-25: use the packaged Bash as the default CLI shell; Simulator host zsh does not establish guest availability.
// [Sync] 2026-10-25: report the original Next server's actual loopback listening event to the private host.
// [Sync] 2026-10-25: verify IPv4 and IPv6 loopback listeners for the existing configured localhost callback.
// [Sync] 2026-10-25: freeze and verify the iOS external-command boundary before the original Runtime imports.
// [Sync] 2026-10-25: report only HTTP failure classes/codes and duration; SDK stdout and HTTP content stay unchanged.
// [Sync] 2026-10-25: correlate fixed Admin BFF operation labels with response headers/EOF without retaining URLs or credentials.
// [Sync] 2026-10-25: restore original connection policy after fresh Admin connections reproduced session timeouts.
// [Sync] 2026-10-26: let pending original filesystem promises close their handles before a Runtime Worker exits.
// [Sync] 2026-10-26: preserve managed venv PATH precedence and execute plugin Python through the existing guest binding.
import { workerData, parentPort } from 'node:worker_threads';
import { pathToFileURL } from 'node:url';
import path from 'node:path';
import fs from 'node:fs';
import net from 'node:net';
import { syncBuiltinESMExports } from 'node:module';
import { subscribe } from 'node:diagnostics_channel';
const { installIOSProcessBoundary } = await import(workerData.processBoundaryURL);

// The pinned Node24 child_process implementation calls these native bindings.
// Preserve its own streams, error events, callback and sync-result conversion;
// Runtime commands use the in-process guest; the Next worker receives ENOSYS.
// Both routes prevent Simulator from using Mac shell, git or MCP executables.
installIOSProcessBoundary(workerData.commandRuntime);
if (workerData.commandRuntime) {
  // Preserve the original plugin launcher's managed venv precedence. Missing
  // guest commands cannot execute desktop binaries outside the mounted App.
  process.env.PATH = (process.env.PATH ? process.env.PATH + ':' : '') + '/usr/local/bin:/usr/bin:/bin';
  process.env.CLAUDE_CODE_SHELL ||= '/bin/bash';
  process.env.SHELL ||= process.env.CLAUDE_CODE_SHELL;
}

// Subscribers never alter or retain HTTP payloads, headers, URLs or errors.
// Diagnostic failures must not interrupt the original Next/Runtime request.
const httpStarts = new WeakMap();
const usedAdminSockets = new WeakSet();
const adminOperations = new Map([
  ['/api/auth/oauth2/token', 'service-token'],
  ['/api/internal/dream/v1/capabilities', 'capabilities'],
  ['/api/internal/dream/v1/browser-sessions/resolve', 'browser-session-resolve'],
  ['/api/internal/dream/v1/browser-sessions/exchange', 'browser-session-exchange'],
  ['/api/internal/dream/v1/operations/user-profile.current', 'user-profile'],
]);
let httpSequence = 0;
const adminOperation = request => {
  if (workerData.application !== 'next') return undefined;
  const origin = process.env.INK_ADMIN_DREAM_TRANSPORT_BASE_URL || process.env.INK_ADMIN_DREAM_BASE_URL;
  if (!origin || String(request?.origin) !== origin) return undefined;
  return adminOperations.get(String(request?.path).split('?')[0]);
};
const reportAdminPhase = (request, phase, response, reusedConnection) => {
  const observation = httpStarts.get(request);
  if (!observation?.operation) return;
  process.stderr.write('IOS_NEXT_ADMIN_HTTP ' + JSON.stringify({
    id: observation.id, operation: observation.operation, phase,
    ...(Number.isInteger(response?.statusCode) ? {status: response.statusCode} : {}),
    ...(typeof reusedConnection === 'boolean' ? {reusedConnection} : {}),
    elapsedMs: Math.round(performance.now() - observation.started),
  }) + '\n');
};
subscribe('undici:request:create', ({ request }) => {
  try {
    if (request && typeof request === 'object') {
      httpStarts.set(request, {started: performance.now(), id: ++httpSequence, operation: adminOperation(request)});
      reportAdminPhase(request, 'start');
    }
  } catch { /* Observability preserves the original request outcome. */ }
});
subscribe('undici:request:headers', ({request, response}) => {
  try { reportAdminPhase(request, 'headers', response); }
  catch { /* Observability preserves the original request outcome. */ }
});
subscribe('undici:client:sendHeaders', ({request, socket}) => {
  try {
    if (!httpStarts.get(request)?.operation || !socket) return;
    const reused = usedAdminSockets.has(socket);
    usedAdminSockets.add(socket);
    reportAdminPhase(request, 'sent', undefined, reused);
  } catch { /* Observability preserves the original request outcome. */ }
});
subscribe('undici:request:trailers', ({request}) => {
  try { reportAdminPhase(request, 'complete'); }
  catch { /* Observability preserves the original request outcome. */ }
});
subscribe('undici:request:error', ({ request, error }) => {
  try {
    const codes = [];
    for (let cause = error; cause && codes.length < 3; cause = cause.cause) {
      const code = cause.code;
      codes.push(typeof code === 'string' && /^[A-Z][A-Z0-9_]{0,79}$/.test(code) ? code : 'unavailable');
    }
    const observation = httpStarts.get(request);
    process.stderr.write('IOS_NODE_HTTP_FAILURE ' + JSON.stringify({
      application: workerData.application === 'next' ? 'next' : 'runtime',
      ...(observation?.operation ? {id: observation.id, operation: observation.operation} : {}),
      errorClass: typeof error?.name === 'string' && /^[A-Za-z][A-Za-z0-9_]{0,79}$/.test(error.name) ? error.name : 'Error',
      codes, elapsedMs: observation === undefined ? null : Math.round(performance.now() - observation.started),
    }) + '\n');
  } catch { /* Observability preserves the original request outcome. */ }
});

if (workerData.application === 'next') {
  const listen = net.Server.prototype.listen;
  net.Server.prototype.listen = function (...args) {
    this.once('listening', () => {
      const address = this.address();
      if (address && ['127.0.0.1', '::1'].includes(address.address) && address.port === workerData.webPort) {
        parentPort.postMessage({ type: 'next_listening', pid: process.pid, port: address.port });
      }
    });
    return listen.apply(this, args);
  };
}

// Node workers reject process.chdir(). Keep relative filesystem calls and cwd
// session-local, and leave the application's process-wide cwd unchanged.
let cwd = workerData.cwd;
process.cwd = () => cwd;
process.chdir = destination => {
  const next = fs.realpathSync(path.resolve(cwd, destination));
  if (!fs.statSync(next).isDirectory()) throw new Error('ENOTDIR');
  cwd = next;
};
const absolute = value => typeof value === 'string' && !path.isAbsolute(value) ? path.resolve(cwd, value) : value;
const pendingFileOperations = new Set();
const trackFileOperation = operation => {
  if (workerData.commandRuntime && operation && typeof operation.then === 'function') {
    pendingFileOperations.add(operation);
    const completed = () => pendingFileOperations.delete(operation);
    operation.then(completed, completed);
  }
  return operation;
};
const singlePath = ['access', 'appendFile', 'chmod', 'chown', 'lchmod', 'lchown', 'lstat', 'mkdir', 'mkdtemp',
  'open', 'opendir', 'readFile', 'readdir', 'readlink', 'realpath', 'rm', 'rmdir', 'stat', 'statfs',
  'truncate', 'unlink', 'utimes', 'watch', 'watchFile', 'unwatchFile', 'writeFile'];
for (const name of singlePath) {
  for (const target of [name, name + 'Sync']) {
    if (typeof fs[target] !== 'function') continue;
    const original = fs[target];
    fs[target] = (first, ...rest) => original(absolute(first), ...rest);
  }
  if (typeof fs.promises[name] === 'function') {
    const original = fs.promises[name];
    fs.promises[name] = (first, ...rest) => trackFileOperation(original(absolute(first), ...rest));
  }
}
for (const name of ['rename', 'copyFile', 'cp', 'link']) {
  for (const target of [name, name + 'Sync']) {
    if (typeof fs[target] !== 'function') continue;
    const original = fs[target];
    fs[target] = (first, second, ...rest) => original(absolute(first), absolute(second), ...rest);
  }
  if (typeof fs.promises[name] === 'function') {
    const original = fs.promises[name];
    fs.promises[name] = (first, second, ...rest) => trackFileOperation(original(absolute(first), absolute(second), ...rest));
  }
}
syncBuiltinESMExports();
if (workerData.commandRuntime) {
  const exit = process.exit.bind(process);
  let exiting = false;
  process.exit = code => {
    if (exiting) return;
    exiting = true;
    void (async () => {
      while (pendingFileOperations.size) await Promise.allSettled([...pendingFileOperations]);
      exit(code);
    })();
  };
}
if (workerData.application === 'plugin-python') {
  const { spawn } = await import('node:child_process');
  const command = spawn(workerData.argv[0], workerData.argv.slice(1), {cwd, env: process.env, stdio: 'pipe'});
  command.stdin.end();
  command.stdout.pipe(process.stdout, {end: false});
  command.stderr.pipe(process.stderr, {end: false});
  command.once('error', () => process.exit(127));
  command.once('close', code => process.exit(Number.isInteger(code) ? code : 1));
} else {
  const entry = workerData.application === 'next' ? workerData.serverEntry : workerData.runtimeEntry;
  process.argv = [process.execPath, entry, ...workerData.argv];
  await import(pathToFileURL(entry).href);
}

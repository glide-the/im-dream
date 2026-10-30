// [Input] Native-owned endpoint path, fixed Runtime/Next resources, workspace root and private connections.
// [Output] One authenticated application-process socket, persistent original Next and per-session Runtime workers.
// [Pos] iOS Node embedding bootstrap; no model loop, tool router or remote execution.
// [Sync] 2026-10-25: load the fixed worker source as an ESM data URL and leave foreign process descriptors outside Worker unmanaged-FD cleanup.
// [Sync] 2026-10-25: retain the original Workspace Mode-off default at the fixed bundled backend directory.
// [Sync] 2026-10-25: require Next worker listening ownership before qualifying the configured Web origin.
// [Sync] 2026-10-25: load ordinary application .env and reuse its original browser origin without another authentication mode.
// [Sync] 2026-10-25: bind the process-boundary module to a fixed bundle URL for the data-URL worker entry.
// [Sync] 2026-10-25: stage bundled Linux commands in App data and pass native-owned paths to Runtime workers.
// [Sync] 2026-10-26: accept explicit Worker termination and report the existing exit packet after cleanup completes.
// [Sync] 2026-10-26: permit plugin-management cwd only inside the application's managed plugin root.
// [Sync] 2026-10-26: execute managed plugin Python commands through the same authenticated Worker and guest binding.
const fs = require('node:fs');
const path = require('node:path');
const net = require('node:net');
const crypto = require('node:crypto');
const { Worker } = require('node:worker_threads');
const { pathToFileURL } = require('node:url');

const [endpointFile, workspaceRoot, runtimeEntry, applicationDataRoot] = process.argv.slice(2);
if (!endpointFile || !workspaceRoot || !runtimeEntry || !applicationDataRoot) throw new Error('IOS_RUNTIME_CONFIGURATION_REQUIRED');
const resourcesRoot = fs.realpathSync(path.dirname(__dirname));
const dataRoot = fs.realpathSync(applicationDataRoot);
const guestManifest = JSON.parse(fs.readFileSync(path.join(resourcesRoot, 'guest/manifest.json'), 'utf8'));
if (!/^[a-f0-9]{64}$/.test(guestManifest.rootDigest)) throw new Error('IOS_GUEST_MANIFEST_INVALID');
const guestRoot = path.join(path.dirname(endpointFile), 'guest', guestManifest.rootDigest);
if (!fs.existsSync(path.join(guestRoot, '.ready'))) {
  fs.mkdirSync(path.dirname(guestRoot), {recursive: true, mode: 0o700});
  fs.cpSync(path.join(resourcesRoot, 'guest/rootfs'), guestRoot, {recursive: true});
  for (const entry of guestManifest.entries) {
    if (typeof entry.path !== 'string' || path.isAbsolute(entry.path) || entry.path.split('/').includes('..'))
      throw new Error('IOS_GUEST_MANIFEST_INVALID');
    const target = path.join(guestRoot, entry.path);
    if (typeof entry.target === 'string') {
      if (fs.lstatSync(target, {throwIfNoEntry: false})) fs.unlinkSync(target);
      fs.symlinkSync(entry.target, target);
    } else {
      if (!Number.isInteger(entry.mode) || entry.mode < 0 || entry.mode > 0o777) throw new Error('IOS_GUEST_MANIFEST_INVALID');
      fs.chmodSync(target, entry.mode);
    }
  }
  fs.writeFileSync(path.join(guestRoot, '.ready'), guestManifest.rootDigest, {mode: 0o600});
}
const commandRuntime = Object.freeze({root: guestRoot, data: dataRoot, resources: resourcesRoot});
const root = fs.realpathSync(workspaceRoot);
const defaultDirectory = fs.realpathSync(path.join(__dirname, '..', 'app'));
const nextRoot = fs.realpathSync(path.join(__dirname, '..', 'next'));
const nextManifest = JSON.parse(fs.readFileSync(path.join(nextRoot, 'mobile-manifest.json'), 'utf8'));
const nextEntry = fs.realpathSync(path.join(nextRoot, nextManifest.serverEntry));
if (!nextEntry.startsWith(nextRoot + path.sep)) throw new Error('IOS_NEXT_ENTRY_INVALID');
const environmentFile = path.join(path.dirname(nextEntry), '.env.local');
const applicationEnvironment = fs.existsSync(environmentFile)
  ? require('node:util').parseEnv(fs.readFileSync(environmentFile, 'utf8')) : {};
if (fs.existsSync(environmentFile)) process.loadEnvFile(environmentFile);
const workerURL = new URL('data:text/javascript;charset=utf-8,' + encodeURIComponent(
  fs.readFileSync(path.join(__dirname, 'worker.mjs'), 'utf8')));
const processBoundaryURL = pathToFileURL(path.join(__dirname, 'ios-process-boundary.mjs')).href;
const token = crypto.randomBytes(32).toString('hex');
const withinRoot = value => typeof value === 'string' && (value === root || value.startsWith(root + path.sep));
const hostConfig = JSON.parse(fs.readFileSync(path.join(__dirname, 'host-config.json'), 'utf8'));
const configuredWebOrigin = process.env.INK_DREAM_PUBLIC_ORIGIN || hostConfig.webOrigin;
const webOrigin = new URL(configuredWebOrigin);
if (hostConfig.version !== 1 || webOrigin.origin !== configuredWebOrigin || webOrigin.protocol !== 'http:' ||
    !['127.0.0.1', 'localhost', '[::1]'].includes(webOrigin.hostname) || !webOrigin.port || webOrigin.username || webOrigin.password) {
  throw new Error('IOS_NEXT_ORIGIN_INVALID');
}
let webWorker;
let webFailure;
let webListening = false;
let boundBackendOrigin;

function webStatus() {
  return { state: webFailure ? 'failed' : webListening ? 'listening' : webWorker ? 'starting' : 'unstarted',
    origin: webOrigin.origin, backendOrigin: boundBackendOrigin, code: webFailure };
}

function startWeb(backendOrigin) {
  const backend = new URL(backendOrigin);
  if (backend.origin !== backendOrigin || backend.protocol !== 'http:' || backend.hostname !== '127.0.0.1' ||
      !backend.port || backend.username || backend.password) throw new Error('IOS_BACKEND_ORIGIN_INVALID');
  if (boundBackendOrigin && boundBackendOrigin !== backend.origin) throw new Error('IOS_NEXT_BACKEND_ALREADY_BOUND');
  if (!webWorker) {
    boundBackendOrigin = backend.origin;
    webWorker = new Worker(workerURL, {
      workerData: { application: 'next', cwd: path.dirname(nextEntry), serverEntry: nextEntry, argv: [], webPort: Number(webOrigin.port), processBoundaryURL },
      env: { ...applicationEnvironment, HOME: process.env.HOME || path.dirname(endpointFile), TMPDIR: process.env.TMPDIR || path.dirname(endpointFile),
        NODE_ENV: 'production', NEXT_TELEMETRY_DISABLED: '1', HOSTNAME: webOrigin.hostname, PORT: webOrigin.port,
        INK_BACKEND_INTERNAL_URL: backend.origin, INK_DREAM_PUBLIC_ORIGIN: webOrigin.origin,
        INK_DREAM_BFF_REDIRECT_URI: webOrigin.origin + '/auth/callback' },
      stdout: true, stderr: true, trackUnmanagedFds: false,
    });
    webWorker.stdout.on('data', data => process.stdout.write(data));
    webWorker.stderr.on('data', data => process.stderr.write(data));
    webWorker.on('message', message => {
      if (message?.type === 'next_listening' && message.pid === process.pid && message.port === Number(webOrigin.port)) {
        webListening = true;
      }
    });
    webWorker.on('error', () => { webFailure = 'IOS_NEXT_WORKER_FAILED'; });
    webWorker.on('exit', () => { webFailure ||= 'IOS_NEXT_WORKER_STOPPED'; });
  }
  if (webFailure) throw new Error(webFailure);
  return { type: 'web_started', origin: webOrigin.origin, execution: 'application-process', pid: process.pid };
}
const server = net.createServer(socket => {
  let input = Buffer.alloc(0);
  let worker;
  let initialized = false;
  const send = value => socket.write(JSON.stringify(value) + '\n');
  const fail = code => { send({ type: 'error', code }); socket.end(); };
  socket.on('error', () => {});
  socket.on('close', () => { if (worker) void worker.terminate(); });
  socket.on('data', chunk => {
    input = Buffer.concat([input, chunk]);
    // SDK frames are bounded again by the exact SDK parser in embedded Python.
    if (input.length > 16 * 1024 * 1024) { fail('IOS_RUNTIME_FRAME_TOO_LARGE'); return; }
    let end;
    while ((end = input.indexOf(10)) >= 0) {
      let message;
      try { message = JSON.parse(input.subarray(0, end).toString('utf8')); }
      catch { fail('IOS_RUNTIME_FRAME_INVALID'); return; }
      input = input.subarray(end + 1);
      if (message === null || typeof message !== 'object' || Array.isArray(message)) {
        fail('IOS_RUNTIME_FRAME_INVALID'); return;
      }
      if (!initialized) {
        if (message.token !== token || message.version !== 1) { fail('IOS_RUNTIME_AUTH_FAILED'); return; }
        initialized = true;
        if (message.type === 'status') {
          send({ type: 'status', pid: process.pid, platform: process.platform, nodeVersion: process.version,
                 mobileVersion: process.versions.mobile, execution: 'application-process', web: webStatus() });
          socket.end(); return;
        }
        if (message.type === 'start_web') {
          try { send(startWeb(message.backendOrigin)); }
          catch (error) { fail(error.message || 'IOS_NEXT_START_FAILED'); }
          socket.end(); return;
        }
        let canonicalDirectory = false;
        const pluginRoot = path.join(path.dirname(root), 'claude-plugin-runtime');
        const pluginPython = message.purpose === 'plugin-python';
        const pluginDirectory = ['plugin-management', 'plugin-python'].includes(message.purpose) && typeof message.cwd === 'string'
          && (message.cwd === pluginRoot || message.cwd.startsWith(pluginRoot + path.sep));
        try { canonicalDirectory = (withinRoot(message.cwd) || message.cwd === defaultDirectory || pluginDirectory) && fs.realpathSync(message.cwd) === message.cwd && fs.statSync(message.cwd).isDirectory(); }
        catch { /* Invalid session paths do not terminate the application event loop. */ }
        if (message.type !== 'connect' || !canonicalDirectory ||
            !Array.isArray(message.argv) || message.argv.some(v => typeof v !== 'string') ||
            !message.env || typeof message.env !== 'object' || Array.isArray(message.env) ||
            Object.entries(message.env).some(([k, v]) => !/^[A-Za-z_][A-Za-z0-9_]*$/.test(k) || typeof v !== 'string')) {
          fail('IOS_RUNTIME_SESSION_INVALID'); return;
        }
        let pythonExecutable = message.argv[0] === '/usr/bin/python3';
        if (pluginPython && !pythonExecutable) {
          try {
            pythonExecutable = message.argv[0]?.startsWith(pluginRoot + '/plugin-runtimes/') &&
              message.argv[0].endsWith('/venv/bin/python3') &&
              fs.realpathSync(message.argv[0]) === message.argv[0];
          } catch { /* Missing managed interpreters return the existing private error packet. */ }
        }
        if (pluginPython && !pythonExecutable) {
          fail('IOS_PLUGIN_PYTHON_EXECUTABLE_INVALID'); return;
        }
        try {
          worker = new Worker(workerURL, {
            workerData: { application: pluginPython ? 'plugin-python' : undefined,
              cwd: message.cwd, argv: message.argv, runtimeEntry, processBoundaryURL, commandRuntime },
            // Original Runtime uses os.tmpdir() for unsandboxed cwd tracking.
            // Reuse the same server-bound thread temp root without changing its ownership.
            env: {...message.env, TMPDIR: message.env.CLAUDE_CODE_TMPDIR || path.join(dataRoot, 'tmp')},
            stdin: true, stdout: true, stderr: true,
            // CPython shares the process descriptor table. Node's unmanaged-FD
            // teardown must not close descriptors reused by the interpreter.
            trackUnmanagedFds: false,
          });
        } catch { fail('IOS_RUNTIME_WORKER_START_FAILED'); return; }
        for (const [type, stream] of [['stdout', worker.stdout], ['stderr', worker.stderr]]) {
          stream.on('data', data => {
            if (!send({ type, data: data.toString('base64') })) stream.pause();
          });
          socket.on('drain', () => stream.resume());
        }
        worker.on('error', error => send({ type: 'error', code: error.code || 'IOS_RUNTIME_WORKER_FAILED', message: error.message }));
        worker.on('exit', code => { send({ type: 'exit', code }); socket.end(); });
        send({ type: 'connected' });
      } else if (message.type === 'stdin' && worker) {
        if (typeof message.data !== 'string') { fail('IOS_RUNTIME_INPUT_INVALID'); return; }
        if (!worker.stdin.write(Buffer.from(message.data, 'base64'))) {
          socket.pause(); worker.stdin.once('drain', () => socket.resume());
        }
      } else if (message.type === 'end_input' && worker) {
        worker.stdin.end();
      } else if (message.type === 'terminate' && worker) {
        void worker.terminate();
      } else {
        fail('IOS_RUNTIME_MESSAGE_INVALID'); return;
      }
    }
  });
});
server.listen(0, '127.0.0.1', () => {
  fs.writeFileSync(endpointFile, JSON.stringify({ version: 1, port: server.address().port, token,
    pid: process.pid, platform: process.platform, nodeVersion: process.version,
    runtimeEntry, workspaceRoot: root }), { mode: 0o600, flag: 'wx' });
});

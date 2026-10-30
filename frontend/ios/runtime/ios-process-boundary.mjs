// [Input] The pinned iOS Node native process bindings.
// [Output] Original Node child-process API backed by packaged guest commands or explicit command denial.
// [Pos] iOS execution compatibility; original tool permissions remain upstream and sandbox deployment is explicit.
import { constants } from 'node:os';

export const isIOS = process.platform === 'ios';
const nativeProcess = process.binding('process_wrap');
const nativeSync = process.binding('spawn_sync');
const { UV_ENOSYS } = process.binding('uv');
const denySpawn = () => UV_ENOSYS;
let installedProcess, installedSync, installedKill;
const denySpawnSync = () => ({ error: UV_ENOSYS, status: null, signal: null, output: [null, null, null], pid: 0 });

export function installIOSProcessBoundary(configuration) {
  if (!isIOS) throw new Error('IOS_RUNTIME_TARGET_REQUIRED');
  if (!configuration) {
    Object.defineProperty(nativeProcess.Process.prototype, 'spawn', {value: denySpawn, writable: false, configurable: false});
    Object.defineProperty(nativeSync, 'spawn', {value: denySpawnSync, writable: false, configurable: false});
    installedProcess = nativeProcess.Process; installedSync = denySpawnSync;
  } else {
    const binding = process._linkedBinding('ink_dream_process');
    if (binding.version !== 1 || binding.hostPID() !== process.pid ||
        binding.initialize(configuration.root, configuration.data, configuration.resources) !== 0)
      throw new Error('IOS_COMMAND_RUNTIME_UNAVAILABLE');
    const owned = new Map();
    const {UV_ESRCH} = process.binding('uv');
    installedKill = (pid, signal) => {
      if (pid === process.pid) return signal === 0 ? 0 : UV_ENOSYS;
      const generation = owned.get(Math.abs(pid));
      return generation ? binding.signal(Math.abs(pid), signal, pid < 0, generation) : UV_ESRCH;
    };
    Object.defineProperty(process, '_kill', {value: installedKill, writable: false, configurable: false});
    class GuestProcess {
      pid = 0; handle = null;
      spawn(file, args, cwd, envPairs, stdio, flags, uid, gid) {
        if (stdio.length !== 3 || stdio.some(value => value.ipc) || uid !== undefined || gid !== undefined) return UV_ENOSYS;
        const result = binding.spawn({file, args, cwd: cwd || process.cwd(), envPairs: envPairs || [], stdio},
          (code, signal) => this.onexit(code, signal));
        if (result.error) return result.error;
        this.pid = result.pid; this.handle = result.handle;
        owned.set(result.pid, result.generation);
        for (let n = 0; n < 3; n++) if (stdio[n].type === 'pipe') {
          const error = stdio[n].handle.open(result.fds[n]);
          if (error) {binding.close(this.handle); this.handle = null; return error;}
        }
        return 0;
      }
      close() {if (this.handle) {binding.close(this.handle); this.handle = null;}}
      kill(signal) {return this.handle ? binding.kill(this.handle, signal) : UV_ESRCH;}
      ref() {if (this.handle) binding.reference(this.handle, true);}
      unref() {if (this.handle) binding.reference(this.handle, false);}
    }
    installedProcess = GuestProcess;
    installedSync = options => {
      const result = binding.spawnSync({...options, cwd: options.cwd ?? process.cwd()});
      if (result.pid > 1) owned.set(result.pid, result.generation);
      return result;
    };
    Object.defineProperty(nativeProcess, 'Process', {value: GuestProcess, writable: false, configurable: false});
    Object.defineProperty(nativeSync, 'spawn', {value: installedSync, writable: false, configurable: false});
  }
  Object.freeze(nativeProcess.Process.prototype);
  Object.freeze(nativeProcess.Process); Object.freeze(nativeProcess); Object.freeze(nativeSync);
  assertIOSProcessBoundary();
}

export function assertIOSProcessBoundary() {
  if (!isIOS || nativeProcess.Process !== installedProcess || nativeSync.spawn !== installedSync ||
      !Object.isFrozen(nativeProcess) || !Object.isFrozen(nativeProcess.Process) || !Object.isFrozen(nativeSync) ||
      (installedKill && process._kill !== installedKill)) throw new Error('IOS_RUNTIME_PROCESS_BOUNDARY_UNQUALIFIED');
}

export function rejectIOSCommand() {
  assertIOSProcessBoundary();
  const error = new Error('External command execution is unavailable on iOS (ENOSYS)');
  error.code = 'ENOSYS';
  error.errno = constants.errno.ENOSYS;
  throw error;
}

// [Input] Original iOS host resolver function, explicit system-DNS fixtures and a private temporary guest root.
// [Output] Resolver refresh, offline clearing and symlink rejection evidence without network or credentials.
// [Pos] Provider-free qualification of the existing iOS host function; no alternate product implementation.
import assert from 'node:assert/strict';
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import net from 'node:net';
import crypto from 'node:crypto';
import vm from 'node:vm';
import {fileURLToPath} from 'node:url';

const hostPath = fileURLToPath(new URL('../runtime/host.cjs', import.meta.url));
const host = fs.readFileSync(hostPath, 'utf8');
const start = host.indexOf('function refreshGuestResolver() {');
const end = host.indexOf('\nrefreshGuestResolver();', start);
assert(start >= 0 && end > start, 'Original host resolver function was not found');
const guestRoot = fs.mkdtempSync(path.join(os.tmpdir(), 'ink-guest-resolver-'));
const directory = path.join(guestRoot, 'etc');
const target = path.join(directory, 'resolv.conf');
let servers = ['192.0.2.53', '2001:db8::53'];
class ResolverFixture { getServers() { return [...servers]; } }
const context = vm.createContext({fs, path, net, crypto, guestRoot, Resolver: ResolverFixture});
vm.runInContext(host.slice(start, end), context, {filename: hostPath});
let cases = 0;
try {
  fs.mkdirSync(directory, {mode: 0o700});
  vm.runInContext('refreshGuestResolver()', context);
  assert.equal(fs.readFileSync(target, 'utf8'), 'nameserver 192.0.2.53\nnameserver 2001:db8::53\n');
  assert.equal(fs.statSync(target).mode & 0o777, 0o600); cases++;
  const initialInode = fs.statSync(target).ino;
  vm.runInContext('refreshGuestResolver()', context);
  assert.equal(fs.statSync(target).ino, initialInode); cases++;
  servers = ['198.51.100.53'];
  vm.runInContext('refreshGuestResolver()', context);
  assert.equal(fs.readFileSync(target, 'utf8'), 'nameserver 198.51.100.53\n'); cases++;
  servers = [];
  vm.runInContext('refreshGuestResolver()', context);
  assert.equal(fs.readFileSync(target, 'utf8'), ''); cases++;
  servers = ['192.0.2.53:1053', '[2001:db8::53]:1053', 'invalid\nnameserver 203.0.113.53'];
  vm.runInContext('refreshGuestResolver()', context);
  assert.equal(fs.readFileSync(target, 'utf8'), ''); cases++;
  fs.unlinkSync(target);
  const protectedFile = path.join(guestRoot, 'protected');
  fs.writeFileSync(protectedFile, 'unchanged');
  fs.symlinkSync(protectedFile, target);
  assert.throws(() => vm.runInContext('refreshGuestResolver()', context), /IOS_GUEST_RESOLVER_PATH_INVALID/);
  assert.equal(fs.readFileSync(protectedFile, 'utf8'), 'unchanged'); cases++;
  assert.deepEqual(fs.readdirSync(directory), ['resolv.conf']);
  console.log(JSON.stringify({cases, failures: 0, networkRequests: 0, accountCredentialsUsed: false}));
} finally {
  fs.rmSync(guestRoot, {recursive: true, force: true});
}

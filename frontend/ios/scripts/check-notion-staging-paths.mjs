// [Sync] 2026-10-31: reproduce native ancestor aliases while preserving child symlink, digest and mode checks.
// [Input] Original host bootstrap and isolated canonical/aliased native directory fixtures.
// [Output] Notion staging path, digest, symlink rejection and executable-mode regression without CLI/network execution.
// [Pos] Provider-free host validation; all files are created under a named temporary fixture root.
import assert from 'node:assert/strict';
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import crypto from 'node:crypto';
import vm from 'node:vm';
import {createRequire} from 'node:module';
import {fileURLToPath} from 'node:url';

const require=createRequire(import.meta.url);
const hostPath=fileURLToPath(new URL('../runtime/host.cjs',import.meta.url));
const host=fs.readFileSync(hostPath,'utf8');
const end=host.indexOf('\nconst root = fs.realpathSync(workspaceRoot);');
assert(end>0,'Original pre-server host bootstrap was not found');
const bootstrap=host.slice(0,end)+'\nglobalThis.__stagingResult={guestRoot,notionExecutable};';
const rootDigest='a'.repeat(64);
const fixtureBytes=Buffer.from('synthetic pinned Notion executable; never executed');
const digest=value=>crypto.createHash('sha256').update(value).digest('hex');
let passed=0;

function runCase({alias=false,parentSymlink=false,executableSymlink=false,invalidDigest=false}={}) {
 const temporary=fs.realpathSync(fs.mkdtempSync(path.join(os.tmpdir(),'ink-notion-staging-paths-')));
 try {
  const resources=path.join(temporary,'resources'),data=path.join(temporary,'data');
  const runtime=path.join(data,'Library/Application Support/InkMemory/runtime');
  const guest=path.join(runtime,'guest',rootDigest),bin=path.join(guest,'usr/local/bin');
  const source=path.join(resources,'node/notion');
  fs.mkdirSync(bin,{recursive:true});fs.mkdirSync(path.join(guest,'etc'),{recursive:true});
  fs.mkdirSync(path.join(resources,'guest'),{recursive:true});fs.mkdirSync(source,{recursive:true});
  fs.writeFileSync(path.join(guest,'.ready'),rootDigest);
  fs.writeFileSync(path.join(resources,'guest/manifest.json'),JSON.stringify({rootDigest,entries:[]}));
  fs.writeFileSync(path.join(source,'manifest.json'),JSON.stringify({binarySha256:digest(invalidDigest?Buffer.from('different fixture'):fixtureBytes)}));
  fs.writeFileSync(path.join(source,'ntn'),fixtureBytes);
  const outside=path.join(temporary,'outside');fs.mkdirSync(outside);
  const victim=path.join(outside,'retained.txt');fs.writeFileSync(victim,'retained');
  if(parentSymlink){fs.rmdirSync(bin);fs.symlinkSync(outside,bin);}
  if(executableSymlink)fs.symlinkSync(victim,path.join(bin,'ntn'));
  let nativeData=data;
  if(alias){nativeData=path.join(temporary,'native-data-alias');fs.symlinkSync(data,nativeData);}
  const endpoint=path.join(nativeData,'Library/Application Support/InkMemory/runtime/node-fixture.json');
  const workspace=path.join(path.dirname(endpoint),'workspaces');fs.mkdirSync(workspace,{recursive:true});
  const context=vm.createContext({
   __dirname:path.join(resources,'node'),
   process:{argv:['node','host.cjs',endpoint,workspace,path.join(resources,'node/core/cli.js'),nativeData]},
   require:id=>id==='node:dns'?{Resolver:class {getServers(){return [];}}}:require(id),
  });
  const execute=()=>vm.runInContext(bootstrap,context,{filename:hostPath});
  if(invalidDigest)assert.throws(execute,/IOS_NOTION_CLI_DIGEST_MISMATCH/);
  else if(parentSymlink||executableSymlink)assert.throws(execute,/IOS_NOTION_CLI_PATH_INVALID/);
  else {
   execute();
   assert.equal(context.__stagingResult.guestRoot,guest);
   const executable=context.__stagingResult.notionExecutable;
   assert.equal(executable,path.join(guest,'usr/local/bin/ntn'));
   assert.deepEqual(fs.readFileSync(executable),fixtureBytes);
   assert.equal(fs.statSync(executable).mode&0o777,0o755);
   assert.equal(fs.lstatSync(executable).isSymbolicLink(),false);
  }
  assert.equal(fs.readFileSync(victim,'utf8'),'retained');
  if(parentSymlink)assert.equal(fs.existsSync(path.join(outside,'ntn')),false);
  passed++;
 } finally {fs.rmSync(temporary,{recursive:true,force:true});}
}

runCase();
runCase({alias:true});
runCase({parentSymlink:true});
runCase({executableSymlink:true});
runCase({invalidDigest:true});
console.log(JSON.stringify({passed,failed:0,networkRequests:0,cliExecutions:0,credentialReads:0,temporaryRootsRemaining:0}));

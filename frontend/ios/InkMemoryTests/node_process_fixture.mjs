// [Input] Named private target fixture root; no business API or credentials.
// [Output] Original Node ChildProcess/Pipe behavior against actual guest Bash.
// [Pos] Qualification Worker; production Runtime retains its existing boundary.
// [Sync] 2026-10-25: verify per-spawn ownership, foreign signals/proc denial and original child-process behavior.
import fs from 'node:fs';
import path from 'node:path';
import {setTimeout} from 'node:timers/promises';
import {workerData} from 'node:worker_threads';
import {createServer,createConnection} from 'node:net';
const root=workerData.receiptDirectory;
const input=path.join(root,`node-process-input-${process.pid}.json`);
const output=path.join(root,`node-process-result-${process.pid}.json`);
let stage='input';
let lastGuestReceipt;
const check=(value,code)=>{if(!value)throw Object.assign(new Error(code),{code});};
const deadline=Date.now()+30000;
while(!fs.existsSync(input)&&Date.now()<deadline)await setTimeout(20);
try {
    const configuration=JSON.parse(fs.readFileSync(input,'utf8'));
    const binding=process._linkedBinding('ink_posix_fixture');
    const source=process.binding('natives')['internal/child_process'];
    fs.writeFileSync(path.join(root,`node-child-process-source-${process.pid}.js`),source,{mode:0o600});
    fs.writeFileSync(path.join(root,`node-public-child-process-source-${process.pid}.js`),process.binding('natives').child_process,{mode:0o600});
    stage='initialize'; check(binding.initialize(configuration.root)===0,'GUEST_INIT');
    const filesystem={
        denyRead:['/sensitive','/workspace/secret.txt','/sensitive/public/private'],
        allowRead:['/sensitive/public'],
        allowWrite:['/workspace','/dev/null','/runtime-only/thread/.claude-tmp'],
        denyWrite:['/workspace/.claude/settings.json','/workspace/.claude/hooks','/workspace/.dream','/workspace/protected.txt','/workspace/protected-moved.txt','/workspace/protected-mmap.txt']
    };
    const scope=options=>binding.executionScope({filesystem,...options});
    const disabledScope=scope({});
    check(Number.isInteger(disabledScope)&&disabledScope>0,'NETWORK_SCOPE');
    let activeScope=disabledScope;
    const uv=process.binding('uv');
    const ownedPIDs=new Map();
    // The original process.kill retains its validation/error behavior through this native primitive.
    process._kill=(pid,signal)=>{
        if(pid===process.pid)return signal===0&&binding.hostPID()===pid?0:uv.UV_ENOSYS;
        if(!ownedPIDs.has(Math.abs(pid)))return uv.UV_ESRCH;
        return binding.signal(Math.abs(pid),signal,pid<0,ownedPIDs.get(Math.abs(pid)));
    };
    // Reuse Node's original public ChildProcess and native Pipe objects.
    process.binding('process_wrap').Process=class GuestProcess {
        pid=0; handle=null;
        spawn(file,args,cwd,envPairs,stdio,flags,uid,gid) {
            if(stdio.length!==3||stdio.some(s=>s.ipc)||uid!==undefined||gid!==undefined)return uv.UV_ENOSYS;
            const result=binding.spawn({file,args,cwd:cwd||'/workspace',envPairs:envPairs||[],stdio,executionScope:activeScope},(code,signal)=>this.onexit(code,signal));
            if(result.error)return result.error;
            this.pid=result.pid; this.handle=result.handle;
            ownedPIDs.set(result.pid,result.scope);
            for(let n=0;n<3;n++)if(stdio[n].type==='pipe')check(stdio[n].handle.open(result.fds[n])===0,'PIPE_OPEN');
            return 0;
        }
        close() {if(this.handle){binding.close(this.handle);this.handle=null;}}
        kill(signal) {return this.handle?binding.kill(this.handle,signal):uv.UV_ESRCH;}
        ref() {if(this.handle)binding.reference(this.handle,true);}
        unref() {if(this.handle)binding.reference(this.handle,false);}
    };
    process.binding('spawn_sync').spawn=options=>{
        const result=binding.spawnSync({...options,executionScope:activeScope});
        if(result.pid>1)ownedPIDs.set(result.pid,result.scope);
        return result;
    };
    const {spawn,spawnSync,execFileSync,execSync,ChildProcess}=await import('node:child_process');
    const env={PATH:'/bin:/usr/bin',HOME:'/workspace',LANG:'C',TERM:'dumb',FIXTURE_VALUE:'original-env'};
    const syncOptions={cwd:'/workspace',env};
    stage='sync-stdio';
    const sync=spawnSync('/bin/bash',['-c','read -r text; test "$text" = sync-input; test "$FIXTURE_VALUE" = original-env; printf "sync-out\\n"; printf "sync-err\\n" >&2; exit 7'],{...syncOptions,input:'sync-input\n',encoding:'utf8'});
    fs.writeFileSync(path.join(root,`node-sync-fixture-${process.pid}.json`),JSON.stringify({error:sync.error?.code,status:sync.status,signal:sync.signal,out:sync.stdout?.toString().slice(0,4096),err:sync.stderr?.toString().slice(0,4096)}),{mode:0o600});
    check(!sync.error&&sync.status===7&&sync.signal===null&&sync.stdout==='sync-out\n'&&sync.stderr==='sync-err\n','SYNC_STDIO');
    stage='sync-duplex';
    const largeInput=Buffer.alloc(262144,65);
    const duplex=spawnSync('cat',[],{...syncOptions,input:largeInput,timeout:3000,maxBuffer:524288});
    check(!duplex.error&&duplex.status===0&&duplex.stdout.equals(largeInput),'SYNC_DUPLEX');
    stage='sync-pipe-error';
    const closedInput=spawnSync('/bin/bash',['-c','exec 0<&-; printf pipe-closed; /bin/busybox sleep 0.05; exit 0'],{...syncOptions,input:largeInput,timeout:1000,encoding:'utf8'});
    check(closedInput.error?.code==='EPIPE'&&closedInput.status===0&&closedInput.stdout==='pipe-closed','SYNC_PIPE_ERROR');
    const pipeTimeout=spawnSync('/bin/bash',['-c','exec 0<&-; exec /bin/busybox sleep 5'],{...syncOptions,input:largeInput,timeout:80,killSignal:'SIGKILL'});
    check(pipeTimeout.error?.code==='ETIMEDOUT'&&pipeTimeout.signal==='SIGKILL','SYNC_PRIMARY_ERROR');
    stage='sync-shell-discovery';
    const which=spawnSync('which',['bash'],{...syncOptions,encoding:'utf8',stdio:['ignore','pipe','ignore'],timeout:1000});
    check(!which.error&&which.status===0&&which.stdout.trim()==='/bin/bash'&&which.stderr===null,'SYNC_WHICH');
    check(execFileSync('/bin/bash',['--version'],{...syncOptions,stdio:'ignore',timeout:1000})===null,'SYNC_IGNORE');
    check(execSync('printf exec-sync',{...syncOptions,shell:'/bin/bash',encoding:'utf8'})==='exec-sync','EXEC_SYNC');
    stage='sync-path';
    const custom=path.join(configuration.root,'workspace/custom-tool');
    fs.writeFileSync(custom,'#!/bin/bash\nprintf custom-path',{mode:0o700});
    const customResult=spawnSync('custom-tool',[],{...syncOptions,env:{...env,PATH:'/workspace:/bin'},encoding:'utf8'});
    check(!customResult.error&&customResult.stdout==='custom-path','SYNC_CUSTOM_PATH');
    const fallback=spawnSync('bash',['-c','printf fallback-path'],{...syncOptions,env:{HOME:'/workspace'},encoding:'utf8'});
    check(!fallback.error&&fallback.stdout==='fallback-path','SYNC_DEFAULT_PATH');
    stage='sync-errors';
    const missingSync=spawnSync('/missing-sync-executable',[],syncOptions);
    check(missingSync.error?.code==='ENOENT'&&missingSync.status===null&&missingSync.pid===0,'SYNC_ENOENT');
    fs.writeFileSync(path.join(configuration.root,'workspace/not-executable'),'fixture',{mode:0o600});
    const denied=spawnSync('/workspace/not-executable',[],syncOptions);
    check(denied.error?.code==='EACCES','SYNC_EACCES');
    const missingCwd=spawnSync('/bin/bash',['-c','exit 0'],{...syncOptions,cwd:'/missing-cwd'});
    check(missingCwd.error?.code==='ENOENT','SYNC_CWD_ERROR');
    stage='sync-timeout';
    const timed=spawnSync('/bin/bash',['-c','exec /bin/busybox sleep 5'],{...syncOptions,timeout:80,killSignal:'SIGKILL'});
    check(timed.error?.code==='ETIMEDOUT'&&timed.status===null&&timed.signal==='SIGKILL','SYNC_TIMEOUT');
    stage='sync-max-buffer';
    const overflow=spawnSync('/bin/bash',['-c',"printf '%0131072d' 0"],{...syncOptions,maxBuffer:1024,killSignal:'SIGKILL'});
    check(overflow.error?.code==='ENOBUFS'&&overflow.stdout.length>1024,'SYNC_MAX_BUFFER');
    const combined=spawnSync('/bin/bash',['-c',"printf '%0800d' 0; printf '%0800d' 0 >&2"],{...syncOptions,maxBuffer:1200});
    check(combined.error?.code==='ENOBUFS','SYNC_COMBINED_BUFFER');
    stage='sync-inherited-fd';
    const fdPath=path.join(configuration.root,'workspace/inherited-output');
    const fd=fs.openSync(fdPath,'w');
    try {
        const inherited=spawnSync('/bin/bash',['-c','printf inherited-output'],{...syncOptions,stdio:['ignore',fd,'ignore']});
        check(!inherited.error&&inherited.status===0&&inherited.stdout===null,'SYNC_INHERITED_STATUS');
        check(fs.fstatSync(fd).isFile()&&fs.readFileSync(fdPath,'utf8')==='inherited-output','SYNC_INHERITED_FD');
    } finally {fs.closeSync(fd);}
    stage='pid-boundary';
    check(process.kill(process.pid,0)===true,'HOST_PID_EXISTS');
    let unknownPID;
    try{process.kill(2147483000,0);}catch(error){unknownPID=error.code;}
    check(unknownPID==='ESRCH','UNKNOWN_PID_REJECTED');
    let hostSignalDenied;
    try{process.kill(process.pid,'SIGTERM');}catch(error){hostSignalDenied=error.code;}
    check(hostSignalDenied==='ENOSYS','HOST_SIGNAL_REJECTED');
    function collect(file,args,stdin='',onData,executionScope=disabledScope) {
        return new Promise((resolve,reject)=>{
            let child;
            const previousScope=activeScope;
            activeScope=executionScope;
            try {child=spawn(file,args,{cwd:'/workspace',env,stdio:['pipe','pipe','pipe']});}
            finally {activeScope=previousScope;}
            const out=[],err=[];
            child.stdout.on('data',chunk=>{out.push(chunk);onData?.(child,Buffer.concat(out));});
            child.stderr.on('data',chunk=>err.push(chunk));
            child.once('error',reject);
            child.once('close',(code,signal)=>{lastGuestReceipt={code,signal,stderr:Buffer.concat(err).toString().slice(0,4096)};resolve({code,signal,out:Buffer.concat(out),err:Buffer.concat(err),pid:child.pid,scope:ownedPIDs.get(child.pid),original:child instanceof ChildProcess,chunks:out.length});});
            child.stdin.on('error',reject);
            if(stdin!==null)child.stdin.end(stdin);
        });
    }
    stage='bash';
    const script=`set -euo pipefail; read -r incoming; test "$incoming" = input-ok; test "$FIXTURE_VALUE" = original-env; a=(one two three); count=$(printf '%s\\n' "${'${a[@]}'}" | /bin/busybox wc -l); test "$count" -eq 3; (printf 'written\\n' > result.txt); printf 'first\\n'; /bin/busybox sleep 0.08; printf 'second\\n'; printf 'stderr-ok\\n' >&2; exit 7`;
    const main=await collect('/bin/bash',['--noprofile','--norc','-c',script],'input-ok\n');
    check(main.original&&main.code===7&&main.signal===null,'BASH_STATUS');
    check(main.out.toString()==='first\nsecond\n'&&main.err.toString()==='stderr-ok\n','BASH_BYTES');
    check(main.chunks>=2,'BASH_STREAMING');
    check(fs.readFileSync(path.join(configuration.root,'workspace/result.txt'),'utf8')==='written\n','BASH_FILE');
    stage='binary-pipe';
    const binary=await collect('/bin/bash',['-c',"printf 'A\\000B\\377'; printf '%0131072d' 0"]);
    check(binary.code===0&&binary.out.length===131076,'BINARY_LENGTH');
    check(binary.out.subarray(0,4).equals(Buffer.from([65,0,66,255]))&&binary.out.subarray(4).every(byte=>byte===48),'BINARY_BYTES');
    stage='missing-executable';
    let missing;
    try {await collect('/missing-fixture-executable',[]);}catch(error){missing=error.code;}
    check(missing==='ENOENT','SPAWN_ENOENT');
    stage='concurrent';
    const concurrent=await Promise.all([collect('/bin/bash',['-c','printf concurrent-one']),collect('/bin/bash',['-c','printf concurrent-two'])]);
    check(concurrent[0].out.toString()==='concurrent-one'&&concurrent[1].out.toString()==='concurrent-two','CONCURRENT_BYTES');
    stage='process-ownership';
    fs.writeFileSync(path.join(configuration.root,'workspace/process-private'),'process-private',{mode:0o600});
    let victimChild, victimReady=false, victimReleased=false;
    const victim=collect('/bin/bash',['-c','set -e; exec 4<process-private; printf ready; read -r release; test "$release" = release; test "$(cat <&4)" = process-private; printf alive'],null,(child,bytes)=>{
        victimChild=child;victimReady=bytes.toString().startsWith('ready');
    });
    let processProbe, signalProbe;
    try {
        const readyDeadline=Date.now()+3000;
        while(!victimReady&&Date.now()<readyDeadline)await setTimeout(10);
        check(victimReady&&victimChild.pid>1,'PROCESS_VICTIM_READY');
        const foreignPID=victimChild.pid;
        stage='process-signals-and-proc';
        processProbe=await collect('/bin/bash',['-c',`set -euxo pipefail;
            kill -0 $$; kill -0 -- -$$;
            if kill -0 ${foreignPID} 2>/dev/null; then exit 91; fi;
            if kill -TERM ${foreignPID} 2>/dev/null; then exit 92; fi;
            if kill -0 -- -${foreignPID} 2>/dev/null; then exit 93; fi;
            if kill -TERM -- -${foreignPID} 2>/dev/null; then exit 94; fi;
            if kill -TERM 1 2>/dev/null; then exit 95; fi;
            if kill -0 -- -999999 2>/dev/null; then exit 96; fi;
            for file in /proc/${foreignPID}/stat /proc/${foreignPID}/environ /proc/${foreignPID}/fd/4 /proc/${foreignPID}/mem /proc/1/stat; do
                if cat "$file" >/dev/null 2>&1; then exit 97; fi;
            done;
            if readlink /proc/${foreignPID}/cwd >/dev/null 2>&1; then exit 98; fi;
            if ls /proc/ish >/dev/null 2>&1; then exit 99; fi;
            for entry in /proc/[0-9]*; do test "$entry" != /proc/${foreignPID}; done;
            [[ "$(readlink /proc/self)" =~ ^[0-9]+$ ]];
            cat /proc/$$/stat >/dev/null;
            /bin/busybox sleep 30 & child=$!;
            kill -0 "$child"; kill -0 -- -1;
            cat /proc/"$child"/stat >/dev/null;
            kill -TERM "$child";
            if wait "$child"; then exit 100; fi;
            printf process-ok`]);
        check(processProbe.code===0&&processProbe.out.toString()==='process-ok','PROCESS_GUEST_OWNERSHIP');
        check(processProbe.scope!==ownedPIDs.get(foreignPID),'PROCESS_DISTINCT_GENERATIONS');
        stage='process-signal-abi';
        signalProbe=await collect('/workspace/signal-probe',[String(foreignPID)]);
        check(signalProbe.code===0,'PROCESS_SIGNAL_ABI');
        stage='process-native-generation';
        check(binding.signal(foreignPID,0,false,processProbe.scope)===uv.UV_ESRCH,'PROCESS_FOREIGN_GENERATION');
        check(binding.signal(foreignPID,15,true,processProbe.scope)===uv.UV_ESRCH,'PROCESS_FOREIGN_GROUP_GENERATION');
        check(binding.signal(foreignPID,0,false,ownedPIDs.get(foreignPID))===0,'PROCESS_OWN_GENERATION');
        victimChild.stdin.end('release\n');victimReleased=true;
        const survived=await victim;
        check(survived.code===0&&survived.out.toString()==='readyalive','PROCESS_VICTIM_SURVIVED');
        check(binding.signal(foreignPID,0,false,survived.scope)===uv.UV_ESRCH,'PROCESS_EXITED_IDENTITY');
    } finally {
        const attempted=lastGuestReceipt;
        if(!victimReleased){victimChild?.stdin.destroy();victimChild?.kill('SIGKILL');await victim.catch(()=>{});}
        lastGuestReceipt=attempted;
    }
    stage='filesystem-fixtures';
    for(const directory of ['sensitive/public/private','workspace/.claude/hooks','workspace/.dream','forbidden','workspace-sibling','runtime-only/thread/.claude-tmp','runtime-only/thread/.claude-tmp-other'])
        fs.mkdirSync(path.join(configuration.root,directory),{recursive:true,mode:0o700});
    const fileInputs={
        'sensitive/denied.txt':'fixture-private',
        'sensitive/public/allowed.txt':'fixture-public',
        'sensitive/public/private/denied.txt':'fixture-nested-private',
        'workspace/secret.txt':'fixture-secret',
        'workspace/protected.txt':'fixture-protected',
        'workspace/.claude/settings.json':'fixture-settings'
    };
    for(const [relative,body] of Object.entries(fileInputs))
        fs.writeFileSync(path.join(configuration.root,relative),body,{mode:0o600});
    stage='filesystem-allowed';
    const permitted=await collect('/bin/bash',['-c',`set -euo pipefail; test "$(cat /sensitive/public/allowed.txt)" = fixture-public; printf ordinary > ordinary-file; mkdir -p fs-directory; mv ordinary-file fs-directory/moved; ln fs-directory/moved fs-hardlink; chmod 600 fs-directory/moved; touch fs-directory/moved; test "$(cat fs-hardlink)" = ordinary; exec 4>unlinked-file; rm unlinked-file; printf retained >&4; exec 4>&-; mkfifo fixture-fifo; (printf fifo-result >fixture-fifo) & read -r -N 11 value <fixture-fifo; wait; test "$value" = fifo-result; rm fixture-fifo; printf discarded >/dev/null; test ! -s /dev/null; printf allowed`]);
    check(permitted.code===0&&permitted.out.toString()==='allowed','FILESYSTEM_ALLOWED');
    stage='filesystem-denied';
    const attempts=[
        'cat /sensitive/denied.txt',
        'cat /sensitive/public/private/denied.txt',
        'cat /workspace/secret.txt',
        'printf forbidden >/forbidden/file',
        'printf forbidden >/workspace-sibling/file',
        'printf forbidden >/workspace/.claude/settings.json',
        'chmod 777 /workspace/.claude/settings.json',
        'rm /workspace/protected.txt',
        'mv /workspace/.claude /workspace/moved-claude',
        'ln /workspace/protected.txt /workspace/protected-alias',
        'printf forbidden >/tmp/guest-forbidden',
        'printf forbidden >/runtime-only/thread/.claude-tmp-other/file',
        'printf forbidden >/runtime-only/thread/other-file'
    ];
    for(const attempt of attempts) {
        const result=await collect('/bin/bash',['-c',`if ${attempt}; then exit 91; else printf denied; fi`]);
        check(result.code===0&&result.out.toString()==='denied'&&result.err.toString().includes('Permission denied'),'FILESYSTEM_DENIED');
    }
    check(fs.readFileSync(path.join(configuration.root,'workspace/.claude/settings.json'),'utf8')==='fixture-settings','FILESYSTEM_PROTECTED_BYTES');
    check(fs.readFileSync(path.join(configuration.root,'workspace/protected.txt'),'utf8')==='fixture-protected','FILESYSTEM_PROTECTED_INODE');
    stage='filesystem-exact-temp';
    const temporary=await collect('/bin/bash',['-c','set -e; printf exact >/runtime-only/thread/.claude-tmp/file; test "$(cat /runtime-only/thread/.claude-tmp/file)" = exact; printf exact-temp']);
    check(temporary.code===0&&temporary.out.toString()==='exact-temp','FILESYSTEM_EXACT_TEMP');
    check((fs.statSync(path.join(configuration.root,'runtime-only/thread/.claude-tmp')).mode&0o777)===0o700,'FILESYSTEM_TEMP_MODE');
    stage='filesystem-links';
    const linked=await collect('/bin/bash',['-c',`set -e; ln -s /sensitive/denied.txt /workspace/denied-read-link; ln -s /forbidden /workspace/denied-write-link; if cat /workspace/denied-read-link; then exit 91; fi; if printf forbidden >/workspace/denied-write-link/file; then exit 92; fi; printf links-denied`]);
    check(linked.code===0&&linked.out.toString()==='links-denied','FILESYSTEM_LINKS');
    stage='filesystem-inherited-descriptors';
    for(const [relative,writing] of [['sensitive/denied.txt',false],['workspace/protected.txt',true]]) {
        const fd=fs.openSync(path.join(configuration.root,relative),writing?'r+':'r');
        try {
            const denied=spawnSync('/bin/bash',['-c',writing?'printf forbidden':'cat'],{...syncOptions,stdio:writing?['ignore',fd,'ignore']:[fd,'pipe','ignore']});
            check(denied.error?.code==='EACCES'&&denied.pid===0&&fs.fstatSync(fd).isFile(),'FILESYSTEM_INHERITED_DENIED');
        } finally {fs.closeSync(fd);}
    }
    stage='filesystem-open-descriptor';
    let descriptorMoved=false;
    const moved=await collect('/bin/bash',['-c','exec 4>fd-moved.txt; printf ready; read -r continue; if printf forbidden >&4; then exit 91; else printf denied; fi'],null,(child,bytes)=>{
        if(!descriptorMoved&&bytes.toString().includes('ready')) {
            descriptorMoved=true;
            fs.renameSync(path.join(configuration.root,'workspace/fd-moved.txt'),path.join(configuration.root,'workspace/protected-moved.txt'));
            child.stdin.end('continue\n');
        }
    });
    check(descriptorMoved&&moved.code===0&&moved.out.toString()==='readydenied'&&fs.statSync(path.join(configuration.root,'workspace/protected-moved.txt')).size===0,'FILESYSTEM_DESCRIPTOR_RECHECK');
    stage='filesystem-mmap';
    fs.writeFileSync(path.join(configuration.root,'workspace/mmap-moved.txt'),Buffer.alloc(4096),{mode:0o600});
    let mappingMoved=false;
    const mapping=await collect('/workspace/mmap-probe',[],null,(child,bytes)=>{
        if(!mappingMoved&&bytes.toString().includes('ready')) {
            mappingMoved=true;
            fs.renameSync(path.join(configuration.root,'workspace/mmap-moved.txt'),path.join(configuration.root,'workspace/protected-mmap.txt'));
            child.stdin.end('x');
        }
    });
    check(mappingMoved&&mapping.code===0&&mapping.out.toString()==='ready'&&fs.readFileSync(path.join(configuration.root,'workspace/protected-mmap.txt')).equals(Buffer.alloc(4096)),'FILESYSTEM_MMAP_DENIED');
    stage='filesystem-concurrent-scopes';
    for(const name of ['scope-a','scope-b'])fs.mkdirSync(path.join(configuration.root,'workspace',name));
    const scopeA=scope({filesystem:{...filesystem,allowWrite:['/workspace/scope-a','/dev/null']}});
    const scopeB=scope({filesystem:{...filesystem,allowWrite:['/workspace/scope-b','/dev/null']}});
    const scopedWrites=await Promise.all([
        collect('/bin/bash',['-c','printf a >/workspace/scope-a/file; if printf forbidden >/workspace/scope-b/other; then exit 91; else printf scope-a; fi'],'',undefined,scopeA),
        collect('/bin/bash',['-c','printf b >/workspace/scope-b/file; if printf forbidden >/workspace/scope-a/other; then exit 91; else printf scope-b; fi'],'',undefined,scopeB)
    ]);
    check(scopedWrites[0].code===0&&scopedWrites[0].out.toString()==='scope-a'&&scopedWrites[1].code===0&&scopedWrites[1].out.toString()==='scope-b','FILESYSTEM_CONCURRENT');
    const mutable=structuredClone(filesystem), immutableScope=scope({filesystem:mutable});
    mutable.allowWrite.push('/forbidden');
    const immutable=await collect('/bin/bash',['-c','if printf forbidden >/forbidden/immutable; then exit 91; else printf immutable; fi'],'',undefined,immutableScope);
    check(immutable.code===0&&immutable.out.toString()==='immutable','FILESYSTEM_IMMUTABLE');
    stage='filesystem-symlink-race';
    const raceDirectory=path.join(configuration.root,'workspace/race-directory');
    const raceBackup=path.join(configuration.root,'workspace/race-backup');
    const outside=configuration.root+'-outside';
    check(!fs.existsSync(outside),'FILESYSTEM_OUTSIDE_OWNERSHIP');
    fs.mkdirSync(raceDirectory);fs.writeFileSync(path.join(raceDirectory,'file'),'inside\n');
    fs.mkdirSync(outside,{mode:0o700});fs.writeFileSync(path.join(outside,'file'),'outside-fixture-marker\n',{mode:0o600});
    let raceCycles=0, raceResult;
    const race=setInterval(()=>{
        fs.renameSync(raceDirectory,raceBackup);
        fs.symlinkSync(outside,raceDirectory);
        fs.unlinkSync(raceDirectory);
        fs.renameSync(raceBackup,raceDirectory);
        raceCycles++;
    },1);
    try {
        raceResult=await collect('/bin/bash',['-c','for ((i=0;i<80;i++)); do cat /workspace/race-directory/file 2>/dev/null || true; /bin/busybox sleep 0.001; done']);
    } finally {
        clearInterval(race);
        if(fs.existsSync(raceBackup)) {
            if(fs.lstatSync(raceDirectory,{throwIfNoEntry:false})?.isSymbolicLink())fs.unlinkSync(raceDirectory);
            fs.renameSync(raceBackup,raceDirectory);
        }
        fs.rmSync(outside,{recursive:true});
    }
    check(raceCycles>0&&raceResult.code===0&&raceResult.out.toString().replaceAll('inside\n','')==='','FILESYSTEM_SYMLINK_RACE');
    stage='network-boundary';
    let proxyConnections=0, deniedConnections=0;
    const sockets=new Set();
    const proxy=createServer(socket=>{
        proxyConnections++; sockets.add(socket);
        socket.once('close',()=>sockets.delete(socket));
        socket.once('data',()=>socket.end('proxy-ok\n'));
    });
    const other=createServer(socket=>{deniedConnections++;socket.destroy();});
    await new Promise((resolve,reject)=>{proxy.once('error',reject);proxy.listen(0,'127.0.0.1',resolve);});
    await new Promise((resolve,reject)=>{other.once('error',reject);other.listen(0,'127.0.0.1',resolve);});
    const proxyPort=proxy.address().port, otherPort=other.address().port;
    const configurationCopy={httpProxyPort:proxyPort};
    const proxyScope=scope(configurationCopy);
    configurationCopy.httpProxyPort=otherPort;
    const socksScope=scope({socksProxyPort:proxyPort});
    check(scope({httpProxyPort:-1})===undefined,'NETWORK_INVALID_CONFIG');
    const rejected=target=>`if exec 3<>${target}; then exit 91; else printf denied; fi`;
    const exchange=`exec 3<>/dev/tcp/127.0.0.1/${proxyPort}; printf fixture >&3; IFS= read -r answer <&3; printf '%s' "$answer"`;
    const network=[];
    try {
        network.push(await collect('/bin/bash',['-c',rejected(`/dev/tcp/127.0.0.1/${proxyPort}`)]));
        network.push(await collect('/bin/bash',['-c',rejected(`/dev/tcp/127.0.0.1/${otherPort}`)],'',undefined,proxyScope));
        network.push(await collect('/bin/bash',['-c',rejected(`/dev/tcp/203.0.113.1/${proxyPort}`)],'',undefined,proxyScope));
        network.push(await collect('/bin/bash',['-c',rejected(`/dev/udp/127.0.0.1/${proxyPort}`)],'',undefined,proxyScope));
        network.push(await collect('/bin/bash',['-c',`(${rejected(`/dev/tcp/127.0.0.1/${otherPort}`)})`],'',undefined,proxyScope));
        for(const result of network)
            check(result.code===0&&result.out.toString()==='denied'&&result.err.toString().includes('Permission denied'),'NETWORK_DENIED');
        const allowed=await collect('/bin/bash',['-c',exchange],'',undefined,proxyScope);
        check(allowed.code===0&&allowed.out.toString()==='proxy-ok','NETWORK_PROXY');
        const inherited=await collect('/bin/bash',['-c',`(${exchange})`],'',undefined,socksScope);
        check(inherited.code===0&&inherited.out.toString()==='proxy-ok','NETWORK_FORK_PROXY');
        const parallel=await Promise.all([
            collect('/bin/bash',['-c',exchange],'',undefined,proxyScope),
            collect('/bin/bash',['-c',rejected(`/dev/tcp/127.0.0.1/${proxyPort}`)])
        ]);
        check(parallel[0].out.toString()==='proxy-ok'&&parallel[1].out.toString()==='denied','NETWORK_SCOPE_ISOLATION');
        check(proxyConnections===3&&deniedConnections===0,'NETWORK_CONNECTION_COUNT');
        activeScope=0;
        try {
            const invalid=spawnSync('/bin/bash',['-c','exit 0'],syncOptions);
            check(invalid.error?.code==='EACCES'&&invalid.pid===0,'NETWORK_SCOPE_REQUIRED');
        } finally {activeScope=disabledScope;}
    } finally {
        for(const socket of sockets)socket.destroy();
        await Promise.all([new Promise(resolve=>proxy.close(resolve)),new Promise(resolve=>other.close(resolve))]);
    }
    stage='network-inherited-socket';
    let acceptedSocket;
    const inheritedServer=createServer(socket=>{acceptedSocket=socket;});
    await new Promise((resolve,reject)=>{inheritedServer.once('error',reject);inheritedServer.listen(0,'127.0.0.1',resolve);});
    let inheritedSocket;
    try {
        inheritedSocket=await new Promise((resolve,reject)=>{
            const socket=createConnection({host:'127.0.0.1',port:inheritedServer.address().port},()=>resolve(socket));
            socket.once('error',reject);
        });
        const inheritedFD=inheritedSocket._handle.fd;
        check(Number.isInteger(inheritedFD)&&inheritedFD>=0,'NETWORK_INHERITED_FD');
        const refused=spawnSync('/bin/bash',['-c','printf forbidden'],{...syncOptions,stdio:['ignore',inheritedFD,'ignore']});
        check(refused.error?.code==='ENOSYS'&&refused.pid===0&&!inheritedSocket.destroyed,'NETWORK_INHERITED_SOCKET_DENIED');
    } finally {
        inheritedSocket?.destroy(); acceptedSocket?.destroy();
        await new Promise(resolve=>inheritedServer.close(resolve));
    }
    stage='namespace-boundary';
    const namespace=await collect('/bin/bash',['-c',`set -e; mkdir -p /workspace/mountpoint; if /bin/busybox mount -t tmpfs tmpfs /workspace/mountpoint; then exit 91; fi; if /bin/busybox chroot / /bin/true; then exit 92; fi; printf namespace-denied`]);
    fs.writeFileSync(path.join(root,`node-namespace-fixture-${process.pid}.json`),JSON.stringify({code:namespace.code,signal:namespace.signal,out:namespace.out.toString().slice(0,4096),err:namespace.err.toString().slice(0,4096)}),{mode:0o600});
    check(namespace.code===0&&namespace.out.toString()==='namespace-denied'&&namespace.err.toString().includes('Operation not permitted'),'NAMESPACE_DENIED');
    stage='group-cancel';
    let cancelled=false;
    const cancelledRun=await collect('/bin/bash',['-c','/bin/busybox sleep 30 & printf ready; wait'],'',(child,bytes)=>{
        if(!cancelled&&bytes.toString().includes('ready')){cancelled=true;check(process.kill(-child.pid,'SIGTERM'),'KILL_ACCEPTED');}
    });
    check(cancelled&&cancelledRun.code===null&&cancelledRun.signal==='SIGTERM','GROUP_SIGNAL');
    stage='single-cancel';
    const single=await collect('/bin/bash',['-c','printf ready; exec /bin/busybox sleep 5'],'',(child,bytes)=>{
        if(bytes.toString().includes('ready'))check(child.kill('SIGTERM'),'SINGLE_KILL_ACCEPTED');
    });
    check(single.signal==='SIGTERM','SINGLE_SIGNAL');
    fs.writeFileSync(output,JSON.stringify({ok:true,bindingVersion:binding.version,nativePID:binding.hostPID(),nodePID:process.pid,platform:process.platform,builtinBytes:Buffer.byteLength(source),guestPID:main.pid,originalChildProcess:main.original,streamChunks:main.chunks,binaryBytes:binary.out.length,bashExit:main.code,missingCode:missing,concurrent:concurrent.length,cancelSignal:cancelledRun.signal,singleSignal:single.signal,syncExit:sync.status,syncDuplexBytes:duplex.stdout.length,syncPipeError:closedInput.error.code,syncPrimaryError:pipeTimeout.error.code,syncTimeout:timed.error.code,syncOverflow:overflow.error.code,syncCombinedOverflow:combined.error.code,syncWhich:true,syncPath:true,syncErrors:true,syncInheritedFD:true,unknownPID,hostSignalDenied,networkDenied:network.length,networkProxyConnections:proxyConnections,networkOtherConnections:deniedConnections,networkFork:true,networkConcurrent:true,networkImmutable:true,networkInheritedSocketDenied:true,namespaceDenied:true,filesystemAllowed:true,filesystemDenied:attempts.length,filesystemLinks:true,filesystemExactTemp:true,filesystemInheritedDescriptors:2,filesystemDescriptorRecheck:true,filesystemMmapDenied:true,filesystemConcurrent:scopedWrites.length,filesystemImmutable:true,filesystemSymlinkRaceCycles:raceCycles,processDistinctGenerations:true,processForeignSignalsDenied:true,processForeignProcDenied:true,processOwnDescendant:true,processSignalABI:true,processNativeGeneration:true,processVictimSurvived:true,models:0}),{mode:0o600});
} catch(error) {
    if(stage.startsWith('filesystem')||stage.startsWith('process'))fs.writeFileSync(path.join(root,`node-boundary-diagnostic-${process.pid}.json`),JSON.stringify({stage,code:error.code,lastGuest:lastGuestReceipt}),{mode:0o600});
    fs.writeFileSync(output,JSON.stringify({ok:false,stage,code:error.code||error.name}),{mode:0o600});
}

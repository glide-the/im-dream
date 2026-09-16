<!-- [Input] Actual safe command receipt; pinned disclosure checks passed. -->
<!-- [Output] Original outcomes with executed/skipped scope and failures retained. -->
<!-- [Pos] Coordinator-owned isolated technical evidence; real acceptance remains separate. -->
<!-- [Sync] 2026-09-15: preserve launch75/Workspace/failure candidate and continuation/recovery evidence. -->

# Launch75 primary harness static gate

Worktree: `/Users/dmeck/.codex/worktrees/729f/ink-admin-memory`

## TypeScript syntax transformation

- command: `node -e 'const fs=require("fs"),ts=require("typescript"); const files=["/private/tmp/ink-auth-migration-validation/prepare-launch75-continuation.mts","/private/tmp/ink-auth-migration-validation/launch75-atomic-recovery.mts"]; let diagnostics=0; for (const file of files) { const source=fs.readFileSync(file,"utf8"); const out=ts.transpileModule(source,{reportDiagnostics:true,compilerOptions:{target:ts.ScriptTarget.ES2022,module:ts.ModuleKind.ESNext}}); const ds=out.diagnostics||[]; diagnostics+=ds.length; for (const d of ds) console.log(ts.flattenDiagnosticMessageText(d.messageText,"\n")); } console.log(JSON.stringify({result:diagnostics?"FAIL":"PASS",files:files.length,diagnostics})); process.exit(diagnostics?1:0);'`
- cwd: `/Users/dmeck/.codex/worktrees/729f/ink-admin-memory`
- exit code: `0`
- stdout:

```text
{"result":"PASS","files":2,"diagnostics":0}
```

## Python syntax parsing

- command: `python3 -c 'import ast,pathlib; files=[pathlib.Path("/private/tmp/ink-auth-migration-validation/run-prepare-launch75-continuation.py"),pathlib.Path("/private/tmp/ink-auth-migration-validation/run-launch75-public-continuation.py"),pathlib.Path("/private/tmp/ink-auth-migration-validation/run-launch75-atomic-recovery.py")]; [ast.parse(p.read_text(),filename=str(p)) for p in files]; print(f"AST PASS files={len(files)}")'`
- cwd: `/Users/dmeck/.codex/worktrees/729f/ink-admin-memory`
- exit code: `0`
- stdout:

```text
AST PASS files=3
```

## Scope and cleanup

Node read only the two named `.mts` files and transformed them in memory with installed TypeScript; Python parsed the three named helpers only. No script was imported or executed, no output was written, and no private JSON, database, network, production, provider, runtime, fixture, service, pool, or cleanup operation was accessed. These results establish syntax parse/transformation only, not type, database, or business validation.

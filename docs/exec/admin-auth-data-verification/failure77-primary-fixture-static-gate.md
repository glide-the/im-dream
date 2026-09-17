<!-- [Input] Actual safe command receipt or preserved validation plan; pinned disclosure scan passed. -->
<!-- [Output] Executed bounded evidence including original failures and exact outcomes. -->
<!-- [Pos] Coordinator-owned technical evidence; full migration and real acceptance remain separate. -->
<!-- [Sync] 2026-09-15: retain Failure77 public/atomic/preservation and Thread SystemConfig candidate gates. -->

# Failure77 primary fixture static gate

Worktree: `/Users/dmeck/.codex/worktrees/729f/ink-admin-memory`

## TypeScript transpile diagnostics

- command: `node -e 'const fs=require("fs"),{createRequire}=require("module"); const req=createRequire("/Users/dmeck/.codex/worktrees/729f/ink-admin-memory/package.json"); const ts=req("typescript"); const file="/private/tmp/ink-auth-migration-validation/prepare-failure77-fixture.mts"; const source=fs.readFileSync(file,"utf8"); const out=ts.transpileModule(source,{reportDiagnostics:true,compilerOptions:{target:ts.ScriptTarget.ES2022,module:ts.ModuleKind.ESNext}}); const diagnostics=out.diagnostics||[]; for(const d of diagnostics) console.log(ts.flattenDiagnosticMessageText(d.messageText,"\n")); console.log(JSON.stringify({result:diagnostics.length?"FAIL":"PASS",file,diagnostics:diagnostics.length})); process.exit(diagnostics.length?1:0);'`
- cwd: `/Users/dmeck/.codex/worktrees/729f/ink-admin-memory`
- exit code: `0`
- stdout:

```text
{"result":"PASS","file":"/private/tmp/ink-auth-migration-validation/prepare-failure77-fixture.mts","diagnostics":0}
```

## Python AST parse

- command: `python3 -c 'import ast,pathlib; files=[pathlib.Path("/private/tmp/ink-auth-migration-validation/run-prepare-failure77-fixture.py"),pathlib.Path("/private/tmp/ink-auth-migration-validation/run-failure77-public-contract.py")]; [ast.parse(p.read_text(),filename=str(p)) for p in files]; print(f"AST PASS files={len(files)}")'`
- cwd: `/Users/dmeck/.codex/worktrees/729f/ink-admin-memory`
- exit code: `0`
- stdout:

```text
AST PASS files=2
```

## Scope and cleanup

Only in-memory TypeScript transpilation and Python AST parsing were performed. The preparation and public wrapper scripts were not executed; no private JSON/credentials, SQL/DDL, PostgreSQL, token, fixture, provider/model, network, service, or cleanup action was accessed. No broad marker assertions were used. These results establish syntax only and do not claim fixture or business validation.

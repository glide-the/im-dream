<!-- [Input] Actual safe command receipt, pinned disclosure scan passed. -->
<!-- [Output] Executed scope, original failures and concrete outcomes. -->
<!-- [Pos] Coordinator-owned technical evidence; full migration and real acceptance remain separate. -->
<!-- [Sync] 2026-09-15: retain Workspace76/public recovery and unregistered SystemConfig25 gates. -->

# Workspace76 primary fixture static gate

- cwd: `/Users/dmeck/.codex/worktrees/729f/ink-admin-memory`

## TypeScript transpile diagnostics

- command: `node -e 'const fs=require("fs"),ts=require("typescript"); const file="/private/tmp/ink-auth-migration-validation/prepare-workspace76-fixture.mts"; const source=fs.readFileSync(file,"utf8"); const out=ts.transpileModule(source,{reportDiagnostics:true,compilerOptions:{target:ts.ScriptTarget.ES2022,module:ts.ModuleKind.ESNext}}); const diagnostics=out.diagnostics||[]; for(const d of diagnostics) console.log(ts.flattenDiagnosticMessageText(d.messageText,"\n")); console.log(JSON.stringify({result:diagnostics.length?"FAIL":"PASS",file,diagnostics:diagnostics.length})); process.exit(diagnostics.length?1:0);'`
- exit code: `0`
- stdout:

```text
{"result":"PASS","file":"/private/tmp/ink-auth-migration-validation/prepare-workspace76-fixture.mts","diagnostics":0}
```

## Python AST parse

- command: `python3 -c 'import ast,pathlib; p=pathlib.Path("/private/tmp/ink-auth-migration-validation/run-prepare-workspace76-fixture.py"); ast.parse(p.read_text(),filename=str(p)); print("AST PASS")'`
- exit code: `0`
- stdout:

```text
AST PASS
```

## Scope and cleanup

Only in-memory TypeScript transpilation and Python AST parsing were performed. The MTS/Python wrappers were not executed; no private JSON/credentials, PostgreSQL, token, seed, network, DDL, fixture, service, or cleanup action was accessed. These results establish syntax only and do not claim fixture or business validation.

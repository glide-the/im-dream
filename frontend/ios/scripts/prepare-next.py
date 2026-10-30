#!/usr/bin/env python3
# [Input] Original Next app/config/lockfile and the already installed frontend dependency graph.
# [Output] A credential-free, separately owned source directory for an original standalone build.
# [Pos] iOS build preparation; it never modifies the running Web checkout or installs packages.
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import shutil

IOS = Path(__file__).resolve().parents[1]
REPO = IOS.parents[1]
FRONTEND = REPO / "frontend"
ROOT = IOS / "Next"
STAGE = ROOT / "build-source"
MARKER = ".ink-ios-next-build"
if ROOT.is_symlink() or STAGE.is_symlink():
    raise RuntimeError("iOS Next build directories must be ordinary directories")
if STAGE.exists() and not (STAGE / MARKER).is_file():
    raise RuntimeError("Refusing to replace an unowned Next build directory")
if not (FRONTEND / "node_modules/next/package.json").is_file():
    raise RuntimeError("Reuse the installed frontend dependencies before preparing Next")
shutil.rmtree(STAGE, ignore_errors=True)
STAGE.mkdir(parents=True)
(STAGE / MARKER).write_text("ink-memory-ios-next-v1\n")
contract = ROOT / "mobile/shared/bridge/contract.json"
contract.parent.mkdir(parents=True, exist_ok=True)
shutil.copy2(FRONTEND / "shared/bridge/contract.json", contract)
excluded = shutil.ignore_patterns("node_modules", "build", ".next", ".git", ".env", ".env.*", "__pycache__", "*.pyc")
for name in ("app", "packages", "public", "src", "shared"):
    shutil.copytree(FRONTEND / name, STAGE / name, ignore=excluded)
for name in ("package.json", "pnpm-lock.yaml", "pnpm-workspace.yaml", "tsconfig.json", "next-env.d.ts"):
    shutil.copy2(FRONTEND / name, STAGE / name)
config = (FRONTEND / "next.config.js").read_text()
assert config.count("export default nextConfig;") == 1
# These settings own build resources and file tracing, leaving application and
# authentication configuration unchanged. No deployment environment is copied.
config = config.replace("export default nextConfig;", """
nextConfig.output = 'standalone';
nextConfig.outputFileTracingRoot = TRACE_ROOT;
nextConfig.turbopack = { ...nextConfig.turbopack, root: TRACE_ROOT };
nextConfig.experimental = { ...nextConfig.experimental, cpus: 1 };
const originalWebpack = nextConfig.webpack;
nextConfig.webpack = (config, context) => {
  const selected = originalWebpack ? originalWebpack(config, context) : config;
  selected.cache = false;
  return selected;
};
export default nextConfig;
""".replace("TRACE_ROOT", json.dumps(str(REPO))))
(STAGE / "next.config.js").write_text(config)
(STAGE / "node_modules").symlink_to(FRONTEND / "node_modules", target_is_directory=True)
source_files = []
for source in sorted(STAGE.rglob("*")):
    if source.is_file() and not source.is_symlink() and "node_modules" not in source.parts:
        source_files.append({"path": source.relative_to(STAGE).as_posix(),
                             "sha256": hashlib.sha256(source.read_bytes()).hexdigest()})
receipt = {"version": 1, "next": json.loads((FRONTEND / "node_modules/next/package.json").read_text())["version"],
           "lockSha256": hashlib.sha256((FRONTEND / "pnpm-lock.yaml").read_bytes()).hexdigest(),
           "sourceFiles": source_files, "credentials": "excluded", "dependencyInstall": False}
(ROOT / "source-receipt.json").write_text(json.dumps(receipt, indent=2) + "\n")
print(f"Prepared original Next {receipt['next']} without credentials: {STAGE}")

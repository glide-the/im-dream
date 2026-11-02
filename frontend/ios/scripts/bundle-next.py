#!/usr/bin/env python3
# [Input] The isolated original Next standalone build, public assets and Xcode resource directory.
# [Output] A relocatable Next server tree with original web assets and a hashed source receipt.
# [Pos] Credential-free Next source/resources; bundle-node.py owns the separate ordinary runtime env.
# [Sync] 2026-11-01: verify checkout/prepared source freshness before copying resources; support independently owned Next roots.
# [Sync] 2026-10-25: relocate traced dependency links into the application tree; reject all other external symlinks.
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import shutil
import argparse

IOS = Path(__file__).resolve().parents[1]
REPO = IOS.parents[1]
ROOT = Path(os.environ.get("INK_IOS_NEXT_ROOT", str(IOS / "Next"))).absolute()
if not ROOT.resolve().is_relative_to(IOS.resolve()) or ROOT.resolve() == IOS.resolve() or ROOT.is_symlink():
    raise RuntimeError("The Next output root must be an ordinary named directory inside frontend/ios")
BUILD = ROOT / "build-source"
SOURCE = BUILD / ".next/standalone"
parser = argparse.ArgumentParser(description="Verify and bundle the prepared original Next resources")
parser.add_argument("--verify-sources", action="store_true", help="Check source provenance without changing application resources")
args = parser.parse_args()
receipt_path = ROOT / "source-receipt.json"
receipt = json.loads(receipt_path.read_text())
inputs = receipt.get("sourceInputs")
if not isinstance(inputs, list) or not inputs:
    raise RuntimeError("IOS_NEXT_SOURCE_RECEIPT_MISSING: prepare and rebuild the current Next sources")
prepared = {item["path"]: item["sha256"] for item in receipt["sourceFiles"]}
mismatches = []
for item in inputs:
    relative = Path(item["path"])
    if relative.is_absolute() or ".." in relative.parts:
        raise RuntimeError("IOS_NEXT_SOURCE_PATH_INVALID")
    current = REPO / "frontend" / relative
    staged = BUILD / relative
    if relative.as_posix() != "next.config.js" and item["sha256"] != prepared.get(relative.as_posix()):
        mismatches.append(relative.as_posix() + " (checkout/prepared receipt differs)")
    if not current.is_file() or hashlib.sha256(current.read_bytes()).hexdigest() != item["sha256"]:
        mismatches.append(relative.as_posix() + " (checkout changed)")
    if relative.name != "tsconfig.json" and (not staged.is_file() or hashlib.sha256(staged.read_bytes()).hexdigest() != prepared.get(relative.as_posix())):
        mismatches.append(relative.as_posix() + " (prepared source changed)")
if mismatches:
    raise RuntimeError("IOS_NEXT_SOURCES_STALE: prepare and rebuild before packaging: " + "; ".join(mismatches[:10]))
if args.verify_sources:
    print(f"Verified current Next runtime inputs: {len(inputs)}")
    raise SystemExit(0)
APP = Path(os.environ["TARGET_BUILD_DIR"]) / os.environ["UNLOCALIZED_RESOURCES_FOLDER_PATH"]
DESTINATION = APP / "next"
entry = BUILD.relative_to(REPO) / "server.js"
if not (SOURCE / entry).is_file():
    raise RuntimeError("Prepare and build the credential-free iOS Next standalone sources first")
excluded = []
links = []
for source in SOURCE.rglob("*"):
    if source.name == ".env" or source.name.startswith(".env."):
        raise RuntimeError("Next standalone contains a forbidden environment file")
    if source.is_symlink():
        resolved = source.resolve()
        if resolved.is_relative_to(SOURCE.resolve()):
            target = resolved.relative_to(SOURCE.resolve())
        elif (source == SOURCE / entry.parent / "node_modules"
              and resolved == (REPO / "frontend/node_modules").resolve()
              and (SOURCE / "frontend/node_modules").is_dir()):
            # Next traces the installed pnpm closure under its original frontend
            # location. Relocate the isolated build's one source dependency link
            # to that copied closure; no host filesystem target remains.
            target = Path("frontend/node_modules")
        else:
            raise RuntimeError("Next standalone contains a non-relocatable symlink: " + str(source.relative_to(SOURCE)))
        links.append((source.relative_to(SOURCE), target))
    if source.is_file() and source.suffix in {".node", ".dylib", ".so", ".exe", ".dll"}:
        excluded.append(source.relative_to(SOURCE).as_posix())
shutil.rmtree(DESTINATION, ignore_errors=True)
# This target now loads original Next exclusively. Remove only its own stale
# generated static resources from earlier incremental Xcode builds.
shutil.rmtree(APP / "web", ignore_errors=True)
shutil.copytree(SOURCE, DESTINATION, symlinks=True,
                ignore=shutil.ignore_patterns("*.node", "*.dylib", "*.so", "*.exe", "*.dll"))
for relative, target in links:
    link = DESTINATION / relative
    link.unlink()
    link.symlink_to(os.path.relpath(DESTINATION / target, link.parent))
dependency_links = []
installed = REPO / "frontend/node_modules"
aliases = []
for source in installed.iterdir():
    if source.name.startswith("."):
        continue
    aliases.extend(source.iterdir() if source.name.startswith("@") and source.is_dir() else [source])
for source in aliases:
    if not source.is_symlink():
        continue
    resolved = source.resolve()
    if not resolved.is_relative_to(REPO):
        continue
    target = resolved.relative_to(REPO)
    if not (SOURCE / target).is_dir():
        continue
    relative = Path("frontend/node_modules") / source.relative_to(installed)
    link = DESTINATION / relative
    if link.exists() or link.is_symlink():
        continue
    link.parent.mkdir(parents=True, exist_ok=True)
    link.symlink_to(os.path.relpath(DESTINATION / target, link.parent))
    dependency_links.append({"path": relative.as_posix(), "target": target.as_posix()})
for source in DESTINATION.rglob("*"):
    if source.is_symlink() and not source.resolve().is_relative_to(DESTINATION.resolve()):
        raise RuntimeError("Bundled Next dependency link escaped the application")
server_root = DESTINATION / entry.parent
shutil.copytree(BUILD / "public", server_root / "public", dirs_exist_ok=True)
shutil.copytree(BUILD / ".next/static", server_root / ".next/static", dirs_exist_ok=True)
shutil.copy2(receipt_path, DESTINATION / "source-receipt.json")
files = []
for source in sorted(DESTINATION.rglob("*")):
    if source.is_file() and not source.is_symlink():
        files.append({"path": source.relative_to(DESTINATION).as_posix(),
                      "sha256": hashlib.sha256(source.read_bytes()).hexdigest()})
manifest = {"version": 1, "nextVersion": receipt["next"], "serverEntry": entry.as_posix(),
            "sourceLockSha256": receipt["lockSha256"], "sourceReceiptSha256": hashlib.sha256(receipt_path.read_bytes()).hexdigest(), "credentials": "excluded",
            "relocatedSymlinks": [{"path": path.as_posix(), "target": target.as_posix()} for path, target in links],
            "restoredRootDependencyLinks": dependency_links,
            "excludedDesktopNativeModules": excluded, "files": files}
(DESTINATION / "mobile-manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
print(f"Bundled original Next {manifest['nextVersion']}: {len(files)} files; excluded {len(excluded)} desktop native modules")

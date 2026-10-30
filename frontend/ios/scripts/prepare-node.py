#!/usr/bin/env python3
# [Input] Hash-pinned Node Mobile and the existing published Runtime JavaScript archive.
# [Output] Local target libraries and same-source Node-compatible Runtime resources.
# [Pos] Build preparation only; no Agent, account, service or model is executed.
# [Sync] 2026-10-25: separate generated RuntimeArtifacts from tracked runtime sources on case-insensitive volumes.
# [Sync] 2026-10-25: retain original SandboxManager; the existing deployment setting disables the command sandbox.
import base64
import hashlib
import json
import os
from pathlib import Path
import shutil
import tarfile
import urllib.request
import zipfile

IOS = Path(__file__).resolve().parents[1]
LOCK = json.loads((IOS / "node-dependencies.json").read_text())


def download(record, destination):
    if not destination.exists():
        temporary = destination.with_suffix(".partial")
        urllib.request.urlretrieve(record["url"], temporary)
        temporary.replace(destination)
    data = destination.read_bytes()
    valid = (hashlib.sha256(data).hexdigest() == record["sha256"] if "sha256" in record
             else base64.b64encode(hashlib.sha512(data).digest()).decode() == record["sha512"])
    if not valid:
        raise RuntimeError("Dependency digest mismatch: " + destination.name)


def prepare():
    node = IOS / "Node"
    node.mkdir(exist_ok=True)
    archive = node / "nodejs-mobile-ios-24.21.0-0.zip"
    download(LOCK["node"], archive)
    with zipfile.ZipFile(archive) as bundle:
        bundle.extractall(node)
    runtime = IOS / "RuntimeArtifacts"
    runtime.mkdir(exist_ok=True)
    archive = runtime / "runtime-0.1.12-darwin-arm64.tgz"
    download(LOCK["runtime"], archive)
    with tarfile.open(archive) as bundle:
        bundle.extractall(runtime, filter="data")
    generated = runtime / "generated"
    shutil.rmtree(generated, ignore_errors=True)
    core = generated / "core"
    core.mkdir(parents=True)
    receipt = []
    source = runtime / "package/runtime/lib/core"
    for original in sorted(source.rglob("*.js")):
        relative = original.relative_to(source)
        target = core / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        data = original.read_text()
        marker = "var __require = import.meta.require;"
        count = data.count(marker)
        if count:
            if count != 1:
                raise RuntimeError("Unexpected Bun require adapter inventory")
            data = data.replace(marker, 'import { createRequire as __iosCreateRequire } from "node:module";\nvar __require = __iosCreateRequire(import.meta.url);')
        target.write_text(data)
        receipt.append({"path": str(relative), "sourceSha256": hashlib.sha256(original.read_bytes()).hexdigest(),
                        "sha256": hashlib.sha256(target.read_bytes()).hexdigest(), "nodeRequireAdapter": bool(count),
                        "iosCommandSandboxAdapter": False})
    if sum(item["nodeRequireAdapter"] for item in receipt) != 1:
        raise RuntimeError("The pinned Runtime must contain exactly one Bun require adapter")
    (core / "package.json").write_text('{"type":"module"}\n')
    for name in ("host.cjs", "worker.mjs", "ios-process-boundary.mjs"):
        shutil.copy2(IOS / "runtime" / name, generated / name)
    licenses = generated / "licenses"
    licenses.mkdir()
    notice = node / "LICENSE"
    download(LOCK["node"]["notice"], notice)
    shutil.copy2(notice, licenses / "NodeMobile-LICENSE")
    for original in (runtime / "package").rglob("LICENSE*"):
        if original.is_file():
            name = "-".join(original.relative_to(runtime / "package").parts)
            shutil.copy2(original, licenses / name)
    (generated / "runtime-adaptation.json").write_text(json.dumps({"runtime": LOCK["runtime"], "files": receipt}, indent=2) + "\n")
    print(f"Prepared Node {LOCK['node']['version']} and {len(receipt)} original Runtime JavaScript files; desktop binaries excluded.")


if __name__ == "__main__":
    prepare()

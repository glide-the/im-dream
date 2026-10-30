#!/usr/bin/env python3
# [Input] Prepared original Runtime resources and Xcode target build settings.
# [Output] App-local Node, original Runtime and original Next standalone resources with provenance receipts.
# [Pos] iOS resource build phase; normal application configuration stays outside React assets.
# [Sync] 2026-10-29: project the existing public MCP callback env key to this native target URI; source env/client credentials remain unchanged.
# [Sync] 2026-10-25: keep generated RuntimeArtifacts separate from tracked runtime sources.
# [Sync] 2026-10-25: copy the explicit loopback host configuration and package the isolated original Next build.
# [Sync] 2026-10-25: retain the original frontend/.env.local and backend/.env configuration owners in the app.
# [Sync] 2026-10-25: bundle the pinned command root and the existing sandbox-disabled deployment value.
# [Sync] 2026-10-26: retain the verified offline plugin wheelhouse with the packaged command resources.
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys

ios = Path(__file__).resolve().parents[1]
source = ios / "RuntimeArtifacts/generated"
if not (source / "runtime-adaptation.json").is_file():
    raise RuntimeError("Run python3 frontend/ios/scripts/prepare-node.py before building")
destination = Path(os.environ["TARGET_BUILD_DIR"]) / os.environ["UNLOCALIZED_RESOURCES_FOLDER_PATH"] / "node"
shutil.rmtree(destination, ignore_errors=True)
shutil.copytree(source, destination)
for name in ("host.cjs", "worker.mjs", "ios-process-boundary.mjs"):
    shutil.copy2(ios / "runtime" / name, destination / name)
receipt_path = destination / "runtime-adaptation.json"
receipt = json.loads(receipt_path.read_text())
receipt["platformFiles"] = {name: hashlib.sha256((destination / name).read_bytes()).hexdigest()
    for name in ("host.cjs", "worker.mjs", "ios-process-boundary.mjs")}
receipt_path.write_text(json.dumps(receipt, indent=2) + "\n")
shutil.copy2(ios / "host-config.json", destination / "host-config.json")
print("Bundled original Runtime JavaScript and iOS application-process host.")
fonts = ios / 'RuntimeArtifacts/fonts'
if not (fonts / 'font-receipt.json').is_file():
    raise RuntimeError('Prepare the original native fonts with scripts/prepare-fonts.py first')
for font in json.loads((fonts / 'font-receipt.json').read_text())['fonts']:
    original = ios.parent / 'public' / font['source']
    prepared = fonts / font['output']
    if hashlib.sha256(original.read_bytes()).hexdigest() != font['sourceSha256'] or hashlib.sha256(prepared.read_bytes()).hexdigest() != font['outputSha256']:
        raise RuntimeError('Native font receipt differs from the original public font')
shutil.copytree(fonts, destination.parent / 'fonts', dirs_exist_ok=True)
subprocess.run([sys.executable, str(ios / "scripts/bundle-next.py")], check=True)
next_root = destination.parent / "next"
next_entry = json.loads((next_root / "mobile-manifest.json").read_text())["serverEntry"]
for source, target in (
    (ios.parents[1] / "backend/.env", destination.parent / "app/.env"),
    (ios.parents[1] / "frontend/.env.local", (next_root / next_entry).parent / ".env.local"),
):
    if source.is_file():
        shutil.copy2(source, target)
        target.chmod(0o600)
    else:
        target.unlink(missing_ok=True)

# Command resources come only from the hash-verified local preparation directory.
guest = ios / "Guest"
if not (guest / "manifest.json").is_file():
    raise RuntimeError("Run scripts/prepare-guest.py with the pinned prepared core before building")
commands = destination.parent / "guest"
shutil.rmtree(commands, ignore_errors=True)
shutil.copytree(guest / "rootfs", commands / "rootfs")
shutil.copy2(guest / "manifest.json", commands / "manifest.json")
shutil.copytree(guest / 'python-wheels', commands / 'python-wheels')
licenses = commands / "licenses"
licenses.mkdir()
for name in ("LICENSE.md", "LICENSE.IOS"):
    shutil.copy2(guest / "source" / name, licenses / name)
# Reuse the existing process-level configuration key; other env values keep their owners.
value = os.environ.get("INK_AGENT_SANDBOX_ENABLED")
if value not in ("false", "true"):
    raise RuntimeError("INK_AGENT_SANDBOX_ENABLED must be an explicit build configuration value")
environment = destination.parent / "app/.env"
import re
body = environment.read_text() if environment.is_file() else ""
body = re.sub(r"(?m)^\s*(?:export\s+)?INK_AGENT_SANDBOX_ENABLED\s*=.*(?:\n|$)", "", body)
if body and not body.endswith("\n"):
    body += "\n"
environment.write_text(body + "INK_AGENT_SANDBOX_ENABLED=" + value + "\n")
environment.chmod(0o600)
identifier = os.environ.get("PRODUCT_BUNDLE_IDENTIFIER", "")
if not re.fullmatch(r"[A-Za-z][A-Za-z0-9.-]*\.[A-Za-z0-9.-]+", identifier):
    raise RuntimeError("A native bundle identifier is required for the MCP callback")
callback = identifier + ".mcp:/oauth/callback"
body = environment.read_text()
body = re.sub(r"(?m)^\s*(?:export\s+)?INK_CLAUDE_MCP_OAUTH_REDIRECT_URI\s*=.*(?:\n|$)", "", body)
environment.write_text(body + "INK_CLAUDE_MCP_OAUTH_REDIRECT_URI=" + callback + "\n")
environment.chmod(0o600)

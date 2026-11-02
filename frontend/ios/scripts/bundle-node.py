# [Sync] 2026-11-02: connect original account failures to runtime diagnostics and align the packaged native callback.
# [Sync] 2026-10-31: include the private native Admin HTTP adapter and its exact resource digest.
#!/usr/bin/env python3
# [Input] Prepared original Runtime resources and Xcode target build settings.
# [Output] App-local Node, original Runtime and original Next standalone resources with provenance receipts.
# [Pos] iOS resource build phase; normal application configuration stays outside React assets.
# [History] 2026-10-31: the earlier package retained the HTTP callback pending published native registration.
# [Sync] 2026-10-29: project the existing public MCP callback env key to this native target URI; source env/client credentials remain unchanged.
# [Sync] 2026-10-25: keep generated RuntimeArtifacts separate from tracked runtime sources.
# [Sync] 2026-10-25: copy the explicit loopback host configuration and package the isolated original Next build.
# [Sync] 2026-10-25: retain the original frontend/.env.local and backend/.env configuration owners in the app.
# [Sync] 2026-10-25: bundle the pinned command root and the existing sandbox-disabled deployment value.
# [Sync] 2026-10-26: retain the verified offline plugin wheelhouse with the packaged command resources.
# [Sync] 2026-10-30: require the locked Notion CLI binary and notice before copying application resources.
import hashlib
import json
import os
from pathlib import Path
import shutil
import plistlib
import subprocess
import sys

ios = Path(__file__).resolve().parents[1]
source = ios / "RuntimeArtifacts/generated"
if not (source / "runtime-adaptation.json").is_file():
    raise RuntimeError("Run python3 frontend/ios/scripts/prepare-node.py before building")
notion = json.loads((ios / "node-dependencies.json").read_text())["notionCli"]
if json.loads((source / "notion/manifest.json").read_text()) != notion:
    raise RuntimeError("Prepared Notion CLI manifest differs from the dependency lock")
for name, expected in (("ntn", notion["binarySha256"]), ("LICENSE.md", notion["licenseSha256"])):
    if hashlib.sha256((source / "notion" / name).read_bytes()).hexdigest() != expected:
        raise RuntimeError("Prepared Notion CLI resource digest mismatch")
destination = Path(os.environ["TARGET_BUILD_DIR"]) / os.environ["UNLOCALIZED_RESOURCES_FOLDER_PATH"] / "node"
shutil.rmtree(destination, ignore_errors=True)
shutil.copytree(source, destination)
for name in ("host.cjs", "worker.mjs", "ios-process-boundary.mjs", "ios-admin-http.mjs"):
    shutil.copy2(ios / "runtime" / name, destination / name)
receipt_path = destination / "runtime-adaptation.json"
receipt = json.loads(receipt_path.read_text())
receipt["platformFiles"] = {name: hashlib.sha256((destination / name).read_bytes()).hexdigest()
    for name in ("host.cjs", "worker.mjs", "ios-process-boundary.mjs", "ios-admin-http.mjs")}
receipt["notionCli"] = notion
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
    raise RuntimeError("A native bundle identifier is required for application callbacks")
callback = identifier + ".mcp:/oauth/callback"
body = environment.read_text()
body = re.sub(r"(?m)^\s*(?:export\s+)?INK_CLAUDE_MCP_OAUTH_REDIRECT_URI\s*=.*(?:\n|$)", "", body)
environment.write_text(body + "INK_CLAUDE_MCP_OAUTH_REDIRECT_URI=" + callback + "\n")
environment.chmod(0o600)

# The same published Client retains its original HTTP callback and an exact App
# callback. Only the packaged frontend copy adopts the native target receiver.
account = identifier + ".auth:/auth/callback"
metadata = plistlib.loads((ios / "InkMemory/Info.plist").read_bytes())
if metadata.get("InkAccountOAuthCallbackURI", "").replace("$(PRODUCT_BUNDLE_IDENTIFIER)", identifier) != account:
    raise RuntimeError("The packaged account callback must match Info.plist")
account_environment = (next_root / next_entry).parent / ".env.local"
if account_environment.is_file():
    body = account_environment.read_text()
    pattern = r"(?m)^([ \t]*(?:export[ \t]+)?INK_DREAM_BFF_REDIRECT_URI[ \t]*=[ \t]*)([^\r\n]*)"
    if len(re.findall(pattern, body)) > 1:
        raise RuntimeError("Duplicate BFF account callback configuration")
    body, count = re.subn(pattern, lambda match: match.group(1) + account, body)
    if not count:
        body = body.rstrip("\r\n") + "\nINK_DREAM_BFF_REDIRECT_URI=" + account + "\n"
    account_environment.write_text(body)
    account_environment.chmod(0o600)

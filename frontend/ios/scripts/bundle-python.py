#!/usr/bin/env python3
# [Input] Prepared, hash-pinned Python dependencies and Xcode's target build settings.
# [Output] Target-specific Python sources and signed extension frameworks in the app bundle.
# [Pos] Xcode resource phase; copies an explicit backend source list without credentials or data.
# [Sync] 2026-10-25: bundle production business routers, DTO dependencies and their original prompts.
# [Sync] 2026-10-25: retain the original backend Python package graph while excluding tests, credentials and runtime data.
# [Sync] 2026-10-25: retain both original memory policy assets used by the normal Chat turn preparation.
# [Sync] 2026-10-25: retain the original Dream workbench and asset-collaboration source contracts.
# [Sync] 2026-10-26: bundle declared builtins/local-marketplace plugins from the immutable digest-verified artifact store.

import os
import json
from pathlib import Path
import plistlib
import re
import shutil
import subprocess
import sys

IOS = Path(__file__).resolve().parents[1]
REPO = IOS.parents[1]
DEPENDENCIES = IOS / "Python"
APP = Path(os.environ["TARGET_BUILD_DIR"]) / os.environ["UNLOCALIZED_RESOURCES_FOLDER_PATH"]
SIMULATOR = os.environ["PLATFORM_NAME"] == "iphonesimulator"
ARCH = os.environ["CURRENT_ARCH"]
if ARCH == "undefined_arch":
    ARCH = os.environ["ARCHS"].split()[0]
if ARCH != "arm64":
    raise RuntimeError("The pinned pydantic-core build currently supports arm64 device/simulator")
SLICE = "ios-arm64_x86_64-simulator" if SIMULATOR else "ios-arm64"
TARGET = "aarch64-apple-ios-sim" if SIMULATOR else "aarch64-apple-ios"
FRAMEWORKS = APP / "Frameworks"
FRAMEWORKS.mkdir(parents=True, exist_ok=True)
EXTENSION = DEPENDENCIES / "extensions" / TARGET / "_pydantic_core.so"
if not EXTENSION.is_file():
    raise RuntimeError("Run python3 frontend/ios/scripts/prepare-python.py before building")

# Each build replaces only this phase's own resource directories.
for name in ("python", "app", "app_packages"):
    shutil.rmtree(APP / name, ignore_errors=True)
stdlib = APP / "python/lib/python3.13"
shutil.copytree(DEPENDENCIES / "Python.xcframework/lib/python3.13", stdlib,
                ignore=shutil.ignore_patterns("__pycache__", "test", "tests", "turtledemo", "idlelib", "tkinter", "ensurepip"))
shutil.copytree(DEPENDENCIES / "Python.xcframework" / SLICE / ("lib-" + ARCH) / "python3.13", stdlib, dirs_exist_ok=True)
shutil.copytree(DEPENDENCIES / "packages", APP / "app_packages",
                ignore=shutil.ignore_patterns("__pycache__"))
if (DEPENDENCIES / "native-packages" / TARGET).is_dir():
    shutil.copytree(DEPENDENCIES / "native-packages" / TARGET, APP / "app_packages", dirs_exist_ok=True)
shutil.copy2(EXTENSION, APP / "app_packages/pydantic_core/_pydantic_core.so")
if (DEPENDENCIES / "extensions" / TARGET / "rpds.so").is_file():
    shutil.copy2(DEPENDENCIES / "extensions" / TARGET / "rpds.so", APP / "app_packages/rpds/rpds.so")
shutil.copy2(DEPENDENCIES / "pydantic_core-2.41.5/LICENSE", APP / "app_packages/pydantic_core/LICENSE")
for name in ("mobile_runtime/__init__.py", "mobile_runtime/ios.py", "mobile_runtime/capabilities.py",
             "mobile_runtime/ios_claude_transport.py",
             "mobile_runtime/asgi_transport.py",
             "mobile_runtime/contract.py", "mobile_runtime/runtime.py", "routers/__init__.py",
             "routers/public.py", "routers/auth.py", "routers/deps.py", "routers/preferences.py",
             "routers/sessions.py", "routers/reports.py", "routers/pictures.py", "routers/friends.py",
             "routers/deck_versions.py", "routers/memory.py", "routers/oauth.py", "routers/device_oauth.py",
             "routers/voices.py", "services/deck/__init__.py", "services/deck/defaults.py",
             "config.py", "session_events.py", "chat_message_projection.py", "voice_projection.py",
             "models/workflow_run.py", "models/workflow_preflight.py", "models/deck_version.py", "libs/__init__.py",
             "story_workspace/__init__.py", "story_workspace/contracts.py",
             "services/story_workspace/dream_launch_application_service.py",
             "libs/claude_agent_kit/__init__.py", "libs/claude_agent_kit/types.py",
             "libs/claude_agent_kit/server/__init__.py", "libs/claude_agent_kit/server/session_projection_protocol.py",
             "libs/claude_agent_kit/server/image_generation_protocol.py", "libs/claude_agent_kit/server/reflection_memory_tool.py",
             "seo_content.py", "pyproject.toml", "reflections_agent.py", "reflections_config.py",
             "llm_json_parser.py", "memory_workspace_defaults.py", "agent_stream_events.py"):
    destination = APP / "app" / name
    destination.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(REPO / "backend" / name, destination)
for directory in ("mobile_runtime", "routers", "services", "claude_agent", "claude_mcp", "models", "story_workspace", "notion", "libs"):
    for source in sorted((REPO / "backend" / directory).rglob("*.py")):
        if any(part in {"__pycache__", "tests", "test", ".venv"} for part in source.parts):
            continue
        destination = APP / "app" / source.relative_to(REPO / "backend")
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, destination)
for name in ("memory_contract.json", "memory_contract_v2.json"):
    shutil.copy2(REPO / "backend/services/admin_data" / name, APP / "app/services/admin_data" / name)
for name in ("policy.json", "policy-v2.json"):
    shutil.copy2(REPO / "backend/services/memory" / name, APP / "app/services/memory" / name)
for name in ("dream_workbench_context.md", "dream_asset_collaboration.md"):
    shutil.copy2(REPO / "backend/story_workspace" / name, APP / "app/story_workspace" / name)
for name in ("holder", "starter", "mirror", "weaver", "absurdist"):
    destination = APP / "app/prompts" / (name + ".md")
    destination.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(REPO / "backend/prompts" / (name + ".md"), destination)
for source in sorted((REPO / "backend/builtin_skills").rglob("*")):
    if source.is_symlink():
        raise RuntimeError("Bundled builtin skills must use regular source files")
    if not source.is_file() or "__pycache__" in source.parts:
        continue
    if source.suffix not in {".md", ".py", ".json", ".txt", ".html", ".svg", ".skill", ".yaml"}:
        raise RuntimeError("Unexpected builtin skill asset type: " + source.suffix)
    destination = APP / "app" / source.relative_to(REPO / "backend")
    destination.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source, destination)
policy = APP / "mobile/shared/bridge/contract.json"
policy.parent.mkdir(parents=True, exist_ok=True)
shutil.copy2(REPO / "frontend/shared/bridge/contract.json", policy)

# Build input contains plugin content only; installation/auth metadata stays in Admin.
sys.path.insert(0, str(REPO / "backend"))
from services.claude_plugin.builtin_sources import PLATFORM_BUILTIN_SOURCES, KNOWN_MARKETPLACE_LOCAL_PATHS
from services.claude_plugin.digest import compute_plugin_digest
artifact_input = Path(os.environ.get("INK_CLAUDE_PLUGIN_RUNTIME_ROOT", str(REPO / "backend/data/claude-plugin-runtime"))) / "artifacts"
plugin_output = APP / "plugin-artifacts"
shutil.rmtree(plugin_output, ignore_errors=True)
plugin_output.mkdir()
plugin_records = []
declarations = [{**value, "required": True} for value in PLATFORM_BUILTIN_SOURCES.values()]
for marketplace, relative in KNOWN_MARKETPLACE_LOCAL_PATHS.items():
    marketplace_root = (REPO / relative).resolve()
    catalog = marketplace_root / ".claude-plugin/marketplace.json"
    if not catalog.is_file():
        continue
    for plugin in json.loads(catalog.read_text())["plugins"]:
        source = plugin.get("source")
        if not isinstance(source, str) or not source.startswith("./"):
            continue
        plugin_source = (marketplace_root / source).resolve()
        if not plugin_source.is_relative_to(marketplace_root) or not plugin_source.is_dir():
            raise RuntimeError("Declared local plugin source escapes its marketplace")
        if re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._-]*", plugin["name"]) is None:
            raise RuntimeError("Invalid declared local plugin name")
        declarations.append({"package_name": plugin["name"], "marketplace": marketplace, "required": False})
for declaration in declarations:
    prefix = declaration["package_name"] + "@" + declaration["marketplace"] + "@"
    matches = sorted(artifact_input.glob(prefix + "sha256-*"))
    if not matches and declaration["required"]:
        raise RuntimeError("Missing prepared immutable builtin plugin: " + prefix)
    for source in matches:
        if source.is_symlink() or any(item.is_symlink() for item in source.rglob("*")):
            raise RuntimeError("Bundled plugin artifacts require regular files")
        digest = compute_plugin_digest(source)
        if source.name != prefix + digest.replace(":", "-"):
            raise RuntimeError("Prepared plugin artifact digest mismatch")
        destination = plugin_output / source.name
        shutil.copytree(source, destination)
        # Normalize bundle input modes; the original store applies read-only
        # modes after importing and renaming inside the application data root.
        for item in (destination, *destination.rglob("*")):
            item.chmod(0o755 if item.is_dir() else 0o644)
        if compute_plugin_digest(destination) != digest:
            raise RuntimeError("Bundled plugin artifact digest mismatch")
        plugin_records.append({"package_name": declaration["package_name"], "marketplace": declaration["marketplace"], "digest": digest})
(plugin_output / "manifest.json").write_text(json.dumps(plugin_records, sort_keys=True) + "\n")

# CPython's AppleFrameworkLoader resolves .fwork markers to signed Frameworks.
# Packaging follows the CPython iOS guide (PSF-2.0 / examples 0BSD).
for root in (stdlib / "lib-dynload", APP / "app_packages"):
    for extension in sorted(root.rglob("*.so")):
        relative = extension.relative_to(root)
        module = ".".join((*relative.parts[:-1], relative.name.split(".")[0]))
        framework = FRAMEWORKS / (module + ".framework")
        shutil.rmtree(framework, ignore_errors=True)
        framework.mkdir()
        binary = framework / module
        architectures = subprocess.check_output(["xcrun", "lipo", "-archs", str(extension)], text=True).split()
        if len(architectures) > 1:
            subprocess.run(["xcrun", "lipo", str(extension), "-thin", ARCH, "-output", str(binary)], check=True)
        else:
            shutil.copy2(extension, binary)
        binary.chmod(0o755)
        subprocess.run(["xcrun", "install_name_tool", "-id",
                        f"@rpath/{module}.framework/{module}", str(binary)], check=True)
        identifier = (os.environ["PRODUCT_BUNDLE_IDENTIFIER"] + "." + module).replace("_", "-")
        with (framework / "Info.plist").open("wb") as stream:
            plistlib.dump({"CFBundleExecutable": module, "CFBundleIdentifier": identifier,
                          "CFBundleName": module, "CFBundlePackageType": "FMWK",
                          "CFBundleVersion": "1", "CFBundleShortVersionString": "1.0",
                          "MinimumOSVersion": os.environ["IPHONEOS_DEPLOYMENT_TARGET"],
                          "CFBundleSupportedPlatforms": ["iPhoneSimulator" if SIMULATOR else "iPhoneOS"]}, stream)
        marker = extension.with_suffix(".fwork")
        marker.write_text(str(binary.relative_to(APP)) + "\n")
        (framework / (module + ".origin")).write_text(str(marker.relative_to(APP)) + "\n")
        extension.unlink()
        identity = "-" if SIMULATOR else os.environ.get("EXPANDED_CODE_SIGN_IDENTITY", "")
        if identity and os.environ.get("CODE_SIGNING_ALLOWED") != "NO":
            subprocess.run(["/usr/bin/codesign", "--force", "--sign", identity,
                            "--timestamp=none", str(framework)], check=True, stdout=subprocess.DEVNULL)
print("Bundled CPython, FastAPI, pydantic-core and existing Dream business routes for " + TARGET)

#!/usr/bin/env python3
# [Input] Exact realfs-only interpreter prototype, existing Dream app and XCTest manifest.
# [Output] An isolated simulator test bundle, signed app copy and single-test manifest.
# [Pos] Named provider-free qualification builder; production targets remain unchanged.
# [Sync] 2026-10-25: preserve ordinary app env and restore guest modes/links as fixture data.
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import plistlib
import shutil
import stat
import subprocess


UPSTREAM_COMMIT = "c5c264da19148512167aa493d7bd4e50aae1b74e"
PATCH_SHA256 = "7e74e2134465e7f87e0f00b30a4c70023ae3b1dc8e4eed4c6c2b6adb59e1238e"
OWNER = "ink-ios-posix-qualification-20261025"


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--prototype", type=Path, required=True)
    parser.add_argument("--app", type=Path, required=True)
    parser.add_argument("--xctestrun", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    prototype = args.prototype.resolve(strict=True)
    original = args.app.resolve(strict=True)
    output = args.output.absolute()
    if output.is_symlink():
        raise RuntimeError("Qualification output must be an owned directory")
    marker = output / ".owner"
    if output.exists() and (not marker.is_file() or marker.read_text().strip() != OWNER):
        raise RuntimeError("Qualification output already exists without its owner marker")
    output.mkdir(parents=True, exist_ok=True)
    marker.write_text(OWNER + "\n")
    source = prototype / "source"
    commit = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=source, text=True).strip()
    patch = subprocess.check_output(["git", "diff", "--binary"], cwd=source)
    if commit != UPSTREAM_COMMIT or hashlib.sha256(patch).hexdigest() != PATCH_SHA256:
        raise RuntimeError("Interpreter source or private-fd adaptation differs from the qualification receipt")

    def locate(*argv: str) -> Path:
        return Path(subprocess.check_output(["xcrun", *argv], text=True).strip())

    sdk = locate("--sdk", "iphonesimulator", "--show-sdk-path")
    frameworks = sdk.parents[1] / "Library/Frameworks"
    clang = locate("--find", "clang")
    app_info = plistlib.loads((original / "Info.plist").read_bytes())
    minimum = app_info["MinimumOSVersion"]
    base = [str(clang), "-target", f"arm64-apple-ios{minimum}-simulator",
            "-isysroot", str(sdk), "-O2", "-fblocks"]
    commands = []

    def run(argv: list[str]) -> None:
        print(json.dumps({"command": argv}), flush=True)
        result = subprocess.run(argv, check=False)
        commands.append({"command": argv, "exitCode": result.returncode})
        (output / "build-receipt.json").write_text(json.dumps(commands, indent=2) + "\n")
        result.check_returncode()

    tests = Path(__file__).resolve().parents[1] / "InkMemoryTests"
    run(base + ["-std=gnu11", "-DINK_REALFS_ONLY=1", "-DGUEST_ARM64=1",
                "-DENGINE_ASBESTOS=1", "-DLOG_HANDLER_DPRINTF=1",
                "-I" + str(source), "-I" + str(prototype / "build-ios-sim"),
                "-I" + str(source / "vdso/arm64"), "-c", str(tests / "guest_fixture.c"),
                "-o", str(output / "guest_fixture.o")])
    run(base + ["-fobjc-arc", "-F" + str(frameworks), "-c",
                str(tests / "PosixCompatibilityTests.m"),
                "-o", str(output / "PosixCompatibilityTests.o")])
    bundle = output / "InkMemoryTests.xctest"
    bundle.mkdir(exist_ok=True)
    run(base + ["-bundle", str(output / "guest_fixture.o"),
                str(output / "PosixCompatibilityTests.o"),
                str(prototype / "build-ios-sim/libish.a"),
                str(prototype / "build-ios-sim/libish_emu.a"),
                "-F" + str(frameworks), "-framework", "XCTest", "-framework", "Foundation",
                "-Wl,-rpath,@loader_path/Frameworks", "-Wl,-rpath,@executable_path/Frameworks",
                "-o", str(bundle / "InkMemoryTests")])
    bundle_info = {"CFBundleIdentifier": app_info["CFBundleIdentifier"] + ".tests",
                   "CFBundleName": "InkMemoryTests", "CFBundleExecutable": "InkMemoryTests",
                   "CFBundlePackageType": "BNDL", "CFBundleVersion": "1",
                   "CFBundleSupportedPlatforms": ["iPhoneSimulator"], "MinimumOSVersion": minimum}
    (bundle / "Info.plist").write_bytes(plistlib.dumps(bundle_info))
    rootfs = bundle / "rootfs"
    if rootfs.exists():
        shutil.rmtree(rootfs)
    shutil.copytree(prototype / "rootfs", rootfs, symlinks=True,
                    ignore=shutil.ignore_patterns("*.apk"))
    modes, links = [], []
    for entry in sorted(rootfs.rglob("*")):
        relative = entry.relative_to(rootfs).as_posix()
        if entry.is_symlink():
            links.append({"path": relative, "target": os.readlink(entry)})
            entry.unlink()
        else:
            modes.append({"path": relative, "mode": stat.S_IMODE(entry.stat().st_mode) & 0o777})
    (bundle / "guest-modes.json").write_text(json.dumps(modes) + "\n")
    (bundle / "guest-symlinks.json").write_text(json.dumps(links) + "\n")
    run(["/usr/bin/codesign", "--force", "--sign", "-", str(bundle)])
    app = output / original.name
    if app.exists():
        shutil.rmtree(app)
    run(["/bin/cp", "-cR", str(original), str(app)])
    owned_tests = app / "PlugIns/InkMemoryTests.xctest"
    if owned_tests.exists():
        shutil.rmtree(owned_tests)
    shutil.copytree(bundle, owned_tests, symlinks=True)
    run(["/usr/bin/codesign", "--force", "--sign", "-", "--preserve-metadata=entitlements", str(app)])
    run(["/usr/bin/codesign", "--verify", "--deep", "--strict", str(app)])
    manifest = plistlib.loads(args.xctestrun.read_bytes())
    target = manifest["InkMemoryTests"]
    target.update(TestHostPath=str(app), TestBundlePath="__TESTHOST__/PlugIns/InkMemoryTests.xctest",
                  TestHostBundleIdentifier=app_info["CFBundleIdentifier"],
                  DependentProductPaths=[str(app), str(owned_tests)], CommandLineArguments=[],
                  OnlyTestIdentifiers=["PosixCompatibilityTests/testActualGuestBashInsideExistingDreamApplication"],
                  EnvironmentVariables={"OS_ACTIVITY_DT_MODE": "YES", "TERM": "dumb"})
    for key, value in list(target["TestingEnvironmentVariables"].items()):
        if isinstance(value, str):
            target["TestingEnvironmentVariables"][key] = value.replace(str(original), str(app))
    (output / "simulator-fixture.xctestrun").write_bytes(plistlib.dumps(manifest))
    print("TARGET_FIXTURE_BUILD_OK production_project_edits=0", flush=True)


if __name__ == "__main__":
    main()

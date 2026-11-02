#!/usr/bin/env python3
# [Input] Exact interpreter prototype, existing Dream App and original XCTest manifest.
# [Output] Named App copy with a Node/native process fixture and a single-test manifest.
# [Pos] Provider-free qualification builder; original production targets stay unchanged.
# [Sync] 2026-10-25: build a traced proc-guard archive copy; retain the pinned prototype and production target.
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import plistlib
import shutil
import subprocess
import struct
import sys


OWNER = "ink-ios-node-process-qualification-20261025"
TEST = "NodeProcessCompatibilityTests/testOriginalNodeChildProcessInsideApplication"


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("prototype", "app", "xctestrun", "output"):
        parser.add_argument("--" + name, type=Path, required=True)
    args = parser.parse_args()
    prototype = args.prototype.resolve(strict=True)
    original = args.app.resolve(strict=True)
    output = args.output.absolute()
    marker = output / ".owner"
    if output.is_symlink() or (output.exists() and
            (not marker.is_file() or marker.read_text().strip() != OWNER)):
        raise RuntimeError("Qualification output must have its own owner marker")
    output.mkdir(parents=True, exist_ok=True)
    marker.write_text(OWNER + "\n")
    ios = Path(__file__).resolve().parents[1]
    tests = ios / "InkMemoryTests"
    fixture = output / "base"
    commands = []

    def run(argv: list[str]) -> None:
        print(json.dumps({"command": argv}), flush=True)
        result = subprocess.run(argv, check=False)
        commands.append({"command": argv, "exitCode": result.returncode})
        (output / "build-receipt.json").write_text(json.dumps(commands, indent=2) + "\n")
        result.check_returncode()

    run([sys.executable, str(ios / "scripts/build-posix-qualification.py"),
         "--prototype", str(prototype), "--app", str(original),
         "--xctestrun", str(args.xctestrun.resolve(strict=True)), "--output", str(fixture)])
    sdk = Path(subprocess.check_output(
        ["xcrun", "--sdk", "iphonesimulator", "--show-sdk-path"], text=True).strip())
    frameworks = sdk.parents[1] / "Library/Frameworks"
    clang = subprocess.check_output(["xcrun", "--find", "clang"], text=True).strip()
    minimum = plistlib.loads((original / "Info.plist").read_bytes())["MinimumOSVersion"]
    base = [clang, "-target", f"arm64-apple-ios{minimum}-simulator",
            "-isysroot", str(sdk), "-O2", "-fblocks"]
    node = ios / "Node"
    framework = node / "NodeMobile.xcframework"
    available = plistlib.loads((framework / "Info.plist").read_bytes())["AvailableLibraries"]
    slices = [entry for entry in available if entry.get("SupportedPlatform") == "ios"
              and entry.get("SupportedPlatformVariant") == "simulator"
              and "arm64" in entry.get("SupportedArchitectures", [])]
    if len(slices) != 1:
        raise RuntimeError("Exactly one arm64 Node Mobile Simulator slice is required")
    node_frameworks = framework / slices[0]["LibraryIdentifier"]
    run(base + ["-std=c++20", "-I" + str(node / "include/node"), "-c",
                str(tests / "node_process_binding.cc"), "-o", str(output / "node_process_binding.o")])
    run(base + ["-std=gnu11", "-DINK_REALFS_ONLY=1", "-DGUEST_ARM64=1",
                "-DENGINE_ASBESTOS=1", "-DLOG_HANDLER_DPRINTF=1",
                "-I" + str(prototype / "source"), "-I" + str(prototype / "build-ios-sim"),
                "-I" + str(prototype / "source/vdso/arm64"), "-c",
                str(tests / "node_guest_fixture.c"), "-o", str(output / "node_guest_fixture.o")])
    run(base + ["-std=gnu11", "-DINK_REALFS_ONLY=1", "-DGUEST_ARM64=1",
                "-DENGINE_ASBESTOS=1", "-DLOG_HANDLER_DPRINTF=1",
                "-I" + str(prototype / "source"), "-I" + str(prototype / "build-ios-sim"),
                "-I" + str(prototype / "source/vdso/arm64"), "-c",
                str(tests / "node_guest_filesystem_fixture.c"), "-o", str(output / "node_guest_filesystem_fixture.o")])
    # Enforce ownership inside the original task lookup while its PID lock is held.
    # The base prototype/source/archive remain unchanged; qualify a recorded archive copy.
    proc_source = prototype / "source/fs/proc/pid.c"
    original_proc = proc_source.read_text()
    needle = "if (task != NULL && (task->exiting || task->sighand == NULL || task->group == NULL))"
    if original_proc.count(needle) != 1:
        raise RuntimeError("Pinned proc task-lookup guard changed")
    guarded_proc = original_proc.replace(
        '#include "kernel/calls.h"',
        '#include "kernel/calls.h"\nextern int InkNodeGuestTaskAccessAllowed(struct task *task);', 1,
    ).replace(needle, "if (task != NULL && (task->exiting || task->sighand == NULL || task->group == NULL || !InkNodeGuestTaskAccessAllowed(task)))")
    guarded_source = output / "qualified_proc_pid.c"
    guarded_source.write_text(guarded_proc)
    guarded_object = output / "fs_proc_pid.c.o"
    run(base + ["-std=gnu11", "-DINK_REALFS_ONLY=1", "-DGUEST_ARM64=1",
                "-DENGINE_ASBESTOS=1", "-DLOG_HANDLER_DPRINTF=1",
                "-I" + str(prototype / "source"), "-I" + str(prototype / "build-ios-sim"),
                "-I" + str(prototype / "source/vdso/arm64"), "-c",
                str(guarded_source), "-o", str(guarded_object)])
    archive = output / "libish-process-qualification.a"
    shutil.copy2(prototype / "build-ios-sim/libish.a", archive)
    run(["xcrun", "ar", "-d", str(archive), "fs_proc_pid.c.o"])
    run(["xcrun", "ar", "-r", str(archive), str(guarded_object)])
    run(["xcrun", "ranlib", str(archive)])
    (output / "proc-core-provenance.json").write_text(json.dumps({
        "originalSHA256": hashlib.sha256(original_proc.encode()).hexdigest(),
        "qualifiedSHA256": hashlib.sha256(guarded_proc.encode()).hexdigest(),
        "archiveSHA256": hashlib.sha256(archive.read_bytes()).hexdigest(),
        "guard": "InkNodeGuestTaskAccessAllowed under pids_lock", "basePrototypeEdits": 0,
    }, indent=2) + "\n")
    run(base + ["-fobjc-arc", "-F" + str(frameworks), "-c",
                str(tests / "NodeProcessCompatibilityTests.m"),
                "-o", str(output / "NodeProcessCompatibilityTests.o")])
    bundle = fixture / "InkMemoryTests.xctest"
    # Both probes use relocation-free interpreted Linux arm64 instructions.
    modes_path = bundle / "guest-modes.json"
    modes = json.loads(modes_path.read_text())
    for probe_name in ("mmap", "signal"):
        probe_object = output / f"node_guest_{probe_name}_fixture.o"
        run(base + ["-x", "assembler", "-c", str(tests / f"node_guest_{probe_name}_fixture.S"), "-o", str(probe_object)])
        macho = probe_object.read_bytes()
        if struct.unpack_from("<I", macho)[0] != 0xFEEDFACF:
            raise RuntimeError("Expected a 64-bit Mach-O assembly object")
        commands_count = struct.unpack_from("<I", macho, 16)[0]
        position, instructions = 32, None
        for _ in range(commands_count):
            command, size = struct.unpack_from("<II", macho, position)
            if command == 0x19:
                section_count = struct.unpack_from("<I", macho, position + 64)[0]
                for n in range(section_count):
                    section = position + 72 + n * 80
                    if macho[section:section + 16].rstrip(b"\0") != b"__text":
                        continue
                    length = struct.unpack_from("<Q", macho, section + 40)[0]
                    offset, _, _, relocations = struct.unpack_from("<IIII", macho, section + 48)
                    if instructions is not None or relocations:
                        raise RuntimeError("Probe must have one relocation-free text section")
                    instructions = macho[offset:offset + length]
            position += size
        if not instructions:
            raise RuntimeError("Missing guest syscall probe instructions")
        elf_size = 4096 + len(instructions)
        identity = b"\x7fELF\x02\x01\x01" + bytes(9)
        header = struct.pack("<16sHHIQQQIHHHHHH", identity, 2, 183, 1, 0x401000, 64, 0, 0, 64, 56, 1, 0, 0, 0)
        segment = struct.pack("<IIQQQQQQ", 1, 7, 0, 0x400000, 0, elf_size, elf_size, 4096)
        executable = (header + segment).ljust(4096, b"\0") + instructions
        probe = bundle / f"rootfs/workspace/{probe_name}-probe"
        probe.parent.mkdir(parents=True, exist_ok=True)
        probe.write_bytes(executable)
        probe.chmod(0o700)
        modes.append({"path": f"workspace/{probe_name}-probe", "mode": 0o700})
        (output / f"guest-{probe_name}-fixture.json").write_text(json.dumps({
            "elfSHA256": hashlib.sha256(executable).hexdigest(), "textSHA256": hashlib.sha256(instructions).hexdigest(),
            "bytes": len(executable), "guestABI": "Linux arm64", "hostExecution": False,
        }, indent=2) + "\n")
    modes_path.write_text(json.dumps(modes, indent=2) + "\n")
    run(base + ["-bundle", str(output / "NodeProcessCompatibilityTests.o"),
                str(output / "node_process_binding.o"), str(output / "node_guest_fixture.o"),
                str(output / "node_guest_filesystem_fixture.o"),
                str(archive), str(prototype / "build-ios-sim/libish_emu.a"),
                "-F" + str(frameworks), "-F" + str(node_frameworks), "-framework", "XCTest",
                "-framework", "Foundation", "-framework", "NodeMobile", "-lc++",
                "-Wl,-rpath,@executable_path/Frameworks", "-o", str(bundle / "InkMemoryTests")])
    run(["/usr/bin/codesign", "--force", "--sign", "-", str(bundle)])
    app = fixture / original.name
    owned_tests = app / "PlugIns/InkMemoryTests.xctest"
    shutil.rmtree(owned_tests)
    shutil.copytree(bundle, owned_tests, symlinks=True)
    shutil.copy2(tests / "node_process_fixture.mjs", app / "node/node_process_fixture.mjs")
    with (app / "node/host.cjs").open("a") as host:
        host.write("""
// Explicit qualification Worker in this named App copy only.
new Worker(path.join(__dirname, 'node_process_fixture.mjs'), {
  workerData:{receiptDirectory:path.dirname(endpointFile)}, trackUnmanagedFds:false
}).on('error', () => {
  fs.writeFileSync(path.join(path.dirname(endpointFile), `node-process-result-${process.pid}.json`),
    JSON.stringify({ok:false,stage:'worker'}), {mode:0o600});
});
""")
    run(["/usr/bin/codesign", "--force", "--sign", "-", "--preserve-metadata=entitlements", str(app)])
    run(["/usr/bin/codesign", "--verify", "--deep", "--strict", str(app)])
    manifest = plistlib.loads((fixture / "simulator-fixture.xctestrun").read_bytes())
    manifest["InkMemoryTests"]["OnlyTestIdentifiers"] = [TEST]
    (output / "node-process.xctestrun").write_bytes(plistlib.dumps(manifest))
    source_hashes = {name: hashlib.sha256((tests / name).read_bytes()).hexdigest() for name in (
        "node_guest_fixture.h", "node_guest_fixture.c", "node_guest_filesystem_fixture.h",
        "node_guest_filesystem_fixture.c", "node_process_binding.cc",
        "node_process_fixture.mjs", "NodeProcessCompatibilityTests.m", "node_guest_mmap_fixture.S",
        "node_guest_signal_fixture.S")}
    (output / "fixture-source-hashes.json").write_text(json.dumps(source_hashes, indent=2) + "\n")
    print("NODE_FIXTURE_BUILD_OK production_project_edits=0", flush=True)


if __name__ == "__main__":
    main()

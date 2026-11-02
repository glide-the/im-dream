#!/usr/bin/env python3
# [Input] Pinned CPython support archive, backend wheel hashes, and pydantic-core source.
# [Output] Local iOS Python runtime and exact FastAPI dependencies for device and simulator.
# [Pos] One-time dependency preparation for the existing Xcode target; no app or business service starts.
# [Sync] 2026-10-25: prepare real CPython and cross-compile the locked pydantic-core release.
# [Sync] 2026-10-25: include the original SDK/MCP dependency closure and target rpds extension.
# [Sync] 2026-10-25: package the locked PyYAML Python implementation for existing workspace/Skill readers.
# [Sync] 2026-10-25: cross-compile locked cryptography with target Python headers and verified iOS OpenSSL; prepare target cffi separately from host build tools.

import concurrent.futures
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import tarfile
import zipfile

IOS = Path(__file__).resolve().parents[1]
ROOT = IOS / "Python"
LOCK = json.loads((IOS / "python-dependencies.json").read_text())
CACHE = ROOT / "downloads"


def prepare_cryptography(packages, host_python, sysroot, config):
    record = LOCK["cryptography"]
    source = ROOT / ("cryptography-" + record["version"])
    archive = download(record["url"], record["sha256"])
    if not source.exists():
        with tarfile.open(archive) as bundle:
            bundle.extractall(ROOT, filter="data")
    shutil.copytree(source / "src/cryptography", packages / "cryptography", dirs_exist_ok=True)
    for name in ("LICENSE", "LICENSE.APACHE", "LICENSE.BSD"):
        shutil.copy2(source / name, packages / "cryptography" / name)
    tools = ROOT / "crypto-build-tools"
    if not (tools / "bin/python").exists():
        subprocess.run([host_python, "-m", "venv", str(tools)], check=True)
    host_archives = [download(item["url"], item["sha256"]) for item in record["buildTools"]]
    subprocess.run([str(tools / "bin/python"), "-m", "pip", "install", "--no-index", "--no-deps",
                    *map(str, host_archives)], check=True)
    build_script = source / "src/rust/cryptography-cffi/build.rs"
    original = build_script.read_text()
    adapted = original.replace('target.contains("apple") && openssl_static',
                               'target.contains("apple-darwin") && openssl_static')
    if 'env::var("CRYPTOGRAPHY_IOS_PYTHON_INCLUDE_DIR")' not in adapted:
        adapted = adapted.replace('let python_includes = run_python_script(',
            'let python_includes = env::var("CRYPTOGRAPHY_IOS_PYTHON_INCLUDE_DIR").unwrap_or_else(|_| run_python_script(')
        adapted = adapted.replace('.unwrap();\n    let openssl_c', '.unwrap());\n    let openssl_c')
    build_script.write_text(adapted)
    (source / "ios-build-adaptation.json").write_text(json.dumps({
        "sourceArchiveSha256": record["sha256"], "file": "src/rust/cryptography-cffi/build.rs",
        "outputSha256": hashlib.sha256(adapted.encode()).hexdigest(),
        "changes": ["Use target Python headers", "Link macOS compiler runtime only for macOS"],
    }, indent=2) + "\n")
    for target, wheels in LOCK["nativeWheels"].items():
        destination = ROOT / "native-packages" / target
        destination.mkdir(parents=True, exist_ok=True)
        for item in wheels:
            path = download(item["url"], item["sha256"])
            with zipfile.ZipFile(path) as bundle:
                bundle.extractall(destination)
        openssl = ROOT / "openssl" / target
        path = download(record["openssl"][target]["url"], record["openssl"][target]["sha256"])
        with tarfile.open(path) as bundle:
            bundle.extractall(openssl, filter="data")
        output = destination / "cryptography/hazmat/bindings/_rust.abi3.so"
        if output.exists():
            continue
        simulator = target.endswith("-sim")
        slice_name = "ios-arm64_x86_64-simulator" if simulator else "ios-arm64"
        sdk = subprocess.check_output(["xcrun", "--sdk", "iphonesimulator" if simulator else "iphoneos", "--show-sdk-path"], text=True).strip()
        environment = os.environ.copy()
        environment.update({
            "CARGO_HOME": str(ROOT / "cargo"), "CARGO_TARGET_DIR": str(ROOT / "cryptography-build"),
            "RUSTC": str(sysroot / "bin/rustc"), "PYO3_CONFIG_FILE": str(config),
            "PYO3_PYTHON": str(tools / "bin/python"), "PYTHON_SYS_EXECUTABLE": str(tools / "bin/python"),
            "IPHONEOS_DEPLOYMENT_TARGET": "16.4", "SDKROOT": sdk,
            "CRYPTOGRAPHY_IOS_PYTHON_INCLUDE_DIR": str(ROOT / "Python.xcframework" / slice_name / "include/python3.13"),
            "OPENSSL_DIR": str(openssl), "OPENSSL_STATIC": "1", "OPENSSL_NO_VENDOR": "1",
            "RUSTFLAGS": f"--sysroot={sysroot} -C link-arg=-undefined -C link-arg=dynamic_lookup",
        })
        subprocess.run(["cargo", "build", "--locked", "--release", "--lib", "--package", "cryptography-rust",
                        "--target", target, "--features", "pyo3/extension-module"], cwd=source, env=environment, check=True)
        output.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(ROOT / "cryptography-build" / target / "release/libcryptography_rust.dylib", output)


def download(url, digest):
    destination = CACHE / url.rsplit("/", 1)[-1]
    if not destination.exists() or hashlib.sha256(destination.read_bytes()).hexdigest() != digest:
        print("Downloading " + destination.name, flush=True)
        temporary = destination.with_suffix(destination.suffix + ".partial")
        subprocess.run(["curl", "--fail", "--location", "--silent", "--show-error",
                        "--retry", "3", "--connect-timeout", "20", "--max-time", "240",
                        "--output", str(temporary), url], check=True)
        if hashlib.sha256(temporary.read_bytes()).hexdigest() != digest:
            temporary.unlink()
            raise RuntimeError("Dependency SHA-256 mismatch: " + destination.name)
        temporary.replace(destination)
    return destination


def prepare():
    CACHE.mkdir(parents=True, exist_ok=True)
    python = LOCK["python"]
    support = download(python["url"], python["sha256"])
    if not (ROOT / "Python.xcframework").exists():
        with tarfile.open(support) as archive:
            archive.extractall(ROOT, filter="data")
    if ("Python version: " + python["version"]) not in (ROOT / "VERSIONS").read_text():
        raise RuntimeError("Remove the stale local Python dependency directory and prepare again")
    packages = ROOT / "packages"
    packages.mkdir(exist_ok=True)
    with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:
        archives = list(pool.map(lambda p: download(p["url"], p["sha256"]), LOCK["wheels"]))
    for path in archives:
        with zipfile.ZipFile(path) as archive:
            archive.extractall(packages)

    for record in LOCK.get("pureSources", []):
        path = download(record["url"], record["sha256"])
        with tarfile.open(path) as archive:
            archive.extractall(ROOT / "pure-sources", filter="data")
        source = ROOT / "pure-sources" / (record["name"] + "-" + record["version"])
        shutil.copytree(source / record["sourcePackage"], packages / record["targetPackage"], dirs_exist_ok=True)
        shutil.copy2(source / "LICENSE", packages / record["targetPackage"] / "LICENSE")

    core = LOCK["pydanticCore"]
    source_archive = download(core["url"], core["sha256"])
    source = ROOT / ("pydantic_core-" + core["version"])
    if not source.exists():
        with tarfile.open(source_archive) as archive:
            archive.extractall(ROOT, filter="data")
    shutil.copytree(source / "python/pydantic_core", packages / "pydantic_core", dirs_exist_ok=True)

    rust_version = LOCK["rust"]["version"]
    host_python = shutil.which("python3.13")
    if not host_python:
        raise RuntimeError("The pydantic-core build requires an existing host python3.13")
    sysroot = ROOT / "rust"
    # Homebrew rebuilds have different Rust metadata from official target libraries.
    # Keep the matching compiler and libraries local to this dependency directory.
    for key, component in [("compiler", "rustc"), ("hostStd", "rust-std-aarch64-apple-darwin")]:
        artifact = LOCK["rust"][key]
        archive = download(artifact["url"], artifact["sha256"])
        with tarfile.open(archive) as bundle:
            bundle.extractall(ROOT / "rust-installers", filter="data")
        installer = ROOT / "rust-installers" / archive.name.removesuffix(".tar.xz")
        shutil.copytree(installer / component, sysroot, dirs_exist_ok=True)
    config = ROOT / "pyo3-config.txt"
    config.write_text(
        "implementation=CPython\nversion=3.13\nshared=true\nabi3=false\n"
        "pointer_width=64\nbuild_flags=\nsuppress_build_script_link_lines=true\n"
    )
    for target, digest in LOCK["rust"]["targets"].items():
        output = ROOT / "extensions" / target / "_pydantic_core.so"
        if output.exists():
            continue
        url = f"https://static.rust-lang.org/dist/rust-std-{rust_version}-{target}.tar.xz"
        archive = download(url, digest)
        with tarfile.open(archive) as bundle:
            bundle.extractall(ROOT / "rust-installers", filter="data")
        installer = ROOT / "rust-installers" / archive.name.removesuffix(".tar.xz")
        target_lib = sysroot / "lib/rustlib" / target
        if not target_lib.exists():
            shutil.copytree(installer / ("rust-std-" + target) / "lib/rustlib" / target, target_lib)
        environment = os.environ.copy()
        environment.update({
            "CARGO_HOME": str(ROOT / "cargo"),
            "CARGO_TARGET_DIR": str(ROOT / "pydantic-build"),
            "RUSTC": str(sysroot / "bin/rustc"),
            "PYO3_CONFIG_FILE": str(config),
            "PYO3_PYTHON": host_python,
            "PYTHON_SYS_EXECUTABLE": host_python,
            "IPHONEOS_DEPLOYMENT_TARGET": "16.4",
            "RUSTFLAGS": f"--sysroot={sysroot} -C link-arg=-undefined -C link-arg=dynamic_lookup",
        })
        subprocess.run(["cargo", "build", "--locked", "--release", "--lib", "--target", target, "--features", "pyo3/extension-module"], cwd=source, env=environment, check=True)
        output.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(ROOT / "pydantic-build" / target / "release/lib_pydantic_core.dylib", output)
    if "rpds" in LOCK:
        record = LOCK["rpds"]
        archive = download(record["url"], record["sha256"])
        with tarfile.open(archive) as bundle:
            bundle.extractall(ROOT, filter="data")
        source = ROOT / ("rpds_py-" + record["version"])
        # Maturin generates this import-only package for the native rpds module.
        (packages / "rpds").mkdir(exist_ok=True)
        (packages / "rpds/__init__.py").write_text("from .rpds import *\n")
        shutil.copy2(source / "rpds.pyi", packages / "rpds/__init__.pyi")
        shutil.copy2(source / "LICENSE", packages / "rpds/LICENSE")
        for target in LOCK["rust"]["targets"]:
            output = ROOT / "extensions" / target / "rpds.so"
            if output.exists():
                continue
            environment = os.environ.copy()
            environment.update({
                "CARGO_HOME": str(ROOT / "cargo"), "CARGO_TARGET_DIR": str(ROOT / "rpds-build"),
                "RUSTC": str(sysroot / "bin/rustc"), "PYO3_CONFIG_FILE": str(config),
                "PYO3_PYTHON": host_python, "PYTHON_SYS_EXECUTABLE": host_python,
                "IPHONEOS_DEPLOYMENT_TARGET": "16.4",
                "RUSTFLAGS": f"--sysroot={sysroot} -C link-arg=-undefined -C link-arg=dynamic_lookup",
            })
            subprocess.run(["cargo", "build", "--locked", "--release", "--lib", "--target", target,
                            "--features", "pyo3/extension-module"], cwd=source, env=environment, check=True)
            output.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(ROOT / "rpds-build" / target / "release/librpds.dylib", output)
    if "cryptography" in LOCK:
        prepare_cryptography(packages, host_python, sysroot, config)
    print("iOS Python dependencies prepared with verified source hashes.")


if __name__ == "__main__":
    prepare()


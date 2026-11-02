#!/usr/bin/env python3
# [Input] Existing hash-pinned realfs-only interpreter build and its Linux command root.
# [Output] App-build libraries, headers, root files and complete preparation provenance.
# [Pos] Local dependency preparation; starts no service, guest command or model.
# [Sync] 2026-10-26: add hash-pinned Linux Python command packages to the existing prepared root.
from __future__ import annotations

import argparse
import base64
import csv
import hashlib
import io
import json
import os
from pathlib import Path
import shutil
import stat
import subprocess
import tarfile
import urllib.request
import zipfile


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def command_entries(root: Path) -> list[dict]:
    entries = []
    for path in sorted(root.rglob('*')):
        relative = path.relative_to(root).as_posix()
        if path.is_symlink():
            entries.append({'path': relative, 'target': os.readlink(path)})
        else:
            entry = {'path': relative, 'mode': stat.S_IMODE(path.stat().st_mode) & 0o777}
            if path.is_file():
                entry['sha256'] = digest(path)
            entries.append(entry)
    return entries


def add_python_packages(root: Path, records: list[dict], cache: Path) -> None:
    cache.mkdir(parents=True, exist_ok=True)
    for record in records:
        url = record['url']
        if not url.startswith('https://dl-cdn.alpinelinux.org/alpine/v3.21/main/aarch64/'):
            raise RuntimeError('Python command package must use the pinned Alpine source')
        archive = cache / url.rsplit('/', 1)[-1]
        if not archive.is_file() or digest(archive) != record['sha256']:
            body = urllib.request.urlopen(url, timeout=30).read()
            if hashlib.sha256(body).hexdigest() != record['sha256']:
                raise RuntimeError('Python command package SHA-256 mismatch')
            archive.write_bytes(body)
        with tarfile.open(archive, 'r:gz', ignore_zeros=True) as bundle:
            members = [member for member in bundle.getmembers()
                if not member.name.startswith('.')
                and 'sqlite3' not in Path(member.name).parts
                and not Path(member.name).name.startswith('_sqlite3.')]
            bundle.extractall(root, members=members, filter='data')
            for member in members:
                if member.isdir() or member.isfile():
                    (root / member.name).chmod(member.mode & 0o777)


def prepare_plugin_wheel(source: Path, destination: Path, platform_tag: str | None) -> None:
    if platform_tag is None:
        shutil.copy2(source, destination)
        return
    if platform_tag != 'linux_aarch64':
        raise RuntimeError('Unsupported pure Linux wheel platform')
    with zipfile.ZipFile(source) as archive:
        names = archive.namelist()
        if any(name.endswith(('.so', '.dll', '.dylib', '.jws', '.p7s')) for name in names):
            raise RuntimeError('Only unsigned Python-only wheels may change Linux tags')
        metadata = [name for name in names if name.endswith('.dist-info/WHEEL')]
        receipts = [name for name in names if name.endswith('.dist-info/RECORD')]
        if len(metadata) != 1 or len(receipts) != 1:
            raise RuntimeError('Wheel metadata is incomplete')
        payloads = {name: archive.read(name) for name in names}
        original = payloads[metadata[0]].decode()
        tags = [line[5:] for line in original.splitlines() if line.startswith('Tag: ')]
        if tags != ['py3-none-manylinux2014_aarch64']:
            raise RuntimeError('Pure Linux wheel source tag differs from the approved input')
        payloads[metadata[0]] = original.replace('Tag: py3-none-manylinux2014_aarch64',
            'Tag: py3-none-' + platform_tag).encode()
        receipt = io.StringIO(newline='')
        writer = csv.writer(receipt, lineterminator='\n')
        for name, body in payloads.items():
            if name != receipts[0]:
                checksum = base64.urlsafe_b64encode(hashlib.sha256(body).digest()).decode().rstrip('=')
                writer.writerow((name, 'sha256=' + checksum, len(body)))
        writer.writerow((receipts[0], '', ''))
        payloads[receipts[0]] = receipt.getvalue().encode()
        with zipfile.ZipFile(destination, 'w') as target:
            for entry in archive.infolist():
                target.writestr(entry, payloads[entry.filename])


def add_plugin_wheels(output: Path, records: list[dict], cache: Path) -> None:
    output.mkdir()
    for record in records:
        url = record['url']
        if not url.startswith('https://files.pythonhosted.org/packages/'):
            raise RuntimeError('Plugin wheels must use the pinned PyPI source')
        source = cache / url.rsplit('/', 1)[-1]
        if not source.is_file() or digest(source) != record['sha256']:
            body = urllib.request.urlopen(url, timeout=30).read()
            if hashlib.sha256(body).hexdigest() != record['sha256']:
                raise RuntimeError('Plugin wheel SHA-256 mismatch')
            source.write_bytes(body)
        name = record['filename']
        if Path(name).name != name or not name.endswith('.whl'):
            raise RuntimeError('Invalid prepared wheel filename')
        target = output / name
        prepare_plugin_wheel(source, target, record.get('platformTag'))
        if digest(target) != record.get('preparedSha256', record['sha256']):
            raise RuntimeError('Prepared plugin wheel SHA-256 mismatch')


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument('--prototype', type=Path, required=True)
    args = parser.parse_args()
    prototype = args.prototype.resolve(strict=True)
    ios = Path(__file__).resolve().parents[1]
    lock = json.loads((ios / 'guest-dependencies.json').read_text())
    source = prototype / 'source'
    revision = subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=source, text=True).strip()
    patch = subprocess.check_output(['git', 'diff', '--binary'], cwd=source)
    if revision != lock['revision'] or hashlib.sha256(patch).hexdigest() != lock['realfsPatchSHA256']:
        raise RuntimeError('Guest source or realfs patch differs from the pinned build')
    for sdk, directory in [('iphonesimulator', 'build-ios-sim'), ('iphoneos', 'build-ios-device')]:
        options = json.loads((prototype / directory / 'meson-info/intro-buildoptions.json').read_text())
        values = {entry['name']: entry['value'] for entry in options}
        if any(values.get(name) != value for name, value in
               [('jit', False), ('engine', 'asbestos'), ('guest_arch', 'arm64'), ('default_library', 'static')]):
            raise RuntimeError('Guest build must use the interpreted arm64 static core')
        for name, expected in lock['preparedArchives'][sdk].items():
            if digest(prototype / directory / name) != expected:
                raise RuntimeError('Prepared guest archive digest mismatch: ' + sdk + '/' + name)
    output = ios / 'Guest'
    marker = output / '.owner'
    owner = 'ink-memory-ios-guest-dependencies'
    if output.is_symlink() or (output.exists() and
            (not marker.is_file() or marker.read_text().strip() != owner)):
        raise RuntimeError('Guest output is not an owned preparation directory')
    if output.exists():
        shutil.rmtree(output)
    output.mkdir()
    marker.write_text(owner + '\n')
    paths = subprocess.check_output(['git', 'ls-files', '-z'], cwd=source).decode().split('\0')
    for relative in paths:
        original = source / relative
        if not relative or not original.is_file() or original.is_symlink():
            continue
        target = output / 'source' / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(original, target)
    for sdk, directory in [('iphonesimulator', 'build-ios-sim'), ('iphoneos', 'build-ios-device')]:
        target = output / sdk
        target.mkdir()
        for name in lock['preparedArchives'][sdk]:
            shutil.copy2(prototype / directory / name, target / name)
        shutil.copy2(prototype / directory / 'cpu-offsets.h', target / 'cpu-offsets.h')
    shutil.copy2(prototype / 'realfs-only.patch', output / 'realfs-only.patch')
    root = output / 'rootfs'
    shutil.copytree(prototype / 'rootfs', root, symlinks=True, ignore=shutil.ignore_patterns('*.apk'))
    base_digest = hashlib.sha256(json.dumps(command_entries(root), sort_keys=True).encode()).hexdigest()
    if base_digest != lock.get('preparedBaseRootDigest', lock['preparedRootDigest']):
        raise RuntimeError('Prepared base command root differs from its pinned digest')
    add_python_packages(root, lock.get('pythonPackages', []), ios / 'Python/downloads')
    entries = command_entries(root)
    root_digest = hashlib.sha256(json.dumps(entries, sort_keys=True).encode()).hexdigest()
    if root_digest != lock['preparedRootDigest']:
        raise RuntimeError('Prepared guest command root differs from its pinned digest')
    for path in root.rglob('*'):
        if path.is_symlink():
            path.unlink()
    add_plugin_wheels(output / 'python-wheels', lock.get('pythonWheels', []), ios / 'Python/downloads')
    (output / 'manifest.json').write_text(json.dumps({'rootDigest': root_digest,
        'entries': entries, 'source': lock}, indent=2) + '\n')
    print(json.dumps({'guestPrepared': True, 'revision': revision, 'entries': len(entries),
        'rootDigest': root_digest, 'jit': False, 'nativeOffload': False, 'models': 0}))


if __name__ == '__main__':
    main()

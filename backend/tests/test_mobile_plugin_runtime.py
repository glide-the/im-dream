# [Input] Original plugin digest/store algorithms and an isolated native protocol socket fixture.
# [Output] Immutable artifact, unchanged CLI argv/env/cwd, exit and timeout evidence without a model.
# [Pos] iOS plugin transport tests; no Admin, user records or desktop CLI is invoked.
# [Sync] 2026-10-26: cover managed Python argv/offline inputs, actual-version checks and original venv cache receipts.
import base64
from contextlib import contextmanager
import csv
import hashlib
import importlib.util
import io
import json
from pathlib import Path
import socket
import subprocess
import threading
import zipfile

import pytest

from mobile_runtime import ios_plugin_runtime as adapter
from services.claude_plugin import artifact_store, cli, workspace_init


@contextmanager
def native_fixture(monkeypatch, tmp_path, *, code=0, delay=False, output=b"2.1.241 (Claude Code)\n"):
    listener = socket.socket()
    listener.bind(("127.0.0.1", 0))
    listener.listen(1)
    listener.settimeout(2)
    endpoint = {"port": listener.getsockname()[1], "token": "fixture-only", "runtimeEntry": str(tmp_path / "cli.js")}
    monkeypatch.setattr(adapter, "read_native_endpoint", lambda path: endpoint)
    received = []
    failures = []
    finished = threading.Event()
    def serve():
        try:
            with listener.accept()[0] as connection, connection.makefile("rb") as reader:
                connection.settimeout(2)
                received.append(json.loads(reader.readline()))
                connection.sendall(b'{"type":"connected"}\n')
                assert json.loads(reader.readline()) == {"type": "end_input"}
                if delay:
                    while reader.read(1):
                        pass
                else:
                    for packet in ({"type": "stdout", "data": base64.b64encode(output).decode()},
                                   {"type": "stderr", "data": base64.b64encode(b"diagnostic").decode()},
                                   {"type": "exit", "code": code}):
                        connection.sendall((json.dumps(packet) + "\n").encode())
        except BaseException as failure:
            failures.append(failure)
        finally:
            finished.set()
    worker = threading.Thread(target=serve)
    worker.start()
    try:
        yield endpoint, received
    finally:
        listener.close()
        worker.join(timeout=3)
        assert finished.is_set() and not worker.is_alive()
        assert not failures


@pytest.mark.parametrize("code", [0, 7])
def test_native_plugin_cli_preserves_original_command_and_exit(tmp_path, monkeypatch, code):
    with native_fixture(monkeypatch, tmp_path, code=code) as (endpoint, received):
        args = [endpoint["runtimeEntry"], "plugin", "--help"]
        result = adapter._run_native_cli("endpoint", args, cwd=tmp_path, env={"HOME": str(tmp_path), "CLAUDE_CONFIG_DIR": str(tmp_path / "managed")},
            capture_output=True, text=True, timeout=2, check=False)
        assert result.args == args and result.returncode == code
        assert result.stdout == "2.1.241 (Claude Code)\n" and result.stderr == "diagnostic"
        assert received == [{"type": "connect", "version": 1, "token": "fixture-only", "purpose": "plugin-management",
            "cwd": str(tmp_path.resolve()), "env": {"HOME": str(tmp_path), "CLAUDE_CONFIG_DIR": str(tmp_path / "managed")}, "argv": ["plugin", "--help"]}]


def test_native_plugin_timeout_closes_its_worker_connection(tmp_path, monkeypatch):
    with native_fixture(monkeypatch, tmp_path, delay=True) as (endpoint, received):
        with pytest.raises(subprocess.TimeoutExpired) as failure:
            adapter._run_native_cli("endpoint", [endpoint["runtimeEntry"], "--version"], env={},
                capture_output=True, text=True, timeout=0.1, check=False)
        assert failure.value.timeout == 0.1
        assert len(received) == 1


@pytest.mark.parametrize("tamper", [False, True])
def test_bundled_artifact_uses_original_digest_and_store(tmp_path, monkeypatch, tamper):
    resources = tmp_path / "bundle"
    executable = resources / "node/core/cli.js"
    executable.parent.mkdir(parents=True)
    executable.write_text("// runtime fixture")
    bundle = resources / "plugin-artifacts"
    source = tmp_path / "source"
    (source / ".claude-plugin").mkdir(parents=True)
    (source / ".claude-plugin/plugin.json").write_text('{"name":"fixture-plugin","version":"1.0.0"}')
    digest = artifact_store.compute_plugin_digest(source)
    name = artifact_store.artifact_dir_name("fixture-plugin", "platform-builtin", digest)
    bundle.mkdir()
    source.rename(bundle / name)
    (bundle / "manifest.json").write_text(json.dumps([{"package_name":"fixture-plugin","marketplace":"platform-builtin","digest":digest}]))
    monkeypatch.setenv("INK_CLAUDE_PLUGIN_RUNTIME_ROOT", str(tmp_path / "runtime"))
    monkeypatch.setattr(adapter, "read_native_endpoint", lambda path: {"runtimeEntry": str(executable)})
    monkeypatch.setattr(adapter, "_bound_endpoint", None)
    monkeypatch.setattr(cli, "_command_execution", None)
    monkeypatch.setattr(workspace_init, "_python_execution", None)
    monkeypatch.setattr(adapter, "_run_native_python", lambda *args, **kwargs:
        subprocess.CompletedProcess(args[1], 0, '3.12.15\n', ''))
    if tamper:
        (bundle / name / "changed.md").write_text("unexpected")
        with pytest.raises(cli.ClaudeCliError, match="DIGEST_MISMATCH"):
            adapter.prepare_plugin_runtime("endpoint")
        assert cli._command_execution is None
        assert not (tmp_path / "runtime/artifacts" / name).exists()
    else:
        adapter.prepare_plugin_runtime("endpoint")
        artifact = artifact_store.get_artifact("fixture-plugin", "platform-builtin", digest)
        assert artifact.digest == digest
        assert cli._command_execution[0] == executable.resolve()
        adapter.prepare_plugin_runtime("endpoint")
        with pytest.raises(cli.ClaudeCliError, match="ALREADY_BOUND"):
            adapter.prepare_plugin_runtime("another-endpoint")


def test_managed_python_uses_original_venv_receipt_and_cache(tmp_path, monkeypatch):
    monkeypatch.setattr(workspace_init, '_python_execution', None)
    plugin = tmp_path / 'plugin'
    plugin.mkdir()
    (plugin / 'requirements.txt').write_text('example>=1\n')
    calls = []
    def run(argv, **options):
        calls.append((argv, options))
        if argv[1:3] == ['-m', 'venv']:
            target = Path(argv[-1]) / 'bin/python3'
            target.parent.mkdir(parents=True)
            target.write_bytes(b'fixture interpreter')
        return subprocess.CompletedProcess(argv, 0, '', '')
    workspace_init.bind_python_execution('/usr/bin/python3', '3.12.15', run)
    spec = workspace_init.PythonRuntimeSpec('requirements.txt', '3.11')
    venv = workspace_init.ensure_plugin_venv(tmp_path / 'runtime', 'sha256:' + 'a' * 64, plugin, spec)
    assert calls[0][0] == ['/usr/bin/python3', '-m', 'venv', '--copies', str(venv)]
    assert calls[1][0] == [str(venv / 'bin/python3'), '-m', 'pip', 'install',
        '--disable-pip-version-check', '--no-input', '-r', str(plugin / 'requirements.txt')]
    receipt = json.loads((venv.parent / 'runtime-receipt.json').read_text())
    assert receipt['python_version'] == '3.12.15' and receipt['artifact_digest'] == 'sha256:' + 'a' * 64
    assert workspace_init.ensure_plugin_venv(tmp_path / 'runtime', 'sha256:' + 'a' * 64, plugin, spec) == venv
    assert len(calls) == 2
    with pytest.raises(workspace_init.WorkspaceInitError):
        workspace_init.ensure_plugin_venv(tmp_path / 'runtime', 'sha256:' + 'a' * 64,
            plugin, workspace_init.PythonRuntimeSpec('requirements.txt', '3.13'))


def test_native_python_preserves_command_and_uses_bundled_offline_wheels(tmp_path, monkeypatch):
    with native_fixture(monkeypatch, tmp_path, output=b'3.12.15\n') as (endpoint, received):
        executable = tmp_path / 'resources/node/core/cli.js'
        endpoint['runtimeEntry'] = str(executable)
        wheels = tmp_path / 'resources/guest/python-wheels'
        wheels.mkdir(parents=True)
        args = ['/usr/bin/python3', '--version']
        result = adapter._run_native_python('endpoint', args, capture_output=True,
            text=True, timeout=2, cwd=tmp_path, env={'PYTHONHOME':'native-only', 'PYTHONPATH':'native-packages'})
        assert result.returncode == 0 and result.args == args
        assert received[0]['argv'] == args and received[0]['purpose'] == 'plugin-python'
        assert received[0]['env']['PIP_NO_INDEX'] == '1'
        assert received[0]['env']['PIP_FIND_LINKS'] == str(wheels)
        assert 'PYTHONHOME' not in received[0]['env'] and 'PYTHONPATH' not in received[0]['env']


@pytest.mark.parametrize('binary', [False, True])
def test_pure_linux_wheel_adjustment_preserves_payload_and_rejects_binary(tmp_path, binary):
    script = Path(__file__).parents[2] / 'mobile/ios/scripts/prepare-guest.py'
    spec = importlib.util.spec_from_file_location('plugin_wheel_preparation', script)
    preparation = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(preparation)
    source = tmp_path / 'source.whl'
    with zipfile.ZipFile(source, 'w') as archive:
        archive.writestr('example/__init__.py', b'payload unchanged\n')
        archive.writestr('example-1.0.dist-info/WHEEL', 'Wheel-Version: 1.0\nTag: py3-none-manylinux2014_aarch64\n')
        archive.writestr('example-1.0.dist-info/RECORD', '')
        if binary:
            archive.writestr('example/extension.so', b'ELF fixture')
    first = tmp_path / 'first.whl'
    if binary:
        with pytest.raises(RuntimeError, match='Python-only'):
            preparation.prepare_plugin_wheel(source, first, 'linux_aarch64')
        assert not first.exists()
        return
    second = tmp_path / 'second.whl'
    preparation.prepare_plugin_wheel(source, first, 'linux_aarch64')
    preparation.prepare_plugin_wheel(source, second, 'linux_aarch64')
    assert first.read_bytes() == second.read_bytes()
    with zipfile.ZipFile(first) as archive:
        assert archive.read('example/__init__.py') == b'payload unchanged\n'
        assert b'Tag: py3-none-linux_aarch64' in archive.read('example-1.0.dist-info/WHEEL')
        for name, checksum, size in csv.reader(io.StringIO(archive.read('example-1.0.dist-info/RECORD').decode())):
            if checksum:
                body = archive.read(name)
                expected = base64.urlsafe_b64encode(hashlib.sha256(body).digest()).decode().rstrip('=')
                assert checksum == 'sha256=' + expected and int(size) == len(body)

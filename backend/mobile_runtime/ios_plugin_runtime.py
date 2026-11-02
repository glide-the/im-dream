# [Input] Bundled immutable plugin artifacts and the application's original Runtime endpoint.
# [Output] Digest-verified local artifacts and original CLI receipts through the native Worker.
# [Pos] iOS plugin execution compatibility; Admin owns installation metadata and permissions.
# [Sync] 2026-10-26: bind original venv/pip setup to packaged guest Python and digest-pinned offline wheels.
from __future__ import annotations

import base64
import json
import os
from pathlib import Path
import socket
import subprocess
import time

from services.claude_plugin import artifact_store, cli, runtime, workspace_init
from .ios_claude_transport import read_native_endpoint

_bound_endpoint = None


def prepare_plugin_runtime(endpoint_path):
    global _bound_endpoint
    if _bound_endpoint is not None:
        if Path(endpoint_path).resolve() != _bound_endpoint:
            raise cli.ClaudeCliError("IOS_PLUGIN_RUNTIME_ALREADY_BOUND")
        return
    endpoint = read_native_endpoint(endpoint_path)
    bundle = Path(endpoint["runtimeEntry"]).parents[2] / "plugin-artifacts"
    records = json.loads((bundle / "manifest.json").read_text())
    for record in records:
        name = artifact_store.artifact_dir_name(record["package_name"], record["marketplace"], record["digest"])
        source = (bundle / name).resolve(strict=True)
        if source.parent != bundle.resolve():
            raise cli.ClaudeCliError("IOS_PLUGIN_ARTIFACT_PATH_INVALID")
        if artifact_store.compute_plugin_digest(source) != record["digest"]:
            raise cli.ClaudeCliError("IOS_PLUGIN_ARTIFACT_DIGEST_MISMATCH")
        artifact = artifact_store.import_tree(source, package_name=record["package_name"], marketplace=record["marketplace"])
        if artifact.digest != record["digest"]:
            raise cli.ClaudeCliError("IOS_PLUGIN_ARTIFACT_DIGEST_MISMATCH")
    probe = _run_native_python(endpoint_path, ['/usr/bin/python3', '-c',
        'import sys; print(".".join(map(str, sys.version_info[:3])))'],
        capture_output=True, text=True, timeout=30, check=False)
    version = probe.stdout.strip()
    if probe.returncode != 0 or not version:
        raise cli.ClaudeCliError('IOS_PLUGIN_PYTHON_UNAVAILABLE')
    workspace_init.bind_python_execution('/usr/bin/python3', version,
        lambda argv, **options: _run_native_python(endpoint_path, argv, **options))
    cli.bind_command_execution(Path(endpoint["runtimeEntry"]),
        lambda argv, **options: _run_native_cli(endpoint_path, argv, **options))
    _bound_endpoint = Path(endpoint_path).resolve()


def _run_native_cli(endpoint_path, argv, *, capture_output, text, timeout, check, cwd=None, env=None):
    """Execute the unchanged CLI argv without CPython subprocess creation."""
    return _run_native_process(endpoint_path, argv, capture_output=capture_output,
        text=text, timeout=timeout, check=check, cwd=cwd, env=env, purpose='plugin-management')


def _run_native_python(endpoint_path, argv, *, capture_output, text, timeout, check=False, cwd=None, env=None):
    endpoint = read_native_endpoint(endpoint_path)
    wheels = Path(endpoint['runtimeEntry']).parents[2] / 'guest/python-wheels'
    if not wheels.is_dir():
        raise cli.ClaudeCliError('IOS_PLUGIN_PYTHON_WHEELS_MISSING')
    environment = dict(os.environ if env is None else env)
    environment.pop('PYTHONHOME', None)
    environment.pop('PYTHONPATH', None)
    environment.update(PIP_NO_INDEX='1', PIP_FIND_LINKS=str(wheels), PIP_NO_CACHE_DIR='1')
    return _run_native_process(endpoint_path, argv, capture_output=capture_output,
        text=text, timeout=timeout, check=check, cwd=cwd or runtime.get_runtime_root(),
        env=environment, purpose='plugin-python')


def _run_native_process(endpoint_path, argv, *, capture_output, text, timeout, check, purpose, cwd=None, env=None):
    if not capture_output or not text or check:
        raise cli.ClaudeCliError("IOS_PLUGIN_CLI_CAPTURE_INVALID")
    endpoint = read_native_endpoint(endpoint_path)
    if purpose == 'plugin-management' and Path(argv[0]).resolve() != Path(endpoint["runtimeEntry"]).resolve():
        raise cli.ClaudeCliError("IOS_PLUGIN_CLI_EXECUTABLE_MISMATCH")
    directory = Path(cwd) if cwd is not None else Path(__file__).parents[1]
    environment = dict(os.environ if env is None else env)
    environment.setdefault("HOME", str(Path.home()))
    output = {"stdout": bytearray(), "stderr": bytearray()}
    deadline = time.monotonic() + timeout
    try:
        with socket.create_connection(("127.0.0.1", endpoint["port"]), timeout=timeout) as connection:
            connection.sendall((json.dumps({"type": "connect", "version": 1, "token": endpoint["token"],
                "purpose": purpose, "cwd": str(directory.resolve()), "env": environment,
                "argv": list(argv[1:] if purpose == 'plugin-management' else argv)}) + "\n").encode())
            with connection.makefile("rb") as reader:
                connected = False
                while True:
                    remaining = deadline - time.monotonic()
                    if remaining <= 0:
                        raise TimeoutError()
                    connection.settimeout(remaining)
                    line = reader.readline(128 * 1024 + 1)
                    if not line or len(line) > 128 * 1024 or not line.endswith(b"\n"):
                        raise cli.ClaudeCliError("IOS_PLUGIN_CLI_FRAME_INVALID")
                    packet = json.loads(line)
                    kind = packet.get("type")
                    if kind == "connected" and not connected:
                        connected = True
                        connection.sendall(b'{"type":"end_input"}\n')
                    elif connected and kind in output:
                        chunk = base64.b64decode(packet["data"], validate=True)
                        if sum(map(len, output.values())) + len(chunk) > 64 * 1024:
                            raise cli.ClaudeCliError("IOS_PLUGIN_CLI_OUTPUT_LIMIT")
                        output[kind].extend(chunk)
                    elif connected and kind == "exit" and type(packet.get("code")) is int:
                        return subprocess.CompletedProcess(argv, packet["code"],
                            output["stdout"].decode("utf-8", errors="replace"),
                            output["stderr"].decode("utf-8", errors="replace"))
                    else:
                        raise cli.ClaudeCliError("IOS_PLUGIN_CLI_EXECUTION_FAILED")
    except TimeoutError as exc:
        raise subprocess.TimeoutExpired(argv, timeout, output=output["stdout"].decode("utf-8", errors="replace"),
            stderr=output["stderr"].decode("utf-8", errors="replace")) from exc

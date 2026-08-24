# [Input] Local synthetic wheel/sdist/npm tgz fixtures and injected registry/tool seams.
# [Output] Provider-free proof of exact registry identity, integrity, zero-map,
#          isolated SDK ownership/API/cli_path, CLI version, and safe 404 failure.
# [Pos] Unit contract for scripts/verify_claude_registry_release.py; no registry,
#       model, credential, database, Docker, or production service is accessed.
# [Sync] 2026-08-24: initial provider-free registry release acceptance coverage.

from __future__ import annotations

import base64
import hashlib
import io
import json
import os
import subprocess
import sys
import tarfile
import urllib.error
import zipfile
from pathlib import Path
from unittest import mock

import pytest


ROOT = Path(__file__).resolve().parents[2]
SCRIPTS = ROOT / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import verify_claude_registry_release as acceptance


FIXTURE = json.loads(
    (Path(__file__).parent / "fixtures" / "claude_registry_release.json").read_text(
        encoding="utf-8"
    )
)


def _tar_bytes(files: dict[str, bytes]) -> bytes:
    output = io.BytesIO()
    with tarfile.open(fileobj=output, mode="w:gz") as archive:
        for name, body in files.items():
            info = tarfile.TarInfo(name)
            info.size = len(body)
            info.mode = 0o755 if name.endswith("/ink-claude-code-dream") else 0o644
            archive.addfile(info, io.BytesIO(body))
    return output.getvalue()


def _wheel_bytes(*, with_map: bool = False) -> bytes:
    output = io.BytesIO()
    with zipfile.ZipFile(output, "w") as archive:
        archive.writestr("claude_agent_sdk/__init__.py", "")
        archive.writestr(
            "ink_claude_dream_agent_sdk-9.8.7.dist-info/METADATA",
            "Metadata-Version: 2.1\nName: ink-claude-dream-agent-sdk\nVersion: 9.8.7\n",
        )
        if with_map:
            archive.writestr("claude_agent_sdk/assets/nested/debug.js.map", "{}")
    return output.getvalue()


def _pypi_fixture(wheel: bytes, sdist: bytes) -> tuple[dict[str, object], dict[str, bytes]]:
    sdk = FIXTURE["sdk"]
    wheel_url = f"https://files.pythonhosted.org/packages/test/{sdk['wheel']}"
    sdist_url = f"https://files.pythonhosted.org/packages/test/{sdk['sdist']}"
    metadata = {
        "info": {"name": sdk["name"], "version": sdk["version"]},
        "urls": [
            {
                "packagetype": "bdist_wheel",
                "filename": sdk["wheel"],
                "url": wheel_url,
                "digests": {"sha256": hashlib.sha256(wheel).hexdigest()},
            },
            {
                "packagetype": "sdist",
                "filename": sdk["sdist"],
                "url": sdist_url,
                "digests": {"sha256": hashlib.sha256(sdist).hexdigest()},
            },
        ],
    }
    metadata_url = acceptance.PYPI_JSON_TEMPLATE.format(
        name=sdk["name"], version=sdk["version"]
    )
    return metadata, {
        metadata_url: json.dumps(metadata).encode(),
        wheel_url: wheel,
        sdist_url: sdist,
    }


def test_pypi_exact_wheel_sdist_hash_and_zero_map(tmp_path: Path) -> None:
    wheel = _wheel_bytes()
    sdist = _tar_bytes({"ink-sdk-9.8.7/pyproject.toml": b"[project]\n"})
    _, responses = _pypi_fixture(wheel, sdist)

    receipt = acceptance.acquire_pypi_release(
        FIXTURE["sdk"]["version"], tmp_path, fetch=responses.__getitem__
    )

    assert set(receipt) == {"bdist_wheel", "sdist"}
    assert receipt["bdist_wheel"]["sha256"] == hashlib.sha256(wheel).hexdigest()
    assert receipt["sdist"]["sha256"] == hashlib.sha256(sdist).hexdigest()
    assert Path(receipt["bdist_wheel"]["path"]).is_file()


def test_pypi_nested_source_map_fails_closed(tmp_path: Path) -> None:
    wheel = _wheel_bytes(with_map=True)
    sdist = _tar_bytes({"ink-sdk-9.8.7/pyproject.toml": b"[project]\n"})
    _, responses = _pypi_fixture(wheel, sdist)

    with pytest.raises(acceptance.AcceptanceError) as caught:
        acceptance.acquire_pypi_release(
            FIXTURE["sdk"]["version"], tmp_path, fetch=responses.__getitem__
        )

    assert caught.value.code == "SOURCE_MAP_FORBIDDEN"
    assert caught.value.receipt()["safe"] is True


def _npm_tarball(package: str, version: str) -> bytes:
    manifest: dict[str, object] = {
        "name": package,
        "version": version,
        "license": "MIT",
        "publishConfig": {"access": "public", "provenance": True},
        "scripts": {"prepack": "node scripts/prepack.mjs"},
    }
    if package == acceptance.NPM_SELECTOR:
        manifest.update(
            {
                "bin": {
                    acceptance.CLI_COMMAND: f"bin/{acceptance.CLI_COMMAND}"
                },
                "optionalDependencies": {
                    platform_package: version
                    for platform_package in acceptance.NPM_PLATFORMS.values()
                },
            }
        )
    else:
        target = next(
            target
            for target, platform_package in acceptance.NPM_PLATFORMS.items()
            if platform_package == package
        )
        os_name, cpu = target.split("-", 1)
        manifest.update(
            {
                "os": [os_name],
                "cpu": [cpu],
                "dependencies": {"bun": acceptance.BUN_VERSION},
                "inkRuntime": {
                    "target": target,
                    "entrypoint": "runtime/bin/ink-claude-code-dream",
                    "ripgrepPath": "runtime/lib/core/vendor/rg",
                    "ripgrepSha256": "a" * 64,
                    "bunVersion": acceptance.BUN_VERSION,
                    "sourceMapsIncluded": False,
                },
            }
        )
    package_json = json.dumps(manifest).encode()
    return _tar_bytes(
        {
            "package/package.json": package_json,
            "package/bin/ink-claude-code-dream": b"#!/bin/sh\nexit 0\n",
        }
    )


def _integrity(body: bytes) -> str:
    return "sha512-" + base64.b64encode(hashlib.sha512(body).digest()).decode()


class FakeNpmRunner:
    def __init__(self, destination: Path) -> None:
        runtime = FIXTURE["runtime"]
        self.version = runtime["version"]
        self.packages = [runtime["selector"], *runtime["platforms"]]
        self.bodies = {package: _npm_tarball(package, self.version) for package in self.packages}
        self.destination = destination
        self.metadata: dict[str, dict[str, object]] = {}
        for package in self.packages:
            value: dict[str, object] = {
                "name": package,
                "version": self.version,
                "dist": {"integrity": _integrity(self.bodies[package])},
            }
            if package == runtime["selector"]:
                value["optionalDependencies"] = {
                    platform_package: self.version
                    for platform_package in runtime["platforms"]
                }
            elif package.endswith("darwin-arm64"):
                value.update({"os": ["darwin"], "cpu": ["arm64"]})
            elif package.endswith("darwin-x64"):
                value.update({"os": ["darwin"], "cpu": ["x64"]})
            elif package.endswith("linux-arm64"):
                value.update({"os": ["linux"], "cpu": ["arm64"]})
            else:
                value.update({"os": ["linux"], "cpu": ["x64"]})
            self.metadata[package] = value

    def __call__(self, argv, *, cwd, env, timeout=180.0):
        del cwd, env, timeout
        spec = argv[2]
        package, version = spec.rsplit("@", 1)
        assert version == self.version
        if argv[1] == "view":
            output = self.metadata[package]
        elif argv[1] == "pack":
            filename = package.removeprefix("@").replace("/", "-") + f"-{version}.tgz"
            (self.destination / filename).write_bytes(self.bodies[package])
            output = [
                {
                    "name": package,
                    "version": version,
                    "filename": filename,
                    "integrity": _integrity(self.bodies[package]),
                }
            ]
        else:  # pragma: no cover - guards fixture misuse
            raise AssertionError(argv)
        return subprocess.CompletedProcess(argv, 0, json.dumps(output), "")


def test_npm_exact_five_package_integrity_and_zero_map(tmp_path: Path) -> None:
    runner = FakeNpmRunner(tmp_path)

    receipt = acceptance.acquire_npm_release(
        FIXTURE["runtime"]["version"],
        tmp_path,
        target=FIXTURE["runtime"]["target"],
        env={"PATH": os.environ.get("PATH", "")},
        runner=runner,
    )

    assert set(receipt["packages"]) == {
        FIXTURE["runtime"]["selector"],
        *FIXTURE["runtime"]["platforms"],
    }
    assert receipt["currentPlatformPackage"].endswith("darwin-arm64")
    assert all(item["files"] == 2 for item in receipt["packages"].values())


def test_npm_selector_contract_rejects_inexact_platform_version() -> None:
    runner = FakeNpmRunner(Path("unused"))
    metadata = json.loads(json.dumps(runner.metadata))
    selector = FIXTURE["runtime"]["selector"]
    platform_package = FIXTURE["runtime"]["platforms"][0]
    metadata[selector]["optionalDependencies"][platform_package] = "latest"

    with pytest.raises(acceptance.AcceptanceError) as caught:
        acceptance.validate_npm_metadata_contract(
            metadata, FIXTURE["runtime"]["version"], FIXTURE["runtime"]["target"]
        )

    assert caught.value.code == "PACKAGE_SET_MISMATCH"


def test_npm_tarball_manifest_rejects_bun_and_runtime_drift() -> None:
    package = FIXTURE["runtime"]["platforms"][0]
    manifest = {
        "name": package,
        "version": FIXTURE["runtime"]["version"],
        "license": "MIT",
        "publishConfig": {"access": "public", "provenance": True},
        "scripts": {"prepack": "node scripts/prepack.mjs"},
        "os": ["darwin"],
        "cpu": ["arm64"],
        "dependencies": {"bun": "latest"},
        "inkRuntime": {},
    }

    with pytest.raises(acceptance.AcceptanceError) as caught:
        acceptance.validate_npm_tarball_manifest(
            manifest, package, FIXTURE["runtime"]["version"]
        )

    assert caught.value.code == "BUN_VERSION_MISMATCH"


@pytest.mark.parametrize(
    ("mutation", "code"),
    [
        ({"license": "UNLICENSED"}, "PUBLICATION_CONTRACT_MISMATCH"),
        ({"dependencies": {"unexpected": "1.0.0"}}, "PACKAGE_SET_MISMATCH"),
    ],
)
def test_selector_tarball_rejects_publication_or_dependency_drift(
    mutation: dict[str, object], code: str
) -> None:
    runtime = FIXTURE["runtime"]
    manifest: dict[str, object] = {
        "name": runtime["selector"],
        "version": runtime["version"],
        "license": "MIT",
        "publishConfig": {"access": "public", "provenance": True},
        "scripts": {"prepack": "node scripts/prepack.mjs"},
        "bin": {acceptance.CLI_COMMAND: f"bin/{acceptance.CLI_COMMAND}"},
        "optionalDependencies": {
            package: runtime["version"] for package in runtime["platforms"]
        },
    }
    manifest.update(mutation)

    with pytest.raises(acceptance.AcceptanceError) as caught:
        acceptance.validate_npm_tarball_manifest(
            manifest, runtime["selector"], runtime["version"]
        )

    assert caught.value.code == code


def test_npm_404_is_structured_and_redacts_tool_output(tmp_path: Path) -> None:
    def missing(argv, *, cwd, env, timeout=180.0):
        del cwd, env, timeout
        return subprocess.CompletedProcess(
            argv, 1, "", "npm ERR! E404 secret-token-should-not-escape"
        )

    with pytest.raises(acceptance.AcceptanceError) as caught:
        acceptance.npm_view(
            acceptance.NPM_SELECTOR,
            "404.0.0",
            cwd=tmp_path,
            env={},
            runner=missing,
        )

    payload = caught.value.receipt()
    assert payload["error"]["code"] == "REGISTRY_VERSION_NOT_FOUND"
    assert payload["error"]["http_status"] == 404
    assert "secret-token" not in json.dumps(payload)


def test_pypi_404_is_structured_without_network_or_url_leak(tmp_path: Path) -> None:
    failure = urllib.error.HTTPError(
        "https://pypi.org/private-query?token=must-not-leak",
        404,
        "not found",
        hdrs=None,
        fp=None,
    )
    with (
        mock.patch.object(acceptance.urllib.request, "urlopen", side_effect=failure),
        pytest.raises(acceptance.AcceptanceError) as caught,
    ):
        acceptance.acquire_pypi_release(FIXTURE["sdk"]["version"], tmp_path)

    payload = caught.value.receipt()
    assert payload["error"]["code"] == "REGISTRY_VERSION_NOT_FOUND"
    assert payload["error"]["version"] == FIXTURE["sdk"]["version"]
    assert "must-not-leak" not in json.dumps(payload)


def _fake_sdk_wheel(path: Path, version: str) -> Path:
    wheel = path / f"ink_claude_dream_agent_sdk-{version}-py3-none-any.whl"
    dist_info = f"ink_claude_dream_agent_sdk-{version}.dist-info"
    module = f"""
__version__ = {version!r}
class ClaudeAgentOptions:
    def __init__(self, *, cli_path=None):
        self.cli_path = cli_path
class ClaudeSDKClient:
    pass
async def query(*args, **kwargs):
    if False:
        yield None
"""
    with zipfile.ZipFile(wheel, "w") as archive:
        archive.writestr("claude_agent_sdk/__init__.py", module)
        archive.writestr(
            "claude_agent_sdk/_cli_version.py", "__cli_version__ = '2.1.241'\n"
        )
        archive.writestr(
            f"{dist_info}/METADATA",
            f"Metadata-Version: 2.1\nName: ink-claude-dream-agent-sdk\nVersion: {version}\n",
        )
        archive.writestr(
            f"{dist_info}/WHEEL",
            "Wheel-Version: 1.0\nGenerator: provider-free-fixture\nRoot-Is-Purelib: true\nTag: py3-none-any\n",
        )
        archive.writestr(f"{dist_info}/top_level.txt", "claude_agent_sdk\n")
        archive.writestr(f"{dist_info}/RECORD", "")
    return wheel


def test_isolated_install_owns_import_and_binds_cli_path(tmp_path: Path) -> None:
    version = FIXTURE["sdk"]["version"]
    wheel = _fake_sdk_wheel(tmp_path, version)
    cli = tmp_path / acceptance.CLI_COMMAND
    cli.write_text(f"#!/bin/sh\nprintf '%s\\n' '{FIXTURE['cliVersion']}'\n", encoding="utf-8")
    cli.chmod(0o700)
    home = tmp_path / "home"
    home.mkdir()
    env = acceptance._safe_environment(home)

    python = acceptance.create_sdk_venv(wheel, tmp_path, env=env)
    receipt = acceptance.probe_installed_contract(
        python,
        version,
        cli,
        FIXTURE["cliVersion"],
        root=tmp_path,
        env=env,
    )

    assert receipt["providers"] == [acceptance.PYPI_DISTRIBUTION]
    assert receipt["sdkVersion"] == version
    assert receipt["sdkCliCompatibility"] == "2.1.241"
    assert receipt["officialDistributionInstalled"] is False
    assert receipt["publicApi"] == list(acceptance.PUBLIC_API)
    assert receipt["cliPath"] == str(cli.resolve())
    assert receipt["cliVersion"] == FIXTURE["cliVersion"]


def test_main_prints_only_structured_safe_error(capsys) -> None:
    error = acceptance.AcceptanceError(
        "REGISTRY_VERSION_NOT_FOUND",
        "pypi-download",
        "requested PyPI release is unavailable",
        registry="pypi",
        package=acceptance.PYPI_DISTRIBUTION,
        version="9.8.7",
        http_status=404,
    )
    with mock.patch.object(acceptance, "run_acceptance", side_effect=error):
        exit_code = acceptance.main(
            [
                "--sdk-version",
                "9.8.7",
                "--runtime-version",
                "1.2.3",
                "--expected-cli-version",
                FIXTURE["cliVersion"],
            ]
        )

    payload = json.loads(capsys.readouterr().out)
    assert exit_code == 2
    assert payload["status"] == "failed"
    assert payload["safe"] is True
    assert payload["error"]["http_status"] == 404


def test_archive_rejects_absolute_link_and_device_members(tmp_path: Path) -> None:
    absolute = tmp_path / "absolute.tgz"
    absolute.write_bytes(_tar_bytes({"/package/package.json": b"{}"}))
    with pytest.raises(acceptance.AcceptanceError) as caught:
        acceptance.inspect_archive_without_source_maps(absolute, phase="test")
    assert caught.value.code == "UNSAFE_ARCHIVE_PATH"

    linked = tmp_path / "linked.tgz"
    output = io.BytesIO()
    with tarfile.open(fileobj=output, mode="w:gz") as archive:
        info = tarfile.TarInfo("package/link")
        info.type = tarfile.SYMTYPE
        info.linkname = "/outside"
        archive.addfile(info)
    linked.write_bytes(output.getvalue())
    with pytest.raises(acceptance.AcceptanceError) as caught:
        acceptance.inspect_archive_without_source_maps(linked, phase="test")
    assert caught.value.code == "UNSAFE_ARCHIVE_MEMBER"

    device = tmp_path / "device.tgz"
    output = io.BytesIO()
    with tarfile.open(fileobj=output, mode="w:gz") as archive:
        info = tarfile.TarInfo("package/device")
        info.type = tarfile.CHRTYPE
        archive.addfile(info)
    device.write_bytes(output.getvalue())
    with pytest.raises(acceptance.AcceptanceError) as caught:
        acceptance.inspect_archive_without_source_maps(device, phase="test")
    assert caught.value.code == "UNSAFE_ARCHIVE_MEMBER"


def test_zip_symlink_and_noncanonical_pypi_name_are_rejected(tmp_path: Path) -> None:
    linked = tmp_path / "linked.whl"
    with zipfile.ZipFile(linked, "w") as archive:
        info = zipfile.ZipInfo("claude_agent_sdk/link")
        info.create_system = 3
        info.external_attr = (0o120777 << 16)
        archive.writestr(info, "/outside")
    with pytest.raises(acceptance.AcceptanceError) as caught:
        acceptance.inspect_archive_without_source_maps(linked, phase="test")
    assert caught.value.code == "UNSAFE_ARCHIVE_MEMBER"

    wheel = _wheel_bytes()
    sdist = _tar_bytes({"ink-sdk-9.8.7/pyproject.toml": b"[project]\n"})
    metadata, responses = _pypi_fixture(wheel, sdist)
    metadata["urls"][0]["filename"] = "renamed.whl"
    metadata_url = acceptance.PYPI_JSON_TEMPLATE.format(
        name=FIXTURE["sdk"]["name"], version=FIXTURE["sdk"]["version"]
    )
    responses[metadata_url] = json.dumps(metadata).encode()
    with pytest.raises(acceptance.AcceptanceError) as caught:
        acceptance.acquire_pypi_release(
            FIXTURE["sdk"]["version"], tmp_path / "pypi", fetch=responses.__getitem__
        )
    assert caught.value.code == "ARTIFACT_NAME_MISMATCH"


def test_child_environment_strips_model_and_registry_tokens(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    sensitive = {
        "ANTHROPIC_API_KEY": "model-secret",
        "CLAUDE_CODE_OAUTH_TOKEN": "provider-secret",
        "NPM_TOKEN": "npm-secret",
        "NODE_AUTH_TOKEN": "npm-secret-2",
        "PYPI_API_TOKEN": "pypi-secret",
        "PIP_INDEX_URL": "https://token@example.invalid/simple",
    }
    for key, value in sensitive.items():
        monkeypatch.setenv(key, value)
    env = acceptance._safe_environment(tmp_path)

    assert not (set(sensitive) - {"PIP_INDEX_URL"}).intersection(env)
    assert env["PIP_INDEX_URL"] == acceptance.PYPI_SIMPLE
    assert "token" not in env["PIP_INDEX_URL"]
    assert env["PIP_CONFIG_FILE"] == os.devnull
    assert env["NPM_CONFIG_USERCONFIG"] == os.devnull
    assert env["NPM_CONFIG_REGISTRY"] == acceptance.NPM_REGISTRY


def test_npm_install_allows_real_postinstall_before_cli_probe(tmp_path: Path) -> None:
    selector = tmp_path / "selector.tgz"
    native = tmp_path / "native.tgz"
    selector.write_bytes(b"selector")
    native.write_bytes(b"native")
    target = FIXTURE["runtime"]["target"]
    platform_package = acceptance.NPM_PLATFORMS[target]

    def install(argv, *, cwd, env, timeout=180.0):
        del env, timeout
        assert argv[:2] == ["npm", "install"]
        assert "--ignore-scripts" not in argv
        assert "--omit=optional" in argv
        executable = cwd / "node_modules" / ".bin" / acceptance.CLI_COMMAND
        executable.parent.mkdir(parents=True)
        executable.write_text("#!/bin/sh\nexit 0\n", encoding="utf-8")
        executable.chmod(0o700)
        return subprocess.CompletedProcess(argv, 0, "", "")

    executable = acceptance.install_npm_runtime(
        {
            "paths": {
                acceptance.NPM_SELECTOR: selector,
                platform_package: native,
            },
            "currentPlatformPackage": platform_package,
        },
        tmp_path,
        env={},
        runner=install,
    )
    assert executable.name == acceptance.CLI_COMMAND

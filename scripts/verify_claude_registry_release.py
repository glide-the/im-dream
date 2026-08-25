# [Input] Exact SDK/Runtime/CLI versions plus public PyPI and npm registry metadata.
# [Output] A structured, provider-free release receipt or a redacted fail-closed error.
# [Pos] Post-publication acceptance harness for the custom Claude SDK and Runtime.
# [Sync] 2026-08-24: verify exact wheel/sdist and five npm packages, source-map
#        absence, isolated install ownership, SDK cli_path, and CLI version.
# [Sync] 2026-08-26: require source-only sdist installation, full npm evidence,
#        selector-to-four-tarball bindings, and both supported CLI aliases.

"""Accept an already-published Dream Claude SDK/Runtime registry release.

The harness never invokes an Agent query and deliberately removes model/provider
credentials from every child process.  It is intended to run only after both
registries contain the exact requested immutable versions.
"""

from __future__ import annotations

import argparse
import base64
import email.parser
import email.policy
import hashlib
import io
import json
import os
import platform
import re
import stat
import subprocess
import sys
import tarfile
import tempfile
import urllib.error
import urllib.parse
import urllib.request
import zipfile
from pathlib import Path, PurePosixPath
from typing import Any, Callable, Iterable, Mapping, Sequence


PYPI_DISTRIBUTION = "ink-claude-dream-agent-sdk"
PYTHON_IMPORT = "claude_agent_sdk"
NPM_SELECTOR = "@glide-the/ink-claude-code-dream"
CLI_COMMAND = "ink-claude-code-dream"
CLI_ALIASES = (CLI_COMMAND, "claude")
NPM_PLATFORMS = {
    "darwin-arm64": f"{NPM_SELECTOR}-darwin-arm64",
    "darwin-x64": f"{NPM_SELECTOR}-darwin-x64",
    "linux-arm64": f"{NPM_SELECTOR}-linux-arm64",
    "linux-x64": f"{NPM_SELECTOR}-linux-x64",
}
NPM_RIPGREP_PATHS = {
    target: f"runtime/lib/core/chunks/vendor/ripgrep/{target.split('-', 1)[1]}-{target.split('-', 1)[0]}/rg"
    for target in NPM_PLATFORMS
}
REQUIRED_RUNTIME_CAPABILITIES = {
    "extensions.plugins",
    "lifecycle.cancel",
    "mcp.http",
    "mcp.management.identity",
    "mcp.oauth",
    "mcp.stdio",
    "protocol.control.bidirectional",
    "protocol.streaming",
    "sandbox",
    "session.resume",
    "tmpdir.thread-local",
    "transcript.jsonl",
    "workspace.cwd",
}
PUBLIC_API = ("ClaudeAgentOptions", "ClaudeSDKClient", "query")
PYPI_JSON_TEMPLATE = "https://pypi.org/pypi/{name}/{version}/json"
PYPI_FILE_HOST = "files.pythonhosted.org"
PYPI_SIMPLE = "https://pypi.org/simple"
NPM_REGISTRY = "https://registry.npmjs.org"
BUN_VERSION = "1.4.0"
NPM_REPOSITORY = "glide-the/ink-claude-code-dream"
SAFE_VERSION = re.compile(r"^[0-9A-Za-z][0-9A-Za-z._+-]*$")


class AcceptanceError(RuntimeError):
    """A redacted, machine-readable acceptance failure."""

    def __init__(
        self,
        code: str,
        phase: str,
        message: str,
        *,
        registry: str | None = None,
        package: str | None = None,
        version: str | None = None,
        http_status: int | None = None,
    ) -> None:
        super().__init__(message)
        self.code = code
        self.phase = phase
        self.safe_message = message
        self.registry = registry
        self.package = package
        self.version = version
        self.http_status = http_status

    def receipt(self) -> dict[str, Any]:
        error: dict[str, Any] = {
            "code": self.code,
            "phase": self.phase,
            "message": self.safe_message,
        }
        for key in ("registry", "package", "version", "http_status"):
            value = getattr(self, key)
            if value is not None:
                error[key] = value
        return {
            "schemaVersion": "ink-claude-registry-acceptance-error/v1",
            "status": "failed",
            "safe": True,
            "error": error,
        }


def _require_safe_version(value: str, label: str) -> str:
    if not SAFE_VERSION.fullmatch(value):
        raise AcceptanceError(
            "INVALID_INPUT",
            "input",
            f"{label} must be one exact registry version",
            version=value,
        )
    return value


def _normalise_distribution(value: str) -> str:
    return re.sub(r"[-_.]+", "-", value).lower()


def _json_object(raw: str | bytes, *, phase: str) -> dict[str, Any]:
    try:
        value = json.loads(raw)
    except (json.JSONDecodeError, UnicodeDecodeError) as exc:
        raise AcceptanceError(
            "INVALID_REGISTRY_RESPONSE", phase, "registry returned invalid JSON"
        ) from exc
    if not isinstance(value, dict):
        raise AcceptanceError(
            "INVALID_REGISTRY_RESPONSE", phase, "registry JSON must be an object"
        )
    return value


def _fetch_public_bytes(url: str, *, timeout: float = 60.0) -> bytes:
    request = urllib.request.Request(
        url,
        headers={"User-Agent": "ink-dream-registry-acceptance/1"},
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            return response.read()
    except urllib.error.HTTPError as exc:
        code = "REGISTRY_VERSION_NOT_FOUND" if exc.code == 404 else "REGISTRY_UNAVAILABLE"
        raise AcceptanceError(
            code,
            "pypi-download",
            "requested PyPI release is unavailable",
            registry="pypi",
            package=PYPI_DISTRIBUTION,
            http_status=exc.code,
        ) from None
    except (urllib.error.URLError, TimeoutError):
        raise AcceptanceError(
            "REGISTRY_UNAVAILABLE",
            "pypi-download",
            "PyPI could not be reached safely",
            registry="pypi",
            package=PYPI_DISTRIBUTION,
        ) from None


def _ensure_pypi_file_url(url: str, version: str) -> None:
    parsed = urllib.parse.urlsplit(url)
    if parsed.scheme != "https" or parsed.hostname != PYPI_FILE_HOST:
        raise AcceptanceError(
            "UNTRUSTED_ARTIFACT_URL",
            "pypi-metadata",
            "PyPI metadata referenced an untrusted artifact host",
            registry="pypi",
            package=PYPI_DISTRIBUTION,
            version=version,
        )


def _has_source_map(names: Iterable[str]) -> str | None:
    for name in names:
        path = PurePosixPath(name.replace("\\", "/"))
        if path.is_absolute() or any(part in {"", ".", ".."} for part in path.parts):
            raise AcceptanceError(
                "UNSAFE_ARCHIVE_PATH",
                "artifact-inspection",
                "release archive contains an unsafe path",
            )
        if path.name.lower().endswith(".map"):
            return str(path)
    return None


def inspect_archive_without_source_maps(path: Path, *, phase: str) -> int:
    try:
        if zipfile.is_zipfile(path):
            with zipfile.ZipFile(path) as archive:
                infos = archive.infolist()
                names = [info.filename for info in infos]
                if any(
                    (info.external_attr >> 16)
                    and stat.S_ISLNK(info.external_attr >> 16)
                    for info in infos
                ):
                    raise AcceptanceError(
                        "UNSAFE_ARCHIVE_MEMBER",
                        phase,
                        "release archive contains a symbolic link",
                    )
        elif tarfile.is_tarfile(path):
            with tarfile.open(path, "r:*") as archive:
                members = archive.getmembers()
                names = [member.name for member in members]
                if any(
                    member.issym()
                    or member.islnk()
                    or member.isdev()
                    or member.isfifo()
                    for member in members
                ):
                    raise AcceptanceError(
                        "UNSAFE_ARCHIVE_MEMBER",
                        phase,
                        "release archive contains a link or device member",
                    )
        else:
            raise AcceptanceError(
                "INVALID_ARCHIVE", phase, "downloaded release is not a supported archive"
            )
    except (OSError, tarfile.TarError, zipfile.BadZipFile) as exc:
        raise AcceptanceError(
            "INVALID_ARCHIVE", phase, "downloaded release archive is unreadable"
        ) from exc
    mapped = _has_source_map(names)
    if mapped is not None:
        raise AcceptanceError(
            "SOURCE_MAP_FORBIDDEN", phase, "release archive contains a source map"
        )
    return len(names)


def validate_sdk_sdist(path: Path, version: str) -> None:
    """Validate canonical source-distribution identity before installation."""

    expected_root = f"ink_claude_dream_agent_sdk-{version}"
    try:
        with tarfile.open(path, "r:*") as archive:
            regular = {
                member.name: member
                for member in archive.getmembers()
                if member.isfile()
            }
            roots = {PurePosixPath(name).parts[0] for name in regular}
            if roots != {expected_root}:
                raise AcceptanceError(
                    "SDIST_STRUCTURE_MISMATCH",
                    "pypi-artifact",
                    "SDK sdist must have one canonical release root",
                )
            pkg_info_name = f"{expected_root}/PKG-INFO"
            pyproject_name = f"{expected_root}/pyproject.toml"
            if pkg_info_name not in regular or pyproject_name not in regular:
                raise AcceptanceError(
                    "SDIST_STRUCTURE_MISMATCH",
                    "pypi-artifact",
                    "SDK sdist is missing PKG-INFO or pyproject.toml",
                )
            pkg_stream = archive.extractfile(regular[pkg_info_name])
            if pkg_stream is None:
                raise AcceptanceError(
                    "SDIST_STRUCTURE_MISMATCH", "pypi-artifact", "SDK PKG-INFO is unreadable"
                )
            metadata = email.parser.BytesParser(policy=email.policy.default).parsebytes(
                pkg_stream.read()
            )
            if (
                _normalise_distribution(str(metadata.get("Name", "")))
                != _normalise_distribution(PYPI_DISTRIBUTION)
                or metadata.get("Version") != version
            ):
                raise AcceptanceError(
                    "VERSION_MISMATCH",
                    "pypi-artifact",
                    "SDK sdist PKG-INFO identity does not match the requested release",
                )
    except (OSError, tarfile.TarError) as exc:
        raise AcceptanceError(
            "INVALID_ARCHIVE", "pypi-artifact", "SDK sdist is unreadable"
        ) from exc


def acquire_pypi_release(
    version: str,
    destination: Path,
    *,
    fetch: Callable[[str], bytes] = _fetch_public_bytes,
) -> dict[str, Any]:
    """Download and authenticate one exact wheel plus one exact sdist."""

    version = _require_safe_version(version, "SDK version")
    metadata_url = PYPI_JSON_TEMPLATE.format(name=PYPI_DISTRIBUTION, version=version)
    try:
        metadata = _json_object(fetch(metadata_url), phase="pypi-metadata")
    except AcceptanceError as exc:
        if exc.version is None:
            exc.version = version
        raise
    info = metadata.get("info")
    urls = metadata.get("urls")
    if not isinstance(info, dict) or not isinstance(urls, list):
        raise AcceptanceError(
            "INVALID_REGISTRY_RESPONSE",
            "pypi-metadata",
            "PyPI release metadata is incomplete",
            registry="pypi",
            package=PYPI_DISTRIBUTION,
            version=version,
        )
    if (
        _normalise_distribution(str(info.get("name", "")))
        != _normalise_distribution(PYPI_DISTRIBUTION)
        or info.get("version") != version
    ):
        raise AcceptanceError(
            "VERSION_MISMATCH",
            "pypi-metadata",
            "PyPI returned a different package identity or version",
            registry="pypi",
            package=PYPI_DISTRIBUTION,
            version=version,
        )

    selected: dict[str, dict[str, Any]] = {}
    for kind in ("bdist_wheel", "sdist"):
        candidates = [item for item in urls if isinstance(item, dict) and item.get("packagetype") == kind]
        if len(candidates) != 1:
            raise AcceptanceError(
                "ARTIFACT_SET_MISMATCH",
                "pypi-metadata",
                "PyPI must expose exactly one wheel and one sdist",
                registry="pypi",
                package=PYPI_DISTRIBUTION,
                version=version,
            )
        selected[kind] = candidates[0]

    destination.mkdir(parents=True, exist_ok=True)
    receipt: dict[str, Any] = {}
    expected_filenames = {
        "bdist_wheel": f"ink_claude_dream_agent_sdk-{version}-py3-none-any.whl",
        "sdist": f"ink_claude_dream_agent_sdk-{version}.tar.gz",
    }
    for kind, item in selected.items():
        filename = item.get("filename")
        url = item.get("url")
        digest = item.get("digests", {}).get("sha256") if isinstance(item.get("digests"), dict) else None
        if not isinstance(filename, str) or Path(filename).name != filename:
            raise AcceptanceError("INVALID_ARTIFACT_NAME", "pypi-metadata", "PyPI artifact filename is unsafe")
        if filename != expected_filenames[kind]:
            raise AcceptanceError(
                "ARTIFACT_NAME_MISMATCH",
                "pypi-metadata",
                "PyPI artifact filename is not the canonical SDK release name",
                registry="pypi",
                package=PYPI_DISTRIBUTION,
                version=version,
            )
        if not isinstance(url, str) or not isinstance(digest, str) or not re.fullmatch(r"[0-9a-f]{64}", digest):
            raise AcceptanceError("INVALID_REGISTRY_RESPONSE", "pypi-metadata", "PyPI artifact digest metadata is invalid")
        _ensure_pypi_file_url(url, version)
        body = fetch(url)
        actual = hashlib.sha256(body).hexdigest()
        if actual != digest:
            raise AcceptanceError(
                "HASH_MISMATCH", "pypi-artifact", "PyPI artifact SHA-256 does not match metadata"
            )
        output = destination / filename
        output.write_bytes(body)
        file_count = inspect_archive_without_source_maps(output, phase="pypi-artifact")
        if kind == "sdist":
            validate_sdk_sdist(output, version)
        receipt[kind] = {
            "filename": filename,
            "sha256": actual,
            "bytes": len(body),
            "files": file_count,
            "path": str(output),
        }
    return receipt


def _safe_environment(home: Path) -> dict[str, str]:
    allowed = {
        "PATH",
        "LANG",
        "LC_ALL",
        "HTTP_PROXY",
        "HTTPS_PROXY",
        "NO_PROXY",
        "ALL_PROXY",
        "SSL_CERT_FILE",
        "REQUESTS_CA_BUNDLE",
        "SYSTEMROOT",
        "COMSPEC",
        "PATHEXT",
    }
    env = {key: value for key, value in os.environ.items() if key.upper() in allowed}
    env.update(
        {
            "HOME": str(home),
            "PIP_DISABLE_PIP_VERSION_CHECK": "1",
            "PIP_NO_INPUT": "1",
            "PIP_CONFIG_FILE": os.devnull,
            "PIP_INDEX_URL": PYPI_SIMPLE,
            "NPM_CONFIG_USERCONFIG": os.devnull,
            "NPM_CONFIG_REGISTRY": NPM_REGISTRY,
            "NPM_CONFIG_ALWAYS_AUTH": "false",
            "NPM_CONFIG_UPDATE_NOTIFIER": "false",
        }
    )
    return env


def run_command(
    argv: Sequence[str],
    *,
    cwd: Path,
    env: Mapping[str, str],
    timeout: float = 180.0,
) -> subprocess.CompletedProcess[str]:
    try:
        return subprocess.run(
            list(argv),
            cwd=cwd,
            env=dict(env),
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=timeout,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise AcceptanceError(
            "TOOL_UNAVAILABLE", "local-tool", "required local packaging tool failed safely"
        ) from exc


def _npm_json_command(
    argv: Sequence[str],
    *,
    phase: str,
    package: str,
    version: str,
    cwd: Path,
    env: Mapping[str, str],
    runner: Callable[..., subprocess.CompletedProcess[str]] = run_command,
) -> Any:
    result = runner(argv, cwd=cwd, env=env)
    if result.returncode != 0:
        missing = "E404" in result.stderr or "E404" in result.stdout
        raise AcceptanceError(
            "REGISTRY_VERSION_NOT_FOUND" if missing else "REGISTRY_UNAVAILABLE",
            phase,
            "requested npm release is unavailable",
            registry="npm",
            package=package,
            version=version,
            http_status=404 if missing else None,
        )
    try:
        return json.loads(result.stdout)
    except json.JSONDecodeError as exc:
        raise AcceptanceError(
            "INVALID_REGISTRY_RESPONSE", phase, "npm returned invalid JSON",
            registry="npm", package=package, version=version,
        ) from exc


def npm_view(
    package: str,
    version: str,
    *,
    cwd: Path,
    env: Mapping[str, str],
    runner: Callable[..., subprocess.CompletedProcess[str]] = run_command,
) -> dict[str, Any]:
    value = _npm_json_command(
        ["npm", "view", f"{package}@{version}", "--json", "--registry", NPM_REGISTRY],
        phase="npm-metadata",
        package=package,
        version=version,
        cwd=cwd,
        env=env,
        runner=runner,
    )
    if not isinstance(value, dict):
        raise AcceptanceError("INVALID_REGISTRY_RESPONSE", "npm-metadata", "npm metadata must be an object")
    return value


def host_runtime_target() -> str:
    os_name = {"Darwin": "darwin", "Linux": "linux"}.get(platform.system())
    cpu = {
        "arm64": "arm64",
        "aarch64": "arm64",
        "x86_64": "x64",
        "amd64": "x64",
    }.get(platform.machine().lower())
    target = f"{os_name}-{cpu}" if os_name and cpu else "unsupported"
    if target not in NPM_PLATFORMS:
        raise AcceptanceError(
            "UNSUPPORTED_PLATFORM", "platform", "host is outside the four-package Runtime contract"
        )
    return target


def validate_npm_metadata_contract(
    metadata: Mapping[str, Mapping[str, Any]], version: str, target: str
) -> None:
    expected = {NPM_SELECTOR, *NPM_PLATFORMS.values()}
    if set(metadata) != expected:
        raise AcceptanceError("PACKAGE_SET_MISMATCH", "npm-metadata", "npm package set is not the exact five-package contract")
    for package, value in metadata.items():
        integrity = value.get("dist", {}).get("integrity") if isinstance(value.get("dist"), dict) else None
        if value.get("name") != package or value.get("version") != version:
            raise AcceptanceError("VERSION_MISMATCH", "npm-metadata", "npm returned a different package identity or version")
        if not isinstance(integrity, str) or not integrity.startswith("sha512-"):
            raise AcceptanceError("INVALID_INTEGRITY", "npm-metadata", "npm package has no SHA-512 integrity")
    optional = metadata[NPM_SELECTOR].get("optionalDependencies")
    if optional != {package: version for package in NPM_PLATFORMS.values()}:
        raise AcceptanceError("PACKAGE_SET_MISMATCH", "npm-metadata", "selector optionalDependencies are not the exact four-platform contract")
    platform_meta = metadata[NPM_PLATFORMS[target]]
    expected_os, expected_cpu = target.split("-", 1)
    if expected_os not in _as_list(platform_meta.get("os")) or expected_cpu not in _as_list(platform_meta.get("cpu")):
        raise AcceptanceError("PLATFORM_MISMATCH", "npm-metadata", "current platform package metadata does not match the host")


def _as_list(value: Any) -> list[str]:
    if isinstance(value, str):
        return [value]
    if isinstance(value, list) and all(isinstance(item, str) for item in value):
        return value
    return []


def _sha512_integrity(body: bytes) -> str:
    digest = base64.b64encode(hashlib.sha512(body).digest()).decode("ascii")
    return f"sha512-{digest}"


def read_npm_package_manifest(tarball: Path) -> dict[str, Any]:
    """Read the authenticated package manifest without extracting the tgz."""

    try:
        with tarfile.open(tarball, "r:gz") as archive:
            matches = [
                member
                for member in archive.getmembers()
                if member.name == "package/package.json"
            ]
            if len(matches) != 1 or not matches[0].isfile() or matches[0].size > 1024 * 1024:
                raise AcceptanceError(
                    "NPM_MANIFEST_INVALID",
                    "npm-artifact",
                    "npm tarball must contain one bounded regular package.json",
                )
            stream = archive.extractfile(matches[0])
            if stream is None:
                raise AcceptanceError(
                    "NPM_MANIFEST_INVALID",
                    "npm-artifact",
                    "npm package.json could not be read safely",
                )
            return _json_object(stream.read(), phase="npm-artifact")
    except (OSError, tarfile.TarError) as exc:
        raise AcceptanceError(
            "INVALID_ARCHIVE", "npm-artifact", "npm release archive is unreadable"
        ) from exc


def _npm_tarball_files(tarball: Path) -> tuple[dict[str, bytes], str]:
    body = tarball.read_bytes()
    files: dict[str, bytes] = {}
    try:
        with tarfile.open(fileobj=io.BytesIO(body), mode="r:gz") as archive:
            for member in archive.getmembers():
                if not member.isfile():
                    continue
                if member.name in files:
                    raise AcceptanceError(
                        "UNSAFE_ARCHIVE_MEMBER", "npm-artifact", "npm tarball has a duplicate file"
                    )
                stream = archive.extractfile(member)
                if stream is None:
                    raise AcceptanceError(
                        "INVALID_ARCHIVE", "npm-artifact", "npm tarball file is unreadable"
                    )
                files[member.name] = stream.read()
    except (OSError, tarfile.TarError) as exc:
        raise AcceptanceError(
            "INVALID_ARCHIVE", "npm-artifact", "npm release archive is unreadable"
        ) from exc
    return files, hashlib.sha256(body).hexdigest()


def _npm_json_file(files: Mapping[str, bytes], name: str) -> dict[str, Any]:
    body = files.get(f"package/{name}")
    if body is None:
        raise AcceptanceError(
            "RUNTIME_EVIDENCE_MISSING", "npm-artifact", f"npm tarball is missing {name}"
        )
    return _json_object(body, phase="npm-artifact")


def _verify_cleanroom_npm_release_tarballs(
    paths: Mapping[str, Path], version: str
) -> dict[str, dict[str, Any]]:
    """Verify the current standalone clean-room selector/platform contract."""

    summaries: dict[str, dict[str, Any]] = {}
    expected_platforms: dict[str, Any] | None = None
    business_receipt: str | None = None
    for package, tarball in paths.items():
        files, tarball_sha256 = _npm_tarball_files(tarball)
        manifest = _npm_json_file(files, "package.json")
        attestation = _npm_json_file(files, "npm-publication-attestation.json")
        validate_npm_tarball_manifest(manifest, package, version)
        receipt = attestation.get("businessAcceptanceReceiptSha256")
        entrypoint_sha = attestation.get("entrypointSha256")
        if (
            attestation.get("repository") != NPM_REPOSITORY
            or attestation.get("version") != version
            or attestation.get("productionEligible") is not True
            or attestation.get("publicationAllowed") is not True
            or attestation.get("redistributionAllowed") is not True
            or attestation.get("sourceMapsIncluded") is not False
            or not isinstance(receipt, str)
            or not re.fullmatch(r"[0-9a-f]{64}", receipt)
            or not isinstance(entrypoint_sha, str)
            or not re.fullmatch(r"[0-9a-f]{64}", entrypoint_sha)
        ):
            raise AcceptanceError(
                "PUBLICATION_ATTESTATION_MISMATCH",
                "npm-artifact",
                "clean-room npm publication attestation is invalid",
            )
        if business_receipt is None:
            business_receipt = receipt
        elif business_receipt != receipt:
            raise AcceptanceError(
                "PUBLICATION_ATTESTATION_MISMATCH",
                "npm-artifact",
                "clean-room npm packages do not share one business receipt",
            )

        if package == NPM_SELECTOR:
            prefix = "package/"
            runtime_meta = _npm_json_file(files, "runtime-manifest.json")
            release = _npm_json_file(files, "release-manifest.json")
            artifact = _npm_json_file(files, "manifest/artifact-manifest.json")
            capabilities = _npm_json_file(files, "manifest/capabilities.json")
            entrypoint = "bin/ink-claude-code-dream"
            expected_schema = "ink-cleanroom-npm-meta-publication-attestation/v1"
            expected_platforms = artifact.get("platforms")
            expected_optional = {
                platform_package: version
                for platform_package in NPM_PLATFORMS.values()
            }
            if (
                runtime_meta.get("schemaVersion") != "ink-cleanroom-npm-meta/v1"
                or runtime_meta.get("selector") != entrypoint
                or runtime_meta.get("sourcemap") != "none"
                or runtime_meta.get("commands") != ["claude", CLI_COMMAND]
                or runtime_meta.get("optionalDependencies") != expected_optional
                or runtime_meta.get("supportedTargets") != list(NPM_PLATFORMS)
                or not isinstance(expected_platforms, dict)
            ):
                raise AcceptanceError(
                    "RUNTIME_BINDING_MISMATCH",
                    "npm-artifact",
                    "selector Runtime manifest is incomplete or inconsistent",
                )
        else:
            prefix = "package/runtime/"
            runtime_meta = _npm_json_file(files, "runtime-manifest.json")
            release = _npm_json_file(files, "runtime/release-manifest.json")
            artifact = _npm_json_file(files, "runtime/manifest/artifact-manifest.json")
            capabilities = _npm_json_file(files, "runtime/manifest/capabilities.json")
            entrypoint = "runtime/bin/ink-claude-code-dream"
            expected_schema = "ink-cleanroom-npm-platform-publication-attestation/v1"

        entrypoint_body = files.get(f"package/{entrypoint}")
        checksums = files.get("package/SHA256SUMS")
        capabilities_body = files.get(f"{prefix}manifest/capabilities.json")
        if entrypoint_body is None or checksums is None or capabilities_body is None:
            raise AcceptanceError(
                "RUNTIME_EVIDENCE_MISSING",
                "npm-artifact",
                "clean-room npm tarball is missing executable or checksum evidence",
            )
        actual_entrypoint_sha = hashlib.sha256(entrypoint_body).hexdigest()
        actual_capabilities_sha = hashlib.sha256(capabilities_body).hexdigest()
        capability_ids = {
            item.get("id")
            for item in capabilities.get("capabilities", [])
            if isinstance(item, dict)
        }
        release_runtime = release.get("runtime", {})
        release_status = release.get("status", {})
        artifact_record = artifact.get("artifact", {})
        if (
            attestation.get("schemaVersion") != expected_schema
            or attestation.get("entrypointSha256") != actual_entrypoint_sha
            or checksums.decode("utf-8", errors="strict").strip()
            != f"{actual_entrypoint_sha}  {entrypoint}"
            or artifact.get("schemaVersion") != "ink-cleanroom-artifact-manifest/v1"
            or artifact.get("capabilitiesSha256") != actual_capabilities_sha
            or artifact_record.get("entrypointSha256") != actual_entrypoint_sha
            or artifact_record.get("productionEligible") is not True
            or artifact_record.get("publicationAllowed") is not True
            or artifact_record.get("redistributionAllowed") is not True
            or release.get("schemaVersion") != "ink-claude-cli-envelope/v1"
            or release.get("core", {}).get("entrypointSha256") != actual_entrypoint_sha
            or release.get("core", {}).get("productionEligible") is not True
            or release_runtime.get("version") != version
            or release_runtime.get("integration", {}).get("sdkVersion") is None
            or release_status
            != {
                "productionEligible": True,
                "publicationAllowed": True,
                "redistributionAllowed": True,
            }
            or capability_ids != REQUIRED_RUNTIME_CAPABILITIES
        ):
            raise AcceptanceError(
                "RUNTIME_EVIDENCE_MISMATCH",
                "npm-artifact",
                "clean-room Runtime evidence is not bound to its executable",
            )

        summary: dict[str, Any] = {
            "package": package,
            "version": version,
            "tarballSha256": tarball_sha256,
            "entrypointSha256": actual_entrypoint_sha,
        }
        if package != NPM_SELECTOR:
            target = next(key for key, value in NPM_PLATFORMS.items() if value == package)
            os_name, cpu = target.split("-", 1)
            runtime_record = runtime_meta.get("runtime", {})
            if (
                runtime_meta.get("schemaVersion") != "ink-cleanroom-npm-platform/v1"
                or runtime_meta.get("package")
                != {"license": "MIT", "name": package, "version": version}
                or runtime_record.get("target") != target
                or runtime_record.get("os") != os_name
                or runtime_record.get("cpu") != cpu
                or runtime_record.get("bunVersion") != BUN_VERSION
                or runtime_record.get("executable") != entrypoint
                or runtime_record.get("sha256") != actual_entrypoint_sha
                or runtime_record.get("sourcemap") != "none"
                or release.get("core", {}).get("runtimeTarget") != target
                or artifact_record.get("runtimeTarget") != target
                or capabilities.get("runtime", {}).get("runtimeTarget") != target
                or attestation.get("runtimeTarget") != target
            ):
                raise AcceptanceError(
                    "RUNTIME_BINDING_MISMATCH",
                    "npm-artifact",
                    "platform Runtime target binding is incomplete or inconsistent",
                )
            summary["target"] = target
        summaries[package] = summary

    if expected_platforms is None or set(expected_platforms) != set(NPM_PLATFORMS):
        raise AcceptanceError(
            "META_BINDING_MISMATCH",
            "npm-artifact",
            "selector artifact manifest does not bind all Runtime targets",
        )
    for target, platform_package in NPM_PLATFORMS.items():
        if expected_platforms.get(target) != {
            "executableSha256": summaries[platform_package]["entrypointSha256"],
            "package": platform_package,
        }:
            raise AcceptanceError(
                "META_BINDING_MISMATCH",
                "npm-artifact",
                "selector artifact manifest does not bind the platform executable",
            )
    return summaries


def verify_npm_release_tarballs(
    paths: Mapping[str, Path], version: str
) -> dict[str, dict[str, Any]]:
    """Verify platform evidence and the selector's exact four-tarball binding."""

    attestation_schemas = {
        _npm_json_file(_npm_tarball_files(tarball)[0], "npm-publication-attestation.json").get("schemaVersion")
        for tarball in paths.values()
    }
    cleanroom_schemas = {
        "ink-cleanroom-npm-meta-publication-attestation/v1",
        "ink-cleanroom-npm-platform-publication-attestation/v1",
    }
    if attestation_schemas == cleanroom_schemas:
        return _verify_cleanroom_npm_release_tarballs(paths, version)

    summaries: dict[str, dict[str, Any]] = {}
    meta_attestation: dict[str, Any] | None = None
    common_policy_digest: str | None = None
    for package, tarball in paths.items():
        files, tarball_sha256 = _npm_tarball_files(tarball)
        manifest = _npm_json_file(files, "package.json")
        attestation = _npm_json_file(files, "npm-publication-attestation.json")
        validate_npm_tarball_manifest(manifest, package, version)
        policy_digest = attestation.get("npmReleasePolicySha256")
        if (
            attestation.get("repository") != NPM_REPOSITORY
            or attestation.get("version") != version
            or attestation.get("productionEligible") is not True
            or attestation.get("publicationAllowed") is not True
            or attestation.get("redistributionAllowed") is not True
            or attestation.get("sourceMapsIncluded") is not False
            or not isinstance(policy_digest, str)
            or not re.fullmatch(r"[0-9a-f]{64}", policy_digest)
        ):
            raise AcceptanceError(
                "PUBLICATION_ATTESTATION_MISMATCH",
                "npm-artifact",
                "npm publication attestation common contract is invalid",
            )
        if common_policy_digest is None:
            common_policy_digest = policy_digest
        elif policy_digest != common_policy_digest:
            raise AcceptanceError(
                "PUBLICATION_ATTESTATION_MISMATCH",
                "npm-artifact",
                "npm packages do not share one release policy digest",
            )
        if package == NPM_SELECTOR:
            if (
                attestation.get("schemaVersion")
                != "ink-npm-meta-publication-attestation/v1"
                or "runtimeTarget" in attestation
            ):
                raise AcceptanceError(
                    "PUBLICATION_ATTESTATION_MISMATCH",
                    "npm-artifact",
                    "selector publication attestation is invalid",
                )
            meta_attestation = attestation
            summaries[package] = {"tarballSha256": tarball_sha256}
            continue

        target = next(key for key, value in NPM_PLATFORMS.items() if value == package)
        ink_runtime = manifest["inkRuntime"]
        release = _npm_json_file(files, "runtime/release-manifest.json")
        artifact = _npm_json_file(files, "runtime/manifest/artifact-manifest.json")
        core = _npm_json_file(files, "runtime/manifest/core-build-receipt.json")
        qualification = files.get("package/runtime/manifest/qualification-summary.json")
        ripgrep = files.get(f"package/{ink_runtime['ripgrepPath']}")
        if qualification is None or ripgrep is None:
            raise AcceptanceError(
                "RUNTIME_EVIDENCE_MISSING",
                "npm-artifact",
                "platform tarball is missing qualification summary or ripgrep",
            )
        qualification_sha = hashlib.sha256(qualification).hexdigest()
        ripgrep_sha = hashlib.sha256(ripgrep).hexdigest()
        artifact_record = artifact.get("artifact", {})
        if (
            attestation.get("schemaVersion")
            != "ink-npm-platform-publication-attestation/v1"
            or attestation.get("runtimeTarget") != target
            or release.get("core", {}).get("runtimeTarget") != target
            or artifact_record.get("runtimeTarget") != target
            or core.get("runtimeTarget") != target
            or release.get("status", {}).get("productionEligible") is not True
            or release.get("status", {}).get("publicationAllowed") is not True
            or release.get("status", {}).get("redistributionAllowed") is not True
            or artifact_record.get("productionEligible") is not True
            or artifact_record.get("publicationAllowed") is not True
            or artifact_record.get("redistributionAllowed") is not True
            or attestation.get("coreBundleSha256") != artifact.get("coreBundleSha256")
            or attestation.get("payloadTreeSha256") != artifact.get("payloadTreeSha256")
            or attestation.get("qualificationSummarySha256") != qualification_sha
            or ink_runtime.get("ripgrepSha256") != ripgrep_sha
        ):
            raise AcceptanceError(
                "RUNTIME_EVIDENCE_MISMATCH",
                "npm-artifact",
                "platform Runtime evidence is not bound to the publication attestation",
            )
        summaries[package] = {
            "target": target,
            "package": package,
            "version": version,
            "tarballSha256": tarball_sha256,
            "qualificationSummarySha256": qualification_sha,
            "coreBundleSha256": attestation["coreBundleSha256"],
            "payloadTreeSha256": attestation["payloadTreeSha256"],
        }

    if meta_attestation is None:
        raise AcceptanceError(
            "RUNTIME_EVIDENCE_MISSING", "npm-artifact", "selector attestation is missing"
        )
    expected_bindings = [
        {
            "target": target,
            "package": package,
            "version": version,
            "tarballSha256": summaries[package]["tarballSha256"],
            "qualificationSummarySha256": summaries[package]["qualificationSummarySha256"],
            "coreBundleSha256": summaries[package]["coreBundleSha256"],
            "payloadTreeSha256": summaries[package]["payloadTreeSha256"],
        }
        for target, package in NPM_PLATFORMS.items()
    ]
    if meta_attestation.get("platforms") != expected_bindings:
        raise AcceptanceError(
            "META_BINDING_MISMATCH",
            "npm-artifact",
            "selector attestation does not bind the exact four platform tarballs",
        )
    return summaries


def validate_npm_tarball_manifest(
    manifest: Mapping[str, Any], package: str, version: str
) -> None:
    """Re-prove package identity and Runtime binding from tgz contents."""

    if (
        manifest.get("name") != package
        or manifest.get("version") != version
        or manifest.get("private") is True
    ):
        raise AcceptanceError(
            "VERSION_MISMATCH",
            "npm-artifact",
            "npm tarball package.json identity does not match the requested release",
        )
    license_name = manifest.get("license")
    if (
        not isinstance(license_name, str)
        or not license_name.strip()
        or license_name.upper() == "UNLICENSED"
        or manifest.get("publishConfig")
        != {"access": "public", "provenance": True}
        or manifest.get("scripts") != {"prepack": "node scripts/prepack.mjs"}
    ):
        raise AcceptanceError(
            "PUBLICATION_CONTRACT_MISMATCH",
            "npm-artifact",
            "npm tarball license, provenance, access, or prepack contract is invalid",
        )
    if package == NPM_SELECTOR:
        expected_optional = {
            platform_package: version
            for platform_package in NPM_PLATFORMS.values()
        }
        if manifest.get("optionalDependencies") != expected_optional:
            raise AcceptanceError(
                "PACKAGE_SET_MISMATCH",
                "npm-artifact",
                "selector tarball does not bind the exact four-platform package set",
            )
        expected_bins = {alias: f"bin/{CLI_COMMAND}" for alias in CLI_ALIASES}
        if manifest.get("bin") != expected_bins:
            raise AcceptanceError(
                "CLI_CONTRACT_FAILED",
                "npm-artifact",
                "selector tarball does not expose the exact Runtime command aliases",
            )
        if manifest.get("dependencies") not in (None, {}):
            raise AcceptanceError(
                "PACKAGE_SET_MISMATCH",
                "npm-artifact",
                "selector tarball must not have ordinary dependencies",
            )
        return

    target = next(
        (candidate for candidate, name in NPM_PLATFORMS.items() if name == package),
        None,
    )
    if target is None:
        raise AcceptanceError(
            "PACKAGE_SET_MISMATCH", "npm-artifact", "unexpected npm platform package"
        )
    expected_os, expected_cpu = target.split("-", 1)
    dependencies = manifest.get("dependencies")
    ink_runtime = manifest.get("inkRuntime")
    if manifest.get("os") != [expected_os] or manifest.get("cpu") != [expected_cpu]:
        raise AcceptanceError(
            "PLATFORM_MISMATCH",
            "npm-artifact",
            "platform tarball os/cpu does not match its package name",
        )
    if ink_runtime is None and dependencies in (None, {}):
        return
    if dependencies != {"bun": BUN_VERSION}:
        raise AcceptanceError(
            "BUN_VERSION_MISMATCH",
            "npm-artifact",
            "platform tarball does not pin the qualified Bun version",
        )
    if not isinstance(ink_runtime, dict) or (
        ink_runtime.get("target") != target
        or ink_runtime.get("entrypoint") != "runtime/bin/ink-claude-code-dream"
        or ink_runtime.get("ripgrepPath") != NPM_RIPGREP_PATHS[target]
        or ink_runtime.get("bunVersion") != BUN_VERSION
        or ink_runtime.get("sourceMapsIncluded") is not False
        or not re.fullmatch(r"[0-9a-f]{64}", str(ink_runtime.get("ripgrepSha256", "")))
    ):
        raise AcceptanceError(
            "RUNTIME_BINDING_MISMATCH",
            "npm-artifact",
            "platform tarball inkRuntime binding is incomplete or inconsistent",
        )


def acquire_npm_release(
    version: str,
    destination: Path,
    *,
    target: str | None = None,
    env: Mapping[str, str] | None = None,
    runner: Callable[..., subprocess.CompletedProcess[str]] = run_command,
) -> dict[str, Any]:
    """Download all five tgz files and validate selector/current-platform use."""

    version = _require_safe_version(version, "Runtime version")
    target = target or host_runtime_target()
    if target not in NPM_PLATFORMS:
        raise AcceptanceError("UNSUPPORTED_PLATFORM", "platform", "requested target is outside the Runtime contract")
    destination.mkdir(parents=True, exist_ok=True)
    command_env = dict(env or _safe_environment(destination / "home"))
    packages = [NPM_SELECTOR, *NPM_PLATFORMS.values()]
    metadata = {
        package: npm_view(package, version, cwd=destination, env=command_env, runner=runner)
        for package in packages
    }
    validate_npm_metadata_contract(metadata, version, target)

    receipts: dict[str, Any] = {}
    paths: dict[str, Path] = {}
    for package in packages:
        packed = _npm_json_command(
            [
                "npm", "pack", f"{package}@{version}", "--json", "--ignore-scripts",
                "--pack-destination", str(destination), "--registry", NPM_REGISTRY,
            ],
            phase="npm-pack",
            package=package,
            version=version,
            cwd=destination,
            env=command_env,
            runner=runner,
        )
        if not isinstance(packed, list) or len(packed) != 1 or not isinstance(packed[0], dict):
            raise AcceptanceError("INVALID_REGISTRY_RESPONSE", "npm-pack", "npm pack returned an invalid receipt")
        record = packed[0]
        filename = record.get("filename")
        if not isinstance(filename, str) or Path(filename).name != filename:
            raise AcceptanceError("INVALID_ARTIFACT_NAME", "npm-pack", "npm tarball filename is unsafe")
        tarball = destination / filename
        if not tarball.is_file():
            raise AcceptanceError("ARTIFACT_MISSING", "npm-pack", "npm pack did not create its declared tarball")
        body = tarball.read_bytes()
        expected_integrity = metadata[package]["dist"]["integrity"]
        actual_integrity = _sha512_integrity(body)
        if record.get("name") != package or record.get("version") != version:
            raise AcceptanceError("VERSION_MISMATCH", "npm-pack", "npm tarball identity does not match the requested version")
        if record.get("integrity") != expected_integrity or actual_integrity != expected_integrity:
            raise AcceptanceError("INTEGRITY_MISMATCH", "npm-pack", "npm tarball integrity does not match registry metadata")
        file_count = inspect_archive_without_source_maps(tarball, phase="npm-artifact")
        validate_npm_tarball_manifest(
            read_npm_package_manifest(tarball), package, version
        )
        paths[package] = tarball
        receipts[package] = {
            "filename": filename,
            "integrity": actual_integrity,
            "sha256": hashlib.sha256(body).hexdigest(),
            "bytes": len(body),
            "files": file_count,
            "path": str(tarball),
        }
    evidence = verify_npm_release_tarballs(paths, version)
    return {
        "target": target,
        "currentPlatformPackage": NPM_PLATFORMS[target],
        "packages": receipts,
        "paths": paths,
        "evidence": evidence,
    }


def install_npm_runtime(
    npm_release: Mapping[str, Any],
    root: Path,
    *,
    env: Mapping[str, str],
    runner: Callable[..., subprocess.CompletedProcess[str]] = run_command,
) -> Path:
    install_root = root / "npm-install"
    install_root.mkdir(parents=True)
    paths = npm_release["paths"]
    selector = Path(paths[NPM_SELECTOR]).resolve()
    platform_package = str(npm_release["currentPlatformPackage"])
    native = Path(paths[platform_package]).resolve()
    (install_root / "package.json").write_text(
        json.dumps(
            {
                "private": True,
                "dependencies": {
                    NPM_SELECTOR: f"file:{selector}",
                    platform_package: f"file:{native}",
                },
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    result = runner(
        [
            "npm",
            "install",
            "--no-audit",
            "--no-fund",
            "--package-lock=false",
            "--omit=optional",
        ],
        cwd=install_root,
        env=env,
    )
    if result.returncode != 0:
        raise AcceptanceError("INSTALL_FAILED", "npm-install", "isolated npm installation failed")
    executables = [
        install_root / "node_modules" / ".bin" / alias for alias in CLI_ALIASES
    ]
    if any(not executable.is_file() for executable in executables):
        raise AcceptanceError("CLI_MISSING", "npm-install", "installed selector did not expose both Runtime command aliases")
    resolved = {executable.resolve() for executable in executables}
    if len(resolved) != 1:
        raise AcceptanceError("CLI_CONTRACT_FAILED", "npm-install", "installed Runtime command aliases resolve to different executables")
    executable = executables[0]
    return executable.resolve()


def create_sdk_venv(
    artifact: Path,
    root: Path,
    *,
    source_only: bool = False,
    env: Mapping[str, str],
    runner: Callable[..., subprocess.CompletedProcess[str]] = run_command,
) -> Path:
    venv = root / ("sdk-sdist-venv" if source_only else "sdk-wheel-venv")
    created = runner([sys.executable, "-m", "venv", str(venv)], cwd=root, env=env)
    if created.returncode != 0:
        raise AcceptanceError("INSTALL_FAILED", "venv-create", "isolated Python environment creation failed")
    python = venv / ("Scripts/python.exe" if os.name == "nt" else "bin/python")
    install_argv = [str(python), "-m", "pip", "install"]
    # For the sdist lane the explicit local .tar.gz is the only top-level SDK
    # candidate.  Let pip resolve its declared build and runtime dependencies
    # normally so divergent Requires-Dist metadata cannot be hidden by wheel
    # dependencies installed in advance.
    install_argv.append(str(artifact))
    installed = runner(install_argv, cwd=root, env=env)
    if installed.returncode != 0:
        raise AcceptanceError("INSTALL_FAILED", "sdk-install", "isolated SDK artifact installation failed")
    return python


_PROBE = r"""
import importlib.metadata as md
import json
import pathlib
import sys
import claude_agent_sdk as sdk
from claude_agent_sdk._cli_version import __cli_version__

expected_version, expected_cli_compatibility, cli = sys.argv[1:]
providers = sorted({
    name.lower().replace('_', '-').replace('.', '-')
    for name in (md.packages_distributions().get('claude_agent_sdk') or [])
})
required = ('ClaudeAgentOptions', 'ClaudeSDKClient', 'query')
if providers != ['ink-claude-dream-agent-sdk']:
    raise SystemExit('import provider ownership mismatch')
if md.version('ink-claude-dream-agent-sdk') != expected_version:
    raise SystemExit('distribution version mismatch')
if sdk.__version__ != expected_version:
    raise SystemExit('SDK module version mismatch')
if __cli_version__ != expected_cli_compatibility:
    raise SystemExit('SDK CLI compatibility version mismatch')
try:
    md.distribution('claude-agent-sdk')
except md.PackageNotFoundError:
    pass
else:
    raise SystemExit('official distribution overlap')
if any(not hasattr(sdk, name) for name in required):
    raise SystemExit('public API missing')
options = sdk.ClaudeAgentOptions(cli_path=cli)
if pathlib.Path(options.cli_path).resolve() != pathlib.Path(cli).resolve():
    raise SystemExit('SDK cli_path mismatch')
print(json.dumps({'providers': providers, 'sdkVersion': sdk.__version__, 'sdkCliCompatibility': __cli_version__, 'officialDistributionInstalled': False, 'publicApi': list(required), 'cliPath': str(pathlib.Path(cli).resolve())}))
"""


def probe_installed_contract(
    python: Path,
    sdk_version: str,
    cli_path: Path,
    expected_cli_version: str,
    *,
    root: Path,
    env: Mapping[str, str],
    runner: Callable[..., subprocess.CompletedProcess[str]] = run_command,
) -> dict[str, Any]:
    cli_compatibility = expected_cli_version.split(maxsplit=1)[0]
    _require_safe_version(cli_compatibility, "SDK CLI compatibility version")
    probe = runner(
        [
            str(python),
            "-c",
            _PROBE,
            sdk_version,
            cli_compatibility,
            str(cli_path),
        ],
        cwd=root,
        env=env,
    )
    if probe.returncode != 0:
        raise AcceptanceError("SDK_CONTRACT_FAILED", "isolated-probe", "installed SDK ownership or public API contract failed")
    payload = _json_object(probe.stdout, phase="isolated-probe")
    cli = runner([str(cli_path), "--version"], cwd=root, env=env)
    if cli.returncode != 0:
        raise AcceptanceError("CLI_CONTRACT_FAILED", "cli-version", "installed Runtime --version failed")
    actual_cli_version = cli.stdout.strip()
    if actual_cli_version != expected_cli_version:
        raise AcceptanceError("CLI_VERSION_MISMATCH", "cli-version", "installed Runtime reported an unexpected version")
    payload["cliVersion"] = actual_cli_version
    return payload


def run_acceptance(sdk_version: str, runtime_version: str, expected_cli_version: str) -> dict[str, Any]:
    sdk_version = _require_safe_version(sdk_version, "SDK version")
    runtime_version = _require_safe_version(runtime_version, "Runtime version")
    if not expected_cli_version or any(char in expected_cli_version for char in "\r\n"):
        raise AcceptanceError("INVALID_INPUT", "input", "expected CLI version must be one output line")
    with tempfile.TemporaryDirectory(prefix="ink-registry-acceptance-") as raw_root:
        root = Path(raw_root)
        home = root / "home"
        home.mkdir(mode=0o700)
        env = _safe_environment(home)
        pypi = acquire_pypi_release(sdk_version, root / "pypi")
        npm = acquire_npm_release(runtime_version, root / "npm", env=env)
        cli = install_npm_runtime(npm, root, env=env)
        wheel_python = create_sdk_venv(Path(pypi["bdist_wheel"]["path"]), root, env=env)
        wheel_probe = probe_installed_contract(
            wheel_python, sdk_version, cli, expected_cli_version, root=root, env=env
        )
        sdist_python = create_sdk_venv(
            Path(pypi["sdist"]["path"]),
            root,
            source_only=True,
            env=env,
        )
        sdist_probe = probe_installed_contract(
            sdist_python, sdk_version, cli, expected_cli_version, root=root, env=env
        )
        return {
            "schemaVersion": "ink-claude-registry-acceptance/v1",
            "status": "passed",
            "providerFree": True,
            "networkUse": ["pypi", "npm"],
            "modelInvoked": False,
            "modelProviderCredentialEnvironmentForwarded": False,
            "packageRegistryTokenEnvironmentForwarded": False,
            "sdk": {
                "distribution": PYPI_DISTRIBUTION,
                "version": sdk_version,
                "wheel": {key: value for key, value in pypi["bdist_wheel"].items() if key != "path"},
                "sdist": {key: value for key, value in pypi["sdist"].items() if key != "path"},
            },
            "runtime": {
                "selector": NPM_SELECTOR,
                "version": runtime_version,
                "target": npm["target"],
                "currentPlatformPackage": npm["currentPlatformPackage"],
                "packages": {
                    package: {key: value for key, value in receipt.items() if key != "path"}
                    for package, receipt in npm["packages"].items()
                },
            },
            "isolatedWheelInstall": wheel_probe,
            "isolatedSdistInstall": sdist_probe,
        }


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--sdk-version", required=True, help="exact PyPI SDK version")
    parser.add_argument("--runtime-version", required=True, help="exact npm five-package version")
    parser.add_argument("--expected-cli-version", required=True, help="exact CLI --version stdout")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    try:
        receipt = run_acceptance(args.sdk_version, args.runtime_version, args.expected_cli_version)
    except AcceptanceError as exc:
        print(json.dumps(exc.receipt(), ensure_ascii=False, sort_keys=True))
        return 2
    except KeyboardInterrupt:
        return 130
    except Exception:
        error = AcceptanceError(
            "INTERNAL_ACCEPTANCE_ERROR", "internal", "unexpected acceptance failure was safely redacted"
        )
        print(json.dumps(error.receipt(), ensure_ascii=False, sort_keys=True))
        return 2
    print(json.dumps(receipt, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

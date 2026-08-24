# [Input] Backend dependency manifests and Docker image specification.
# [Output] Static regression proof that the immutable Dream SDK and explicit
#          official rollback CLI remain atomically pinned without SDK overlap.
# [Pos] Docker/dependency release contract tests.
# [Sync] 2026-08-24: lock custom SDK 0.2.143 at bcdfbcf9 and pair its CLI pin
#        with the Docker-only explicit official rollback artifact 2.1.241.

from __future__ import annotations

import tomllib
from pathlib import Path


BACKEND_ROOT = Path(__file__).resolve().parents[1]
SDK_COMMIT = "bcdfbcf9f72bc34865d0efeb5f971d6df005f5b4"
SDK_REQUIREMENT = (
    "ink-claude-dream-agent-sdk @ "
    "git+https://github.com/glide-the/ink-claude-dream-agent-sdk-python.git@"
    f"{SDK_COMMIT}"
)
SDK_VERSION = "0.2.143"
CLI_VERSION = "2.1.241"


def _normalized_distribution_name(value: str) -> str:
    return value.lower().replace("_", "-")


def test_dependency_manifests_lock_only_custom_sdk() -> None:
    pyproject = tomllib.loads((BACKEND_ROOT / "pyproject.toml").read_text())
    dependencies = pyproject["project"]["dependencies"]
    normalized_dependencies = {
        _normalized_distribution_name(dependency.split(maxsplit=1)[0])
        for dependency in dependencies
    }
    assert SDK_REQUIREMENT in dependencies
    assert "ink-claude-dream-agent-sdk" in normalized_dependencies
    assert "claude-agent-sdk" not in normalized_dependencies

    requirements = (BACKEND_ROOT / "requirements.txt").read_text()
    assert SDK_REQUIREMENT in requirements
    assert "\nclaude-agent-sdk" not in requirements

    lock = tomllib.loads((BACKEND_ROOT / "uv.lock").read_text())
    sdk_packages = [
        package
        for package in lock["package"]
        if package["name"] == "ink-claude-dream-agent-sdk"
    ]
    assert len(sdk_packages) == 1
    assert sdk_packages[0]["version"] == SDK_VERSION
    assert SDK_COMMIT in sdk_packages[0]["source"]["git"]
    assert all(package["name"] != "claude-agent-sdk" for package in lock["package"])


def test_dockerfile_cross_asserts_sdk_and_rollback_cli_pair() -> None:
    dockerfile = (BACKEND_ROOT / "Dockerfile").read_text()
    assert f"ARG CLAUDE_CODE_VERSION={CLI_VERSION}" in dockerfile
    assert f'test "${{CLAUDE_CODE_VERSION}}" = "{CLI_VERSION}"' in dockerfile
    assert '"@anthropic-ai/claude-code@${CLAUDE_CODE_VERSION}"' in dockerfile
    assert "CLAUDE_CODE_CLI_PATH=/usr/local/bin/claude" in dockerfile
    assert "from claude_agent_sdk._cli_version import __cli_version__" in dockerfile
    assert f"assert __cli_version__ == '{CLI_VERSION}'" in dockerfile
    assert f"assert dist.version == '{SDK_VERSION}'" in dockerfile
    assert "assert providers == {'ink-claude-dream-agent-sdk'}" in dockerfile
    assert "assert 'claude-agent-sdk' not in installed" in dockerfile

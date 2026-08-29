# [Input] Backend dependency manifests and Docker image specification.
# [Output] Static regression proof that the immutable Dream SDK, default public
#          Dream Runtime and explicit official rollback CLI remain atomically
#          pinned without SDK overlap.
# [Pos] Docker/dependency release contract tests.
# [Sync] 2026-08-26: install custom SDK 0.2.144 from PyPI with an exact
#        hash-locked export, install public Runtime selector 0.1.3 by default,
#        and retain the Docker-only official rollback artifact 2.1.241.
# [Sync] 2026-08-28: lock the supported Notion CLI and backend-bundled Skill
#                    into the same standard Agent startup image.
# [Sync] 2026-08-28: require the complete Notion Skill reference package in the
#                    backend build context.
# [Sync] 2026-08-30: require the renamed upstream notion-cli package beside notion-session.

from __future__ import annotations

from pathlib import Path

import tomllib
from packaging.requirements import Requirement

BACKEND_ROOT = Path(__file__).resolve().parents[1]
SDK_VERSION = "0.2.144"
SDK_REQUIREMENT = f"ink-claude-dream-agent-sdk=={SDK_VERSION}"
CLI_VERSION = "2.1.241"
RUNTIME_VERSION = "0.1.3"
NOTION_CLI_VERSION = "0.15.1"


def _normalized_distribution_name(value: str) -> str:
    return value.lower().replace("_", "-")


def test_dependency_manifests_lock_only_custom_sdk() -> None:
    pyproject = tomllib.loads((BACKEND_ROOT / "pyproject.toml").read_text())
    dependencies = pyproject["project"]["dependencies"]
    normalized_dependencies = {
        _normalized_distribution_name(Requirement(dependency).name)
        for dependency in dependencies
    }
    assert SDK_REQUIREMENT in dependencies
    assert "ink-claude-dream-agent-sdk" in normalized_dependencies
    assert "claude-agent-sdk" not in normalized_dependencies

    requirements = (BACKEND_ROOT / "requirements.txt").read_text()
    assert SDK_REQUIREMENT in requirements
    assert "git+https://github.com/glide-the/ink-claude-dream-agent-sdk-python" not in requirements
    assert "--hash=sha256:" in requirements
    assert "\nclaude-agent-sdk" not in requirements

    lock = tomllib.loads((BACKEND_ROOT / "uv.lock").read_text())
    sdk_packages = [
        package
        for package in lock["package"]
        if package["name"] == "ink-claude-dream-agent-sdk"
    ]
    assert len(sdk_packages) == 1
    assert sdk_packages[0]["version"] == SDK_VERSION
    assert sdk_packages[0]["source"] == {"registry": "https://pypi.org/simple"}
    assert sdk_packages[0]["wheels"]
    assert all("hash" in artifact for artifact in sdk_packages[0]["wheels"])
    assert all(package["name"] != "claude-agent-sdk" for package in lock["package"])


def test_dockerfile_cross_asserts_sdk_runtime_and_rollback_cli_pair() -> None:
    dockerfile = (BACKEND_ROOT / "Dockerfile").read_text()
    assert f"ARG INK_CLAUDE_CODE_VERSION={RUNTIME_VERSION}" in dockerfile
    assert f"ARG CLAUDE_CODE_VERSION={CLI_VERSION}" in dockerfile
    assert f'test "${{INK_CLAUDE_CODE_VERSION}}" = "{RUNTIME_VERSION}"' in dockerfile
    assert f'test "${{CLAUDE_CODE_VERSION}}" = "{CLI_VERSION}"' in dockerfile
    assert (
        '"@glide-the/ink-claude-code-dream@${INK_CLAUDE_CODE_VERSION}"'
        in dockerfile
    )
    assert dockerfile.index(
        '"@glide-the/ink-claude-code-dream@${INK_CLAUDE_CODE_VERSION}"'
    ) < dockerfile.index('"@anthropic-ai/claude-code@${CLAUDE_CODE_VERSION}"')
    assert 'test -L /usr/local/bin/claude' in dockerfile
    assert (
        'test "$(realpath /usr/local/bin/claude)" = '
        '"${DREAM_RUNTIME_ENTRYPOINT}"'
    ) in dockerfile
    assert "unlink /usr/local/bin/claude" in dockerfile
    assert "npm install -g --force" not in dockerfile
    assert "INK_CLAUDE_NPM_REGISTRY=https://registry.npmjs.org" in dockerfile
    assert (
        'test "$(ink-claude-code-dream --version)" = '
        '"${CLAUDE_CODE_VERSION} (Claude Code)"'
    ) in dockerfile
    assert ".core.corePruned == true" in dockerfile
    assert ".core.productionEligible == true" in dockerfile
    assert '"@anthropic-ai/claude-code@${CLAUDE_CODE_VERSION}"' in dockerfile
    assert (
        'test "$(realpath "$(command -v claude)")" != '
        '"${DREAM_RUNTIME_ENTRYPOINT}"'
    ) in dockerfile
    assert "CLAUDE_CODE_CLI_PATH" in dockerfile
    assert "/usr/local/bin/claude" in dockerfile
    assert "resolve_claude_cli_path" in dockerfile
    assert "--require-hashes" in dockerfile
    assert "https://pypi.org/simple" in dockerfile
    assert "from claude_agent_sdk._cli_version import __cli_version__" in dockerfile
    assert f"assert __cli_version__ == '{CLI_VERSION}'" in dockerfile
    assert f"assert dist.version == '{SDK_VERSION}'" in dockerfile
    assert "assert providers == {'ink-claude-dream-agent-sdk'}" in dockerfile
    assert "assert 'claude-agent-sdk' not in installed" in dockerfile


def test_dockerfile_installs_supported_notion_cli_and_bundled_skill() -> None:
    dockerfile = (BACKEND_ROOT / "Dockerfile").read_text()
    assert f"ARG NOTION_CLI_VERSION={NOTION_CLI_VERSION}" in dockerfile
    assert '"ntn@${NOTION_CLI_VERSION}"' in dockerfile
    assert 'test "$(ntn --version)" = "ntn ${NOTION_CLI_VERSION}"' in dockerfile
    assert "ntn login --help" in dockerfile
    assert "ntn doctor --help" in dockerfile
    skill = BACKEND_ROOT / "builtin_skills" / "notion-session" / "SKILL.md"
    assert skill.is_file()
    content = skill.read_text(encoding="utf-8")
    assert ".notion/pages/<page_id>.json" in content
    assert 'tools: ["Read"]' in content
    assert "mcp__notion__" not in content
    assert "ntn api" not in content
    references = skill.parent / "references"
    assert {path.name for path in references.glob("*.md")} == {
        "notion-search.md",
        "notion-page-read.md",
        "notion-db-query.md",
    }
    cli_skill = BACKEND_ROOT / "builtin_skills" / "notion-cli" / "SKILL.md"
    assert cli_skill.is_file()
    cli_content = cli_skill.read_text(encoding="utf-8")
    assert "name: notion-cli" in cli_content
    assert 'tools: ["Bash"]' in cli_content
    assert "ntn api v1/search" in cli_content
    assert {path.name for path in (cli_skill.parent / "references").glob("*.md")} == {
        "notion-search.md",
        "notion-page-read.md",
        "notion-db-query.md",
    }

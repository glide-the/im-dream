# [Input] System Deck policy, Admin Registry104 candidate DTO and local plugin verifiers.
# [Output] Default template identity plus artifact/CLI evidence mapping without Dream persistence.
# [Pos] Pure Deck-default policy test; create/reconcile transactions belong to Admin DTO/ORM operations.
# [Sync] 2026-09-16: retire legacy Dream Deck/default SQL authority tests.
# [Sync] 2026-09-19: cover the screenplay and music code-owned system template registry.

from __future__ import annotations

from typing import Any

import pytest

import config
from services.admin_data.deck_default_data import DefaultPluginInstallationDTO
from services.deck import defaults as deck_defaults
from services.claude_plugin.builtin_sources import resolve_local_marketplace


def _verified_installation() -> dict[str, Any]:
    return {
        "id": "installation-drama-forge",
        "package_name": "drama-forge",
        "marketplace": "drama-studio",
        "resolved_version": "1.0.1",
        "artifact_digest": f"sha256:{'a' * 64}",
    }


def _default_ref() -> dict[str, str]:
    installation = _verified_installation()
    return {
        "plugin_installation_id": installation["id"],
        "package_name": installation["package_name"],
        "resolved_version": installation["resolved_version"],
        "artifact_digest": installation["artifact_digest"],
    }


def _candidate() -> DefaultPluginInstallationDTO:
    installation = _verified_installation()
    return DefaultPluginInstallationDTO(
        plugin_installation_id=installation["id"],
        package_name=installation["package_name"],
        marketplace=installation["marketplace"],
        resolved_version=installation["resolved_version"],
        artifact_digest=installation["artifact_digest"],
        compatibility_json='{"claude_code":">=1.0.0"}',
    )


def test_screenplay_and_music_are_active_system_templates() -> None:
    template = config.SCREENPLAY_DECK_TEMPLATE
    assert template["id"] == config.DEFAULT_SYSTEM_DECK_ID
    assert template["name"] == "剧本创作团队"
    assert [voice["name"] for voice in template["voices"]] == [
        "编剧",
        "戏剧结构师",
        "人物塑造师",
        "对白编辑",
        "连续性审校",
    ]
    assert config.RETIRED_SYSTEM_DECK_IDS == (
        "introspection_deck",
        "scholar_deck",
        "philosophy_deck",
    )
    assert config.SYSTEM_DECK_TEMPLATES == (
        config.SCREENPLAY_DECK_TEMPLATE,
        config.MUSIC_DECK_TEMPLATE,
    )
    music = config.MUSIC_DECK_TEMPLATE
    assert music["id"] == config.MUSIC_SYSTEM_DECK_ID
    assert music["name"] == "音乐创作"
    assert [voice["name"] for voice in music["voices"]] == ["风格和歌词生成"]
    assert music["plugins"] == (
        {
            "package_name": "yue2",
            "marketplace": "yue2-skills",
            "resolved_version": "0.4.0",
        },
    )
    marketplace = resolve_local_marketplace("yue2-skills")
    assert marketplace is not None
    assert marketplace.name == "yue2-skills"
    assert (marketplace / "claude-code" / ".claude-plugin" / "plugin.json").is_file()


def test_default_service_resolves_exact_verified_installation(monkeypatch) -> None:
    candidate = _candidate()
    checked: list[dict[str, Any]] = []
    monkeypatch.setattr(
        deck_defaults.PluginInstallService,
        "verify_installation_artifact",
        staticmethod(lambda record: checked.append(record) or True),
    )
    monkeypatch.setattr(
        deck_defaults.PluginInstallService,
        "check_cli_compatibility",
        staticmethod(lambda record: checked.append(record) or True),
    )

    assert deck_defaults.resolve_default_deck_plugin_ref(candidate).model_dump() == _default_ref()
    assert checked == [candidate.model_dump(), candidate.model_dump()]


@pytest.mark.parametrize("failure", ["missing", "artifact", "cli"])
def test_default_service_fails_closed_without_local_evidence(monkeypatch, failure: str) -> None:
    candidate = _candidate()
    monkeypatch.setattr(
        deck_defaults.PluginInstallService,
        "verify_installation_artifact",
        staticmethod(lambda _record: failure != "artifact"),
    )
    monkeypatch.setattr(
        deck_defaults.PluginInstallService,
        "check_cli_compatibility",
        staticmethod(lambda _record: failure != "cli"),
    )

    with pytest.raises(deck_defaults.DefaultDeckPluginUnavailable):
        deck_defaults.resolve_default_deck_plugin_ref(None if failure == "missing" else candidate)

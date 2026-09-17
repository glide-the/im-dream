# [Input] Registry105 Dream DTO consumer, capability catalog and fixed Admin responses.
# [Output] Exact hash, strict response binding, fail-closed catalog and request-owner registration evidence.
# [Pos] Provider-free Admin Deck chat-context consumer contract test.
# [Sync] 2026-09-15: pin Admin 0100e9c before replacing the public Dream database path.
from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import Mock

import pytest
from pydantic import ValidationError

from services.admin_data.config import AdminDataConfig
from services.admin_data.deck_chat_context_data import (
    AdminDeckChatContextData,
    AdminDeckChatContextResolution,
    DECK_CHAT_CONTEXT_OPERATIONS,
    DeckChatContextInputDTO,
    DeckChatContextOutputDTO,
    RESOLVE_DECK_CHAT_CONTEXT,
)
from services.admin_data.errors import AdminDataError
from services.admin_data.request_auth import AdminRequestAuth
from services.admin_data.workflow_data import WORKFLOW_SCHEMA_REQUIREMENTS


def _output(**updates) -> DeckChatContextOutputDTO:
    value = {
        "deck": {
            "id": "deck-1",
            "name": "Deck",
            "name_zh": "创作组",
            "name_en": None,
            "description": "说明",
            "description_zh": None,
            "description_en": "Description",
            "enabled": True,
        },
        "voices": [
            {
                "id": "voice-1",
                "name": "Writer",
                "name_zh": "编剧",
                "name_en": "Writer",
                "system_prompt": "写作😀",
                "enabled": True,
            }
        ],
        "plugin_refs": [
            {
                "plugin_installation_id": "install-1",
                "package_spec": "drama-forge@official",
                "resolved_version": "1.2.3",
                "artifact_digest": "sha256:" + "a" * 64,
                "order_index": 0,
                "enabled": True,
                "installation_status": "ready",
            }
        ],
        **updates,
    }
    return DeckChatContextOutputDTO.model_validate(value)


def _data(output: DeckChatContextOutputDTO | None = None):
    client = Mock()
    client.capabilities.return_value = SimpleNamespace(
        schema_capabilities=list(WORKFLOW_SCHEMA_REQUIREMENTS)
    )
    client.execute.return_value = output or _output()
    return AdminDeckChatContextData(client, canonical_user_id="42"), client


def test_registry105_contract_and_strict_dtos_are_exact():
    assert DECK_CHAT_CONTEXT_OPERATIONS == (RESOLVE_DECK_CHAT_CONTEXT,)
    assert RESOLVE_DECK_CHAT_CONTEXT.capability.model_dump() == {
        "name": "deck-chat-context.resolve",
        "kind": "read",
        "user_scope": "dream:read",
        "background_scope": None,
        "input_schema_version": 1,
        "output_schema_version": 1,
        "contract_sha256": "c956db969d76208bd99d2d8ad2c9e7eb2f6154d835388424e7db5ca09ca74b97",
    }
    with pytest.raises(ValidationError):
        DeckChatContextInputDTO.model_validate(
            {"deck_id": "deck-1", "voice_id": None, "actor_id": "42"}
        )
    with pytest.raises(ValidationError):
        DeckChatContextOutputDTO.model_validate(
            {**_output().model_dump(), "database_row": True}
        )


def test_resolve_checks_capability_and_preserves_the_typed_snapshot():
    data, client = _data()
    selection = DeckChatContextInputDTO(deck_id="deck-1", voice_id="voice-1")
    result = data.resolve(
        selection,
        "deck-context-request",
        access_token="oauth-token",
    )
    assert isinstance(result, AdminDeckChatContextResolution)
    assert result.snapshot is client.execute.return_value
    assert result.context_for(
        actor_id="42",
        deck_id="deck-1",
        voice_id="voice-1",
    ) is client.execute.return_value
    client.capabilities.assert_called_once_with("deck-context-request")
    client.execute.assert_called_once_with(
        RESOLVE_DECK_CHAT_CONTEXT,
        selection,
        "deck-context-request",
        access_token="oauth-token",
    )
    with pytest.raises(AdminDataError) as caught:
        result.context_for(
            actor_id="43",
            deck_id="deck-1",
            voice_id="voice-1",
        )
    assert caught.value.code == "DREAM_DELEGATION_ENTITY_DENIED"


@pytest.mark.parametrize(
    "output",
    [
        _output(deck={**_output().deck.model_dump(), "id": "deck-other"}),
        _output(voices=[*_output().voices, *_output().voices]),
        _output(plugin_refs=[*_output().plugin_refs, *_output().plugin_refs]),
        _output(
            plugin_refs=[
                {**_output().plugin_refs[0].model_dump(), "order_index": 2},
                {
                    **_output().plugin_refs[0].model_dump(),
                    "plugin_installation_id": "install-2",
                    "order_index": 1,
                },
            ]
        ),
    ],
)
def test_resolve_rejects_mismatched_or_ambiguous_admin_data(output):
    data, _client = _data(output)
    with pytest.raises(AdminDataError) as caught:
        data.resolve(
            DeckChatContextInputDTO(deck_id="deck-1", voice_id="voice-1"),
            "deck-context-request",
            access_token="oauth-token",
        )
    assert caught.value.code == "ADMIN_RESPONSE_INVALID"


def test_resolve_preserves_missing_selected_voice_for_dream_policy():
    data, _client = _data(_output(voices=[]))
    result = data.resolve(
        DeckChatContextInputDTO(deck_id="deck-1", voice_id="voice-1"),
        "deck-context-request",
        access_token="oauth-token",
    )
    assert result.snapshot.voices == []


def test_resolve_fails_before_domain_io_when_unified_capability_is_missing():
    data, client = _data()
    client.capabilities.return_value = SimpleNamespace(schema_capabilities=[])
    with pytest.raises(AdminDataError) as caught:
        data.resolve(
            DeckChatContextInputDTO(deck_id="deck-1", voice_id=None),
            "deck-context-request",
            access_token="oauth-token",
        )
    assert caught.value.code == "ADMIN_CAPABILITY_UNAVAILABLE"
    client.execute.assert_not_called()


def test_production_request_owner_registers_registry105_operation():
    config = AdminDataConfig(
        base_url="https://admin.example",
        issuer="https://admin.example/api/auth",
        resource="https://dream.example/api",
        service_client_id="dream-service",
        service_secret="s" * 32,
    )
    owner = AdminRequestAuth(config)
    try:
        assert (
            owner.client._operations[RESOLVE_DECK_CHAT_CONTEXT.capability.name]
            is RESOLVE_DECK_CHAT_CONTEXT
        )
    finally:
        owner.close()

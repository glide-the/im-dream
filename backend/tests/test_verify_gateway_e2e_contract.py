from __future__ import annotations

import json

import pytest

from backend.script import verify_gateway_e2e as verifier


def _event(payload: dict, newline: str = "\n") -> bytes:
    return (
        "data: "
        + json.dumps(payload, ensure_ascii=False, separators=(",", ":"))
        + newline
        + newline
    ).encode("utf-8")


def _successful_wire(
    *,
    delta: str = "中文🙂",
    final_text: str = "完成",
    newline: str = "\n",
) -> bytes:
    return b"".join(
        [
            _event({"type": "message-metadata"}, newline),
            _event({"type": "text-start", "id": "text-1"}, newline),
            _event(
                {"type": "text-delta", "id": "text-1", "delta": delta},
                newline,
            ),
            _event({"type": "text-end", "id": "text-1"}, newline),
            _event(
                {
                    "type": "message-final",
                    "text": final_text,
                    "sessionId": "opaque",
                },
                newline,
            ),
            _event({"type": "finish", "finishReason": "stop"}, newline),
        ]
    )


def test_sse_parser_is_incremental_unicode_and_crlf_safe() -> None:
    wire = _successful_wire(newline="\r\n")

    frames = verifier._parse_sse_chunks(bytes([byte]) for byte in wire)

    assert [frame["type"] for frame in frames] == [
        "message-metadata",
        "text-start",
        "text-delta",
        "text-end",
        "message-final",
        "finish",
    ]
    assert frames[2]["delta"] == "中文🙂"


def test_sse_parser_allows_whitespace_delta_when_text_is_still_nonempty() -> None:
    wire = b"".join(
        [
            _event({"type": "text-start"}),
            _event({"type": "text-delta", "delta": "\n"}),
            _event({"type": "text-delta", "delta": "OK"}),
            _event({"type": "text-delta", "delta": " "}),
            _event({"type": "text-end"}),
            _event({"type": "message-final", "text": "\nOK ", "sessionId": "opaque"}),
            _event({"type": "finish"}),
        ]
    )

    frames = verifier._parse_sse_chunks([wire])

    assert [frame["type"] for frame in frames].count("text-delta") == 3


@pytest.mark.parametrize(
    "wire",
    [
        b"data: not-json\n\n",
        _successful_wire() + _event({"type": "text-delta", "delta": "late"}),
        _event({"type": "finish"})
        + _event({"type": "message-final", "sessionId": "opaque"}),
        _event({"type": "message-final", "sessionId": "opaque"})
        + b"data: {\"type\":\"finish\"}",
        b"event: message\n" + _event({"type": "message-final"}),
    ],
)
def test_sse_parser_rejects_malformed_or_noncanonical_streams(wire: bytes) -> None:
    with pytest.raises(verifier.SSEProtocolError):
        verifier._parse_sse_chunks([wire])


@pytest.mark.parametrize(
    "wire",
    [
        b"".join(
            [
                _event({"type": "text-start"}),
                _event({"type": "text-end"}),
                _event({"type": "message-final", "text": "OK"}),
                _event({"type": "finish"}),
            ]
        ),
        _successful_wire(delta=""),
        b"".join(
            [
                _event({"type": "text-delta", "delta": "OK"}),
                _event({"type": "text-start"}),
                _event({"type": "text-end"}),
                _event({"type": "message-final", "text": "OK"}),
                _event({"type": "finish"}),
            ]
        ),
        _successful_wire(final_text="   "),
    ],
    ids=["missing-delta", "empty-delta", "misordered-delta", "empty-final"],
)
def test_sse_parser_rejects_incomplete_text_transcript(wire: bytes) -> None:
    with pytest.raises(verifier.SSEProtocolError):
        verifier._parse_sse_chunks([wire])


def test_sse_response_requires_exact_event_stream_mime() -> None:
    class Response:
        headers = {"content-type": "application/json"}

        @staticmethod
        def iter_content(*, chunk_size: int, decode_unicode: bool):
            del chunk_size, decode_unicode
            return iter(())

    with pytest.raises(verifier.SSEProtocolError):
        verifier._parse_sse_response(Response())  # type: ignore[arg-type]


def _projected_history(*, metadata: dict | None = None) -> list[dict]:
    return [
        {
            "role": "user",
            "parts": [{"type": "text", "text": "private fixed prompt"}],
            "metadata": {},
        },
        {
            "role": "assistant",
            "parts": [{"type": "text", "text": "private answer"}],
            "metadata": metadata or {},
        },
    ]


def test_projected_history_receipt_is_content_free_and_exact() -> None:
    receipt = verifier._projected_history_receipt(
        _projected_history(),
        expected_user_text="private fixed prompt",
    )

    assert receipt["valid"] is True
    assert receipt["messageCount"] == 2
    assert receipt["blankProjectionCount"] == 0
    encoded = json.dumps(receipt)
    assert "fixed prompt" not in encoded
    assert "private answer" not in encoded
    assert all(isinstance(value, (bool, int)) for value in receipt.values())


@pytest.mark.parametrize(
    "discriminator",
    ["visibility", "dispatch_status", "dispatchStatus"],
)
def test_projected_history_rejects_hidden_discriminator(discriminator: str) -> None:
    receipt = verifier._projected_history_receipt(
        _projected_history(metadata={discriminator: "system-hidden"}),
        expected_user_text="private fixed prompt",
    )

    assert receipt["valid"] is False
    assert receipt["privateDiscriminatorCount"] == 1


def test_projected_history_rejects_empty_or_blank_projection() -> None:
    empty = verifier._projected_history_receipt(
        [],
        expected_user_text="private fixed prompt",
    )
    blank_messages = _projected_history()
    blank_messages[1]["parts"] = []
    blank = verifier._projected_history_receipt(
        blank_messages,
        expected_user_text="private fixed prompt",
    )

    assert empty["valid"] is False
    assert empty["messageCount"] == 0
    assert blank["valid"] is False
    assert blank["blankProjectionCount"] == 1


def test_missing_model_contract_fails_before_database_access(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.setattr(verifier, "TARGET_MODEL_ALIAS", None)
    monkeypatch.setattr(verifier, "EXPECTED_UPSTREAM_MODEL", None)

    def unexpected_database_access():
        raise AssertionError("database must not be accessed")

    monkeypatch.setattr(verifier.database, "get_db", unexpected_database_access)

    assert verifier._safe_entrypoint() == 3
    assert json.loads(capsys.readouterr().out) == {
        "errorClass": "ModelContractError",
        "phase": "model-contract",
        "privateContentPrinted": False,
        "secretsPrinted": False,
    }


def test_business_preflight_failure_emits_only_safe_structured_code(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.setattr(
        verifier,
        "main",
        lambda: (_ for _ in ()).throw(
            verifier.BusinessPreflightError(
                "subscription-preflight",
                "SUBSCRIPTION_OR_ALLOWANCE_UNAVAILABLE",
            )
        ),
    )

    assert verifier._safe_entrypoint() == 3
    assert json.loads(capsys.readouterr().out) == {
        "errorClass": "BusinessPreflightError",
        "errorCode": "SUBSCRIPTION_OR_ALLOWANCE_UNAVAILABLE",
        "phase": "subscription-preflight",
        "privateContentPrinted": False,
        "secretsPrinted": False,
    }


def test_existing_subscription_can_use_gateway_allowance_without_exact_entitlement() -> None:
    evidence = verifier._current_subscription_access_evidence(
        {
            "subscription": {"id": "sub-private"},
            "planVersion": {"planCode": "free"},
            "entitlements": [
                {"modelAliases": ["another-model"]},
            ],
            "allowance": {"remaining": 50_000_000},
        },
        "hy-preview",
    )

    assert evidence == {
        "provisioned": False,
        "planCode": "free",
        "remainingTokensPositive": True,
        "accessMode": "allowance-only",
    }


def test_existing_subscription_records_exact_plan_entitlement_mode() -> None:
    evidence = verifier._current_subscription_access_evidence(
        {
            "subscription": {"id": "sub-private"},
            "planVersion": {"planCode": "dream"},
            "entitlements": [{"modelAliases": ["hy-preview"]}],
            "allowance": {"remaining": 1},
        },
        "hy-preview",
    )

    assert evidence == {
        "provisioned": False,
        "planCode": "dream",
        "remainingTokensPositive": True,
        "accessMode": "plan-entitlement",
    }


@pytest.mark.parametrize(
    "context",
    [
        {"planVersion": {"planCode": "free"}, "allowance": {"remaining": 1}},
        {
            "subscription": {"id": "sub-private"},
            "planVersion": {"planCode": "free"},
            "allowance": {"remaining": 0},
        },
    ],
)
def test_existing_subscription_requires_subscription_and_positive_allowance(
    context: dict,
) -> None:
    assert verifier._current_subscription_access_evidence(
        context, "hy-preview"
    ) is None


def test_unexpected_failure_does_not_emit_exception_message(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.setattr(
        verifier,
        "main",
        lambda: (_ for _ in ()).throw(RuntimeError("private-account-content")),
    )

    assert verifier._safe_entrypoint() == 3
    output = capsys.readouterr().out
    assert "private-account-content" not in output
    assert json.loads(output) == {
        "errorClass": "RuntimeError",
        "phase": "gateway-real-e2e",
        "privateContentPrinted": False,
        "secretsPrinted": False,
    }


def test_thread_receipt_uses_text_json_casts_and_exact_session(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list[tuple[str, tuple]] = []

    class Result:
        def __init__(self, *, rows=None, row=None):
            self.rows = rows
            self.row = row

        def fetchall(self):
            return self.rows

        def fetchone(self):
            return self.row

    class Connection:
        def execute(self, sql: str, params: tuple):
            calls.append((sql, params))
            if "WITH messages AS" in sql:
                return Result(rows=[(1, 1, 2, True, True, True)])
            return Result(row=(True, True))

        def close(self):
            return None

    monkeypatch.setattr(verifier.database, "get_db", Connection)

    receipt = verifier._thread_receipt(
        "thread",
        "7",
        "message",
        expected_user_text="private fixed prompt",
        expected_alias="hy-preview",
        expected_session_id="opaque-session",
        expected_agent_contract_version="contract-v1",
    )

    assert receipt["sdkSessionMatchesFinal"] is True
    assert receipt["dreamAuthorityMetadataPresent"] is False
    assert "parts::jsonb" in calls[0][0]
    assert "COALESCE(metadata, '{}')::jsonb" in calls[0][0]
    denylist = calls[0][1][-1]
    assert "visibility" in denylist
    assert "dispatch_status" in denylist
    assert "dispatchStatus" in denylist
    assert "claude_session_id = %s" in calls[1][0]
    assert calls[1][1] == ("opaque-session", "contract-v1", "thread", 7)

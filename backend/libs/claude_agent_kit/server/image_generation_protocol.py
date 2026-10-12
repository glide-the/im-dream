# [Sync] 2026-10-10: bind image operation/model ownership and preserve real call identity through original authorization, files and history.
# [Sync] 2026-10-10: preserve actual Gateway request identity separately from broker identity, with optional old-history compatibility.
# [Input] Prompt and current-Thread workspace references over the existing private broker.
# [Output] Strict image tool input, request and small file-reference result DTOs.
# [Pos] Neutral image protocol shared by Host and image_gen stdio; contains no credentials.
# [Sync] 2026-10-10: add the Images tool contract without changing public Chat events.
from __future__ import annotations

import json
from typing import Annotated, Literal
from uuid import uuid4

from pydantic import BaseModel, ConfigDict, Field, field_validator
from .session_projection_protocol import SessionProjectionBrokerClient, SessionProjectionProtocolError

IMAGE_TOOL_NAME = "mcp__image_gen__imagegen"
IMAGE_SELECTION_TOOL_NAME = "mcp__image_gen__select_image_operation"
# Admin createPlatformId("req") owns this public Gateway identity contract.
GATEWAY_REQUEST_ID_PATTERN = r"^req_[0-9a-f]{32}$"
ReferenceURI = Annotated[str, Field(pattern=r"^workspace://files/[^\s?#]+$")]


class ImageToolInput(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    prompt: str = Field(min_length=1)
    reference_images: list[ReferenceURI]

    @field_validator("prompt")
    @classmethod
    def nonempty_prompt(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("Prompt is empty")
        return value


class ImageGenerationRequest(ImageToolInput):
    operation: Literal["image.generate"] = "image.generate"
    capability: str = Field(pattern=r"^[A-Za-z0-9_-]{43}$")
    request_id: str = Field(min_length=1, max_length=160, pattern=r"^[A-Za-z0-9._:-]+$")
    source_call_id: str | None = Field(default=None, min_length=1, max_length=200, pattern=r"^[A-Za-z0-9._:-]+$")


class ImageSelectionInput(ImageToolInput):
    operation: Literal["none", "unclear", "native_generate", "native_edit", "image_gen_generate", "image_gen_edit"]


class ImageSelectionRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    operation: Literal["image.select"] = "image.select"
    capability: str = Field(pattern=r"^[A-Za-z0-9_-]{43}$")
    request_id: str = Field(min_length=1, max_length=160, pattern=r"^[A-Za-z0-9._:-]+$")
    source_call_id: str = Field(min_length=1, max_length=200, pattern=r"^[A-Za-z0-9._:-]+$")
    arguments: ImageSelectionInput


class GeneratedImage(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    uri: ReferenceURI
    alt: str
    mediaType: Literal["image/png", "image/jpeg", "image/webp"]


class ImageGenerationResult(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    kind: Literal["image-generation-result"] = "image-generation-result"
    version: Literal[1] = 1
    requestId: str
    # Optional when reading original v1 results; newly executed calls carry the
    # actual Admin Gateway response identity independently of the broker ID.
    gatewayRequestId: str | None = Field(default=None, pattern=GATEWAY_REQUEST_ID_PATTERN)
    responseId: str | None = Field(default=None, min_length=1, max_length=200, pattern=r"^[A-Za-z0-9._:-]+$")
    outputIndex: int | None = Field(default=None, ge=0)
    operation: Literal["generate", "edit"] | None = None
    images: list[GeneratedImage] = Field(min_length=1)


def request_image(client: SessionProjectionBrokerClient, arguments: dict, source_call_id: str | None = None) -> ImageGenerationResult:
    # The MCP transport request and the SDK toolCallId are distinct identifiers.
    request_id = str(uuid4())
    request = ImageGenerationRequest(**arguments, capability=client._capability, request_id=request_id, source_call_id=source_call_id)
    raw = client._round_trip(request, request_id)
    response = json.loads(raw)
    if response.get("ok") is not True:
        error = response.get("error") or {}
        raise SessionProjectionProtocolError(error.get("code", "IMAGE_REQUEST_FAILED"), error.get("status_code", 503), request_id)
    if set(response) != {"ok", "result"}:
        raise SessionProjectionProtocolError("IMAGE_RESULT_INVALID", 502, request_id)
    result = ImageGenerationResult.model_validate(response["result"])
    if result.requestId != request_id:
        raise SessionProjectionProtocolError("IMAGE_RESULT_INVALID", 502, request_id)
    return result


def request_image_selection(client: SessionProjectionBrokerClient, arguments: dict, source_call_id: str) -> dict:
    request_id = str(uuid4())
    request = ImageSelectionRequest(arguments=arguments, source_call_id=source_call_id, capability=client._capability, request_id=request_id)
    response = json.loads(client._round_trip(request, request_id))
    if response.get("ok") is not True:
        error = response.get("error") or {}
        raise SessionProjectionProtocolError(error.get("code", "IMAGE_SELECTION_FAILED"), error.get("status_code", 503), request_id)
    if set(response) != {"ok", "result"} or not isinstance(response["result"], dict):
        raise SessionProjectionProtocolError("IMAGE_RESULT_INVALID", 502, request_id)
    return response["result"]

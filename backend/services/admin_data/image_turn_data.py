# [Sync] 2026-10-10: bind image operation/model ownership and preserve real call identity through original authorization, files and history.
# [Input] Exact Admin image-turn contracts and the current server-persistence grant.
# [Output] Immutable binding/selection and verified native-result facts with original receipt-only recovery.
# [Pos] Image-only adapter; its unknown-write state never blocks unrelated assistant/session persistence.
# [Sync] 2026-10-10: keep actual source call, file hash and Gateway result identities independent.
# [Sync] 2026-10-26: recover a definite same-message bind conflict from the original immutable receipt when only the Runtime attempt ID changed.
from __future__ import annotations

import hashlib
import json
from threading import RLock
from typing import Annotated, Literal
from uuid import uuid4

from pydantic import Field, field_validator
from .client import AdminDataClient, DomainOperation
from .errors import AdminDataError, invalid_response
from .models import OperationCapabilityDTO, SchemaCapabilityDTO, StrictDTO, CommittedReceiptDTO

CallId = Annotated[str, Field(min_length=1, max_length=200, pattern=r"^[A-Za-z0-9._:-]+$")]
TurnKey = Annotated[str, Field(pattern=r"^dream-turn-[0-9a-f]{64}$")]
Digest = Annotated[str, Field(pattern=r"^[0-9a-f]{64}$")]
Reference = Annotated[str, Field(pattern=r"^workspace://files/[^\s?#]+$")]
Alias = Annotated[str, Field(min_length=1, max_length=120, pattern=r"^[A-Za-z0-9][A-Za-z0-9._:-]*$")]
GatewayId = Annotated[str, Field(pattern=r"^req_[0-9a-f]{32}$")]
ImageOperation = Literal["none", "unclear", "native_generate", "native_edit", "image_gen_generate", "image_gen_edit"]


def image_input_digest(value) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, ensure_ascii=False, separators=(",", ":"), allow_nan=False).encode()).hexdigest()


def image_receipt_key(turn_key: str) -> str:
    return image_input_digest([turn_key, ""])


def image_material_header(turn_key: str, message_id: str) -> str:
    return f"[Ink image materials: {turn_key} {message_id}]"


class ImageMaterialDTO(StrictDTO):
    uri: Reference
    sha256: Digest


class ImageTurnBindInputDTO(StrictDTO):
    thread_id: CallId
    turn_id: CallId
    turn_key: TurnKey
    message_id: CallId
    ai_model: Alias
    image_model: Alias | None
    materials: list[ImageMaterialDTO]


class ImageTurnBindOutputDTO(ImageTurnBindInputDTO):
    canonical_user_id: Annotated[str, Field(pattern=r"^[1-9][0-9]*$")]
    run_id: CallId | None


class ImageSelectionArgumentsDTO(StrictDTO):
    operation: ImageOperation
    prompt: str = Field(min_length=1)
    reference_images: list[Reference]

    @field_validator("prompt")
    @classmethod
    def nonempty_prompt(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("Empty prompt")
        return value


class ImageTurnSelectInputDTO(StrictDTO):
    thread_id: CallId
    turn_key: TurnKey
    source_call_id: CallId
    arguments: ImageSelectionArgumentsDTO


class ImageTurnSelectOutputDTO(StrictDTO):
    turn_key: TurnKey
    source_call_id: CallId
    operation: ImageOperation
    arguments_sha256: Digest
    reference_images: list[Reference]


class NativeImageCallDTO(StrictDTO):
    callId: CallId
    outputIndex: int = Field(ge=0)
    status: Literal["completed"]
    operation: Literal["generate", "edit"]
    reportedAction: Literal["generate", "edit"] | None
    format: Literal["png", "jpeg", "webp"]
    byteLength: int = Field(gt=0)
    sha256: Digest


class NativeImageSummaryDTO(StrictDTO):
    gatewayRequestId: GatewayId
    responseId: CallId
    providerHttpRequestId: CallId | None
    configuredImageModel: str | None
    reportedImageModel: None
    usageKnown: Literal[False]
    usageUnknownReason: Literal["responses_image_usage_not_reported"]
    imageCalls: list[NativeImageCallDTO] = Field(min_length=1)


class ImageTurnResultInputDTO(StrictDTO):
    thread_id: CallId
    turn_key: TurnKey
    gateway_request_id: GatewayId
    call_id: CallId


def _operation(name, kind, digest, input_type, output_type):
    return DomainOperation(OperationCapabilityDTO(name=name, kind=kind, user_scope="dream:write", background_scope=None,
        input_schema_version=1, output_schema_version=1, contract_sha256=digest), input_type, output_type)


BIND_IMAGE_TURN = _operation("image-turn.bind", "write", "b65b67e0eed869a30081251a648bd5fa40e922478efdae8a1c66a97aef1dcf45", ImageTurnBindInputDTO, ImageTurnBindOutputDTO)
SELECT_IMAGE_OPERATION = _operation("image-turn.select", "write", "d6b342bc0992c80b7db91353d2c56235013d417c2146dca9faa2dd22b2276814", ImageTurnSelectInputDTO, ImageTurnSelectOutputDTO)
READ_NATIVE_IMAGE_RESULT = _operation("image-turn.result", "read", "be0cf93f9b947031371e82d4180ac16661bf08e85838b49bdb01d14ee45dd99f", ImageTurnResultInputDTO, NativeImageSummaryDTO)
IMAGE_TURN_OPERATIONS = (BIND_IMAGE_TURN, SELECT_IMAGE_OPERATION, READ_NATIVE_IMAGE_RESULT)
IMAGE_TURN_SCHEMA = SchemaCapabilityDTO(capability="dream.image-turn.v1", version=1,
    contract_sha256="2f7e1eedb84d974b6bf203611acaf22b00d1cb82e377276a73822e73253f96e2")


class AdminImageTurnData:
    def __init__(self, client: AdminDataClient, grant_provider, *, canonical_user_id: str):
        self._client, self._grant_provider = client, grant_provider
        self._canonical_user_id = canonical_user_id
        self._lock = RLock()
        self._pending = None

    def ready(self) -> bool:
        return self._client.supports(IMAGE_TURN_OPERATIONS, (IMAGE_TURN_SCHEMA,))

    def _execute(self, operation, input_dto):
        if not self.ready():
            raise AdminDataError("IMAGE_TURN_CONFIGURATION_UNAVAILABLE", 503)
        grant = self._grant_provider()
        if grant.purpose != "server-persistence" or grant.thread_id != input_dto.thread_id:
            raise AdminDataError("IMAGE_TURN_AUTHORITY_REQUIRED", 403)
        key = image_receipt_key(input_dto.turn_key) if operation.capability.kind == "write" else str(uuid4())
        with self._lock:
            if self._pending is not None:
                old_operation, old_input, old_key = self._pending
                if (operation, input_dto, key) != self._pending:
                    raise AdminDataError("IMAGE_TURN_OUTCOME_UNKNOWN", 503, old_key, True)
                receipt = self._client.receipt(old_operation, old_key, access_token=grant.token)
                if not isinstance(receipt, CommittedReceiptDTO):
                    raise AdminDataError("IMAGE_TURN_OUTCOME_UNKNOWN", 503, old_key, True)
                result = receipt.result
            else:
                try:
                    result = self._client.execute(operation, input_dto, key, access_token=grant.token)
                except AdminDataError as error:
                    if operation.capability.kind == "write" and error.outcome_unknown:
                        self._pending = (operation, input_dto, key)
                    raise
            if operation is BIND_IMAGE_TURN and (result.model_dump(exclude={"canonical_user_id", "run_id"}) != input_dto.model_dump()
                or result.canonical_user_id != self._canonical_user_id or result.run_id != grant.run_id):
                self._pending = (operation, input_dto, key)
                raise invalid_response(key, write=True)
            if operation is SELECT_IMAGE_OPERATION and (result.turn_key != input_dto.turn_key or result.source_call_id != input_dto.source_call_id
                or result.operation != input_dto.arguments.operation or result.reference_images != input_dto.arguments.reference_images
                or result.arguments_sha256 != image_input_digest(input_dto.arguments.model_dump())):
                self._pending = (operation, input_dto, key)
                raise invalid_response(key, write=True)
            if operation is READ_NATIVE_IMAGE_RESULT and (result.gatewayRequestId != input_dto.gateway_request_id
                or not any(call.callId == input_dto.call_id for call in result.imageCalls)):
                raise invalid_response(key)
            self._pending = None
            return result

    def bind(self, input_dto: ImageTurnBindInputDTO) -> ImageTurnBindOutputDTO:
        with self._lock:
            try:
                return self._execute(BIND_IMAGE_TURN, input_dto)
            except AdminDataError as error:
                if error.code != "OPERATION_REQUEST_CONFLICT" or error.status_code != 409 or error.outcome_unknown:
                    raise
                grant = self._grant_provider()
                if grant.purpose != "server-persistence" or grant.thread_id != input_dto.thread_id:
                    raise AdminDataError("IMAGE_TURN_AUTHORITY_REQUIRED", 403) from None
                key = image_receipt_key(input_dto.turn_key)
                receipt = self._client.receipt(BIND_IMAGE_TURN, key, access_token=grant.token)
                if (not isinstance(receipt, CommittedReceiptDTO) or receipt.request_id != key
                    or receipt.operation != BIND_IMAGE_TURN.capability.name
                    or not isinstance(receipt.result, ImageTurnBindOutputDTO)):
                    raise error
                result = receipt.result
                # The receipt owns the first attempt ID. Reuse that fact for
                # the same saved message without replacing the Factory's new
                # attempt, the stable Gateway key or any persisted binding.
                if (result.model_dump(exclude={"turn_id", "canonical_user_id", "run_id"})
                    != input_dto.model_dump(exclude={"turn_id"})
                    or result.canonical_user_id != self._canonical_user_id or result.run_id != grant.run_id):
                    raise error
                return result

    def select(self, input_dto: ImageTurnSelectInputDTO) -> ImageTurnSelectOutputDTO:
        return self._execute(SELECT_IMAGE_OPERATION, input_dto)

    def result(self, input_dto: ImageTurnResultInputDTO) -> NativeImageSummaryDTO:
        return self._execute(READ_NATIVE_IMAGE_RESULT, input_dto)

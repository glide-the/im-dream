# [Sync] 2026-10-12: turn-owned HTTP cancellation closes the original Images socket before headers/body and fences late publication.
# [Sync] 2026-10-10: bind image operation/model ownership and preserve real call identity through original authorization, files and history.
# [Sync] 2026-10-10: separate saved AI/Image ownership; native result publication and explicit Images execution share exact turn identity, with real acceptance pending.
# [Input] Server-bound Thread workspace, renewing Gateway runtime, image catalog and Images responses.
# [Output] Verified new image files and small per-call results; no secret or base64 leaves Host.
# [Pos] Chat image executor using existing Admin public Images, file and authorization contracts.
# [Sync] 2026-10-10: implement generation/editing with bounded decoding, no HTTP replay and cancellation fencing.
# [Sync] 2026-10-10: align publication and reference reads with the public workspace://files/ namespace.
from __future__ import annotations

import asyncio
import base64
import hashlib
import io
import json
import os
from pathlib import Path, PurePosixPath
import re
import threading
from urllib.parse import unquote
from uuid import uuid4

from PIL import Image
import httpx
import requests
from pydantic import ValidationError

from libs.claude_agent_kit.server.image_generation_protocol import GATEWAY_REQUEST_ID_PATTERN, GeneratedImage, ImageGenerationRequest, ImageGenerationResult, ImageToolInput, IMAGE_TOOL_NAME, IMAGE_SELECTION_TOOL_NAME
from services.admin_data.image_turn_data import ImageTurnBindInputDTO, ImageTurnSelectInputDTO, ImageTurnResultInputDTO, image_input_digest
from libs.claude_agent_kit.server.workspace import read_workspace_file_content
from services.admin_data.errors import AdminDataError
from .config import AdminGatewayConfig
from .models import GatewayModelCatalogClient
from .errors import GatewayInferenceError


def _bound(values, name, default):
    raw = values.get(name, str(default))
    if not isinstance(raw, str) or not raw.isdecimal() or int(raw) < 1:
        raise AdminDataError("IMAGE_CONFIGURATION_INVALID", 503)
    return int(raw)


class ImageGenerationProvider:
    def __init__(self, *, workspace: str, runtime, turn_key: str, model_alias: str | None = None, configuration=None, environment=None, transport=None):
        values = os.environ if environment is None else environment
        self.configuration = configuration or AdminGatewayConfig.from_environment(values)
        self.workspace = Path(workspace)
        if not self.configuration.enabled or not self.workspace.is_absolute() or self.workspace.is_symlink() or self.workspace.resolve() != self.workspace:
            raise AdminDataError("IMAGE_CONFIGURATION_INVALID", 503)
        self.timeout = _bound(values, "INK_IMAGE_TIMEOUT_SECONDS", 600)
        self.max_bytes = _bound(values, "INK_IMAGE_MAX_BYTES", 32 * 1024 * 1024)
        self.max_response_bytes = _bound(values, "INK_IMAGE_MAX_RESPONSE_BYTES", 64 * 1024 * 1024)
        self.max_pixels = _bound(values, "INK_IMAGE_MAX_PIXELS", 50_000_000)
        # The Settings snapshot owns this choice; env/default/single-candidate
        # routing must not silently replace the user's Image model.
        self._model_alias = model_alias.strip() if isinstance(model_alias, str) else ""
        self.runtime, self.turn_key, self.transport = runtime, turn_key, transport
        self._lock = threading.RLock()
        self._request_lock = threading.Lock()
        self._closed = False
        self._http_task = None
        self._published: dict[str, tuple[dict, ImageGenerationResult]] = {}
        self._requests: set[str] = set()
        self._image_turn_data = None
        self._thread_id = None
        self._ai_model = None
        self._selection = None
        self._pending_image_calls: dict[str, tuple[str, dict]] = {}
        self._native_calls: set[str] = set()
        # Pin identity so a renamed/replaced Thread directory cannot receive results.
        st = self.workspace.stat()
        self._root_identity = (st.st_dev, st.st_ino)

    def close(self):
        with self._lock:
            if self._closed:
                return
            self._closed = True
            owned = self._http_task
        if owned is not None:
            loop, task = owned
            try:
                loop.call_soon_threadsafe(task.cancel)
            except RuntimeError:
                # The same worker already closed its own loop.
                pass

    async def _read_http_response(self, url, headers, kwargs):
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            async with client.stream("POST", url, headers=headers, **kwargs) as upstream:
                response = requests.Response()
                response.status_code = upstream.status_code
                response.headers.update(upstream.headers)
                raw = bytearray()
                if upstream.status_code == 200:
                    async for chunk in upstream.aiter_bytes():
                        self._active()
                        raw.extend(chunk)
                        if len(raw) > self.max_response_bytes:
                            raise AdminDataError("IMAGE_RESULT_TOO_LARGE", 502)
                response._content = bytes(raw)
                response._content_consumed = True
                return response

    def _post_image(self, url, headers, kwargs):
        if self.transport is not None:
            return self.transport.post(url, headers=headers, timeout=self.timeout, stream=True, **kwargs)
        loop = asyncio.new_event_loop()
        task = None
        try:
            with self._lock:
                self._active()
                task = loop.create_task(self._read_http_response(url, headers, kwargs))
                self._http_task = (loop, task)
            return loop.run_until_complete(task)
        except asyncio.CancelledError:
            raise AdminDataError("IMAGE_CANCELLED", 409) from None
        finally:
            with self._lock:
                if self._http_task is not None and self._http_task == (loop, task):
                    self._http_task = None
            loop.close()

    @property
    def model_alias(self) -> str:
        return self._model_alias

    def _active(self):
        with self._lock:
            if self._closed:
                raise AdminDataError("IMAGE_CANCELLED", 409)

    def _decode(self, data: bytes, *, allow_gif=False):
        if len(data) > self.max_bytes:
            raise AdminDataError("IMAGE_SIZE_EXCEEDED", 413)
        try:
            with Image.open(io.BytesIO(data)) as image:
                if image.format not in ({"PNG", "JPEG", "WEBP", "GIF"} if allow_gif else {"PNG", "JPEG", "WEBP"}) or image.width * image.height > self.max_pixels:
                    raise ValueError("Unsupported format or pixel count")
                image.load()
                return {"PNG": ("png", "image/png"), "JPEG": ("jpg", "image/jpeg"), "WEBP": ("webp", "image/webp"), "GIF": ("gif", "image/gif")}[image.format]
        except Exception:
            raise AdminDataError("IMAGE_DECODE_INVALID", 502) from None

    def _reference(self, uri: str, *, allow_gif=False):
        path = unquote(uri.removeprefix("workspace://"))
        parts = PurePosixPath(path).parts
        if not parts or path.startswith("/") or "\\" in path or "\x00" in path or any(part.startswith(".") for part in parts):
            raise AdminDataError("IMAGE_REFERENCE_DENIED", 403)
        try:
            content = read_workspace_file_content(self.workspace, path, reject_symlinks=True, require_regular_file=True, max_bytes=self.max_bytes, expected_root_identity=self._root_identity)
        except Exception:
            raise AdminDataError("IMAGE_REFERENCE_UNAVAILABLE", 403) from None
        ext, media = self._decode(content.content, allow_gif=allow_gif)
        return (f"reference.{ext}", content.content, media)

    def bind_turn(self, data, *, thread_id: str, turn_id: str, turn_key: str, message_id: str, ai_model: str, materials: list[str]):
        self._active()
        if self._image_turn_data is not None or len(materials) != len(set(materials)):
            raise AdminDataError("IMAGE_TURN_CONFLICT", 409)
        facts = [{"uri": uri, "sha256": hashlib.sha256(self._reference(uri, allow_gif=True)[1]).hexdigest()} for uri in materials]
        data.bind(ImageTurnBindInputDTO(thread_id=thread_id, turn_id=turn_id, turn_key=turn_key,
            message_id=message_id, ai_model=ai_model, image_model=self.model_alias or None, materials=facts))
        self._image_turn_data, self._thread_id, self.turn_key = data, thread_id, turn_key
        self._ai_model = ai_model

    @property
    def selected_operation(self):
        return self._selection.operation if self._selection is not None else None

    def authorize_tool(self, name: str, call_id: str, arguments: dict):
        self._active()
        if self._image_turn_data is None or not isinstance(call_id, str) or re.fullmatch(r"[A-Za-z0-9._:-]{1,200}", call_id) is None:
            raise AdminDataError("IMAGE_CALL_NOT_AUTHORIZED", 403)
        if name == IMAGE_TOOL_NAME:
            checked = ImageToolInput.model_validate(arguments).model_dump()
            if self._selection is None or not self._selection.operation.startswith("image_gen_") or checked != self._selection_arguments:
                raise AdminDataError("IMAGE_TURN_SELECTION_MISMATCH", 409)
        elif name == IMAGE_SELECTION_TOOL_NAME:
            from services.admin_data.image_turn_data import ImageSelectionArgumentsDTO
            checked = ImageSelectionArgumentsDTO.model_validate(arguments).model_dump()
        else:
            raise AdminDataError("IMAGE_CALL_NOT_AUTHORIZED", 403)
        with self._lock:
            prior = self._pending_image_calls.get(call_id)
            if prior is not None and prior != (name, checked):
                raise AdminDataError("IMAGE_CALL_NOT_AUTHORIZED", 403)
            self._pending_image_calls[call_id] = (name, checked)

    def _take_call(self, name, call_id, arguments):
        with self._lock:
            self._active()
            pending = self._pending_image_calls.pop(call_id, None)
            if pending != (name, arguments):
                raise AdminDataError("IMAGE_CALL_NOT_AUTHORIZED", 403)

    def select(self, request):
        arguments = request.arguments.model_dump()
        self._take_call(IMAGE_SELECTION_TOOL_NAME, request.source_call_id, arguments)
        if arguments["operation"].startswith("native_"):
            try:
                catalog = GatewayModelCatalogClient(access_token=self.runtime.access_token(), configuration=self.configuration, transport=self.transport or requests).fetch_catalog()
            except GatewayInferenceError as error:
                raise AdminDataError(error.code, error.status_code) from None
            selected = next((model for model in catalog.models if model.model_alias == self._ai_model), None)
            capabilities = selected.responses_image if selected is not None else None
            action = "edit" if arguments["operation"] == "native_edit" else "generation"
            if selected is None or not capabilities or not capabilities.get(action) or not capabilities.get("callable"):
                raise AdminDataError("AI_MODEL_IMAGE_OPERATION_UNAVAILABLE", 409)
        selection = self._image_turn_data.select(ImageTurnSelectInputDTO(thread_id=self._thread_id, turn_key=self.turn_key,
            source_call_id=request.source_call_id, arguments=arguments))
        self._selection, self._selection_arguments = selection, {key: arguments[key] for key in ("prompt", "reference_images")}
        return {"operation": selection.operation, "source_call_id": selection.source_call_id,
            "instruction": "Continue the conversation; the selected AI model performs the native image operation." if selection.operation.startswith("native_")
            else "Call imagegen with the same prompt and material." if selection.operation.startswith("image_gen_")
            else "No image operation was started. Reply to the user or explain what operation or material is missing."}

    def publish_native(self, block):
        self._active()
        if self._image_turn_data is None or not isinstance(block, dict):
            raise AdminDataError("IMAGE_RESULT_INVALID", 502)
        call_id, gateway_id = block.get("tool_use_id"), block.get("gateway_request_id")
        summary = self._image_turn_data.result(ImageTurnResultInputDTO(thread_id=self._thread_id,
            turn_key=self.turn_key, gateway_request_id=gateway_id, call_id=call_id))
        if summary.responseId != block.get("response_id") or self._selection is None or not self._selection.operation.startswith("native_"):
            raise AdminDataError("IMAGE_RESULT_INVALID", 502)
        call = next(value for value in summary.imageCalls if value.callId == call_id)
        if call.operation != self._selection.operation.removeprefix("native_"):
            raise AdminDataError("IMAGE_RESULT_INVALID", 502)
        content = block.get("content")
        if not isinstance(content, list) or len(content) != 1 or not isinstance(content[0], dict) or content[0].get("type") != "image":
            raise AdminDataError("IMAGE_RESULT_INVALID", 502)
        source = content[0].get("source", {})
        if not isinstance(source, dict) or source.get("type") != "base64" or not isinstance(source.get("data"), str) or len(source["data"]) > (self.max_bytes + 2) // 3 * 4:
            raise AdminDataError("IMAGE_RESULT_INVALID", 502)
        try:
            data = base64.b64decode(source["data"], validate=True)
        except Exception:
            raise AdminDataError("IMAGE_RESULT_INVALID", 502) from None
        ext, media = self._decode(data)
        if source.get("media_type") != media or call.byteLength != len(data) or call.sha256 != hashlib.sha256(data).hexdigest():
            raise AdminDataError("IMAGE_RESULT_INVALID", 502)
        with self._lock:
            if call_id in self._native_calls:
                raise AdminDataError("IMAGE_RESULT_ALREADY_PUBLISHED", 409)
            self._native_calls.add(call_id)
        from types import SimpleNamespace
        return self._publish(SimpleNamespace(request_id=call_id, prompt="Native image operation", reference_images=[]), [(data, ext, media)], gateway_id,
            response_id=summary.responseId, output_index=call.outputIndex, operation=call.operation)

    def _model(self, token, editing):
        if not self.model_alias:
            raise AdminDataError("IMAGE_MODEL_NOT_SELECTED", 409)
        try:
            catalog = GatewayModelCatalogClient(access_token=token, configuration=self.configuration, transport=self.transport or requests).fetch_catalog()
        except GatewayInferenceError as error:
            raise AdminDataError(error.code, error.status_code) from None
        selected = next((m for m in catalog.models if m.model_alias == self.model_alias), None)
        if selected is None:
            raise AdminDataError("IMAGE_MODEL_SELECTION_STALE", 409)
        if not (selected.image_edit if editing else selected.image_generation):
            raise AdminDataError("IMAGE_MODEL_OPERATION_UNSUPPORTED", 409)
        if not selected.image_callable:
            raise AdminDataError("IMAGE_MODEL_UNAVAILABLE", 403)
        return selected.model_alias

    def generate(self, request: ImageGenerationRequest) -> ImageGenerationResult:
        with self._request_lock:
            self._active()
            self._take_call(IMAGE_TOOL_NAME, request.source_call_id, ImageToolInput(prompt=request.prompt, reference_images=request.reference_images).model_dump())
            with self._lock:
                if request.request_id in self._requests:
                    raise AdminDataError("IMAGE_REQUEST_ALREADY_DISPATCHED", 409)
                self._requests.add(request.request_id)
            references = []
            reference_bytes = 0
            for uri in request.reference_images:
                self._active()
                reference = self._reference(uri)
                reference_bytes += len(reference[1])
                if reference_bytes > self.max_bytes:
                    raise AdminDataError("IMAGE_SIZE_EXCEEDED", 413)
                references.append(reference)
            if not self.runtime.allows("images:create"):
                raise AdminDataError("IMAGE_SCOPE_REQUIRED", 403)
            token = self.runtime.access_token()
            model = self._model(token, bool(references))
            headers = {"authorization": f"Bearer {token}", "x-api-key": self.configuration.service_key, "accept": "application/json", "Idempotency-Key": "dream-image-" + hashlib.sha256(f"{self.turn_key}\n{request.request_id}".encode()).hexdigest()}
            headers.update({"x-ink-image-turn-key": self.turn_key, "x-ink-image-selection-call-id": self._selection.source_call_id,
                "x-ink-image-tool-call-id": request.source_call_id, "x-ink-image-reference-uris": json.dumps(request.reference_images, separators=(",", ":"))})
            body = {"model": model, "prompt": request.prompt}
            self._active()
            try:
                kwargs = {"data": body, "files": [("image[]", reference) for reference in references]} if references else {"json": body}
                with self._post_image(f"{self.configuration.base_url}/v1/images/{'edits' if references else 'generations'}", headers, kwargs) as response:
                    if response.status_code != 200:
                        # Do not read or echo upstream rejection bodies.
                        raise AdminDataError("IMAGE_GATEWAY_REQUEST_FAILED", response.status_code)
                    gateway_request_id = response.headers.get("x-request-id")
                    if not isinstance(gateway_request_id, str) or re.fullmatch(GATEWAY_REQUEST_ID_PATTERN, gateway_request_id) is None:
                        raise AdminDataError("IMAGE_GATEWAY_RESPONSE_INVALID", 502) from None
                    raw = bytearray()
                    for chunk in response.iter_content(65536):
                        self._active()
                        raw.extend(chunk)
                        if len(raw) > self.max_response_bytes:
                            raise AdminDataError("IMAGE_RESULT_TOO_LARGE", 502)
            except AdminDataError:
                raise
            except Exception:
                raise AdminDataError("IMAGE_REQUEST_OUTCOME_UNKNOWN", 503) from None
            self._active()
            try:
                payload = json.loads(raw)
                entries = payload["data"]
                if not isinstance(entries, list) or not entries:
                    raise ValueError("No images")
                decoded = []
                for entry in entries:
                    encoded = entry["b64_json"]
                    if not isinstance(encoded, str) or len(encoded) > (self.max_bytes + 2) // 3 * 4:
                        raise ValueError("Invalid image bytes")
                    data = base64.b64decode(encoded, validate=True)
                    ext, media = self._decode(data)
                    decoded.append((data, ext, media))
            except AdminDataError:
                raise
            except Exception:
                raise AdminDataError("IMAGE_RESULT_INVALID", 502) from None
            return self._publish(request, decoded, gateway_request_id)

    def _publish(self, request, decoded, gateway_request_id, *, response_id=None, output_index=None, operation=None):
        # Cancellation and publishing share a lock: close fences all future file publication.
        with self._lock:
            self._active()
            root_fd = files_fd = directory_fd = -1
            created = []
            temp = None
            try:
                flags = os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW
                root_fd = os.open(self.workspace, flags)
                st = os.fstat(root_fd)
                if (st.st_dev, st.st_ino) != self._root_identity:
                    raise ValueError("Workspace replaced")
                try:
                    os.mkdir("files", mode=0o700, dir_fd=root_fd)
                except FileExistsError:
                    pass
                files_fd = os.open("files", flags, dir_fd=root_fd)
                try:
                    os.mkdir("generated", mode=0o700, dir_fd=files_fd)
                except FileExistsError:
                    pass
                directory_fd = os.open("generated", flags, dir_fd=files_fd)
                images = []
                for data, ext, media in decoded:
                    name = f"{uuid4().hex}.{ext}"
                    temp = f".{uuid4().hex}.tmp"
                    fd = os.open(temp, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600, dir_fd=directory_fd)
                    with os.fdopen(fd, "wb") as handle:
                        handle.write(data)
                        handle.flush()
                        os.fsync(handle.fileno())
                    os.link(temp, name, src_dir_fd=directory_fd, dst_dir_fd=directory_fd, follow_symlinks=False)
                    created.append(name)
                    os.unlink(temp, dir_fd=directory_fd)
                    temp = None
                    images.append(GeneratedImage(uri=f"workspace://files/generated/{name}", alt="Generated image", mediaType=media))
                os.fsync(directory_fd)
                result = ImageGenerationResult(requestId=request.request_id, gatewayRequestId=gateway_request_id, images=images,
                    responseId=response_id, outputIndex=output_index, operation=operation)
                self._published[request.request_id] = (ImageToolInput(prompt=request.prompt, reference_images=request.reference_images).model_dump(), result)
                return result
            except Exception:
                for name in created + ([temp] if temp else []):
                    try:
                        os.unlink(name, dir_fd=directory_fd)
                    except OSError:
                        pass
                raise AdminDataError("IMAGE_FILE_SAVE_FAILED", 503) from None
            finally:
                for fd in (directory_fd, files_fd, root_fd):
                    if fd >= 0:
                        os.close(fd)

    def consume_result(self, output, tool_input) -> ImageGenerationResult | None:
        try:
            if isinstance(output, str):
                output = json.loads(output)
            result = ImageGenerationResult.model_validate(output)
            arguments = ImageToolInput.model_validate(tool_input).model_dump()
        except (ValidationError, ValueError, TypeError):
            return None
        with self._lock:
            if self._closed:
                return None
            owned = self._published.get(result.requestId)
            if owned is None or owned != (arguments, result):
                return None
            self._published.pop(result.requestId)
            return result

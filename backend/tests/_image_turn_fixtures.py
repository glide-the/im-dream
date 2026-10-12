# [Input] Production image-turn DTOs and a test-owned Host/broker.
# [Output] Injected Admin data boundary and explicit bind/select/Hook steps for provider-free tests.
# [Pos] Test fixture only; it does not implement an alternate runtime or Gateway state machine.
# [Sync] 2026-10-10: make saved-turn and actual tool ID authorization prerequisites visible in tests.
from types import SimpleNamespace
from uuid import uuid4
import hashlib

from libs.claude_agent_kit.server.image_generation_protocol import (
    IMAGE_TOOL_NAME, IMAGE_SELECTION_TOOL_NAME, ImageSelectionRequest, ImageSelectionInput,
    request_image as raw_request_image,
)
from services.admin_data.image_turn_data import (
    ImageTurnBindOutputDTO, ImageTurnSelectOutputDTO, image_input_digest,
)


class ImageDataFixture:
    def __init__(self):
        self.binding = None
        self.selection = None
        self.native_summary = None

    def ready(self):
        return True

    def bind(self, dto):
        result = ImageTurnBindOutputDTO(**dto.model_dump(), canonical_user_id='7', run_id=None)
        assert self.binding is None or self.binding == result
        self.binding = result
        return result

    def select(self, dto):
        assert self.binding is not None and dto.turn_key == self.binding.turn_key
        assert set(dto.arguments.reference_images) <= {item.uri for item in self.binding.materials}
        result = ImageTurnSelectOutputDTO(turn_key=dto.turn_key, source_call_id=dto.source_call_id,
            operation=dto.arguments.operation, arguments_sha256=image_input_digest(dto.arguments.model_dump()),
            reference_images=dto.arguments.reference_images)
        assert self.selection is None or self.selection == result
        self.selection = result
        return result

    def result(self, dto):
        assert self.native_summary.gatewayRequestId == dto.gateway_request_id
        assert any(call.callId == dto.call_id for call in self.native_summary.imageCalls)
        return self.native_summary


def bind_provider(provider, args, *, data=None):
    if provider._image_turn_data is None:
        provider.bind_turn(data or ImageDataFixture(), thread_id='image-thread', turn_id='turn',
            turn_key='dream-turn-' + hashlib.sha256(uuid4().bytes).hexdigest(), message_id='message',
            ai_model='ai-model', materials=args['reference_images'])


def select_provider(provider, args, *, operation=None, capability='a' * 43):
    args.setdefault('reference_images', [])
    bind_provider(provider, args)
    choice = dict(args, operation=operation or ('image_gen_edit' if args['reference_images'] else 'image_gen_generate'))
    call_id = 'selection-' + uuid4().hex
    provider.authorize_tool(IMAGE_SELECTION_TOOL_NAME, call_id, choice)
    provider.select(ImageSelectionRequest(capability=capability, request_id=str(uuid4()), source_call_id=call_id,
        arguments=ImageSelectionInput.model_validate(choice)))


def authorize_execution(provider, args, *, call_id=None):
    args.setdefault('reference_images', [])
    if provider.selected_operation is None:
        select_provider(provider, args)
    call_id = call_id or 'image-call-' + uuid4().hex
    provider.authorize_tool(IMAGE_TOOL_NAME, call_id, args)
    return call_id


def request_image(client, arguments):
    arguments.setdefault('reference_images', [])
    provider = client.fixture_image_provider
    call_id = authorize_execution(provider, arguments)
    return raw_request_image(client, arguments, source_call_id=call_id)

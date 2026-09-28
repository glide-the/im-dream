# [Sync] 2026-09-27: bind returning task creation to Admin's separate operation without changing side-task defaults.
# [Sync] 2026-09-27: bind task-session source/created navigation to its exact Admin operation hash.
# [Sync] 2026-09-27: bind task-session create/get/launch to exact Admin operation hashes.
# [Sync] 2026-09-26: bind queue enqueue/list/transition to exact Admin operation hashes.
# [Input] Exact Admin chat operation artifact and strict domain DTOs, with explicit user/turn credentials.
# [Output] Named typed Chat HTTP operations; original request IDs and receipt lookup remain explicit.
# [Pos] Chat domain consumer; never accepts user IDs, database rows, SQL or remote transaction handles.
# [Sync] 2026-09-14: pin actual 14 request/response candidates; production actor/delegation binding remains pending.
from __future__ import annotations

from .client import AdminDataClient, DomainOperation
from .models import OperationCapabilityDTO
from .errors import invalid_response
from . import chat_models as dto

CREATE_THREAD = DomainOperation(
    OperationCapabilityDTO(name='chat-thread.create', kind='write', user_scope='dream:write',
        background_scope=None, input_schema_version=1, output_schema_version=1,
        contract_sha256='19b04d55803cce164d1953792c1bd9ad7c321ab1d46d4463cd54b4e09d1c6f64'),
    dto.ThreadCreateInputDTO, dto.ThreadCreateResultDTO,
)
GET_THREAD = DomainOperation(
    OperationCapabilityDTO(name='chat-thread.get', kind='read', user_scope='dream:read',
        background_scope=None, input_schema_version=1, output_schema_version=1,
        contract_sha256='0a9fc326462f186660a9b4143b3eedf77de4a20666fa60ad159572d6b35a4cb7'),
    dto.ThreadIdInputDTO, dto.ThreadResultDTO,
)
LIST_THREADS = DomainOperation(
    OperationCapabilityDTO(name='chat-thread.list', kind='read', user_scope='dream:read',
        background_scope=None, input_schema_version=1, output_schema_version=1,
        contract_sha256='cf75d9de2e7c3426f9b6b4c374e4ea1e8be13d2204c2e0e1bcd4fff349ee1d49'),
    dto.ThreadListInputDTO, dto.ThreadListResultDTO,
)
SEARCH_THREADS = DomainOperation(
    OperationCapabilityDTO(name='chat-thread.search', kind='read', user_scope='dream:read',
        background_scope=None, input_schema_version=1, output_schema_version=1,
        contract_sha256='d9113d4abdcc5a8636a8ea38d1fb6b9f2b09867a4db616cb6db6d0c57b50ab0a'),
    dto.ThreadSearchInputDTO, dto.ThreadSearchResultDTO,
)
DELETE_THREAD = DomainOperation(
    OperationCapabilityDTO(name='chat-thread.delete', kind='write', user_scope='dream:write',
        background_scope=None, input_schema_version=1, output_schema_version=1,
        contract_sha256='b6f02853deb848208881982cf9f282993874d33da2b4b9675553740f5d74c573'),
    dto.ThreadIdInputDTO, dto.ChangedResultDTO,
)
BIND_DECK = DomainOperation(
    OperationCapabilityDTO(name='chat-thread.bind-deck', kind='write', user_scope='dream:write',
        background_scope=None, input_schema_version=1, output_schema_version=1,
        contract_sha256='0336658485ce06e867bfd0f2033e23243b36ed40c03bbcce60a992580332af16'),
    dto.ThreadBindDeckInputDTO, dto.ChangedResultDTO,
)
SELECT_VOICE = DomainOperation(
    OperationCapabilityDTO(name='chat-thread.select-voice', kind='write', user_scope='dream:write',
        background_scope=None, input_schema_version=1, output_schema_version=1,
        contract_sha256='a41cdb829390fdffcb76442be42229a3d1d3f63ef5b4cfe3887707746f94637a'),
    dto.ThreadSelectVoiceInputDTO, dto.ChangedResultDTO,
)
UPDATE_TITLE = DomainOperation(
    OperationCapabilityDTO(name='chat-thread.update-title', kind='write', user_scope='dream:write',
        background_scope=None, input_schema_version=1, output_schema_version=1,
        contract_sha256='4cffa38eabef5626b499e76919f5e91648f0d81dd332218d3cc311f9a4d7ab25'),
    dto.ThreadTitleInputDTO, dto.ChangedResultDTO,
)
UPDATE_SESSION = DomainOperation(
    OperationCapabilityDTO(name='chat-thread.update-session', kind='write', user_scope='dream:write',
        background_scope=None, input_schema_version=1, output_schema_version=1,
        contract_sha256='4bbfd190bb85af6878ec57fd765dff06dc5d96e82219919f359f7de41956ba0f'),
    dto.ThreadSessionInputDTO, dto.ChangedResultDTO,
)
PERSIST_MESSAGE = DomainOperation(
    OperationCapabilityDTO(name='chat-message.persist', kind='write', user_scope='dream:write',
        background_scope=None, input_schema_version=1, output_schema_version=1,
        contract_sha256='68380eb4a4e5ec4ab85f9e6ef47dcf757c77b5a9a0cf9f9d28b8f42dc92f0103'),
    dto.MessagePersistInputDTO, dto.MessagePersistResultDTO,
)
LIST_MESSAGES = DomainOperation(
    OperationCapabilityDTO(name='chat-message.list', kind='read', user_scope='dream:read',
        background_scope=None, input_schema_version=1, output_schema_version=1,
        contract_sha256='fff1487e9498c1dd925a6ceff211ae4d16ffc520a55e64829e1c0ea4bd967be0'),
    dto.ThreadIdInputDTO, dto.MessageListResultDTO,
)
MESSAGE_PAGE = DomainOperation(
    OperationCapabilityDTO(name='chat-message.page', kind='read', user_scope='dream:read',
        background_scope=None, input_schema_version=1, output_schema_version=1,
        contract_sha256='0ac7024eeac8117c90a8cc891113580b5897339ed2b6f653878001008d286fe8'),
    dto.MessagePageInputDTO, dto.MessagePageResultDTO,
)
PROCESS_DETAIL = DomainOperation(
    OperationCapabilityDTO(name='chat-message.process-detail', kind='read', user_scope='dream:read',
        background_scope=None, input_schema_version=1, output_schema_version=1,
        contract_sha256='8c981743d9b25c3032f11551e02b1d3d8d3c49be647a03ce4cfc0c17e113d209'),
    dto.MessageDetailInputDTO, dto.MessageDetailResultDTO,
)
LATEST_MESSAGE = DomainOperation(
    OperationCapabilityDTO(name='chat-message.latest', kind='read', user_scope='dream:read',
        background_scope=None, input_schema_version=1, output_schema_version=1,
        contract_sha256='d14f4edbe51b5c61f71c77f8200646cb5f9a2ea9d006743ff0586d2b39c5893a'),
    dto.ThreadIdInputDTO, dto.LatestMessageResultDTO,
)
ENQUEUE_INPUT = DomainOperation(
    OperationCapabilityDTO(name='chat-input.enqueue', kind='write', user_scope='dream:write',
        background_scope=None, input_schema_version=1, output_schema_version=1,
        contract_sha256='eb7bb85cd5e3726660264d5e8ff7ff94fdfbb7ebd9aa885a63473d74e639e087'),
    dto.QueueEnqueueInputDTO, dto.QueueEntryResultDTO,
)
LIST_INPUTS = DomainOperation(
    OperationCapabilityDTO(name='chat-input.list', kind='read', user_scope='dream:read',
        background_scope=None, input_schema_version=1, output_schema_version=1,
        contract_sha256='d672093facd591589bd2ee3099a9bbc4009b21a28292b1563f6fae38a19d5196'),
    dto.ThreadIdInputDTO, dto.QueueListResultDTO,
)
TRANSITION_INPUT = DomainOperation(
    OperationCapabilityDTO(name='chat-input.transition', kind='write', user_scope='dream:write',
        background_scope=None, input_schema_version=1, output_schema_version=1,
        contract_sha256='b79ef9d4c8c82de0ae9f7759b06300ac4585a90707661be5d1b5be6afe56edb4'),
    dto.QueueTransitionInputDTO, dto.QueueEntryResultDTO,
)
CREATE_TASK_SESSION = DomainOperation(
    OperationCapabilityDTO(name='task-session.create', kind='write', user_scope='dream:write',
        background_scope=None, input_schema_version=1, output_schema_version=1,
        contract_sha256='50a550fee373c57761d97b2cd56eada5fd4dfdcad4eaefa846b759ae29dcbefb'),
    dto.TaskSessionCreateInputDTO, dto.TaskSessionResultDTO,
)
CREATE_RETURNING_TASK_SESSION = DomainOperation(
    OperationCapabilityDTO(name='task-session.create-returning', kind='write', user_scope='dream:write',
        background_scope=None, input_schema_version=1, output_schema_version=1,
        contract_sha256='1bfce994c2c010b1fc0502c83622a261ef822c33662de32db983cc2b7b3564cf'),
    dto.TaskSessionCreateInputDTO, dto.TaskSessionResultDTO,
)
GET_TASK_SESSION = DomainOperation(
    OperationCapabilityDTO(name='task-session.get', kind='read', user_scope='dream:read',
        background_scope=None, input_schema_version=1, output_schema_version=1,
        contract_sha256='442e68f7fd93ae7f285eaf5ccc591d3211fc07fb498c3a73fc53eaa2de127184'),
    dto.TaskSessionGetInputDTO, dto.TaskSessionResultDTO,
)
LIST_TASK_SESSION_LINKS = DomainOperation(
    OperationCapabilityDTO(name='task-session.links', kind='read', user_scope='dream:read',
        background_scope=None, input_schema_version=1, output_schema_version=1,
        contract_sha256='f9c1bcfec4308aa6fc8f0bc977a48f34b95cb719b143b0544f6b1178edb7f1b3'),
    dto.ThreadIdInputDTO, dto.TaskSessionLinksResultDTO,
)
LAUNCH_TASK_SESSION = DomainOperation(
    OperationCapabilityDTO(name='task-session.launch', kind='write', user_scope='dream:write',
        background_scope=None, input_schema_version=1, output_schema_version=1,
        contract_sha256='03dd117fe923da921eb81f2e22241c6971bbeb3942231f65a5996ca2267e1dcd'),
    dto.TaskSessionLaunchInputDTO, dto.TaskSessionLaunchResultDTO,
)

CHAT_OPERATIONS = (CREATE_THREAD, GET_THREAD, LIST_THREADS, SEARCH_THREADS, DELETE_THREAD, BIND_DECK, SELECT_VOICE, UPDATE_TITLE, UPDATE_SESSION, PERSIST_MESSAGE, LIST_MESSAGES, MESSAGE_PAGE, PROCESS_DETAIL, LATEST_MESSAGE, ENQUEUE_INPUT, LIST_INPUTS, TRANSITION_INPUT, CREATE_TASK_SESSION, CREATE_RETURNING_TASK_SESSION, GET_TASK_SESSION, LIST_TASK_SESSION_LINKS, LAUNCH_TASK_SESSION,)


class AdminChatData:
    """Require server-owned operation registration plus an explicit authenticated actor.

    The request/turn composition supplies the OAuth token or entity-limited
    delegation. Canonical users.id is never accepted in operation input. No
    method retries a mutation; the caller retains its request_id and uses the
    same registered operation with client.receipt after an unknown result.
    """
    def __init__(self, client: AdminDataClient) -> None:
        self._client = client

    def create_thread(self, input_dto: dto.ThreadCreateInputDTO, request_id: str, *, access_token: str) -> dto.ThreadCreateResultDTO:
        return self._client.execute(CREATE_THREAD, input_dto, request_id, access_token=access_token)

    def get_thread(self, input_dto: dto.ThreadIdInputDTO, request_id: str, *, access_token: str) -> dto.ThreadResultDTO:
        return self._client.execute(GET_THREAD, input_dto, request_id, access_token=access_token)

    def list_threads(self, input_dto: dto.ThreadListInputDTO, request_id: str, *, access_token: str) -> dto.ThreadListResultDTO:
        return self._client.execute(LIST_THREADS, input_dto, request_id, access_token=access_token)

    def search_threads(self, input_dto: dto.ThreadSearchInputDTO, request_id: str, *, access_token: str) -> dto.ThreadSearchResultDTO:
        return self._client.execute(SEARCH_THREADS, input_dto, request_id, access_token=access_token)

    def delete_thread(self, input_dto: dto.ThreadIdInputDTO, request_id: str, *, access_token: str) -> dto.ChangedResultDTO:
        return self._client.execute(DELETE_THREAD, input_dto, request_id, access_token=access_token)

    def bind_deck(self, input_dto: dto.ThreadBindDeckInputDTO, request_id: str, *, access_token: str) -> dto.ChangedResultDTO:
        return self._client.execute(BIND_DECK, input_dto, request_id, access_token=access_token)

    def select_voice(self, input_dto: dto.ThreadSelectVoiceInputDTO, request_id: str, *, access_token: str) -> dto.ChangedResultDTO:
        return self._client.execute(SELECT_VOICE, input_dto, request_id, access_token=access_token)

    def update_title(self, input_dto: dto.ThreadTitleInputDTO, request_id: str, *, access_token: str) -> dto.ChangedResultDTO:
        return self._client.execute(UPDATE_TITLE, input_dto, request_id, access_token=access_token)

    def update_session(self, input_dto: dto.ThreadSessionInputDTO, request_id: str, *, access_token: str) -> dto.ChangedResultDTO:
        return self._client.execute(UPDATE_SESSION, input_dto, request_id, access_token=access_token)

    def persist_message(self, input_dto: dto.MessagePersistInputDTO, request_id: str, *, access_token: str) -> dto.MessagePersistResultDTO:
        result = self._client.execute(PERSIST_MESSAGE, input_dto, request_id, access_token=access_token)
        if result.message_id != input_dto.message_id:
            raise invalid_response(request_id, write=True)
        return result

    def list_messages(self, input_dto: dto.ThreadIdInputDTO, request_id: str, *, access_token: str) -> dto.MessageListResultDTO:
        return self._client.execute(LIST_MESSAGES, input_dto, request_id, access_token=access_token)

    def message_page(self, input_dto: dto.MessagePageInputDTO, request_id: str, *, access_token: str) -> dto.MessagePageResultDTO:
        return self._client.execute(MESSAGE_PAGE, input_dto, request_id, access_token=access_token)

    def process_detail(self, input_dto: dto.MessageDetailInputDTO, request_id: str, *, access_token: str) -> dto.MessageDetailResultDTO:
        return self._client.execute(PROCESS_DETAIL, input_dto, request_id, access_token=access_token)

    def latest_message(self, input_dto: dto.ThreadIdInputDTO, request_id: str, *, access_token: str) -> dto.LatestMessageResultDTO:
        return self._client.execute(LATEST_MESSAGE, input_dto, request_id, access_token=access_token)

    def enqueue_input(self, input_dto: dto.QueueEnqueueInputDTO, request_id: str, *, access_token: str) -> dto.QueueEntryResultDTO:
        return self._client.execute(ENQUEUE_INPUT, input_dto, request_id, access_token=access_token)

    def list_inputs(self, input_dto: dto.ThreadIdInputDTO, request_id: str, *, access_token: str) -> dto.QueueListResultDTO:
        return self._client.execute(LIST_INPUTS, input_dto, request_id, access_token=access_token)

    def transition_input(self, input_dto: dto.QueueTransitionInputDTO, request_id: str, *, access_token: str) -> dto.QueueEntryResultDTO:
        return self._client.execute(TRANSITION_INPUT, input_dto, request_id, access_token=access_token)

    def create_task_session(self, input_dto: dto.TaskSessionCreateInputDTO, request_id: str, *, access_token: str) -> dto.TaskSessionResultDTO:
        return self._client.execute(CREATE_TASK_SESSION, input_dto, request_id, access_token=access_token)

    def create_returning_task_session(self, input_dto: dto.TaskSessionCreateInputDTO, request_id: str, *, access_token: str) -> dto.TaskSessionResultDTO:
        return self._client.execute(CREATE_RETURNING_TASK_SESSION, input_dto, request_id, access_token=access_token)

    def get_task_session(self, input_dto: dto.TaskSessionGetInputDTO, request_id: str, *, access_token: str) -> dto.TaskSessionResultDTO:
        return self._client.execute(GET_TASK_SESSION, input_dto, request_id, access_token=access_token)

    def list_task_session_links(self, input_dto: dto.ThreadIdInputDTO, request_id: str, *, access_token: str) -> dto.TaskSessionLinksResultDTO:
        return self._client.execute(LIST_TASK_SESSION_LINKS, input_dto, request_id, access_token=access_token)

    def launch_task_session(self, input_dto: dto.TaskSessionLaunchInputDTO, request_id: str, *, access_token: str) -> dto.TaskSessionLaunchResultDTO:
        return self._client.execute(LAUNCH_TASK_SESSION, input_dto, request_id, access_token=access_token)

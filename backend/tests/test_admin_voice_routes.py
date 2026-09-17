# [Sync] 2026-09-17: verify confidential service OAuth and separate delegated-user Bearer transport.
# [Input] Actual four Voice/FastAPI/auth/DTO operations and controlled server responses.
# [Output] Original mutations, optional/null/raw JSON/scopes/errors/unknown receipt evidence.
# [Pos] Provider-free Voice harness; other Deck routes and internal DB paths remain independent.
# [Sync] 2026-09-15: fence public Voice SQL and preserve optional-field serialization shared with Editor.
from __future__ import annotations

import json
import math
from uuid import UUID

import httpx
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from pydantic import ValidationError

from routers.voices import router
from services.admin_data import AdminDataClient, AdminDataConfig, AdminDataError
from services.admin_data.deck_version_data import DECK_VERSION_SCHEMA_REQUIREMENTS
from services.admin_data.models import AbsentReceiptDTO, CommittedReceiptDTO
from services.admin_data.request_auth import AdminRequestAuth
from services.admin_data.voice_data import AdminVoiceData, VOICE_OPERATIONS, VoiceUpdateFieldsDTO
from tests.test_admin_request_auth import Verifier

HEADERS = {'authorization': 'Bearer write-token'}
CREATE = {'deck_id': 'deck-1', 'name': '人物🌙', 'system_prompt': '正文原样'}
ROUTES = [('post', '/api/voices', 'voice.create', CREATE),
    ('put', '/api/voices/voice-1', 'voice.update', {'name': '新名'}),
    ('delete', '/api/voices/voice-1', 'voice.delete', None),
    ('post', '/api/voices/source-voice/fork', 'voice.collect', {'target_deck_id': 'target-deck'})]


@pytest.fixture
def boundary(monkeypatch):
    import database
    monkeypatch.setattr(database, 'get_db', lambda: pytest.fail('Public Voice must not connect to Dream PG'))
    for name in ('create_voice', 'update_voice', 'delete_voice', 'fork_voice'):
        assert not hasattr(database, name)
    config = AdminDataConfig(base_url='https://admin.example', issuer='https://admin.example/api/auth',
        resource='https://dream.example/api', service_client_id='dream-service', service_secret='s' * 32)
    outputs = {'voice.create': {'voice_id': 'created-voice'}, 'voice.update': {'changed': True},
        'voice.delete': {'changed': True}, 'voice.collect': {'voice_id': 'collected-voice'}}
    schemas = [s.model_dump() for s in DECK_VERSION_SCHEMA_REQUIREMENTS]
    operations = [s.capability.model_dump() for s in VOICE_OPERATIONS]
    calls = []; receipts = {}; receipt_calls = []

    class VoiceVerifier(Verifier):
        def verify(self, token, *, required_scopes):
            if token.startswith('idg_'): raise AdminDataError('INVALID_ACCESS_TOKEN', 401)
            return super().verify(token, required_scopes=required_scopes)

    def handler(request):
        request_id = request.headers['x-request-id']; UUID(request_id)
        if request.url.path.endswith('/capabilities'):
            value = {'version': '1', 'auth': {'issuer': config.issuer, 'jwks_uri': config.jwks_uri, 'resource': config.resource,
                'algorithm': 'ES256', 'clients': {'browser': 'dream-browser', 'device': 'dream-device'},
                'scopes': ['dream:read', 'dream:write'], 'delegations': []}, 'schema_capabilities': schemas, 'operations': operations}
        elif request.url.path.endswith('/principal'):
            value = {'subject': 'opaque-ba-subject', 'canonical_user_id': '42', 'client_id': 'dream-browser',
                'scopes': ['dream:read'] if request.headers['authorization'] == 'Bearer read-token' else ['dream:read', 'dream:write'], 'status': 'active'}
        elif '/receipts/' in request.url.path:
            name = request.url.params['operation']; receipt_calls.append((name, request_id))
            value = receipts.get(request_id, {'status': 'absent', 'operation': name, 'request_id': request_id})
        else:
            name = request.url.path.rsplit('/', 1)[-1]; body = json.loads(request.content)
            assert body['request_id'] == request_id and set(body) == {'request_id', 'input'}
            assert not {'user_id', 'actor_id', 'subject', 'default_plugin_evidence'} & body['input'].keys()
            assert request.headers['authorization'] == 'Bearer write-token' and 'cookie' not in request.headers
            assert request.headers['x-ink-dream-service-authorization'] == 'Bearer fixture.service.access.token'
            assert 'x-ink-dream-credential' not in request.headers
            calls.append((name, body['input'], request_id)); value = outputs[name]
            if isinstance(value, Exception): raise value
            if isinstance(value, tuple):
                status, code = value
                return httpx.Response(status, json={'request_id': request_id, 'error': {'code': code, 'message': 'private upstream text'}})
        return httpx.Response(200, json={'request_id': request_id, 'data': value})

    http = httpx.Client(transport=httpx.MockTransport(handler))
    client = AdminDataClient(config, client=http, operations=VOICE_OPERATIONS)
    app = FastAPI(); app.state.admin_request_auth = AdminRequestAuth(config, client=client, verifier=VoiceVerifier()); app.include_router(router)
    with TestClient(app) as browser:
        yield browser, calls, outputs, schemas, operations, AdminVoiceData(client), receipts, receipt_calls
    http.close()


def call(browser, method, url, body=None, headers=HEADERS):
    return browser.request(method.upper(), url, headers=headers, **({'json': body} if body is not None else {}))


@pytest.mark.parametrize('method,url,name,body', ROUTES)
def test_all_four_mutations_keep_original_results(boundary, method, url, name, body):
    browser, calls, *_ = boundary; response = call(browser, method, url, body)
    expected = {'voice_id': 'created-voice'} if name.endswith('create') else {'voice_id': 'collected-voice'} if name.endswith('collect') else {'success': True}
    assert response.status_code == 200 and response.json() == expected and len(calls) == 1
    if name.endswith('create'):
        assert calls[0][1] == {**CREATE, 'name_zh': None, 'name_en': None, 'icon': None, 'color': None,
            'order_index': None, 'memory_workspace_config_json': None}
    elif name.endswith('update'): assert calls[0][1] == {'voice_id': 'voice-1', 'updates': {'name': '新名'}}
    elif name.endswith('collect'): assert calls[0][1] == {'voice_id': 'source-voice', 'target_deck_id': 'target-deck'}
    else: assert calls[0][1] == {'voice_id': 'voice-1'}


def test_update_null_omitted_false_zero_empty_preserved_and_empty_command_is_empty(boundary):
    browser, calls, *_ = boundary
    body = {'name': None, 'system_prompt': '', 'enabled': False, 'order_index': 0, 'memory_workspace_config': {}}
    assert call(browser, 'put', '/api/voices/voice-1', body).json() == {'success': True}
    assert calls[0][1]['updates'] == {'system_prompt': '', 'enabled': False, 'order_index': 0, 'memory_workspace_config_json': '{}'}
    assert call(browser, 'put', '/api/voices/voice-1', {'memory_workspace_config': None}).json() == {'success': True}
    assert calls[1][1]['updates'] == {}


def test_raw_memory_create_update_keeps_numeric_lexemes_and_update_sorting(boundary):
    browser, calls, *_ = boundary; memory = {'z': -0.0, 'a': 1.0, 'big': 9007199254740993}
    assert call(browser, 'post', '/api/voices', {**CREATE, 'memory_workspace_config': memory}).status_code == 200
    assert call(browser, 'put', '/api/voices/voice-1', {'memory_workspace_config': memory}).status_code == 200
    for raw in [calls[0][1]['memory_workspace_config_json'], calls[1][1]['updates']['memory_workspace_config_json']]:
        assert '-0.0' in raw and '1.0' in raw and '9007199254740993' in raw
        value = json.loads(raw); assert type(value['a']) is float and math.copysign(1, value['z']) == -1 and value['big'] == 9007199254740993
    assert calls[1][1]['updates']['memory_workspace_config_json'].index('"a"') < calls[1][1]['updates']['memory_workspace_config_json'].index('"z"')


def test_empty_memory_create_is_sent_to_admin_without_local_default(boundary):
    browser, calls, *_ = boundary; assert call(browser, 'post', '/api/voices', {**CREATE, 'memory_workspace_config': {}}).status_code == 200
    assert calls[0][1]['memory_workspace_config_json'] == '{}'


@pytest.mark.parametrize('method,name', [('put', 'voice.update'), ('delete', 'voice.delete')])
def test_changed_false_keeps_original_404(boundary, method, name):
    browser, _, outputs, *_ = boundary; outputs[name] = {'changed': False}
    response = call(browser, method, '/api/voices/voice-1', {} if method == 'put' else None)
    assert response.status_code == 404 and response.json() == {'detail': 'Voice not found or permission denied'}


@pytest.mark.parametrize('name,code,method,url,body,detail', [
    ('voice.create', 'DECK_ACCESS_DENIED', 'post', '/api/voices', CREATE, 'Deck not found or permission denied'),
    ('voice.collect', 'DECK_ACCESS_DENIED', 'post', '/api/voices/source-voice/fork', {'target_deck_id': 'target-deck'}, 'Target deck not found or permission denied'),
    ('voice.collect', 'VOICE_ACCESS_DENIED', 'post', '/api/voices/source-voice/fork', {'target_deck_id': 'target-deck'}, 'Voice source-voice not found'),
])
def test_closed_known_domain_errors_keep_original_safe_400(boundary, name, code, method, url, body, detail):
    browser, _, outputs, *_ = boundary; outputs[name] = (404, code); response = call(browser, method, url, body)
    assert response.status_code == 400 and response.json() == {'detail': detail} and 'private upstream text' not in response.text


@pytest.mark.parametrize('name,code,status,method,body', [('voice.update', 'CHAT_THREAD_NOT_FOUND', 404, 'put', {'thread_id': 'other-thread'}),
    ('voice.delete', 'VOICE_REFERENCED', 409, 'delete', None)])
def test_entity_permission_or_reference_failure_is_safe_and_keeps_original_uuid(boundary, name, code, status, method, body):
    browser, calls, outputs, *_ = boundary; outputs[name] = (status, code); response = call(browser, method, '/api/voices/voice-1', body)
    assert response.status_code == status and response.json()['detail'] == {'error_code': code, 'request_id': calls[0][2], 'outcome_unknown': False}
    assert 'private upstream text' not in response.text


@pytest.mark.parametrize('method,url,name,body', ROUTES)
def test_unknown_write_only_original_receipt_no_retry(boundary, method, url, name, body):
    browser, calls, outputs, _, _, data, receipts, receipt_calls = boundary; outputs[name] = httpx.ReadTimeout('private body/token')
    response = call(browser, method, url, body); request_id = calls[0][2]
    assert response.status_code == 504 and response.json()['detail'] == {'error_code': 'ADMIN_TIMEOUT', 'request_id': request_id, 'outcome_unknown': True}
    spec = next(spec for spec in VOICE_OPERATIONS if spec.capability.name == name)
    assert isinstance(data.receipt(spec, request_id, access_token='write-token'), AbsentReceiptDTO)
    result = {'changed': True} if name in {'voice.update', 'voice.delete'} else {'voice_id': 'original-created-id'}
    receipts[request_id] = {'status': 'committed', 'operation': name, 'request_id': request_id, 'result': result}
    committed = data.receipt(spec, request_id, access_token='write-token')
    assert isinstance(committed, CommittedReceiptDTO) and committed.result.model_dump() == result
    assert len(calls) == 1 and receipt_calls == [(name, request_id)] * 2
    assert 'private body/token' not in response.text


@pytest.mark.parametrize('mutation', ['schema-missing', 'schema-hash', 'schema-duplicate', 'op-missing', 'op-hash'])
def test_four_exact_physical_capabilities_and_contract_gate_before_write(boundary, mutation):
    browser, calls, _, schemas, operations, *_ = boundary
    if mutation == 'schema-missing': schemas.pop()
    elif mutation == 'schema-hash': schemas[1]['contract_sha256'] = '0' * 64
    elif mutation == 'schema-duplicate': schemas.append(schemas[0].copy())
    elif mutation == 'op-missing': operations.pop(0)
    else: operations[0]['contract_sha256'] = '0' * 64
    response = call(browser, 'post', '/api/voices', CREATE)
    assert response.status_code == 503 and not calls and not response.json()['detail']['outcome_unknown']


@pytest.mark.parametrize('method,url,name,body', ROUTES)
@pytest.mark.parametrize('token,status', [('read-token', 403), ('idg_synthetic', 401)])
def test_every_voice_mutation_requires_current_user_oauth(boundary, method, url, name, body, token, status):
    browser, calls, *_ = boundary; response = call(browser, method, url, body, {'authorization': 'Bearer ' + token})
    assert response.status_code == status and not calls


@pytest.mark.parametrize('body', [{**CREATE, 'user_id': 42}, {**CREATE, 'voice_id': 'chosen'}, {**CREATE, 'memory_workspace_config': []},
    {**CREATE, 'name': None}, {**CREATE, 'default_plugin_evidence': {}}, {**CREATE, 'order_index': 0}])
def test_strict_create_body_rejects_overrides_and_wrong_shapes_before_write(boundary, body):
    browser, calls, *_ = boundary; response = call(browser, 'post', '/api/voices', body)
    assert response.status_code == 422 and response.json() == {'detail': 'Invalid Voice request'} and not calls


@pytest.mark.parametrize('raw', ['{"memory_workspace_config":{"x":NaN}}', '{"memory_workspace_config":{"x":Infinity}}',
    '{"memory_workspace_config":{"x":1e400}}', '{"enabled":0}', '{"order_index":9007199254740992}', '{"actor_id":"42"}'])
def test_update_input_validation_is_finite_closed_and_no_body_echo(boundary, raw):
    browser, calls, *_ = boundary; response = browser.put('/api/voices/voice-1', headers={**HEADERS, 'content-type': 'application/json'}, content=raw)
    assert response.status_code == 422 and response.json() == {'detail': 'Invalid Voice request'} and not calls


@pytest.mark.parametrize('method,url,name,body', ROUTES)
def test_malformed_write_reply_remains_unknown_no_extra_write(boundary, method, url, name, body):
    browser, calls, outputs, *_ = boundary; outputs[name] = {'voice_id': ''} if name.endswith(('create', 'collect')) else {'changed': 1}
    response = call(browser, method, url, body)
    assert response.status_code == 503 and response.json()['detail'] == {'error_code': 'ADMIN_RESPONSE_INVALID', 'request_id': calls[0][2], 'outcome_unknown': True}
    assert len(calls) == 1


def test_wire_optional_nullable_fields_serialize_only_when_present():
    assert VoiceUpdateFieldsDTO().model_dump(mode='json') == {}
    assert VoiceUpdateFieldsDTO(name_zh=None, memory_workspace_config_json=None).model_dump(mode='json') == {'name_zh': None, 'memory_workspace_config_json': None}
    with pytest.raises(ValidationError): VoiceUpdateFieldsDTO(name=None)
    with pytest.raises(ValidationError): VoiceUpdateFieldsDTO(enabled=None)
    with pytest.raises(ValidationError): VoiceUpdateFieldsDTO(memory_workspace_config_json='{"x":NaN}')

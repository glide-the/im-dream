# [Sync] 2026-09-17: verify confidential service OAuth and separate delegated-user Bearer transport.
# [Input] Actual social routes/RequestAuth/DTO client and synthetic relationship/image responses.
# [Output] Nine public contracts, original errors/IDs/timestamps, scopes and unknown receipt evidence.
# [Pos] Provider-free social harness; Admin owns locks/state/policy and Dream DB is fenced.
# [Sync] 2026-09-15: verify published nine operations without PG/model/network/business data.
from __future__ import annotations

import json
from uuid import UUID

import httpx
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from pydantic import ValidationError

from routers.friends import router
from services.admin_data import AdminDataClient, AdminDataConfig, AdminDataError
from services.admin_data.models import AbsentReceiptDTO, CommittedReceiptDTO
from services.admin_data.request_auth import AdminRequestAuth
from services.admin_data.social_data import (
    AdminSocialData, FriendRequestDTO, FriendSelectorDTO, FriendTimelineDTO,
    SOCIAL_OPERATIONS, USE_INVITE, public_social_result,
)
from services.admin_data.workflow_data import WORKFLOW_SCHEMA_REQUIREMENTS
from tests.test_admin_request_auth import Verifier

HEADERS = {'authorization': 'Bearer write-token'}
TIME = '2026-09-15T03:02:01.123456+08:00'
BIG_ID = '9223372036854775807'
ROUTES = [
    ('post', '/api/friends/invite/generate', 'friend-invite.generate', None, {}),
    ('post', '/api/friends/invite/use', 'friend-invite.use', {'code': '原样 aB '}, {'code': '原样 aB '}),
    ('get', '/api/friends/requests', 'friend-request.list', None, {}),
    ('post', '/api/friends/requests/5/accept', 'friend-request.accept', None, {'request_id': '5'}),
    ('post', '/api/friends/requests/5/reject', 'friend-request.reject', None, {'request_id': '5'}),
    ('get', '/api/friends', 'friendship.list', None, {}),
    ('delete', '/api/friends/7', 'friendship.remove', None, {'friend_id': '7'}),
    ('get', '/api/friends/7/timeline', 'friendship.timeline', None, {'friend_id': '7', 'limit': 30}),
    ('get', '/api/friends/7/pictures/2026-09-15/full', 'friendship.picture-full', None, {'friend_id': '7', 'date': '2026-09-15'}),
]


def defaults():
    return {
        'friend-invite.generate': {'code': 'ABCDEF', 'expires_at': TIME},
        'friend-invite.use': {'success': True, 'friend_request_id': BIG_ID, 'inviter_id': '7', 'inviter_name': '朋友🌙'},
        'friend-request.list': {'requests': [{'id': BIG_ID, 'requester_id': '9007199254740993', 'requester_name': '显示名', 'created_at': None},
            {'id': '6', 'requester_id': '8', 'requester_name': 'email@example.test', 'created_at': TIME}]},
        'friend-request.accept': {'success': True}, 'friend-request.reject': {'success': True},
        'friendship.list': {'friends': [{'friend_id': BIG_ID, 'friend_name': '朋友', 'friend_email': 'friend@example.test', 'since': None},
            {'friend_id': '8', 'friend_name': '邮件', 'friend_email': 'email@example.test', 'since': TIME}]},
        'friendship.remove': {'success': True},
        'friendship.timeline': {'pictures': [{'date': '2026-09-15', 'base64': 'thumbnail-original', 'prompt': None, 'created_at': TIME},
            {'date': '2026-09-14', 'base64': 'image-fallback-original', 'prompt': '', 'created_at': None}]},
        'friendship.picture-full': {'image_base64': 'full-original'},
    }


@pytest.fixture
def boundary(monkeypatch):
    import database
    monkeypatch.setattr(database, 'get_db', lambda: pytest.fail('Social must not connect to Dream PG'))
    config = AdminDataConfig(base_url='https://admin.example', issuer='https://admin.example/api/auth',
        resource='https://dream.example/api', service_client_id='dream-service', service_secret='s' * 32)
    outputs = defaults(); calls = []; receipts = {}; receipt_calls = []
    schemas = [item.model_dump() for item in WORKFLOW_SCHEMA_REQUIREMENTS]
    operations = [item.capability.model_dump() for item in SOCIAL_OPERATIONS]

    class SocialVerifier(Verifier):
        def verify(self, token, *, required_scopes):
            if token.startswith('idg_'):
                raise AdminDataError('INVALID_ACCESS_TOKEN', 401)
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
            assert request.url.path.rsplit('/', 1)[-1] == request_id
            value = receipts.get(request_id, {'operation': name, 'request_id': request_id, 'status': 'absent'})
        else:
            name = request.url.path.rsplit('/', 1)[-1]; body = json.loads(request.content)
            assert set(body) == {'request_id', 'input'} and body['request_id'] == request_id
            assert not {'user_id', 'actor_id', 'subject'} & body['input'].keys()
            assert request.headers['authorization'] in {'Bearer write-token', 'Bearer read-token'}
            assert request.headers['x-ink-dream-service-authorization'] == 'Bearer fixture.service.access.token'
            assert 'x-ink-dream-credential' not in request.headers and 'cookie' not in request.headers
            calls.append((name, body['input'], request_id)); value = outputs[name]
            if isinstance(value, Exception): raise value
        return httpx.Response(200, json={'request_id': request_id, 'data': value})

    http = httpx.Client(transport=httpx.MockTransport(handler))
    client = AdminDataClient(config, client=http, operations=SOCIAL_OPERATIONS)
    app = FastAPI(); app.state.admin_request_auth = AdminRequestAuth(config, client=client, verifier=SocialVerifier()); app.include_router(router)
    with TestClient(app) as browser:
        yield browser, calls, outputs, schemas, operations, AdminSocialData(client), receipts, receipt_calls
    http.close()


def call(browser, method, url, body=None, headers=HEADERS):
    return browser.request(method.upper(), url, headers=headers, **({'json': body} if body is not None else {}))


@pytest.mark.parametrize('method,url,name,body,expected_input', ROUTES)
def test_all_nine_public_routes_keep_original_projections(boundary, method, url, name, body, expected_input):
    browser, calls, outputs, *_ = boundary
    response = call(browser, method, url, body)
    expected = defaults()[name]
    if name == 'friend-invite.use':
        expected['friend_request_id'] = 9223372036854775807
        expected['inviter_id'] = 7
    elif name == 'friend-request.list':
        expected['requests'][0].update(id=9223372036854775807, requester_id=9007199254740993)
        expected['requests'][1].update(id=6, requester_id=8)
    elif name == 'friendship.list':
        expected['friends'][0]['friend_id'] = 9223372036854775807
        expected['friends'][1]['friend_id'] = 8
    assert response.status_code == 200 and response.json() == expected
    assert calls[0][:2] == (name, expected_input) and len(calls) == 1
    if name == 'friend-invite.use':
        assert type(response.json()['friend_request_id']) is int and response.json()['friend_request_id'] == int(BIG_ID)
    if name == 'friend-request.list':
        assert response.json()['requests'][0]['requester_id'] == 9007199254740993
    if name == 'friendship.timeline':
        assert response.json()['pictures'][0]['created_at'] == TIME


@pytest.mark.parametrize('name,url,error', [
    *[('friend-invite.use', '/api/friends/invite/use', error) for error in [
        'Invalid invite code', 'Invite code already used', 'Invite code expired', 'Cannot add yourself as friend',
        'Already friends', 'Friend request already pending']],
    *[(f'friend-request.{action}', f'/api/friends/requests/5/{action}', error) for action in ('accept', 'reject')
      for error in ('Request not found', 'Permission denied', 'Request already accepted', 'Request already rejected')],
    ('friendship.remove', '/api/friends/7', 'Friendship not found'),
])
def test_closed_business_failures_keep_original_400_detail(boundary, name, url, error):
    browser, calls, outputs, *_ = boundary; outputs[name] = {'success': False, 'error': error}
    response = call(browser, 'delete' if name.endswith('remove') else 'post', url, {'code': 'x'} if name.endswith('use') else None)
    assert response.status_code == 400 and response.json() == {'detail': error} and len(calls) == 1


@pytest.mark.parametrize('image', [None, ''])
def test_falsey_full_picture_keeps_original_404(boundary, image):
    browser, _, outputs, *_ = boundary; outputs['friendship.picture-full'] = {'image_base64': image}
    response = browser.get('/api/friends/7/pictures/arbitrary-date-text/full', headers=HEADERS)
    assert response.status_code == 404 and response.json() == {'detail': 'Picture not found or not accessible'}


def test_timeline_null_forbidden_empty_success_and_zero_limit(boundary):
    browser, calls, outputs, *_ = boundary; outputs['friendship.timeline'] = {'pictures': None}
    response = browser.get('/api/friends/7/timeline', headers=HEADERS)
    assert response.status_code == 403 and response.json() == {'detail': 'Not friends or friend not found'}
    outputs['friendship.timeline'] = {'pictures': []}
    assert browser.get('/api/friends/7/timeline?limit=0', headers=HEADERS).json() == {'pictures': []}
    assert calls[-1][1]['limit'] == 0


@pytest.mark.parametrize('name', ['friend-request.list', 'friendship.list'])
def test_empty_lists_keep_wrappers(boundary, name):
    browser, _, outputs, *_ = boundary; key = 'requests' if name.endswith('request.list') else 'friends'
    outputs[name] = {key: []}
    assert browser.get('/api/friends/requests' if key == 'requests' else '/api/friends', headers=HEADERS).json() == {key: []}


@pytest.mark.parametrize('body', [{'code': 'x', 'user_id': 42}, {'code': 'x', 'subject': 'opaque'}, {'code': 6}, {}, {'code': None}, []])
def test_strict_public_code_rejects_actor_and_wrong_shapes_before_data_io(boundary, body):
    browser, calls, *_ = boundary
    response = call(browser, 'post', '/api/friends/invite/use', body)
    assert response.status_code == 422 and response.json() == {'detail': 'Invalid friend request'} and not calls


@pytest.mark.parametrize('url', ['/api/friends/0/timeline', '/api/friends/-1/timeline', '/api/friends/9223372036854775808/timeline',
    '/api/friends/7/timeline?limit=-1', '/api/friends/7/timeline?limit=9007199254740992', '/api/friends/7/timeline?limit=NaN'])
def test_selector_and_pagination_technical_bounds_fail_before_data_io(boundary, url):
    browser, calls, *_ = boundary; response = browser.get(url, headers=HEADERS)
    assert response.status_code == 422 and not calls


@pytest.mark.parametrize('method,url,name,body,expected', ROUTES)
def test_every_social_route_rejects_entity_grant_before_data_io(boundary, method, url, name, body, expected):
    browser, calls, *_ = boundary; response = call(browser, method, url, body, {'authorization': 'Bearer idg_synthetic'})
    assert response.status_code == 401 and not calls


@pytest.mark.parametrize('method,url,name,body,expected', [row for row in ROUTES if row[0] != 'get'])
def test_read_only_oauth_cannot_write_social(boundary, method, url, name, body, expected):
    browser, calls, *_ = boundary; response = call(browser, method, url, body, {'authorization': 'Bearer read-token'})
    assert response.status_code == 403 and not calls


@pytest.mark.parametrize('mutation', ['missing-schema', 'schema-hash', 'duplicate-schema', 'operation-hash', 'missing-operation'])
def test_exact_published_capability_gate_blocks_domain_io(boundary, mutation):
    browser, calls, _, schemas, operations, *_ = boundary
    if mutation == 'missing-schema': schemas.clear()
    elif mutation == 'schema-hash': schemas[0]['contract_sha256'] = '0' * 64
    elif mutation == 'duplicate-schema': schemas.append(schemas[0].copy())
    elif mutation == 'operation-hash': operations[1]['contract_sha256'] = '0' * 64
    else: operations.pop(1)
    response = call(browser, 'post', '/api/friends/invite/use', {'code': 'x'})
    assert response.status_code == 503 and not calls and not response.json()['detail']['outcome_unknown']


@pytest.mark.parametrize('name,value,method,url,body', [
    ('friend-invite.generate', {'code': '', 'expires_at': TIME}, 'post', '/api/friends/invite/generate', None),
    ('friend-invite.use', {'success': 1, 'friend_request_id': '5', 'inviter_id': '7', 'inviter_name': 'x'}, 'post', '/api/friends/invite/use', {'code': 'x'}),
    ('friend-invite.use', {'success': True, 'friend_request_id': '05', 'inviter_id': '7', 'inviter_name': 'x'}, 'post', '/api/friends/invite/use', {'code': 'x'}),
    ('friend-invite.use', {'success': True, 'friend_request_id': '5', 'inviter_id': '9223372036854775808', 'inviter_name': 'x'}, 'post', '/api/friends/invite/use', {'code': 'x'}),
    ('friend-request.accept', {'success': False, 'error': 'private unexpected message'}, 'post', '/api/friends/requests/5/accept', None),
    ('friend-request.reject', {'success': True, 'actor_id': '42'}, 'post', '/api/friends/requests/5/reject', None),
    ('friendship.remove', {'success': 0, 'error': 'Friendship not found'}, 'delete', '/api/friends/7', None),
    ('friend-request.list', {'requests': [{'id': '5', 'requester_id': '7', 'requester_name': 'x'}]}, 'get', '/api/friends/requests', None),
    ('friendship.list', {'friends': [{'friend_id': '7', 'friend_name': 'x', 'friend_email': 'x', 'since': '2026-09-15 03:00:00'}]}, 'get', '/api/friends', None),
    ('friendship.timeline', {'pictures': [{'date': 'x', 'base64': None, 'prompt': None, 'created_at': TIME}]}, 'get', '/api/friends/7/timeline', None),
    ('friendship.picture-full', {'image_base64': False}, 'get', '/api/friends/7/pictures/x/full', None),
])
def test_malformed_reply_is_safe_and_write_outcome_remains_unknown(boundary, name, value, method, url, body):
    browser, calls, outputs, *_ = boundary; outputs[name] = value
    response = call(browser, method, url, body)
    assert response.status_code == 503 and response.json()['detail']['error_code'] == 'ADMIN_RESPONSE_INVALID'
    assert response.json()['detail']['outcome_unknown'] is (method != 'get')
    assert response.json()['detail']['request_id'] == calls[0][2] and len(calls) == 1
    assert 'private unexpected message' not in response.text


@pytest.mark.parametrize('error', [httpx.ReadTimeout('private token/body'), httpx.ConnectError('private token/body')])
def test_unknown_use_keeps_uuid_and_only_original_receipt_recovers(boundary, error):
    browser, calls, outputs, _, _, data, receipts, receipt_calls = boundary; outputs['friend-invite.use'] = error
    response = call(browser, 'post', '/api/friends/invite/use', {'code': 'original'})
    assert response.status_code in (503, 504) and response.json()['detail']['outcome_unknown'] is True
    request_id = response.json()['detail']['request_id']; assert request_id == calls[0][2]
    absent = data.receipt(USE_INVITE, request_id, access_token='write-token')
    assert isinstance(absent, AbsentReceiptDTO) and len(calls) == 1
    receipts[request_id] = {'status': 'committed', 'operation': 'friend-invite.use', 'request_id': request_id,
        'result': defaults()['friend-invite.use']}
    committed = data.receipt(USE_INVITE, request_id, access_token='write-token')
    assert isinstance(committed, CommittedReceiptDTO) and public_social_result(committed.result)['friend_request_id'] == int(BIG_ID)
    assert receipt_calls == [('friend-invite.use', request_id)] * 2 and len(calls) == 1
    assert 'private token/body' not in response.text


@pytest.mark.parametrize('dto,value', [(FriendRequestDTO, {'request_id': 5}), (FriendSelectorDTO, {'friend_id': '0'}),
    (FriendSelectorDTO, {'friend_id': '9223372036854775808'}), (FriendTimelineDTO, {'friend_id': '7', 'limit': True})])
def test_closed_wire_inputs_reject_coercion_and_invalid_database_ids(dto, value):
    with pytest.raises(ValidationError): dto.model_validate(value)


def test_old_database_social_helpers_refuse_before_any_connection(monkeypatch):
    import database
    monkeypatch.setattr(database, 'get_db', lambda: pytest.fail('Retired social helper must not connect'))
    calls = [('generate_invite_code', (42,)), ('use_invite_code', ('x', 42)), ('get_friend_requests', (42,)),
        ('accept_friend_request', (5, 42)), ('reject_friend_request', (5, 42)), ('get_friends', (42,)),
        ('remove_friend', (42, 7)), ('get_friend_timeline', (42, 7)), ('get_friend_picture_full', (42, 7, 'x'))]
    for name, args in calls:
        with pytest.raises(AdminDataError) as exc: getattr(database, name)(*args)
        assert exc.value.code == 'ADMIN_DATA_ACCESS_RETIRED' and exc.value.status_code == 503


def test_request_composition_registers_nine_operations():
    config = AdminDataConfig(base_url='https://admin.example', issuer='https://admin.example/api/auth',
        resource='https://dream.example/api', service_client_id='dream-service', service_secret='s' * 32)
    owner = AdminRequestAuth(config)
    try:
        assert all(owner.client._operations.get(spec.capability.name) is spec for spec in SOCIAL_OPERATIONS)
    finally: owner.close()

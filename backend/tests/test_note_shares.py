# [Input] Production note publication/management routes and exact isolated Admin operation fixture.
# [Output] Saved-prose checks, strict metadata and absence of unowned file-token publication.
# [Pos] Provider-free technical contracts; normal data and real models remain untouched.
from __future__ import annotations
import hashlib
from copy import deepcopy
import pytest
from fastapi.testclient import TestClient
from tests._admin_session_fixture import build_session_boundary
from services.admin_data.external_share_data import EXTERNAL_SHARE_OPERATIONS
from routers import note_shares, external_shares

KEY = '11111111-1111-4111-8111-111111111111'
SHARE_ID = '22222222-2222-4222-8222-222222222222'
PATH = '/share/' + 's' * 43
META = {'id': SHARE_ID, 'kind': 'note', 'source_id': 'session-1', 'title': '正文 hello', 'path': PATH, 'status': 'active', 'source_available': True, 'created_at': '2026-11-12T00:00:00Z', 'revoked_at': None}

@pytest.fixture
def boundary(monkeypatch):
    monkeypatch.setenv('INK_PUBLIC_SITE_URL', 'https://notes.example')
    app, calls, outputs = build_session_boundary(extra_operations=EXTERNAL_SHARE_OPERATIONS)
    app.include_router(note_shares.router); app.include_router(external_shares.router)
    outputs['external-share.create'] = {'share': deepcopy(META)}
    outputs['external-share.get'] = {'share': deepcopy(META)}
    outputs['external-share.revoke'] = {'share': {**META, 'status': 'revoked', 'revoked_at': '2026-11-12T00:01:00Z'}}
    outputs['external-share.list'] = {'shares': [deepcopy(META)], 'counts': {'chat': 0, 'note': 1}, 'next_cursor': None}
    with TestClient(app) as client: yield client, calls, outputs

def publish(client, **options):
    body = options.pop('json', {'request_key': KEY, 'content_sha256': hashlib.sha256('正文 hello'.encode()).hexdigest()})
    return client.post('/api/sessions/session-1/share', headers={'authorization': 'Bearer write-token'}, json=body, **options)

def test_publish_uses_owned_saved_prose_and_stable_receipt_identity(boundary):
    client, calls, outputs = boundary
    outputs['session.get']['session']['editor_state']['cells'].append({'id': 'private', 'type': 'widget', 'widgetType': 'chat', 'data': {'secret': 'private conversation'}})
    response = publish(client)
    assert response.status_code == 201 and response.json()['url'] == 'https://notes.example' + PATH
    assert [call[0] for call in calls] == ['session.get', 'external-share.create']
    assert calls[-1][2] == KEY
    assert calls[-1][1]['snapshot']['paragraphs'] == ['正文 hello']
    assert 'private conversation' not in str(calls[-1][1])

def test_unauthenticated_or_read_only_users_cannot_publish(boundary):
    client, calls, _ = boundary
    assert client.post('/api/sessions/session-1/share', json={'request_key': KEY, 'content_sha256': 'a' * 64}).status_code == 401
    assert client.post('/api/sessions/session-1/share', headers={'authorization': 'Bearer read-only'}, json={'request_key': KEY, 'content_sha256': 'a' * 64}).status_code == 403
    assert calls == []

@pytest.mark.parametrize('condition,status', [('missing', 404), ('empty', 400), ('changed', 409)])
def test_invalid_note_never_creates_a_share(boundary, condition, status):
    client, calls, outputs = boundary
    if condition == 'missing': outputs['session.get'] = {'session': None}
    else: outputs['session.get']['session']['editor_state']['cells'][0]['content'] = '' if condition == 'empty' else 'Changed'
    assert publish(client).status_code == status
    assert all(call[0] != 'external-share.create' for call in calls)

def test_list_revoke_and_missing_record_use_same_owner_boundary(boundary):
    client, calls, outputs = boundary
    headers = {'authorization': 'Bearer write-token'}
    page = client.get('/api/shares?kind=note', headers=headers)
    assert page.status_code == 200 and page.json()['counts']['note'] == 1
    revoked = client.post('/api/shares/' + SHARE_ID + '/revoke', headers=headers, json={'request_key': KEY})
    assert revoked.status_code == 200 and revoked.json()['share']['status'] == 'revoked'
    assert calls[-1][2] == KEY
    outputs['external-share.get'] = {'share': None}
    assert client.get('/api/shares/' + SHARE_ID, headers=headers).status_code == 404

def test_legacy_unowned_file_tokens_have_no_public_fallback(boundary):
    client, calls, _ = boundary
    assert client.get('/api/public/note-shares/old-file-token').status_code == 404
    assert client.get('/api/public/shares/invalid-token').status_code == 404
    assert calls == []

def test_request_cannot_override_content_or_owner(boundary):
    client, calls, _ = boundary
    assert publish(client, json={'request_key': KEY, 'content_sha256': 'a' * 64, 'owner_id': 'foreign'}).status_code == 422
    assert calls == []


def test_invalid_record_or_cursor_ends_before_admin_operation(boundary):
    client, calls, _ = boundary
    headers = {'authorization': 'Bearer write-token'}
    assert client.get('/api/shares/invalid-id', headers=headers).status_code == 404
    assert client.get('/api/shares?kind=note&before_id=' + SHARE_ID, headers=headers).status_code == 400
    assert client.get('/api/shares?kind=note&before_id=' + SHARE_ID + '&before_created_at=invalid', headers=headers).status_code == 400
    assert calls == []

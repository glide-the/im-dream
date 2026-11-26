# [Input] Production anonymous share routes and existing server-owned Chat projection.
# [Output] Credential-free current-state reads, final-only publication and closed failure contracts.
# [Pos] Provider-free technical specifications; no normal service, account, model or database.
from __future__ import annotations
from dataclasses import replace
import httpx
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from routers import external_shares
from services.admin_data.config import AdminDataConfig

TOKEN = 's' * 43

@pytest.fixture
def public_boundary(monkeypatch):
    config = AdminDataConfig(base_url='https://admin.example', issuer='https://admin.example/api/auth',
        resource='https://dream.example/api', service_client_id='dream-service', service_secret='s' * 32)
    state = {'status': 200, 'snapshot': {'kind': 'note', 'title': '正文', 'created_at': None, 'paragraphs': ['公开文字']}, 'config': config}
    reads = []
    def upstream(request):
        reads.append(request)
        return httpx.Response(state['status'], json=state['snapshot'])
    original_client = httpx.AsyncClient
    monkeypatch.setattr(external_shares.AdminDataConfig, 'from_env', lambda: state['config'])
    monkeypatch.setattr(external_shares.httpx, 'AsyncClient', lambda **options: original_client(**options, transport=httpx.MockTransport(upstream)))
    app = FastAPI(); app.include_router(external_shares.router)
    with TestClient(app) as client:
        yield client, state, reads

def test_anonymous_read_forwards_no_visitor_or_service_credentials(public_boundary):
    client, state, reads = public_boundary
    response = client.get('/api/public/shares/' + TOKEN, headers={'authorization': 'Bearer visitor', 'cookie': 'private=visitor'})
    assert response.status_code == 200 and response.json() == state['snapshot']
    assert len(reads) == 1 and str(reads[0].url) == 'https://admin.example/api/public/shares/' + TOKEN
    assert not {'authorization', 'cookie', 'x-ink-dream-service-authorization'} & reads[0].headers.keys()
    assert response.headers['cache-control'] == 'no-store'

@pytest.mark.parametrize('status,expected', [(404, 404), (410, 404), (500, 503), (302, 503)])
def test_missing_revoked_or_unavailable_upstream_hides_snapshot(public_boundary, status, expected):
    client, state, _ = public_boundary; state['status'] = status
    response = client.get('/api/public/shares/' + TOKEN)
    assert response.status_code == expected and '公开文字' not in response.text

def test_invalid_or_oversized_public_output_fails_closed(public_boundary):
    client, state, _ = public_boundary
    state['snapshot']['owner_id'] = 'private-owner'
    assert client.get('/api/public/shares/' + TOKEN).status_code == 503
    del state['snapshot']['owner_id']; state['config'] = replace(state['config'], max_response_bytes=16)
    assert client.get('/api/public/shares/' + TOKEN).status_code == 503

def test_chat_snapshot_excludes_system_tool_process_and_hidden_messages():
    message = lambda role, text, **extra: {'role': role, 'parts': [{'type': 'text', 'text': text}], **extra}
    source = [message('system', 'secret'), message('user', 'question'),
        message('user', 'hidden', metadata={'visibility': 'system-hidden'}),
        {'role': 'assistant', 'parts': [{'type': 'text', 'text': 'process'}, {'type': 'tool-result', 'secret': 'tool'}, {'type': 'text', 'text': 'final'}],
         'metadata': {'turnId': 'turn', 'turnStatus': 'completed', 'finalPartIndex': 2}, 'history_final_text': 'final'},
        message('assistant', 'interrupted process', history_final_text='interrupted process', metadata={'turnId': 'partial', 'turnStatus': 'cancelled', 'is_partial': True}),
        message('assistant', 'legacy final')]
    assert [item.model_dump() for item in external_shares.project_shared_messages(source)] == [
        {'role': 'user', 'content': 'question'}, {'role': 'assistant', 'content': 'final'}, {'role': 'assistant', 'content': 'legacy final'}]

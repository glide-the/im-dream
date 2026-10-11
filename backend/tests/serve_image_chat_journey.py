# [Input] Named temporary root, production public-journey composition and injected provider/storage/SDK seams.
# [Output] One isolated HTTP server for Chrome settings-to-send-to-file-to-history journeys and safe receipts.
# [Pos] Test-only launcher; no alternate production state machine, database or real-model acceptance.
# [Sync] 2026-10-10: reuse public production routers and the same Factory/Service/transport contracts.
# [Sync] 2026-10-11: hold only the injected SDK before Images dispatch to exercise the original public Stop path.
from __future__ import annotations

import argparse
import asyncio
import hashlib
import json
from pathlib import Path
import socket
from types import SimpleNamespace

import pytest
import uvicorn
from fastapi import Request

from tests.test_image_chat_public_journey import build_public_journey_app, Response
from routers import storage as storage_route, system_config as settings_route
from services.admin_data.system_config_data import SystemConfigGetInputDTO


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--root', required=True)
    args = parser.parse_args()
    root = Path(args.root).resolve()
    if root.name != 'image-chat-browser-fixture' or root.exists():
        raise RuntimeError('Use a fresh named image-chat-browser-fixture directory')
    root.mkdir(parents=True, mode=0o700)
    patches = pytest.MonkeyPatch()
    app, fixture, config, transport, runner_calls, factory = build_public_journey_app(patches, root)
    config.update(model='available-text')
    config.pop('image_model', None)
    state = {'fail_result': False, 'fail_image_read': False, 'hold_image': False}
    original_get = transport.get
    original_post = transport.post
    def get(*args, **kwargs):
        response = original_get(*args, **kwargs)
        entry = dict(response.payload['data'][-1], id='image-second', display_name='image-second')
        response.payload['data'].append(entry)
        return response
    def post(*args, **kwargs):
        response = original_post(*args, **kwargs)
        return Response({'data': []}) if state['fail_result'] else response
    transport.get, transport.post = get, post

    class SettingsData:
        def __init__(self, _): pass
        def get_user(self, dto, request_id, *, access_token): return dict(config)
        def patch_user(self, dto, request_id, *, access_token):
            config.update(dto.model_dump(mode='json'))
            return SimpleNamespace(success=True)
        patch_image_model = patch_user
    patches.setattr(settings_route, 'AdminSystemConfigData', SettingsData)
    patches.setattr(settings_route, 'GatewayModelCatalogClient', lambda **kwargs: settings_catalog(**kwargs))
    from services.admin_gateway.models import GatewayModelCatalogClient
    from services.admin_gateway.config import AdminGatewayConfig
    def settings_catalog(*, access_token):
        return GatewayModelCatalogClient(access_token=access_token, configuration=AdminGatewayConfig(True, 'http://127.0.0.1:39999', 'gw_'+'a'*40), transport=transport)

    uploads = {}
    class Storage:
        async def upload(self, data, options):
            key = f'isolated-upload-{len(uploads)}.png'
            metadata = SimpleNamespace(key=key, filename=options.filename, content_type=options.content_type,
                size=len(data), uploaded_at=None)
            uploads[key] = (data, metadata)
            return SimpleNamespace(key=key, metadata=metadata)
        async def download(self, key): return uploads[key][0]
        async def get_metadata(self, key): return uploads[key][1]
    storage = Storage()
    from routers import claude_agent as chat_route
    patches.setattr(chat_route, 'server_file_storage', storage)
    patches.setattr(storage_route, 'server_file_storage', storage)
    patches.setattr(storage_route, 'storage_driver', 'unknown')
    patches.setattr(storage_route, '_check_storage_configuration', lambda: {'is_valid': True})
    app.include_router(settings_route.router)
    app.include_router(storage_route.router)

    @app.middleware('http')
    async def image_read_failure(request: Request, call_next):
        if state['fail_image_read'] and request.url.path == '/api/workspace/files/content':
            return ResponseHttp(status_code=503)
        return await call_next(request)
    from starlette.responses import Response as ResponseHttp

    @app.get('/auth/session')
    async def session():
        return {'user': {'id': '7', 'email': 'image-browser@example.test', 'display_name': 'Isolated fixture',
            'avatar_url': None, 'role': 'user', 'created_at': None}, 'csrf_token': 's'*43}

    @app.get('/_fixture/receipt')
    async def receipt():
        return {'config': config, 'calls': [{'operation': url.rsplit('/', 1)[-1],
            'model': (kwargs.get('json') or kwargs.get('data'))['model'],
            'input_hash': hashlib.sha256(kwargs['files'][0][1][1]).hexdigest() if kwargs.get('files') else None}
            for url, kwargs in transport.calls],
            'native_calls':transport.native_calls, 'runner_models': [call.model for call in runner_calls], 'messages': len(fixture.messages),
            'upload_hashes': [hashlib.sha256(data).hexdigest() for data, _ in uploads.values()]}

    @app.post('/_fixture/mode')
    async def mode(values: dict):
        for key in state:
            if key in values: state[key] = bool(values[key])
        transport.hold_image = state['hold_image']
        return {'ok': True}

    @app.on_event('shutdown')
    async def shutdown(): await factory.aclose()

    owned = socket.socket()
    owned.bind(('127.0.0.1', 0))
    owned.listen(128)
    print(json.dumps({'port': owned.getsockname()[1]}), flush=True)
    try:
        uvicorn.Server(uvicorn.Config(app, log_level='warning')).run(sockets=[owned])
    finally:
        owned.close()
        patches.undo()


if __name__ == '__main__': main()

# [Input] Production BFF, FastAPI dependencies, Deck route and Admin HTTP DTO assembly.
# [Output] Isolated trace parentage, privacy, sampling and failure-path contracts.
# [Pos] Provider-free verification; loopback listeners and synthetic Admin/plugin data only.
from __future__ import annotations

import hashlib
import hmac
import json
import os
from pathlib import Path
import socket
import subprocess
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import httpx
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import SimpleSpanProcessor
from opentelemetry.sdk.trace.export.in_memory_span_exporter import InMemorySpanExporter
from opentelemetry.sdk.trace.sampling import ParentBased, TraceIdRatioBased
from opentelemetry.trace.propagation.tracecontext import TraceContextTextMapPropagator
from opentelemetry import context, trace
from opentelemetry.trace import SpanKind, Status, StatusCode

import observability as obs
from tests.test_admin_deck_default_routes import boundary, HEADERS

SECRET = 'synthetic-trace-key-' + 's' * 32
ATTACKER = '00-' + 'a' * 32 + '-' + 'b' * 16 + '-01'


@pytest.fixture
def tracing(monkeypatch):
    exporter = InMemorySpanExporter()
    provider = TracerProvider(sampler=ParentBased(TraceIdRatioBased(1)))
    provider.add_span_processor(SimpleSpanProcessor(exporter))
    for name, value in {'_tracer': provider.get_tracer('isolated-dream'), '_provider': provider,
        '_propagator': TraceContextTextMapPropagator(), '_context_secret': SECRET.encode(),
        'trace': trace, 'otel_context': context, 'SpanKind': SpanKind, 'Status': Status, 'StatusCode': StatusCode}.items():
        monkeypatch.setattr(obs, name, value)
    yield exporter
    provider.shutdown()


def signed_headers(path='/api/decks/defaults/reconcile', stamp=None, parent=ATTACKER):
    stamp = str(int(time.time())) if stamp is None else stamp
    signature = hmac.new(SECRET.encode(), '\n'.join((stamp, parent, 'POST', path)).encode(), hashlib.sha256).hexdigest()
    return {**HEADERS, 'traceparent': parent, 'x-ink-trace-time': stamp, 'x-ink-trace-signature': signature,
            'tracestate': 'foreign=private-state', 'baggage': 'identity=private-person'}


def traced_client(browser):
    return TestClient(obs.TraceMiddleware(browser.app), raise_server_exceptions=False)


def test_reconcile_signed_parent_and_original_dto_flow(boundary, tracing):
    browser, state, verifiers, _ = boundary
    response = traced_client(browser).post('/api/decks/defaults/reconcile?private_query=secret-query', headers=signed_headers())
    assert response.status_code == 200
    assert response.headers['x-trace-id'] == 'a' * 32
    assert response.headers['x-trace-sampled'] == '1'
    assert [call[0] for call in state['calls']] == ['deck.default-plugin.resolve', 'deck.reconcile-default']
    assert [call[0] for call in verifiers] == ['artifact', 'cli']
    spans = tracing.get_finished_spans()
    root = next(s for s in spans if s.name == 'POST /api/decks/defaults/reconcile')
    assert root.parent.span_id == int('b' * 16, 16)
    expected = {'dream.authentication', 'dream.deck.default_plugin.resolve', 'dream.deck.artifact.verify',
                'dream.deck.cli.compatibility', 'dream.deck.reconcile', 'admin.http'}
    assert expected <= {s.name for s in spans}
    assert {s.context.trace_id for s in spans} == {int('a' * 32, 16)}
    assert sum(s.name == 'POST /api/decks/defaults/reconcile' for s in spans) == 1
    for s in spans:
        assert not s.events and not s.links and s.status.description is None
        attributes = json.dumps(dict(s.attributes))
        for private in ('secret-query', 'write-token', 'private-person', 'private-state', 'installation-drama-forge', 'opaque-ba-subject'):
            assert private not in attributes


@pytest.mark.parametrize('change', ['unsigned', 'signature', 'expired', 'wrong-path', 'duplicate'])
def test_public_trace_headers_never_select_parent(boundary, tracing, change):
    browser, *_ = boundary
    headers = signed_headers()
    if change == 'unsigned': headers.pop('x-ink-trace-signature')
    if change == 'signature': headers['x-ink-trace-signature'] = '0' * 64
    if change == 'expired': headers = signed_headers(stamp='1')
    if change == 'wrong-path': headers = signed_headers(path='/other')
    header_items = list(headers.items())
    if change == 'duplicate': header_items.append(('traceparent', ATTACKER))
    response = traced_client(browser).post('/api/decks/defaults/reconcile', headers=header_items)
    assert response.status_code == 200
    assert response.headers['x-trace-id'] != 'a' * 32
    root = next(s for s in tracing.get_finished_spans() if s.name.startswith('POST /api/'))
    assert root.parent is None


def test_rejected_auth_and_plugin_failure_keep_correlation(boundary, tracing, monkeypatch):
    browser, state, *_ = boundary
    client = traced_client(browser)
    response = client.post('/api/decks/defaults/reconcile')
    assert response.status_code == 401 and len(response.headers['x-trace-id']) == 32
    assert state['calls'] == []
    from services.deck import defaults
    monkeypatch.setattr(defaults.PluginInstallService, 'check_cli_compatibility', staticmethod(lambda _: False))
    response = client.post('/api/decks/defaults/reconcile', headers=HEADERS)
    assert response.status_code == 409
    assert state['calls'][-1][0] == 'deck.default-plugin.resolve'
    assert not any(s.name == 'dream.deck.reconcile' for s in tracing.get_finished_spans())
    assert next(s for s in tracing.get_finished_spans() if s.name == 'dream.deck.cli.compatibility').status.status_code == StatusCode.ERROR


def test_unhandled_500_and_streaming_preserve_response(tracing):
    from fastapi.responses import StreamingResponse
    app = FastAPI()
    @app.get('/broken')
    def broken(): raise RuntimeError('private-error-body')
    @app.get('/stream')
    def stream(): return StreamingResponse(iter([b': first\n\n', b'data: done\n\n']), media_type='text/event-stream')
    client = TestClient(obs.TraceMiddleware(app), raise_server_exceptions=False)
    response = client.get('/broken')
    assert response.status_code == 500 and response.headers['x-trace-id']
    assert client.get('/stream').content == b': first\n\ndata: done\n\n'
    assert all('private-error-body' not in str(s.attributes) for s in tracing.get_finished_spans())


def test_unsampled_request_still_exposes_id(boundary, tracing, monkeypatch):
    provider = TracerProvider(sampler=ParentBased(TraceIdRatioBased(0)))
    monkeypatch.setattr(obs, '_tracer', provider.get_tracer('unsampled'))
    response = traced_client(boundary[0]).post('/api/decks/defaults/reconcile', headers=HEADERS)
    assert response.status_code == 200 and len(response.headers['x-trace-id']) == 32
    assert response.headers['x-trace-sampled'] == '0' and tracing.get_finished_spans() == ()
    provider.shutdown()


def test_disabled_does_not_import_optional_sdk():
    backend = Path(__file__).parents[1]
    script = '''import builtins, os
original = builtins.__import__
def guarded(name, *args, **kwargs):
    if name.startswith('opentelemetry'): raise AssertionError('optional SDK imported')
    return original(name, *args, **kwargs)
builtins.__import__ = guarded
os.environ.pop('INK_TRACE_ENABLED', None)
from observability import TracedFastAPI
from fastapi.testclient import TestClient
app = TracedFastAPI()
@app.get('/ready')
def ready(): return {'ready': True}
response = TestClient(app).get('/ready')
assert response.json() == {'ready': True}
assert 'x-trace-id' not in response.headers
'''
    result = subprocess.run([str(backend / '.venv/bin/python'), '-c', script], cwd=backend, capture_output=True, text=True, timeout=20)
    assert result.returncode == 0, result.stderr


def test_configuration_failure_never_exposes_endpoint(monkeypatch, caplog):
    monkeypatch.setattr(obs, '_configured', False)
    monkeypatch.setattr(obs, '_tracer', None)
    monkeypatch.setenv('INK_TRACE_ENABLED', 'true')
    monkeypatch.setenv('OTEL_EXPORTER_OTLP_TRACES_ENDPOINT', 'invalid-private-license-endpoint')
    obs.configure_tracing()
    assert obs._tracer is None
    assert 'Tracing unavailable' in caplog.text and 'invalid-private-license' not in caplog.text


def test_bff_python_admin_handoff_over_loopback(boundary, tracing, monkeypatch):
    import uvicorn
    browser, state, _, _ = boundary
    http = browser.app.state.admin_request_auth.client._http
    original = http._transport.handle_request
    admin_requests = []
    def admin_handler(request):
        admin_requests.append(request)
        parent = obs._propagator.extract(dict(request.headers), context=context.Context())
        with obs.span('admin.fixture.request', kind='SERVER', parent=parent):
            return original(request)
    monkeypatch.setattr(http._transport, 'handle_request', admin_handler)
    exports = []
    class Collector(BaseHTTPRequestHandler):
        def do_POST(self):
            if self.headers.get('transfer-encoding') == 'chunked':
                body = bytearray()
                while True:
                    length = int(self.rfile.readline().split(b';')[0], 16)
                    if length == 0:
                        self.rfile.readline()
                        break
                    body.extend(self.rfile.read(length))
                    self.rfile.read(2)
            else:
                body = self.rfile.read(int(self.headers['content-length']))
            exports.append(json.loads(body))
            self.send_response(200); self.end_headers(); self.wfile.write(b'{}')
        def log_message(self, *_): pass
    collector = ThreadingHTTPServer(('127.0.0.1', 0), Collector)
    collector_thread = threading.Thread(target=collector.serve_forever, daemon=True)
    collector_thread.start()
    listener = socket.socket()
    listener.bind(('127.0.0.1', 0))
    server = uvicorn.Server(uvicorn.Config(obs.TraceMiddleware(browser.app), log_config=None, access_log=False, lifespan='off'))
    server_thread = threading.Thread(target=server.run, kwargs={'sockets': [listener]}, daemon=True)
    server_thread.start()
    try:
        deadline = time.monotonic() + 5
        while not server.started and time.monotonic() < deadline: time.sleep(.01)
        assert server.started
        environment = {k: v for k, v in os.environ.items() if not k.startswith(('OTEL_', 'ARMS_', 'INK_TRACE_'))}
        environment.update(INK_TRACE_ENABLED='true', INK_TRACE_CONTEXT_SECRET=SECRET, OTEL_SERVICE_NAME='isolated-dream-bff',
            OTEL_TRACES_SAMPLER_ARG='1', OTEL_BSP_SCHEDULE_DELAY='10',
            OTEL_EXPORTER_OTLP_TRACES_ENDPOINT=f'http://127.0.0.1:{collector.server_port}/v1/traces',
            TRACE_FIXTURE_BACKEND=f'http://127.0.0.1:{listener.getsockname()[1]}')
        root = Path(__file__).parents[2]
        result = subprocess.run(['node', '--experimental-strip-types', 'e2e/fixtures/trace-proxy.ts'], cwd=root / 'frontend',
            env=environment, capture_output=True, text=True, timeout=30)
        assert result.returncode == 0, result.stderr
        output = json.loads(result.stdout.strip().splitlines()[-1])
        assert output['status'] == 200 and output['linked'] == '1'
        assert output['id'] != 'a' * 32
        assert [call[0] for call in state['calls']] == ['deck.default-plugin.resolve', 'deck.reconcile-default']
        python_spans = tracing.get_finished_spans()
        root_span = next(s for s in python_spans if s.name == 'POST /api/decks/defaults/reconcile')
        assert f'{root_span.context.trace_id:032x}' == output['id']
        js_spans = [span for batch in exports for resource in batch['resourceSpans'] for scope in resource['scopeSpans'] for span in scope['spans']]
        assert {'POST /api/[[...path]]', 'bff.authentication', 'dream.http', 'admin.http'} <= {s['name'] for s in js_spans}
        assert {s['traceId'] for s in js_spans} == {output['id']}
        dream_client = next(s for s in js_spans if s['name'] == 'dream.http')
        assert f'{root_span.parent.span_id:016x}' == dream_client['spanId']
        assert all(r.headers.get('traceparent', '').split('-')[1] == output['id'] for r in admin_requests)
        assert all('tracestate' not in r.headers and 'baggage' not in r.headers for r in admin_requests)
        ids = {s.context.span_id for s in python_spans}
        assert all(s.parent.span_id in ids for s in python_spans if s.name == 'admin.fixture.request')
        serialized = json.dumps(exports) + result.stdout + result.stderr
        for private in ('secret-query', 'private-cookie', 'write-token', 'fixture.service', 'private-body', 'foreign-state'):
            assert private not in serialized
    finally:
        server.should_exit = True
        server_thread.join(5)
        listener.close()
        collector.shutdown(); collector.server_close(); collector_thread.join(5)
        assert not server_thread.is_alive() and not collector_thread.is_alive()


def test_mobile_packaging_rejects_private_trace_configuration():
    import importlib.util
    scripts = Path(__file__).parents[2] / 'frontend/ios/scripts'
    spec = importlib.util.spec_from_file_location('isolated_mobile_env_policy', scripts / 'mobile_env_policy.py')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    for key in ('OTEL_EXPORTER_OTLP_TRACES_ENDPOINT', 'OTEL_EXPORTER_OTLP_HEADERS', 'ARMS_LICENSE_KEY', 'INK_TRACE_CONTEXT_SECRET'):
        with pytest.raises(RuntimeError, match='outside mobile environment') as error:
            module.validate_mobile_environment(f'export {key}="private-license-value\nsecond-line"\n')
        assert 'private-license-value' not in str(error.value)
    module.validate_mobile_environment('INK_DREAM_PUBLIC_ORIGIN=http://localhost:5173\n# OTEL_SERVICE_NAME=comment\n')
    assert '"observability.py"' in (scripts / 'bundle-python.py').read_text()


def test_real_export_failure_is_redacted_and_independent(monkeypatch, caplog):
    import logging
    from fastapi import FastAPI
    requested = threading.Event()
    release = threading.Event()
    class RejectingCollector(BaseHTTPRequestHandler):
        def do_POST(self):
            self.rfile.read(int(self.headers['content-length']))
            requested.set()
            release.wait(2)
            self.send_response(400); self.end_headers()
            self.wfile.write(b'private-response-credential')
        def log_message(self, *_): pass
    receiver = ThreadingHTTPServer(('127.0.0.1', 0), RejectingCollector)
    thread = threading.Thread(target=receiver.serve_forever, daemon=True)
    thread.start()
    logger = logging.getLogger('dream.trace')
    old_handlers, old_level, old_propagate = list(logger.handlers), logger.level, logger.propagate
    monkeypatch.setattr(obs, '_configured', False)
    monkeypatch.setattr(obs, '_provider', None)
    monkeypatch.setattr(obs, '_tracer', None)
    monkeypatch.setenv('INK_TRACE_ENABLED', 'true')
    monkeypatch.setenv('INK_TRACE_CONTEXT_SECRET', SECRET)
    monkeypatch.setenv('OTEL_SERVICE_NAME', 'isolated-dream-api')
    monkeypatch.setenv('OTEL_TRACES_SAMPLER_ARG', '1')
    monkeypatch.setenv('OTEL_BSP_SCHEDULE_DELAY', '1')
    monkeypatch.setenv('OTEL_EXPORTER_OTLP_TRACES_ENDPOINT', f'http://127.0.0.1:{receiver.server_port}/private-license/v1/traces')
    try:
        app = obs.TracedFastAPI()
        assert obs._tracer is not None
        logger.addHandler(caplog.handler)
        @app.get('/ready')
        def ready(): return {'ready': True}
        response = TestClient(app).get('/ready?secret-query=private')
        assert response.json() == {'ready': True} and response.headers['x-trace-sampled'] == '1'
        assert requested.wait(2)  # Business response completed while export waits.
        release.set()
        assert obs._provider.force_flush(timeout_millis=2000)
        assert 'Trace export failed' in caplog.text
        assert response.headers['x-trace-id'] in caplog.text
        for private in ('private-license', 'private-response-credential', 'secret-query'):
            assert private not in caplog.text
    finally:
        release.set()
        if obs._provider: obs._provider.shutdown()
        logger.handlers, logger.level, logger.propagate = old_handlers, old_level, old_propagate
        receiver.shutdown(); receiver.server_close(); thread.join(5)

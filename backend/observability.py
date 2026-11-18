# [Input] Explicit process-owned OTLP configuration and W3C request context.
# [Output] Bounded metadata-only spans, response IDs and correlated request timings.
# [Pos] Web and embedded iOS ASGI, startup and Admin transport instrumentation.
# [Sync] 2026-11-19: record real startup spans and accept isolated iOS exporter settings.
# [Sync] 2026-11-19: read private Web settings at Python startup and identify real peer endpoints.
from __future__ import annotations

from contextlib import contextmanager
import hashlib
import hmac
import logging
import math
import os
from pathlib import Path
import stat
import threading
import time
from urllib.parse import urlsplit
from uuid import uuid4

from dotenv import dotenv_values
from fastapi import FastAPI
trace = None
otel_context = None
SpanKind = Status = StatusCode = None

_logger = logging.getLogger('dream.trace')
_propagator = None
_context_secret = None
_tracer = None
_provider = None
_configured = False
_lock = threading.Lock()
_METHODS = frozenset({'GET', 'POST', 'PUT', 'PATCH', 'DELETE', 'HEAD', 'OPTIONS', 'CONNECT', 'TRACE'})
_WEB_PYTHON_SERVICE = 'ink-memory-dream-web-python'


def web_trace_settings():
    if 'INK_TRACE_ENABLED' in os.environ:
        return os.environ
    try:
        path = os.environ.get('INK_DREAM_WEB_TRACE_ENV_FILE') or Path.home() / '.config/ink-memory/dream-web-trace.env'
        fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
        with os.fdopen(fd, encoding='utf-8') as source:
            metadata = os.fstat(source.fileno())
            if not stat.S_ISREG(metadata.st_mode) or metadata.st_mode & 0o077 or metadata.st_size > 16384:
                raise ValueError('private settings')
            return {key: value for key, value in dotenv_values(stream=source, interpolate=False).items() if value is not None}
    except FileNotFoundError:
        return {}
    except (OSError, ValueError):
        _logger.warning('Private Web tracing configuration unavailable')
        return {}


def admin_http_attributes(url: str, method: str) -> dict[str, str | int]:
    parsed = urlsplit(url)
    service = 'ink-memory-admin'
    return {'http.request.method': method, 'server.address': parsed.hostname or '',
            'server.port': parsed.port or (443 if parsed.scheme == 'https' else 80),
            'server.service.name': service, 'peer.service': service}


class _ExportLogFilter(logging.Filter):
    def filter(self, record):
        # OTLP endpoints and error response bodies can contain authorization data.
        record.msg, record.args, record.exc_info, record.exc_text = 'Trace export failed', (), None, None
        return True


def configure_tracing(settings=None, *, signed_parent=True) -> None:
    """Initialize once per process; unavailable observation leaves business operational."""
    global _configured, _provider, _tracer, _propagator, _context_secret
    global trace, otel_context, SpanKind, Status, StatusCode
    with _lock:
        if _configured:
            return
        _configured = True
        settings = os.environ if settings is None else settings
        if settings.get('INK_TRACE_ENABLED', '').lower() != 'true':
            return
        try:
            from opentelemetry import context as otel_context, trace
            from opentelemetry.trace import SpanKind, Status, StatusCode
            from opentelemetry.trace.propagation.tracecontext import TraceContextTextMapPropagator
            from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
            from opentelemetry.sdk.resources import Resource
            from opentelemetry.sdk.trace import TracerProvider, SpanLimits
            from opentelemetry.sdk.trace.export import BatchSpanProcessor
            from opentelemetry.sdk.trace.sampling import ALWAYS_ON, ParentBased, TraceIdRatioBased
            from opentelemetry.util.re import parse_env_headers

            endpoint = settings['OTEL_EXPORTER_OTLP_TRACES_ENDPOINT']
            parsed = urlsplit(endpoint)
            if parsed.scheme not in {'http', 'https'} or not parsed.hostname or parsed.username or parsed.password or parsed.fragment:
                raise ValueError('endpoint')
            service = settings.get('OTEL_SERVICE_NAME', '').strip()
            if signed_parent and service in {'', 'ink-memory-dream-web'}:
                service = _WEB_PYTHON_SERVICE
            secret = settings.get('INK_TRACE_CONTEXT_SECRET', '').encode() if signed_parent else None
            if signed_parent and len(secret) < 32:
                raise ValueError('context secret')
            queue = _positive_setting(settings, 'OTEL_BSP_MAX_QUEUE_SIZE', 2048)
            batch = _positive_setting(settings, 'OTEL_BSP_MAX_EXPORT_BATCH_SIZE', 512)
            delay = _positive_setting(settings, 'OTEL_BSP_SCHEDULE_DELAY', 5000)
            if batch > queue:
                raise ValueError('batch budget')
            ratio = float(settings.get('OTEL_TRACES_SAMPLER_ARG', '0.1'))
            if not service or not math.isfinite(ratio) or not 0 <= ratio <= 1:
                raise ValueError('configuration')
            # Dream owns one explicit provider. Reject auto-instrumentation ownership
            # so a second SDK cannot duplicate spans or bypass the metadata policy.
            if not isinstance(trace.get_tracer_provider(), trace.ProxyTracerProvider):
                raise ValueError('provider already installed')
            for name in ('opentelemetry.exporter.otlp.proto.http.trace_exporter', 'opentelemetry.sdk._shared_internal'):
                logging.getLogger(name).addFilter(_ExportLogFilter())
            header_text = settings.get('OTEL_EXPORTER_OTLP_TRACES_HEADERS', settings.get('OTEL_EXPORTER_OTLP_HEADERS', ''))
            exporter = OTLPSpanExporter(endpoint=endpoint, timeout=3, headers=parse_env_headers(header_text, liberal=True))

            class StartupSampler(TraceIdRatioBased):
                def should_sample(self, parent_context, trace_id, name, *args, **kwargs):
                    if name.startswith('dream.startup.'):
                        return ALWAYS_ON.should_sample(parent_context, trace_id, name, *args, **kwargs)
                    return super().should_sample(parent_context, trace_id, name, *args, **kwargs)

            resource = {'service.name': service, 'service.namespace': 'ink-memory-dream',
                        'service.instance.id': str(uuid4()), 'ink.dream.platform': 'web' if signed_parent else 'ios'}
            if settings.get('INK_TRACE_HOST_NAME', '').strip():
                resource['host.name'] = settings['INK_TRACE_HOST_NAME'].strip()
            provider = TracerProvider(resource=Resource(resource),
                sampler=ParentBased(StartupSampler(ratio)), span_limits=SpanLimits(max_events=0, max_links=0))
            provider.add_span_processor(BatchSpanProcessor(exporter, max_queue_size=queue,
                max_export_batch_size=batch, schedule_delay_millis=delay, export_timeout_millis=3000))
            _propagator, _context_secret = TraceContextTextMapPropagator(), secret
            _provider, _tracer = provider, provider.get_tracer('ink-memory-dream')
            _logger.setLevel(logging.INFO)
            if not _logger.handlers:
                _logger.addHandler(logging.StreamHandler())
            _logger.propagate = False
        except Exception:
            # Never include an exception string: configuration may contain keys.
            _logger.warning('Tracing unavailable; continuing without trace export')


def _positive_setting(settings, key: str, default: int) -> int:
    value = int(settings.get(key, str(default)))
    if not 1 <= value <= 2_147_483_647:
        raise ValueError('trace budget')
    return value


def _request_parent(scope):
    # Browser/native callers start a root. Only the private BFF can sign a parent.
    parent = otel_context.Context()
    if _context_secret is None:
        return parent
    values = {}
    for key, value in scope.get('headers', []):
        name = key.decode('latin1').lower()
        if name in {'traceparent', 'x-ink-trace-time', 'x-ink-trace-signature'}:
            if name in values:
                return parent
            values[name] = value.decode('latin1')
    try:
        stamp = values['x-ink-trace-time']
        if len(stamp) > 12 or abs(time.time() - int(stamp)) > 60:
            return parent
        traceparent = values['traceparent']
        if len(traceparent) != 55 or len(values['x-ink-trace-signature']) != 64:
            return parent
        message = '\n'.join((stamp, traceparent, scope['method'], scope['path']))
        expected = hmac.new(_context_secret, message.encode(), hashlib.sha256).hexdigest()
        if not hmac.compare_digest(expected, values['x-ink-trace-signature']):
            return parent
        return _propagator.extract({'traceparent': traceparent}, context=parent)
    except (KeyError, ValueError, TypeError):
        return parent


@contextmanager
def span(name: str, *, kind='INTERNAL', parent=None, attributes=None):
    if _tracer is None:
        yield None
        return
    with _tracer.start_as_current_span(name, context=parent, kind=SpanKind[kind],
        attributes=attributes, record_exception=False, set_status_on_exception=False) as current:
        try:
            yield current
        except BaseException:
            current.set_status(Status(StatusCode.ERROR))
            raise


def mark_error(current) -> None:
    if current is not None:
        current.set_status(Status(StatusCode.ERROR))


def record_startup(component, started_ns, *, ended_ns=None, failed=False):
    """Record a completed launch using a fixed name and an explicit time window."""
    if _tracer is None:
        return
    try:
        current = _tracer.start_span(f'dream.startup.{component}', context=otel_context.Context(),
                                     kind=SpanKind.SERVER, start_time=started_ns)
        if failed:
            mark_error(current)
        current.end(end_time=ended_ns)
    except Exception:
        pass


def inject_trace(headers: dict[str, str]) -> dict[str, str]:
    """Project only W3C trace context; preserve explicit authentication and request IDs."""
    projected = {key: value for key, value in headers.items() if key.lower() not in {'traceparent', 'tracestate', 'baggage'}}
    if _tracer is not None:
        _propagator.inject(projected)
        projected.pop("tracestate", None)
    return projected


class TraceMiddleware:
    """Wrap the entire ASGI stack, including generated 500 responses and streaming."""
    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope['type'] == 'lifespan' and _tracer is not None:
            started = time.time_ns()

            async def startup_observed(message):
                if message['type'] in {'lifespan.startup.complete', 'lifespan.startup.failed'}:
                    record_startup('web.python', started, failed=message['type'] == 'lifespan.startup.failed')
                await send(message)

            return await self.app(scope, receive, startup_observed)
        if scope['type'] != 'http' or _tracer is None:
            return await self.app(scope, receive, send)
        parent = _request_parent(scope)
        method = scope.get('method', '')
        method = method if method in _METHODS else 'OTHER'
        started, status = time.perf_counter(), 500
        with span('HTTP ' + method, kind="SERVER", parent=parent,
                  attributes={'http.request.method': method}) as current:
            identity = current.get_span_context()
            trace_id, span_id = f'{identity.trace_id:032x}', f'{identity.span_id:016x}'

            async def correlated_send(message):
                nonlocal status
                if message['type'] == 'http.response.start':
                    status = message['status']
                    response_headers = [(key, value) for key, value in message.get('headers', [])
                        if key.lower() not in {b'x-trace-id', b'x-trace-sampled'}]
                    response_headers.extend([(b'x-trace-id', trace_id.encode()),
                        (b'x-trace-sampled', b'1' if identity.trace_flags.sampled else b'0')])
                    message = {**message, 'headers': response_headers}
                await send(message)

            try:
                await self.app(scope, receive, correlated_send)
            finally:
                route = getattr(scope.get('route'), 'path', None) or '<unmatched>'
                current.update_name(f'{method} {route}')
                current.set_attribute('http.route', route)
                current.set_attribute('http.response.status_code', status)
                if status >= 500:
                    current.set_status(Status(StatusCode.ERROR))
                try:
                    _logger.info('request trace_id=%s span_id=%s sampled=%s method=%s route=%s status=%s duration_ms=%.3f',
                        trace_id, span_id, int(identity.trace_flags.sampled), method, route, status,
                        (time.perf_counter() - started) * 1000)
                except Exception:
                    pass


class TracedFastAPI(FastAPI):
    """Keep the original FastAPI public interface and trace its complete ASGI call."""
    def __init__(self, *args, trace_settings=None, **kwargs):
        super().__init__(*args, **kwargs)
        configure_tracing(trace_settings)
        self._trace_app = TraceMiddleware(super().__call__)

    async def __call__(self, scope, receive, send):
        await self._trace_app(scope, receive, send)

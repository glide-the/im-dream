# [Input] Current production startup definitions, injected clocks/owners and synthetic console metadata.
# [Output] Provider-free timing/error/startup-compatibility and offline evidence-reader contracts.
# [Pos] APP-03 isolated validation; execution paused at the user's request on 2026-11-02.
# [Sync] 2026-11-02: prepare checks without importing backend configuration or starting native/business services.

import ast
import asyncio
from contextlib import contextmanager, redirect_stderr
import importlib.util
import io
import json
import os
from pathlib import Path
import platform
import sys
import threading
import time
from types import ModuleType, SimpleNamespace
import unittest
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[3]
SOURCE = ROOT / "backend/mobile_runtime/ios.py"


def production_definitions(*names):
    source = ast.parse(SOURCE.read_text())
    selected = ast.Module(body=[node for node in source.body if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name in names], type_ignores=[])
    namespace = dict(contextmanager=contextmanager, json=json, os=os, time=time, sys=sys, platform=platform)
    # Execute the production function bodies with explicit test-owned dependencies.
    exec(compile(selected, str(SOURCE), "exec"), namespace)
    return namespace


spec = importlib.util.spec_from_file_location("app03_summary", Path(__file__).with_name("summarize_startup.py"))
reader = importlib.util.module_from_spec(spec)
spec.loader.exec_module(reader)


class TimingTests(unittest.TestCase):
    def test_wall_and_process_cpu_are_distinct_and_payload_free(self):
        native = production_definitions("_startup_phase")
        native["time"] = SimpleNamespace(
            perf_counter_ns=iter([1_000_000, 9_000_000]).__next__,
            process_time_ns=iter([2_000_000, 3_000_000]).__next__,
            time_ns=lambda: 99_000_000,
        )
        stream = io.StringIO()
        with redirect_stderr(stream), native["_startup_phase"]("public_health_read"):
            pass
        records = reader.read_measurements(stream.getvalue())
        self.assertEqual(records[0]["elapsedMs"], 8)
        self.assertEqual(records[0]["processCpuMs"], 1)
        self.assertEqual(records[0]["outcome"], "ok")
        self.assertNotIn("payload", records[0])

    def test_original_exception_identity_is_preserved_and_omitted_from_log(self):
        native = production_definitions("_startup_phase")
        original = RuntimeError("synthetic-private-account-body")
        stream = io.StringIO()
        with redirect_stderr(stream):
            with self.assertRaises(RuntimeError) as failure:
                with native["_startup_phase"]("next_web_ready"):
                    raise original
        self.assertIs(failure.exception, original)
        self.assertEqual(reader.read_measurements(stream.getvalue())[0]["outcome"], "failed")
        self.assertNotIn(str(original), stream.getvalue())

    def test_closed_diagnostic_stream_does_not_change_success_or_failure(self):
        native = production_definitions("_startup_phase")
        stream = io.StringIO()
        stream.close()
        original = RuntimeError("original-startup-failure")
        with redirect_stderr(stream):
            with native["_startup_phase"]("public_health_read"):
                value = "original-result"
            with self.assertRaises(RuntimeError) as failure:
                with native["_startup_phase"]("next_web_ready"):
                    raise original
        self.assertEqual(value, "original-result")
        self.assertIs(failure.exception, original)


class StartupCompatibilityTests(unittest.TestCase):
    def setUp(self):
        self.native = production_definitions("_startup_phase", "start")
        self.events = []
        self.loops = []

        def new_loop():
            loop = SimpleNamespace(run_forever=lambda: None, stop=lambda: self.events.append("stop"),
                                   call_soon_threadsafe=lambda callback: callback())
            self.loops.append(loop)
            return loop

        async def initialize():
            self.events.append("initialize")
            if getattr(self, "initialization_error", None):
                raise self.initialization_error

        async def complete(value):
            self.assertEqual(value, {"method": "GET", "path": "/api/health"})
            self.events.append("health")
            return {"status": getattr(self, "health_status", 200), "body": '{"status":"ok"}'}

        async def bind(endpoint):
            self.events.append("bind")
            if getattr(self, "binding_error", None):
                raise self.binding_error
            self.assertEqual(endpoint, "synthetic-private-endpoint")

        self.native.update({
            "_loop": None, "_startup_lock": threading.Lock(), "_initialize": initialize, "_complete": complete,
            "_bind_runtime": bind, "_submit": asyncio.run,
            "asyncio": SimpleNamespace(new_event_loop=new_loop),
            "threading": SimpleNamespace(Thread=lambda **kwargs: SimpleNamespace(start=lambda: self.events.append("thread"))),
            "_app": SimpleNamespace(routes=[SimpleNamespace(path="/api/health")]), "_business_routers": (),
            "_factory_owner": None, "_http_owner": None, "_web_origin": None,
        })
        transport = ModuleType("mobile_runtime.ios_claude_transport")

        async def query_status(endpoint):
            self.events.append("status")
            self.assertEqual(endpoint, "synthetic-private-endpoint")
            return {"originalStatus": True}

        transport.query_native_status = query_status
        self.native["__package__"] = "mobile_runtime"
        self.modules = patch.dict(sys.modules, {"mobile_runtime.ios_claude_transport": transport})
        self.modules.start()
        self.addCleanup(self.modules.stop)
        self.stream = io.StringIO()
        self.redirect = redirect_stderr(self.stream)
        self.redirect.__enter__()
        self.addCleanup(self.redirect.__exit__, None, None, None)

    def test_two_stage_start_keeps_one_loop_and_original_facts(self):
        public = json.loads(self.native["start"]())
        bound = json.loads(self.native["start"]('{"runtimeEndpoint":"synthetic-private-endpoint"}'))
        self.assertEqual(self.events, ["thread", "initialize", "health", "health", "status", "bind"])
        self.assertEqual(len(self.loops), 1)
        self.assertIsNone(public["embeddedNode"])
        self.assertEqual(bound["embeddedNode"], {"originalStatus": True})
        self.assertFalse(bound["businessReady"])
        self.assertNotIn("synthetic-private-endpoint", self.stream.getvalue())

    def test_initialization_failure_stops_original_loop_and_allows_retry(self):
        self.initialization_error = RuntimeError("initialization failed")
        with self.assertRaises(RuntimeError) as failure:
            self.native["start"]()
        self.assertIs(failure.exception, self.initialization_error)
        self.assertIsNone(self.native["_loop"])
        self.assertEqual(self.events, ["thread", "initialize", "stop"])
        self.initialization_error = None
        self.native["start"]()
        self.assertEqual(len(self.loops), 2)

    def test_health_failure_preserves_guard_and_skips_binding(self):
        self.health_status = 503
        with self.assertRaisesRegex(RuntimeError, "health handler"):
            self.native["start"]('{"runtimeEndpoint":"synthetic-private-endpoint"}')
        self.assertNotIn("status", self.events)
        self.assertNotIn("bind", self.events)

    def test_binding_failure_propagates_without_reinitializing_public_app(self):
        self.native["start"]()
        self.binding_error = RuntimeError("original bind failure")
        with self.assertRaises(RuntimeError) as failure:
            self.native["start"]('{"runtimeEndpoint":"synthetic-private-endpoint"}')
        self.assertIs(failure.exception, self.binding_error)
        self.assertEqual(self.events.count("initialize"), 1)


class EvidenceReaderTests(unittest.TestCase):
    def record(self, **updates):
        return {"layer": "native", "phase": "startup_total", "outcome": "ok", "elapsedMs": 10,
                "timestampMs": 100, "pid": 42, **updates}

    def test_nested_durations_are_retained_without_summing(self):
        values = [self.record(), self.record(layer="python", phase="factory_prepare", elapsedMs=8, processCpuMs=1)]
        text = "unrelated console\n" + "\n".join("console prefix DREAM_STARTUP " + json.dumps(value) for value in values)
        report = reader.summarize(reader.read_measurements(text), "simulator")
        self.assertTrue(report["durationsOverlap"])
        self.assertTrue(report["processes"][0]["startupCompleted"])
        self.assertEqual(len(report["processes"][0]["phases"]), 2)

    def test_partial_and_failed_samples_remain_incomplete(self):
        for value in [self.record(outcome="failed"), self.record(phase="entry_module_import")]:
            report = reader.summarize([value], "simulator")
            self.assertFalse(report["processes"][0]["startupCompleted"])

    def test_empty_malformed_and_invalid_numeric_records_fail_closed(self):
        for text in ["unrelated console", "DREAM_STARTUP {", "DREAM_STARTUP " + json.dumps(self.record(elapsedMs=-1)),
                     "DREAM_STARTUP " + json.dumps(self.record(processCpuMs=float("nan")))]:
            with self.subTest(text=text), self.assertRaises(ValueError):
                reader.read_measurements(text)


if __name__ == "__main__":
    unittest.main()

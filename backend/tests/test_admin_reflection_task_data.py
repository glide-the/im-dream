# [Input] Frozen Reflections DTO/consumer composition and private snapshot provider.
# [Output] Deterministic contract-shape, receipt, event-bound and workspace tests without Admin/PG/model.
# [Pos] Reflections Admin consumer unit boundary; literal pins identify the reviewed Admin source.
# [Sync] 2026-09-15: cover all sixteen bindings, task-scoped receipt recovery and int4 event limits.

from __future__ import annotations

import tempfile
import unittest
import os
from pathlib import Path
from unittest.mock import patch

import httpx
from pydantic import ValidationError

from services.admin_data.client import AdminDataClient
from services.admin_data.config import AdminDataConfig
from services.admin_data.errors import AdminDataError
from services.admin_data.models import (
    AbsentReceiptDTO,
    CapabilitiesDTO,
    CommittedReceiptDTO,
    OperationCapabilityDTO,
    SchemaCapabilityDTO,
)
from services.admin_data.reflection_task_data import (
    AdminReflectionsData,
    AdminReflectionsWorkerData,
    FROZEN_REFLECTION_TASK_CONTRACTS,
    FROZEN_REFLECTION_TASK_OPERATION_CAPABILITIES,
    FROZEN_REFLECTION_TASK_SCHEMA_REQUIREMENTS,
    REFLECTION_TASK_OPERATION_SPECS,
    REFLECTION_TASK_ADMIN_ARTIFACT_SHA256,
    REFLECTION_TASK_ADMIN_SOURCE_COMMIT,
    REFLECTION_TASK_ADMIN_SOURCE_TREE,
    bind_frozen_reflection_task_contracts,
)
from services.admin_data.request_auth import create_production_admin_request_auth
from services.admin_data.reflection_task_models import (
    AnalysisReportSaveInputDTO,
    AnalysisReportSaveOutputDTO,
    ReflectionEventAppendInputDTO,
    ReflectionEventAppendOutputDTO,
    ReflectionLaunchSnapshotDTO,
    ReflectionSessionSnapshotDTO,
    ReflectionStatsDTO,
    ReflectionTaskAdvanceInputDTO,
    ReflectionTaskLookupDTO,
    ReflectionTaskDTO,
    ReflectionTaskPublicInputDTO,
    ReflectionWorkerLoadOutputDTO,
    reflection_event_id,
)
from services.admin_data.reflection_task_runtime import (
    ReflectionSnapshotSessionProjectionProvider,
    canonical_reflection_workspace,
    prepare_reflection_memory_workspace,
    prepare_reflection_workspace_directory,
    reflection_workspace_root,
    reject_reflection_workspace_symlinks,
    write_reflection_workspace_text,
)
from services.admin_data.session_models import SessionListInputDTO


TASK_ID = "123e4567-e89b-12d3-a456-426614174000"
FIXTURE_HASH = "a" * 64


def _operation_capabilities():
    return tuple(
        OperationCapabilityDTO(
            name=spec.name,
            kind=spec.kind,
            user_scope=spec.user_scope,
            background_scope=spec.background_scope,
            input_schema_version=1,
            output_schema_version=1,
            contract_sha256=FIXTURE_HASH,
        )
        for spec in REFLECTION_TASK_OPERATION_SPECS
    )


def _schema_requirements():
    return tuple(
        SchemaCapabilityDTO(
            capability=name, version=1, contract_sha256=FIXTURE_HASH
        )
        for name in (
            "identity.better-auth.v1",
            "dream.schema.unified.v1",
            "dream.reflection-task-persistence.v1",
        )
    )


def _contracts():
    return bind_frozen_reflection_task_contracts(
        _operation_capabilities(), _schema_requirements()
    )


def _task(status: str = "ASSEMBLING") -> ReflectionTaskDTO:
    terminal = status in {"COMPLETED", "PARTIAL_FAILED", "FAILED"}
    return ReflectionTaskDTO(
        id=TASK_ID,
        task_id=TASK_ID,
        status=status,
        sections=["echoes"],
        input_snapshot=ReflectionTaskPublicInputDTO(
            session_ids=["session-a"],
            start_date=None,
            end_date=None,
            language="en",
            language_label="English",
            session_count=1,
        ),
        workspace_path=f"/tmp/reflections/{TASK_ID}/memory",
        agent_contract_version="reflections-agent-v1",
        error_summary=None,
        revision=2,
        created_at="2026-09-15T00:00:00Z",
        started_at=None,
        completed_at="2026-09-15T00:01:00Z" if terminal else None,
        updated_at="2026-09-15T00:00:01Z",
        section_states=[],
    )


def _snapshot() -> ReflectionLaunchSnapshotDTO:
    return ReflectionLaunchSnapshotDTO(
        schema_version=1,
        task_id=TASK_ID,
        language="en",
        sessions=[
            ReflectionSessionSnapshotDTO(
                id="session-a",
                name="A",
                created_at="2026-09-14T01:00:00Z",
                updated_at="2026-09-15T01:00:00Z",
                labels=["one"],
                first_line="first",
                text="private body",
            )
        ],
        custom_prompts=[],
        stats=ReflectionStatsDTO(days=1, entries=1, words=2),
    )


class _FakeClient:
    def __init__(self, *, receipt_result=None):
        self.capabilities_result = CapabilitiesDTO(
            version="1",
            auth={
                "issuer": "https://admin.example/api/auth",
                "jwks_uri": "https://admin.example/api/auth/jwks",
                "algorithm": "ES256",
                "resource": "dream",
                "clients": {"browser": "browser", "device": "device"},
                "scopes": ["dream:read", "dream:write"],
                "delegations": [],
            },
            schema_capabilities=list(_schema_requirements()),
            operations=list(_operation_capabilities()),
        )
        self.execute_calls = []
        self.receipt_calls = []
        self.execute_result = None
        self.receipt_result = receipt_result

    def capabilities(self, request_id):
        return self.capabilities_result

    def execute(self, operation, input_dto, request_id, *, access_token=None):
        self.execute_calls.append(
            (operation.capability.name, input_dto, request_id, access_token)
        )
        if self.execute_result is None:
            raise AdminDataError("ADMIN_TIMEOUT", 504, request_id, True)
        return self.execute_result

    def receipt(self, operation, request_id, *, access_token=None):
        self.receipt_calls.append(
            ("oauth", operation.capability.name, request_id, access_token)
        )
        return self.receipt_result

    def reflection_task_receipt(self, operation, request_id, *, task_id):
        self.receipt_calls.append(
            ("background", operation.capability.name, request_id, task_id)
        )
        return self.receipt_result


class ReflectionTaskConsumerTest(unittest.TestCase):
    def test_production_composition_matches_frozen_registry99_table(self):
        expected_operations = {
            "reflection-task.create": "c15d1675c16fec60c5c2959dd77913b45ce2fd896a7f34b323112a591b6649af",
            "reflection-task.start": "0a48caa7fb2b25c25162bb5bc493dfe41016023de100eeab0f3f67362726610f",
            "reflection-task.get": "aa53e2b8689cb836e852d6abba39a8842358af64b64d017e5f39df51cb75290e",
            "reflection-task.latest": "ff632283e74a9d8d1d9a42b1641dbcd3e89d5b2bd0993be2878cdea0a85cc709",
            "reflection-task.events": "229d9646d60f27fb284b0be14d3567dfbc231f5909d1af328e72a32be0651e8e",
            "analysis-report.list": "d3507e7ae1cd644bed39f516965cd3a9844ec52c17544f7d6c843dfb0181dcf1",
            "analysis-report.save": "10a26b2fa8af292d5280a86657c6a1dc50a85f52806f9912cf13feaf0f0240c4",
            "reflection-task.worker-load": "4c146054a3d850898582ea1fa303c8039c8ae463cceb7819392450a03ee3c625",
            "reflection-task.advance": "1decdb10f19e0f9cfe16d34f082926e674f9e6cad9a456ac27a0c42ead910516",
            "reflection-section.begin": "b08b0d2b57f03ead192ad47bd478c1b5334666d8e14be860ea4b480fcdc877ee",
            "reflection-section.authority-renew": "f75ac8776ab2ea663594ee11b6f7fff9c2d0cc5a473f27de0ddf6bf88f4c65f0",
            "reflection-section.authority-revoke": "bee7e82dcaefe42ae9e7821265f980eb07cf29d17a067a7987ba98d5fdb5c826",
            "reflection-section.transcript": "27775c5bb6c5510a384a964181419f73d7c42505ea137a833c624aeb8213d00c",
            "reflection-section.finish": "692adcd9cf5c2f622c508f26eec3cebafc2d8ab44b5cc592ecc71d20e4fa666c",
            "reflection-event.append": "68f77f0927e78c6abd71e4dafd42a1ae6ae0f2c62178de50bcd22ceb62cdad66",
            "reflection-report.ensure": "91ec47469be17a39e36ebc9aa493489337a6e8d0d42dbff79da3cc979ca35864",
        }
        expected_schemas = {
            "identity.better-auth.v1": "1dc05e229d3f4147923fcdfe117c4c4930a43bf9f31439d7b4bc83d2a0d04cd3",
            "dream.schema.unified.v1": "8b71cf5687f61dee884c3e6f2fb109c7a951b0789066a0f13583a7b67757fa71",
            "dream.reflection-task-persistence.v1": "52340d24e76db9ee91dfbe8748ebaf3b0f3c2d20f15367c1c096d2e869d4753f",
        }
        self.assertEqual(
            {item.name: item.contract_sha256
             for item in FROZEN_REFLECTION_TASK_OPERATION_CAPABILITIES},
            expected_operations,
        )
        self.assertEqual(
            {item.capability: item.contract_sha256
             for item in FROZEN_REFLECTION_TASK_SCHEMA_REQUIREMENTS},
            expected_schemas,
        )
        self.assertEqual(
            REFLECTION_TASK_ADMIN_ARTIFACT_SHA256,
            "2af7477c424a92c39a1d323b301ef698da147dfa4f1aeb4e8a2166f146981365",
        )
        self.assertEqual(
            REFLECTION_TASK_ADMIN_SOURCE_COMMIT,
            "16a3d9b2796254fa525a966ca851de96d4373445",
        )
        self.assertEqual(
            REFLECTION_TASK_ADMIN_SOURCE_TREE,
            "4ea27088b777163b0e615f963d4e63c32785d69f",
        )
        config = AdminDataConfig(
            base_url="https://admin.example",
            issuer="https://admin.example/api/auth",
            resource="dream",
            service_secret="s" * 32,
            service_client_id="dream",
        )
        owner = create_production_admin_request_auth(config)
        try:
            for operation in FROZEN_REFLECTION_TASK_CONTRACTS.operations:
                self.assertIs(
                    owner.client._operations[operation.capability.name], operation
                )
        finally:
            owner.close()

    def test_binds_all_sixteen_shapes_without_production_hash_constants(self):
        contracts = _contracts()
        self.assertEqual(len(contracts.operations), 16)
        self.assertEqual(
            {item.capability.name for item in contracts.operations},
            {item.name for item in REFLECTION_TASK_OPERATION_SPECS},
        )
        invalid = list(_operation_capabilities())
        invalid[0] = invalid[0].model_copy(update={"kind": "read"})
        with self.assertRaises(AdminDataError):
            bind_frozen_reflection_task_contracts(invalid, _schema_requirements())

    def test_oauth_unknown_write_recovers_only_original_receipt(self):
        output = AnalysisReportSaveOutputDTO(success=True)
        receipt = CommittedReceiptDTO[AnalysisReportSaveOutputDTO](
            status="committed",
            operation="analysis-report.save",
            request_id="request-1",
            result=output,
        )
        client = _FakeClient(receipt_result=receipt)
        data = AdminReflectionsData(client, _contracts())
        result = data.save_report(
            AnalysisReportSaveInputDTO(
                report_type="echoes", report_data_json='{"echoes":[]}'
            ),
            "request-1",
            access_token="oauth-token",
        )
        self.assertIs(result, output)
        self.assertEqual(len(client.execute_calls), 1)
        self.assertEqual(
            client.receipt_calls,
            [("oauth", "analysis-report.save", "request-1", "oauth-token")],
        )

    def test_background_unknown_write_recovers_with_original_task(self):
        event_id = reflection_event_id(TASK_ID, 8)
        output = ReflectionEventAppendOutputDTO(
            event_id=event_id, accepted=True
        )
        receipt = CommittedReceiptDTO[ReflectionEventAppendOutputDTO](
            status="committed",
            operation="reflection-event.append",
            request_id="request-2",
            result=output,
        )
        client = _FakeClient(receipt_result=receipt)
        data = AdminReflectionsWorkerData(client, _contracts())
        result = data.append_event(
            ReflectionEventAppendInputDTO(
                task_id=TASK_ID,
                event_id=event_id,
                sequence=8,
                event_type="reflection.task.started",
                created_at="2026-09-15T00:00:00Z",
                payload={},
            ),
            "request-2",
        )
        self.assertIs(result, output)
        self.assertEqual(len(client.execute_calls), 1)
        self.assertEqual(
            client.receipt_calls,
            [("background", "reflection-event.append", "request-2", TASK_ID)],
        )

    def test_absent_receipt_never_reposts(self):
        client = _FakeClient(
            receipt_result=AbsentReceiptDTO(
                status="absent",
                operation="analysis-report.save",
                request_id="request-3",
            )
        )
        data = AdminReflectionsData(client, _contracts())
        with self.assertRaises(AdminDataError) as caught:
            data.save_report(
                AnalysisReportSaveInputDTO(
                    report_type="echoes", report_data_json='{"echoes":[]}'
                ),
                "request-3",
                access_token="oauth-token",
            )
        self.assertEqual(caught.exception.code, "ADMIN_WRITE_RESULT_UNKNOWN")
        self.assertTrue(caught.exception.outcome_unknown)
        self.assertEqual(len(client.execute_calls), 1)

    def test_event_sequence_uses_postgresql_int4_bounds(self):
        payload = dict(
            task_id=TASK_ID,
            event_type="reflection.task.started",
            created_at="2026-09-15T00:00:00Z",
            payload={},
        )
        ReflectionEventAppendInputDTO(
            **payload,
            sequence=2_147_483_647,
            event_id=reflection_event_id(TASK_ID, 2_147_483_647),
        )
        with self.assertRaises(ValidationError):
            ReflectionEventAppendInputDTO(
                **payload,
                sequence=2_147_483_648,
                event_id=reflection_event_id(TASK_ID, 2_147_483_648),
            )
        with self.assertRaises(ValidationError):
            ReflectionWorkerLoadOutputDTO(
                task=_task(),
                launch_snapshot=_snapshot(),
                last_event_sequence=2_147_483_648,
            )
        restored = ReflectionWorkerLoadOutputDTO(
            task=_task(), launch_snapshot=_snapshot(), last_event_sequence=0
        )
        self.assertEqual(restored.last_event_sequence, 0)

    def test_task_uuid_matches_zod_sentinels_and_rejects_invalid_text(self):
        ReflectionTaskLookupDTO(task_id="00000000-0000-0000-0000-000000000000")
        ReflectionTaskLookupDTO(task_id="ffffffff-ffff-ffff-ffff-ffffffffffff")
        with self.assertRaises(ValidationError):
            ReflectionTaskLookupDTO(task_id="not-a-uuid")

    def test_snapshot_provider_filters_without_using_rta(self):
        provider = ReflectionSnapshotSessionProjectionProvider(_snapshot())
        hidden = provider.list_sessions(
            SessionListInputDTO(
                start_date="2026-09-14",
                end_date="2026-09-14",
                include_text=False,
            ),
            "request-4",
        )
        self.assertEqual([item.id for item in hidden.sessions], ["session-a"])
        self.assertIsNone(hidden.sessions[0].text)
        visible = provider.list_sessions(
            SessionListInputDTO(
                start_date=None, end_date=None, include_text=True
            ),
            "request-5",
        )
        self.assertEqual(visible.sessions[0].text, "private body")

    def test_workspace_locator_requires_exact_configured_task_path(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary).resolve()
            expected = root / TASK_ID / "memory"
            self.assertEqual(
                canonical_reflection_workspace(
                    task_id=TASK_ID,
                    advertised_path=str(expected),
                    workspace_root=str(root),
                ),
                expected,
            )
            with self.assertRaises(AdminDataError):
                canonical_reflection_workspace(
                    task_id=TASK_ID,
                    advertised_path=str(root / "other" / "memory"),
                    workspace_root=str(root),
                )

            outside = root / "outside"
            outside.mkdir()
            task_link = root / TASK_ID
            task_link.symlink_to(outside, target_is_directory=True)
            linked = canonical_reflection_workspace(
                task_id=TASK_ID,
                advertised_path=str(task_link / "memory"),
                workspace_root=str(root),
            )
            with self.assertRaises(AdminDataError) as caught:
                reject_reflection_workspace_symlinks(
                    linked, workspace_root=str(root)
                )
            self.assertEqual(
                caught.exception.code, "REFLECTION_WORKSPACE_SYMLINK_FORBIDDEN"
            )

    def test_workspace_creation_requires_shared_agent_root_and_repairs_mode(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = str(Path(temporary).resolve())
            advertised = str(Path(root) / TASK_ID / "memory")
            with patch.dict(os.environ, {
                "AGENT_CWD": root,
                "DREAM_REFLECTIONS_WORKSPACE_ROOT": root,
            }, clear=False):
                self.assertEqual(reflection_workspace_root(), Path(root))
                memory = prepare_reflection_memory_workspace(
                    identifier=TASK_ID, advertised_path=advertised
                )
            self.assertEqual(memory, Path(advertised))
            self.assertEqual(memory.parent.stat().st_mode & 0o777, 0o700)

    def test_workspace_root_rejects_missing_or_mismatched_configuration(self):
        with tempfile.TemporaryDirectory() as first, tempfile.TemporaryDirectory() as second:
            first = str(Path(first).resolve())
            second = str(Path(second).resolve())
            with patch.dict(os.environ, {}, clear=True):
                with self.assertRaises(AdminDataError):
                    reflection_workspace_root()
            with patch.dict(os.environ, {
                "AGENT_CWD": first,
                "DREAM_REFLECTIONS_WORKSPACE_ROOT": second,
            }, clear=True):
                with self.assertRaises(AdminDataError):
                    reflection_workspace_root()

    def test_workspace_child_writes_reject_existing_symlink(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary).resolve()
            memory = root / TASK_ID / "memory"
            memory.mkdir(parents=True)
            outside = root / "outside"
            outside.mkdir()
            linked = memory / "procedural"
            linked.symlink_to(outside, target_is_directory=True)
            with patch.dict(os.environ, {
                "AGENT_CWD": str(root),
                "DREAM_REFLECTIONS_WORKSPACE_ROOT": str(root),
            }, clear=True):
                with self.assertRaises(AdminDataError) as directory_error:
                    prepare_reflection_workspace_directory(linked)
                self.assertEqual(
                    directory_error.exception.code,
                    "REFLECTION_WORKSPACE_SYMLINK_FORBIDDEN",
                )
                file_link = memory / "WORKFLOW.md"
                file_link.symlink_to(outside / "captured.md")
                with self.assertRaises(AdminDataError) as write_error:
                    write_reflection_workspace_text(file_link, "secret")
                self.assertEqual(
                    write_error.exception.code,
                    "REFLECTION_WORKSPACE_SYMLINK_FORBIDDEN",
                )
                self.assertFalse((outside / "captured.md").exists())


class ReflectionTaskReceiptTransportTest(unittest.TestCase):
    def test_receipt_sends_service_identity_and_exact_task_query(self):
        contracts = _contracts()
        operation = contracts.operation("reflection-event.append")

        def handler(request: httpx.Request) -> httpx.Response:
            self.assertEqual(request.url.path, "/api/internal/dream/v1/receipts/request-6")
            self.assertEqual(
                dict(request.url.params),
                {"operation": "reflection-event.append", "task_id": TASK_ID},
            )
            self.assertNotIn("authorization", request.headers)
            self.assertEqual(request.headers["x-ink-dream-service"], "dream")
            return httpx.Response(
                200,
                json={
                    "request_id": "request-6",
                    "data": {
                        "status": "absent",
                        "operation": "reflection-event.append",
                        "request_id": "request-6",
                    },
                },
            )

        config = AdminDataConfig(
            base_url="https://admin.example",
            issuer="https://admin.example/api/auth",
            resource="dream",
            service_secret="s" * 32,
            service_client_id="dream",
        )
        client = AdminDataClient(
            config,
            client=httpx.Client(transport=httpx.MockTransport(handler)),
            operations=(operation,),
        )
        result = client.reflection_task_receipt(
            operation, "request-6", task_id=TASK_ID
        )
        self.assertIsInstance(result, AbsentReceiptDTO)


if __name__ == "__main__":
    unittest.main()

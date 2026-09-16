# [Input] Admin-authorized Run DTOs, canonical Episode fixtures, and REST requests.
# [Output] Verify Episode index plus explicit Run+Episode artifact isolation and ETags.
# [Pos] Story Workspace Episode read-boundary tests.
# [Sync] 2026-09-16: replace route-side relational fixtures with injected Registry186 authority data.

"""Actor-scoped Episode artifact aggregation and REST boundary tests."""

from __future__ import annotations

import json
import errno
import os
import shutil
import sys
import tempfile
from datetime import datetime, timedelta, timezone
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient


BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from routers import story_workspace
from services.deck.story_workflow_application import DreamArtifactApplicationService
from services.errors.error_registry import ApiRouteError
from services.admin_data.request_auth import AdminRequestActor
from services.admin_data.story_workspace_artifact_data import (
    StoryWorkspaceArtifactAuthorityDTO,
    StoryWorkspaceArtifactIndexObservationDTO,
    StoryWorkspaceArtifactIndexOutputDTO,
    StoryWorkspaceArtifactProjectionDTO,
)
from services.story_workspace.episode_artifact_service import (
    StoryWorkspaceEpisodeArtifactError,
    StoryWorkspaceEpisodeArtifactPathError,
    StoryWorkspaceEpisodeArtifactService,
)
from services.story_workspace.episode_auxiliary_artifact_adapter import (
    StoryWorkspaceEpisodeAuxiliaryArtifactParseError,
)
from services.story_workspace.episode_binding_service import (
    StoryWorkspaceEpisodeBindingContext,
    StoryWorkspaceEpisodeBindingService,
)
from story_workspace.contracts import (
    StoryWorkspaceEpisodeArtifactAvailability,
    StoryWorkspaceEpisodeArtifactSurface,
    StoryWorkspaceEpisodeBindingAvailability,
    StoryWorkspaceEpisodeIndexItem,
    StoryWorkspaceEpisodeIndexSurface,
    StoryWorkspaceStoryIndexProjection,
    StoryWorkspaceStoryIndexReconcileCommand,
)


RUN_ID = "run_0123456789abcdef0123456789abcdef"
OTHER_RUN_ID = "run_fedcba9876543210fedcba9876543210"
ACTOR_ID = "7"
WORKSPACE_ID = "workspace-1"
THREAD_ID = "thread-1"
ARTIFACT_DATA = object()
REQUEST_ACTOR = AdminRequestActor(
    subject="subject-7",
    canonical_user_id=ACTOR_ID,
    client_id="dream-browser",
    scopes=frozenset({"dream:read", "dream:write"}),
    issued_at=1,
    expires_at=2,
    access_token="oauth-access-token",
)
VENDOR_EPISODE = (
    Path(__file__).resolve().parents[2]
    / "vendor"
    / "drama-forge"
    / "drama-forge"
    / "stories"
    / "didi-zhengzhou"
    / "episodes"
    / "EP01"
)


def _binding_context(run_id: str = RUN_ID, story_slug: str = "didi-zhengzhou"):
    return StoryWorkspaceEpisodeBindingContext(
        workflow_run_id=run_id,
        trusted_project_story_slug=story_slug,
        locked_context_story_slug=story_slug,
        run_provenance_story_slug=story_slug,
    )


def _episode_authority(
    episode_uid: str,
    *,
    run_id: str = RUN_ID,
    story_slug: str = "didi-zhengzhou",
) -> dict[str, str]:
    return {
        "schema": "story-workspace-episode-authority/v1",
        "workflow_run_id": run_id,
        "episode_uid": episode_uid,
        "story_slug": story_slug,
        "episode_code": "EP01",
    }


def _unbound_surface() -> StoryWorkspaceEpisodeArtifactSurface:
    return StoryWorkspaceEpisodeArtifactSurface(
        runId=RUN_ID,
        bindingAvailability=StoryWorkspaceEpisodeBindingAvailability.UNBOUND,
    )


class _RecordingGateway:
    def __init__(self, response: StoryWorkspaceEpisodeArtifactSurface) -> None:
        self.response = response
        self.calls: list[tuple[str, dict[str, str], str | None]] = []

    async def get_episode_artifacts(
        self,
        workflow_run_id: str,
        *,
        actor: dict[str, str],
        artifact_data: object,
        access_token: str,
        episode_id: str | None = None,
    ) -> StoryWorkspaceEpisodeArtifactSurface:
        assert artifact_data is ARTIFACT_DATA
        assert access_token == REQUEST_ACTOR.access_token
        self.calls.append((workflow_run_id, actor, episode_id))
        return self.response


def _story_index_projection(
    *,
    status: str = "missing",
    story_id: str | None = None,
) -> StoryWorkspaceStoryIndexProjection:
    revision = "sha256:" + "b" * 64
    return StoryWorkspaceStoryIndexProjection(
        runId=RUN_ID,
        projectId="didi-zhengzhou",
        projectTitle="滴滴郑州",
        storyId=story_id,
        status=status,
        observedManifestRevision=revision,
        observedScriptRevision=revision,
        indexedManifestRevision=revision if status == "indexed" else None,
        indexedScriptRevision=revision if status == "indexed" else None,
        episodeCount=1,
        lastIndexedAt=None,
        errorCode="story_index_row_missing" if status == "missing" else None,
        retryable=status != "indexed",
        etag="sha256:" + "c" * 64,
    )


def test_story_index_contract_rejects_non_v5_story_ids() -> None:
    with pytest.raises(ValueError):
        _story_index_projection(
            story_id="9e8e17bd-d586-4eb1-a0cf-a7a98d44c9b3",
        )


def test_story_index_contract_normalizes_last_indexed_at_to_utc() -> None:
    projection = StoryWorkspaceStoryIndexProjection(
        runId=RUN_ID,
        projectId="didi-zhengzhou",
        projectTitle="滴滴郑州",
        storyId="9e8e17bd-d586-5eb1-a0cf-a7a98d44c9b3",
        status="indexed",
        observedManifestRevision="sha256:" + "b" * 64,
        observedScriptRevision="sha256:" + "c" * 64,
        indexedManifestRevision="sha256:" + "b" * 64,
        indexedScriptRevision="sha256:" + "c" * 64,
        episodeCount=1,
        lastIndexedAt=datetime(
            2026,
            8,
            10,
            9,
            0,
            tzinfo=timezone(timedelta(hours=8)),
        ),
        errorCode=None,
        retryable=False,
        etag="sha256:" + "d" * 64,
    )

    assert projection.last_indexed_at is not None
    assert projection.last_indexed_at.utcoffset() == timedelta(0)
    assert projection.model_dump(mode="json", by_alias=True)["lastIndexedAt"] in {
        "2026-08-10T01:00:00Z",
        "2026-08-10T01:00:00+00:00",
    }


class _StoryIndexGateway:
    def __init__(self, response: StoryWorkspaceStoryIndexProjection) -> None:
        self.response = response
        self.get_calls: list[tuple[str, dict[str, str]]] = []
        self.post_calls: list[tuple[str, object, dict[str, str], str]] = []

    async def get_story_index(self, workflow_run_id: str, *, actor: dict[str, str],
                              artifact_data: object, access_token: str):
        assert artifact_data is ARTIFACT_DATA
        assert access_token == REQUEST_ACTOR.access_token
        self.get_calls.append((workflow_run_id, actor))
        return self.response

    async def reconcile_story_index(
        self,
        workflow_run_id: str,
        request: object,
        *,
        actor: dict[str, str],
        artifact_data: object,
        access_token: str,
        if_match: str,
    ):
        assert artifact_data is ARTIFACT_DATA
        assert access_token == REQUEST_ACTOR.access_token
        self.post_calls.append((workflow_run_id, request, actor, if_match))
        return self.response


def _story_index_client(gateway: object) -> TestClient:
    app = FastAPI()
    app.dependency_overrides[story_workspace.get_current_user] = lambda: {
        "user_id": int(ACTOR_ID),
        "_admin_actor": REQUEST_ACTOR,
    }
    app.dependency_overrides[story_workspace._artifact_data] = lambda: ARTIFACT_DATA
    app.dependency_overrides[story_workspace.get_dream_artifact_service] = (
        lambda: gateway
    )
    app.include_router(story_workspace.router)
    return TestClient(app)


def test_story_index_route_has_an_independent_exact_etag_contract() -> None:
    gateway = _StoryIndexGateway(_story_index_projection())
    quoted = '"sha256:' + "c" * 64 + '"'
    with _story_index_client(gateway) as client:
        first = client.get(
            f"/api/story-workspace/workflow-runs/{RUN_ID}/story-index"
        )
        cached = client.get(
            f"/api/story-workspace/workflow-runs/{RUN_ID}/story-index",
            headers={"If-None-Match": quoted},
        )
    assert first.status_code == 200
    assert first.headers["etag"] == quoted
    assert first.json()["status"] == "missing"
    assert "sourceThreadRef" not in first.text
    assert cached.status_code == 304
    assert gateway.get_calls == [
        (RUN_ID, {"actor_id": ACTOR_ID}),
        (RUN_ID, {"actor_id": ACTOR_ID}),
    ]


def test_story_index_reconcile_accepts_only_optional_idempotency_and_if_match() -> None:
    gateway = _StoryIndexGateway(
        _story_index_projection(
            status="indexed",
            story_id="9e8e17bd-d586-5eb1-a0cf-a7a98d44c9b3",
        )
    )
    quoted = '"sha256:' + "c" * 64 + '"'
    with _story_index_client(gateway) as client:
        response = client.post(
            f"/api/story-workspace/workflow-runs/{RUN_ID}/story-index/reconcile",
            headers={"If-Match": quoted},
            json={"idempotencyKey": "retry-1"},
        )
        rejected = client.post(
            f"/api/story-workspace/workflow-runs/{RUN_ID}/story-index/reconcile",
            headers={"If-Match": quoted},
            json={"projectId": "didi-zhengzhou"},
        )
    assert response.status_code == 200
    assert response.headers["etag"] == quoted
    assert len(gateway.post_calls) == 1
    call = gateway.post_calls[0]
    assert call[0] == RUN_ID
    assert call[2] == {"actor_id": ACTOR_ID}
    assert call[3] == quoted
    assert rejected.status_code == 422


@pytest.mark.parametrize(
    "if_match",
    [
        "sha256:" + "c" * 64,
        'W/"sha256:' + "c" * 64 + '"',
        '"sha256:' + "C" * 64 + '"',
        '"sha256:' + "c" * 63 + '"',
        '"sha256:' + "c" * 64 + '", "sha256:' + "d" * 64 + '"',
        "*",
    ],
)
def test_story_index_reconcile_rejects_every_non_exact_if_match(
    if_match: str,
) -> None:
    gateway = _StoryIndexGateway(_story_index_projection())
    with _story_index_client(gateway) as client:
        response = client.post(
            f"/api/story-workspace/workflow-runs/{RUN_ID}/story-index/reconcile",
            headers={"If-Match": if_match},
            json={},
        )
    assert response.status_code == 422
    assert gateway.post_calls == []


def test_story_index_reconcile_requires_if_match() -> None:
    gateway = _StoryIndexGateway(_story_index_projection())
    with _story_index_client(gateway) as client:
        response = client.post(
            f"/api/story-workspace/workflow-runs/{RUN_ID}/story-index/reconcile",
            json={},
        )
    assert response.status_code == 422
    assert gateway.post_calls == []


@pytest.mark.parametrize(
    ("code", "status"),
    [
        ("artifact_missing", 404),
        ("story_index_revision_conflict", 409),
        ("story_index_invalid_artifact", 422),
        ("story_index_database_unavailable", 503),
    ],
)
def test_story_index_route_serializes_only_fixed_safe_errors(
    code: str,
    status: int,
) -> None:
    class FailingGateway(_StoryIndexGateway):
        async def get_story_index(
            self,
            workflow_run_id: str,
            *,
            actor: dict[str, str],
            **_kwargs,
        ):
            raise ApiRouteError(code, status_code=status)

    with _story_index_client(FailingGateway(_story_index_projection())) as client:
        response = client.get(
            f"/api/story-workspace/workflow-runs/{RUN_ID}/story-index"
        )
    assert response.status_code == status
    assert response.json()["error"]["code"] == code
    assert set(response.json()["error"]) == {
        "code",
        "phase",
        "message",
        "recovery_action",
    }


def test_story_index_route_collapses_unexpected_details_to_safe_503() -> None:
    class FailingGateway(_StoryIndexGateway):
        async def get_story_index(
            self,
            workflow_run_id: str,
            *,
            actor: dict[str, str],
            **_kwargs,
        ):
            raise RuntimeError("/Users/private/secret-story-index")

    with _story_index_client(FailingGateway(_story_index_projection())) as client:
        response = client.get(
            f"/api/story-workspace/workflow-runs/{RUN_ID}/story-index"
        )
    assert response.status_code == 503
    assert response.json()["error"]["code"] == "story_index_database_unavailable"
    assert "private" not in response.text
    assert "secret" not in response.text


def test_story_index_route_never_forwards_unknown_api_error_or_500_status() -> None:
    class FailingGateway(_StoryIndexGateway):
        async def get_story_index(
            self,
            workflow_run_id: str,
            *,
            actor: dict[str, str],
            **_kwargs,
        ):
            raise ApiRouteError("/Users/private/secret-story-index", status_code=500)

    with _story_index_client(FailingGateway(_story_index_projection())) as client:
        response = client.get(
            f"/api/story-workspace/workflow-runs/{RUN_ID}/story-index"
        )
    assert response.status_code == 503
    assert response.json()["error"]["code"] == "story_index_database_unavailable"
    assert "private" not in response.text
    assert "secret" not in response.text


def test_route_passes_run_actor_and_optional_episode_identity() -> None:
    surface = _unbound_surface()
    app = FastAPI()
    gateway = _RecordingGateway(surface)
    app.dependency_overrides[story_workspace.get_current_user] = lambda: {
        "user_id": int(ACTOR_ID),
        "_admin_actor": REQUEST_ACTOR,
    }
    app.dependency_overrides[story_workspace._artifact_data] = lambda: ARTIFACT_DATA
    app.dependency_overrides[story_workspace.get_dream_artifact_service] = (
        lambda: gateway
    )
    app.include_router(story_workspace.router)

    with TestClient(app) as client:
        response = client.get(
            f"/api/story-workspace/workflow-runs/{RUN_ID}/episode-artifacts",
            params={"episode": "a" * 32},
        )

    assert response.status_code == 200
    assert response.json()["bindingAvailability"] == "unbound"
    assert gateway.calls == [(RUN_ID, {"actor_id": ACTOR_ID}, "a" * 32)]


def test_route_returns_304_only_for_the_exact_quoted_manifest_etag() -> None:
    manifest_revision = "sha256:" + "a" * 64
    class EtagGateway(_RecordingGateway):
        async def get_episode_artifacts(
            self,
            workflow_run_id: str,
            *,
            actor: dict[str, str],
            artifact_data: object,
            access_token: str,
            episode_id: str | None = None,
        ):
            assert artifact_data is ARTIFACT_DATA
            assert access_token == REQUEST_ACTOR.access_token
            self.calls.append((workflow_run_id, actor, episode_id))
            return type("Surface", (), {
                "model_dump": lambda self, **_: {
                    "runId": workflow_run_id,
                    "etag": manifest_revision,
                }
            })()

    app = FastAPI()
    gateway = EtagGateway(_unbound_surface())
    app.dependency_overrides[story_workspace.get_current_user] = lambda: {
        "user_id": int(ACTOR_ID),
        "_admin_actor": REQUEST_ACTOR,
    }
    app.dependency_overrides[story_workspace._artifact_data] = lambda: ARTIFACT_DATA
    app.dependency_overrides[story_workspace.get_dream_artifact_service] = lambda: gateway
    app.include_router(story_workspace.router)
    with TestClient(app) as client:
        response = client.get(
            f"/api/story-workspace/workflow-runs/{RUN_ID}/episode-artifacts",
            headers={"If-None-Match": f'"{manifest_revision}"'},
        )
        unquoted = client.get(
            f"/api/story-workspace/workflow-runs/{RUN_ID}/episode-artifacts",
            headers={"If-None-Match": manifest_revision},
        )

    assert response.status_code == 304
    assert response.headers["etag"] == f'"{manifest_revision}"'
    assert response.content == b""
    assert unquoted.status_code == 200


def test_episode_index_route_returns_stable_ids_and_honors_etag() -> None:
    etag = "sha256:" + "d" * 64
    active_id = "a" * 32
    index = StoryWorkspaceEpisodeIndexSurface(
        runId=RUN_ID,
        registryRevision=2,
        activeEpisodeId=active_id,
        etag=etag,
        episodes=[
            StoryWorkspaceEpisodeIndexItem(
                opaqueEpisodeId=active_id,
                episodeCode="EP01",
                active=True,
                availableArtifactCount=1,
                hasArtifactIssues=False,
            ),
            StoryWorkspaceEpisodeIndexItem(
                opaqueEpisodeId="b" * 32,
                episodeCode="EP02",
                active=False,
                availableArtifactCount=0,
                hasArtifactIssues=False,
            ),
        ],
    )

    class IndexGateway(_RecordingGateway):
        async def get_episode_index(
            self,
            workflow_run_id: str,
            *,
            actor: dict[str, str],
            artifact_data: object,
            access_token: str,
        ) -> StoryWorkspaceEpisodeIndexSurface:
            assert workflow_run_id == RUN_ID
            assert actor == {"actor_id": ACTOR_ID}
            assert artifact_data is ARTIFACT_DATA
            assert access_token == REQUEST_ACTOR.access_token
            return index

    app = FastAPI()
    gateway = IndexGateway(_unbound_surface())
    app.dependency_overrides[story_workspace.get_current_user] = lambda: {
        "user_id": int(ACTOR_ID),
        "_admin_actor": REQUEST_ACTOR,
    }
    app.dependency_overrides[story_workspace._artifact_data] = lambda: ARTIFACT_DATA
    app.dependency_overrides[story_workspace.get_dream_artifact_service] = lambda: gateway
    app.include_router(story_workspace.router)
    with TestClient(app) as client:
        response = client.get(
            f"/api/story-workspace/workflow-runs/{RUN_ID}/episodes"
        )
        not_modified = client.get(
            f"/api/story-workspace/workflow-runs/{RUN_ID}/episodes",
            headers={"If-None-Match": f'"{etag}"'},
        )

    assert response.status_code == 200
    assert response.headers["etag"] == f'"{etag}"'
    assert [item["episodeCode"] for item in response.json()["episodes"]] == [
        "EP01",
        "EP02",
    ]
    assert response.json()["episodes"][0]["opaqueEpisodeId"] != response.json()[
        "episodes"
    ][1]["opaqueEpisodeId"]
    assert not_modified.status_code == 304


class TestStoryWorkspaceEpisodeArtifactService:
    def setup_method(self) -> None:
        self.temporary_directory = tempfile.TemporaryDirectory()
        self.workspace = Path(self.temporary_directory.name)
        (self.workspace / ".dream").mkdir()
        self.story = self.workspace / "stories" / "didi-zhengzhou"
        self.episode = self.story / "episodes" / "EP01"
        self.episode.mkdir(parents=True)
        (self.story / "project.yaml").write_text(
            "project_id: didi-zhengzhou\nproject_name: Demo\n",
            encoding="utf-8",
        )
        self.binding = StoryWorkspaceEpisodeBindingService(
            self.workspace
        ).bind_first_episode(_binding_context())
        self.authority = _episode_authority(self.binding.episode_uid)
        self.service = StoryWorkspaceEpisodeArtifactService(self.workspace)

    def teardown_method(self) -> None:
        self.temporary_directory.cleanup()

    def read_surface(self):
        return self.service.read_surface(
            RUN_ID,
            episode_authority=self.authority,
        )

    def test_missing_artifacts_are_six_recoverable_not_generated_facts(self) -> None:
        surface = self.read_surface()

        assert surface.binding_availability is StoryWorkspaceEpisodeBindingAvailability.BOUND
        assert surface.opaque_episode_id == self.binding.episode_uid
        assert len(surface.artifacts) == 6
        assert {
            item.relative_key: item.availability for item in surface.artifacts
        } == {
            "episode-outline.md": StoryWorkspaceEpisodeArtifactAvailability.NOT_GENERATED,
            "script.md": StoryWorkspaceEpisodeArtifactAvailability.NOT_GENERATED,
            "storyboard.yaml": StoryWorkspaceEpisodeArtifactAvailability.NOT_GENERATED,
            "prompts/": StoryWorkspaceEpisodeArtifactAvailability.NOT_GENERATED,
            "renders/": StoryWorkspaceEpisodeArtifactAvailability.NOT_GENERATED,
            "review-report.md": StoryWorkspaceEpisodeArtifactAvailability.NOT_GENERATED,
        }
        assert surface.narrative is not None
        assert surface.narrative.narrative_beats == []
        assert surface.narrative.scenes == []
        assert surface.narrative.shots == []
        assert surface.auxiliary is not None
        assert surface.auxiliary.prompts.total == 0
        assert "stories/didi-zhengzhou" not in surface.model_dump_json()
        assert str(self.workspace) not in surface.model_dump_json()

    def test_bound_surface_accepts_the_same_legacy_project_mapping_identity(
        self,
    ) -> None:
        (self.story / "project.yaml").write_text(
            "project:\n"
            "  project_id: didi-zhengzhou\n"
            "  project_name: Legacy Dream project\n",
            encoding="utf-8",
        )

        surface = self.read_surface()

        assert surface.binding_availability is StoryWorkspaceEpisodeBindingAvailability.BOUND
        assert surface.opaque_episode_id == self.binding.episode_uid

    def test_real_didi_episode_projects_45_prompts_45_queue_and_no_orphans(self) -> None:
        if not VENDOR_EPISODE.is_dir():
            pytest.skip("optional drama-forge vendor fixture is not present")
        for name in (
            "episode-outline.md",
            "script.md",
            "storyboard.yaml",
            "review-report.md",
        ):
            shutil.copy2(VENDOR_EPISODE / name, self.episode / name)
        shutil.copytree(VENDOR_EPISODE / "prompts", self.episode / "prompts")
        shutil.copytree(VENDOR_EPISODE / "renders", self.episode / "renders")

        surface = self.read_surface()

        assert surface.narrative is not None
        assert len(surface.narrative.shots) == 45
        assert surface.auxiliary is not None
        assert surface.auxiliary.prompts.total == 45
        assert surface.auxiliary.render_guide is not None
        assert surface.auxiliary.render_guide.queue.total == 45
        assert surface.auxiliary.associations.orphan_prompts == []
        assert surface.auxiliary.associations.orphan_queue_entries == []
        assert all(
            item.availability is StoryWorkspaceEpisodeArtifactAvailability.AVAILABLE
            for item in surface.artifacts
        )

    def test_three_platform_prompt_package_is_available_and_linked(self) -> None:
        (self.episode / "storyboard.yaml").write_text(
            "shots:\n"
            "  - shot_id: S01-E01-001\n"
            "    visual: Safe establishing shot.\n",
            encoding="utf-8",
        )
        prompts = self.episode / "prompts"
        prompts.mkdir()
        (prompts / "prompt_package.yaml").write_text(
            "shots:\n"
            "  - shot_id: S01-E01-001\n"
            "    kling: Safe Kling prompt\n"
            "    runway: Safe Runway prompt\n"
            "    jimeng: Safe Jimeng prompt\n",
            encoding="utf-8",
        )

        surface = self.read_surface()

        prompt_artifact = next(
            item for item in surface.artifacts if item.relative_key == "prompts/"
        )
        assert prompt_artifact.availability is (
            StoryWorkspaceEpisodeArtifactAvailability.AVAILABLE
        )
        assert surface.auxiliary is not None
        assert surface.auxiliary.prompts.total == 3
        assert surface.auxiliary.associations.shot_prompt_coverage.linked == 1
        assert surface.auxiliary.associations.shot_prompt_coverage.total == 1

    def test_available_markdown_artifacts_project_safe_body_documents(self) -> None:
        (self.episode / "episode-outline.md").write_text(
            "---\ntitle: Afternoon Light\nproject: didi-zhengzhou\n---\n"
            "# Episode Outline\n\n## Story Goals\n- Keep the shop open.\n",
            encoding="utf-8",
        )
        (self.episode / "script.md").write_text(
            "---\ntitle: Afternoon Light\nepisode: 1\n---\n"
            "# Script\n\nS01. Shop [scene-shop] - Day - Interior\n\n"
            "[The owner opens the blinds.]\n",
            encoding="utf-8",
        )
        (self.episode / "review-report.md").write_text(
            "---\nscope: script\noverall_verdict: APPROVED\n"
            "reviewed_files:\n  - script.md\n---\n"
            "# Review Report\n\n## Verdict\n\n| Item | Result |\n"
            "| --- | --- |\n| Structure | Pass |\n",
            encoding="utf-8",
        )

        surface = self.read_surface()

        documents = {item.relative_key: item for item in surface.documents}
        assert set(documents) == {
            "episode-outline.md",
            "script.md",
            "review-report.md",
        }
        assert documents["episode-outline.md"].markdown.startswith("# Episode Outline")
        assert documents["script.md"].markdown.startswith("# Script")
        assert "| Structure | Pass |" in documents["review-report.md"].markdown
        assert "project: didi-zhengzhou" not in surface.model_dump_json()
        assert str(self.workspace) not in surface.model_dump_json()

    def test_review_creative_slash_labels_are_not_misread_as_absolute_paths(self) -> None:
        (self.episode / "review-report.md").write_text(
            "---\nscope: script\noverall_verdict: APPROVED\n"
            "reviewed_files:\n  - script.md\n---\n"
            "# Review\n\n## Format\n\n"
            "| Result | Evidence |\n| --- | --- |\n"
            "| PASS | Scene/CAM/TRANS/@HOOK are valid. |\n",
            encoding="utf-8",
        )

        surface = self.read_surface()

        review_fact = next(
            item for item in surface.artifacts
            if item.relative_key == "review-report.md"
        )
        assert review_fact.availability is StoryWorkspaceEpisodeArtifactAvailability.AVAILABLE
        assert surface.auxiliary is not None
        assert surface.auxiliary.review is not None
        document = next(
            item for item in surface.documents
            if item.relative_key == "review-report.md"
        )
        assert "Scene/CAM/TRANS/@HOOK" in document.markdown

    @pytest.mark.parametrize(
        "leaked_path",
        [
            "/Users/private/story.md",
            "path: /etc/passwd",
            "路径：/home/private/story.md",
        ],
    )
    def test_review_document_still_rejects_actual_absolute_paths(
        self,
        leaked_path: str,
    ) -> None:
        (self.episode / "review-report.md").write_text(
            f"# Review\n\n## Finding\n{leaked_path}\n",
            encoding="utf-8",
        )

        surface = self.read_surface()

        review_fact = next(
            item for item in surface.artifacts
            if item.relative_key == "review-report.md"
        )
        assert review_fact.availability is StoryWorkspaceEpisodeArtifactAvailability.INVALID
        assert surface.documents == []
        assert leaked_path not in surface.model_dump_json()

    def test_manifest_revision_and_etag_change_with_content_fact(self) -> None:
        first = self.read_surface()
        (self.episode / "episode-outline.md").write_text(
            "---\ntitle: Demo\n---\n# Story Goals\n- Begin\n",
            encoding="utf-8",
        )
        second = self.read_surface()

        assert first.manifest_revision != second.manifest_revision
        assert second.etag == second.manifest_revision

    @pytest.mark.parametrize(
        "relative_target",
        [
            "episode-outline.md",
            "prompts",
            "renders",
        ],
    )
    def test_symlink_at_any_artifact_layer_is_rejected(
        self,
        relative_target: str,
    ) -> None:
        outside = self.workspace / "outside"
        outside.write_text("private", encoding="utf-8")
        target = self.episode / relative_target
        target.symlink_to(outside)

        with pytest.raises(StoryWorkspaceEpisodeArtifactPathError):
            self.read_surface()

    def test_invalid_artifact_is_200_surface_fact_without_untrusted_text(self) -> None:
        (self.episode / "storyboard.yaml").write_bytes(b"shots: [\xff]\n")

        surface = self.read_surface()

        storyboard = next(
            item for item in surface.artifacts if item.relative_key == "storyboard.yaml"
        )
        assert storyboard.availability is StoryWorkspaceEpisodeArtifactAvailability.INVALID
        assert "\\xff" not in surface.model_dump_json()

    def test_review_case_variant_links_to_storyboard_canonical_view_id(self) -> None:
        (self.episode / "storyboard.yaml").write_text(
            "shots:\n  - shot_id: S04-E01-020a\n    visual: Canonical shot.\n",
            encoding="utf-8",
        )
        (self.episode / "review-report.md").write_text(
            "# Review\n\n## Shot finding\nS04-E01-020A needs work.\n",
            encoding="utf-8",
        )

        surface = self.read_surface()

        assert surface.narrative is not None
        assert surface.auxiliary is not None
        assert surface.auxiliary.review is not None
        shot = surface.narrative.shots[0]
        target = surface.auxiliary.review.targets[0]
        assert target.source_key == shot.shot_id
        assert target.target_view_id == shot.id
        assert target.association_status.value == "linked"

    def test_duplicate_case_variant_review_target_isolated_from_narrative(self) -> None:
        (self.episode / "storyboard.yaml").write_text(
            "shots:\n  - shot_id: S04-E01-020a\n    visual: Canonical shot.\n",
            encoding="utf-8",
        )
        (self.episode / "review-report.md").write_text(
            (
                "# Review\n\n## First\nS04-E01-020a needs work.\n\n"
                "## Second\nS04-E01-020A repeats the target.\n"
            ),
            encoding="utf-8",
        )

        surface = self.read_surface()

        availability = {item.relative_key: item.availability for item in surface.artifacts}
        assert availability["storyboard.yaml"] is StoryWorkspaceEpisodeArtifactAvailability.AVAILABLE
        assert availability["review-report.md"] is StoryWorkspaceEpisodeArtifactAvailability.INVALID
        assert surface.narrative is not None
        assert len(surface.narrative.shots) == 1
        assert surface.auxiliary is not None
        assert surface.auxiliary.review is None

    def test_verified_file_read_eio_is_local_unavailable(self) -> None:
        storyboard_path = self.episode / "storyboard.yaml"
        storyboard_path.write_text(
            "shots:\n  - shot_id: S04-E01-020a\n    visual: Canonical shot.\n",
            encoding="utf-8",
        )
        real_read = os.read
        storyboard_identity = (storyboard_path.stat().st_dev, storyboard_path.stat().st_ino)

        def fail_storyboard_read(descriptor: int, size: int) -> bytes:
            try:
                metadata = os.fstat(descriptor)
                descriptor_identity = (metadata.st_dev, metadata.st_ino)
            except OSError:
                descriptor_identity = None
            if descriptor_identity == storyboard_identity:
                raise OSError(errno.EIO, "simulated transient read failure")
            return real_read(descriptor, size)

        with patch("services.story_workspace.episode_artifact_service.os.read", fail_storyboard_read):
            surface = self.read_surface()

        availability = {item.relative_key: item.availability for item in surface.artifacts}
        assert availability["storyboard.yaml"] is StoryWorkspaceEpisodeArtifactAvailability.UNAVAILABLE
        assert availability["episode-outline.md"] is StoryWorkspaceEpisodeArtifactAvailability.NOT_GENERATED
        assert surface.narrative is not None
        assert surface.narrative.shots == []

    def test_verified_directory_list_eio_is_local_unavailable(self) -> None:
        prompts_path = self.episode / "prompts"
        prompts_path.mkdir()
        (prompts_path / "shot.yaml").write_text("shots: []\n", encoding="utf-8")
        prompt_identity = (prompts_path.stat().st_dev, prompts_path.stat().st_ino)
        real_listdir = os.listdir

        def fail_prompt_list(directory: int | str | os.PathLike[str]):
            if isinstance(directory, int):
                metadata = os.fstat(directory)
                if (metadata.st_dev, metadata.st_ino) == prompt_identity:
                    raise OSError(errno.EIO, "simulated transient list failure")
            return real_listdir(directory)

        with patch(
            "services.story_workspace.episode_artifact_service.os.listdir",
            fail_prompt_list,
        ):
            surface = self.read_surface()

        availability = {item.relative_key: item.availability for item in surface.artifacts}
        assert availability["prompts/"] is StoryWorkspaceEpisodeArtifactAvailability.UNAVAILABLE
        assert surface.auxiliary is not None
        assert surface.auxiliary.prompts.items == []

    def test_backend_same_entry_closure_rejects_crosswire_to_real_shot(self) -> None:
        (self.episode / "storyboard.yaml").write_text(
            (
                "shots:\n"
                "  - shot_id: S04-E01-020a\n    visual: First shot.\n"
                "  - shot_id: S04-E01-020b\n    visual: Second shot.\n"
            ),
            encoding="utf-8",
        )
        (self.episode / "review-report.md").write_text(
            "# Review\n\n## Shot finding\nS04-E01-020a needs work.\n",
            encoding="utf-8",
        )
        surface = self.read_surface()
        assert surface.narrative is not None
        assert surface.auxiliary is not None
        assert surface.auxiliary.review is not None
        target = surface.auxiliary.review.targets[0]
        wrong_target = target.model_copy(
            update={"target_view_id": surface.narrative.shots[1].id}
        )
        review = surface.auxiliary.review.model_copy(
            update={"targets": [wrong_target]}
        )
        auxiliary = surface.auxiliary.model_copy(update={"review": review})

        with pytest.raises(
            StoryWorkspaceEpisodeAuxiliaryArtifactParseError,
            match="canonical_link_mismatch",
        ):
            self.service._assert_auxiliary_same_entry(
                auxiliary,
                surface.narrative,
                root="review",
            )

    def test_binding_story_or_canonical_project_identity_cannot_be_swapped(self) -> None:
        (self.story / "project.yaml").write_text(
            "project_id: other\n",
            encoding="utf-8",
        )

        with pytest.raises(StoryWorkspaceEpisodeArtifactPathError):
            self.read_surface()

    @pytest.mark.parametrize(
        "binding_updates",
        [
            {"workflow_run_id": OTHER_RUN_ID},
            {"story_slug": "other", "episode_root": "stories/other/episodes/EP01"},
            {"episode_root": "stories/didi-zhengzhou/episodes/../other"},
        ],
    )
    def test_persisted_binding_cannot_change_run_story_or_root(
        self,
        binding_updates: dict[str, str],
    ) -> None:
        binding_path = (
            self.workspace / ".dream" / "runtime" / "runs" / RUN_ID / "episode.json"
        )
        payload = json.loads(binding_path.read_text(encoding="utf-8"))
        payload.update(binding_updates)
        binding_path.write_text(json.dumps(payload), encoding="utf-8")

        surface = self.read_surface()
        assert surface.binding_availability is StoryWorkspaceEpisodeBindingAvailability.UNBOUND
        assert surface.artifacts == []

    @pytest.mark.parametrize(
        ("component", "replacement_kind"),
        [
            ("stories", "dir"),
            ("stories/didi-zhengzhou", "dir"),
            ("stories/didi-zhengzhou/episodes", "dir"),
            ("stories/didi-zhengzhou/episodes/EP01", "dir"),
            (".dream/runtime/runs/" + RUN_ID + "/episode.json", "file"),
        ],
    )
    def test_symlink_in_binding_or_episode_ancestor_is_rejected(
        self,
        component: str,
        replacement_kind: str,
    ) -> None:
        target = self.workspace / component
        outside = self.workspace / ("outside-" + replacement_kind)
        if replacement_kind == "dir":
            outside.mkdir()
            shutil.rmtree(target)
        else:
            outside.write_text("private", encoding="utf-8")
            target.unlink()
        target.symlink_to(outside)

        with pytest.raises(StoryWorkspaceEpisodeArtifactPathError):
            self.read_surface()

    def test_symlink_inside_approved_directory_is_rejected(self) -> None:
        prompts = self.episode / "prompts"
        prompts.mkdir()
        outside = self.workspace / "outside.yaml"
        outside.write_text("shots: []\n", encoding="utf-8")
        (prompts / "episode.yaml").symlink_to(outside)

        with pytest.raises(StoryWorkspaceEpisodeArtifactPathError):
            self.read_surface()

    def test_unbound_does_not_probe_episode_tree(self) -> None:
        service = StoryWorkspaceEpisodeArtifactService(self.workspace)

        with patch.object(
            service,
            "_read_bound_episode",
            side_effect=AssertionError("artifact probe before binding"),
        ) as probe:
            surface = service.read_surface(
                OTHER_RUN_ID,
                episode_authority=_episode_authority(
                    "f" * 32,
                    run_id=OTHER_RUN_ID,
                ),
            )

        assert surface.binding_availability is StoryWorkspaceEpisodeBindingAvailability.UNBOUND
        assert surface.artifacts == []
        assert surface.opaque_episode_id is None
        probe.assert_not_called()

    @pytest.mark.parametrize(
        "authority",
        [
            None,
            {},
            {"schema": "wrong"},
            _episode_authority("e" * 32),
            _episode_authority("a" * 32, run_id=OTHER_RUN_ID),
            _episode_authority("a" * 32, story_slug="other"),
        ],
    )
    def test_missing_invalid_or_mismatched_authority_is_unbound_without_probe(
        self,
        authority: dict[str, str] | None,
    ) -> None:
        with patch.object(
            self.service,
            "_read_bound_episode",
            side_effect=AssertionError("Episode probe without matched authority"),
        ) as probe:
            surface = self.service.read_surface(
                RUN_ID,
                episode_authority=authority,
            )

        assert surface.binding_availability is StoryWorkspaceEpisodeBindingAvailability.UNBOUND
        assert surface.artifacts == []
        probe.assert_not_called()

    def test_self_consistent_binding_and_project_swap_cannot_override_authority(self) -> None:
        binding_path = (
            self.workspace / ".dream" / "runtime" / "runs" / RUN_ID / "episode.json"
        )
        payload = json.loads(binding_path.read_text(encoding="utf-8"))
        payload.update(
            {
                "episode_uid": "e" * 32,
                "story_slug": "other",
                "episode_root": "stories/other/episodes/EP01",
            }
        )
        binding_path.write_text(json.dumps(payload), encoding="utf-8")
        swapped_episode = self.workspace / "stories" / "other" / "episodes" / "EP01"
        swapped_episode.mkdir(parents=True)
        (swapped_episode.parent.parent / "project.yaml").write_text(
            "project_id: other\n",
            encoding="utf-8",
        )
        (swapped_episode / "episode-outline.md").write_text(
            "# Story Goals\n- SWAPPED SOURCE\n",
            encoding="utf-8",
        )

        with patch.object(
            self.service,
            "_read_bound_episode",
            side_effect=AssertionError("swapped Episode must not be probed"),
        ) as probe:
            surface = self.service.read_surface(
                RUN_ID,
                episode_authority=self.authority,
            )

        assert surface.binding_availability is StoryWorkspaceEpisodeBindingAvailability.UNBOUND
        assert "SWAPPED SOURCE" not in surface.model_dump_json()
        probe.assert_not_called()

    def test_oversize_root_is_invalid_while_other_artifacts_remain_available(self) -> None:
        (self.episode / "episode-outline.md").write_bytes(b"x" * (1024 * 1024 + 1))
        (self.episode / "script.md").write_text(
            "---\ntitle: Demo\n---\n# Script\n",
            encoding="utf-8",
        )

        first = self.read_surface()
        (self.episode / "episode-outline.md").write_bytes(b"y" * (1024 * 1024 + 2))
        second = self.read_surface()

        availability = {item.relative_key: item.availability for item in second.artifacts}
        assert availability["episode-outline.md"] is StoryWorkspaceEpisodeArtifactAvailability.INVALID
        assert availability["script.md"] is StoryWorkspaceEpisodeArtifactAvailability.AVAILABLE
        assert first.manifest_revision != second.manifest_revision

    def test_oversize_root_revision_changes_after_same_size_preserved_mtime_rewrite(
        self,
    ) -> None:
        outline = self.episode / "episode-outline.md"
        outline.write_bytes(b"x" * (1024 * 1024 + 1))
        original = outline.stat()
        first = self.read_surface()

        outline.write_bytes(b"y" * original.st_size)
        os.utime(outline, ns=(original.st_atime_ns, original.st_mtime_ns))
        second = self.read_surface()

        outline_fact = next(
            item
            for item in second.artifacts
            if item.relative_key == "episode-outline.md"
        )
        assert (
            outline_fact.availability
            is StoryWorkspaceEpisodeArtifactAvailability.INVALID
        )
        assert first.manifest_revision != second.manifest_revision

    def test_unapproved_directory_entry_revision_changes_after_same_size_preserved_mtime_rewrite(
        self,
    ) -> None:
        renders = self.episode / "renders"
        renders.mkdir()
        unapproved = renders / "private.bin"
        unapproved.write_bytes(b"AAAA")
        original = unapproved.stat()
        first = self.read_surface()

        unapproved.write_bytes(b"BBBB")
        os.utime(unapproved, ns=(original.st_atime_ns, original.st_mtime_ns))
        second = self.read_surface()

        renders_fact = next(
            item for item in second.artifacts if item.relative_key == "renders/"
        )
        assert (
            renders_fact.availability
            is StoryWorkspaceEpisodeArtifactAvailability.INVALID
        )
        assert first.manifest_revision != second.manifest_revision

    def test_prompt_count_and_unapproved_render_entry_are_isolated_invalid_roots(self) -> None:
        prompts = self.episode / "prompts"
        prompts.mkdir()
        for index in range(129):
            (prompts / f"p-{index:03d}.yaml").write_text(
                "shots: []\n",
                encoding="utf-8",
            )
        renders = self.episode / "renders"
        renders.mkdir()
        (renders / "private.bin").write_bytes(b"not approved")

        surface = self.read_surface()

        availability = {item.relative_key: item.availability for item in surface.artifacts}
        assert availability["prompts/"] is StoryWorkspaceEpisodeArtifactAvailability.INVALID
        assert availability["renders/"] is StoryWorkspaceEpisodeArtifactAvailability.INVALID
        assert surface.auxiliary is not None
        assert surface.auxiliary.prompts.total == 0
        assert surface.auxiliary.render_guide is None

    @pytest.mark.parametrize(
        "secret",
        [
            "/Users/private/story.txt",
            r"C:\\Users\\private\\story.txt",
            "api_key=sk-proj-abcdefghijklmnopqrstuv",
            "Bearer abcdefghijklmnop",
            "hidden reasoning: private chain",
            "/drama-forge:drama-init --token secret",
            "token: abcdefghijklmnopqrstuvwxyz123456",
        ],
    )
    def test_narrative_sensitive_text_never_crosses_u2_u4_surface(
        self,
        secret: str,
    ) -> None:
        (self.episode / "episode-outline.md").write_text(
            f"# Story Goals\n- {secret}\n",
            encoding="utf-8",
        )

        surface = self.read_surface()
        payload = surface.model_dump_json()

        assert secret not in payload
        outline = next(
            item for item in surface.artifacts if item.relative_key == "episode-outline.md"
        )
        assert outline.availability is StoryWorkspaceEpisodeArtifactAvailability.INVALID



class _ArtifactDataFake:
    def __init__(self, authority, observation=None):
        self.authority_value = authority
        self.observation = observation
        self.authority_calls = []
        self.inspect_calls = []
        self.reconcile_calls = []

    def authority(self, input_dto, request_id, *, access_token):
        self.authority_calls.append((input_dto, request_id, access_token))
        return SimpleNamespace(authority=self.authority_value)

    def inspect_index(self, input_dto, request_id, *, access_token):
        self.inspect_calls.append((input_dto, request_id, access_token))
        return StoryWorkspaceArtifactIndexOutputDTO(
            observation=self.observation,
            write_status=None,
        )

    def reconcile_index(self, input_dto, request_id, *, access_token):
        self.reconcile_calls.append((input_dto, request_id, access_token))
        return StoryWorkspaceArtifactIndexOutputDTO(
            observation=self.observation,
            write_status="same_revision",
        )


def _artifact_authority(*, bound: bool = True):
    episode = _episode_authority("a" * 32) if bound else None
    return StoryWorkspaceArtifactAuthorityDTO.model_validate({
        "run": {
            "workflow_run_id": RUN_ID,
            "deck_plugin_id": "plugin",
            "deck_plugin_version": "1.0.0",
            "workflow_definition_ref": "workflow",
            "deck_runtime_snapshot_id": "snapshot",
            "status": "queued",
            "failed_step": None,
            "error_code": None,
            "retry_of_run_id": None,
            "deck_plugin_manifest_hash": "sha256:" + "1" * 64,
            "deck_plugin_binding_id": "binding",
            "binding_revision": 1,
            "runtime_plugin_lock_id": "lock",
            "runtime_load_receipt_id": None,
            "workflow_preflight_id": "pf_" + "2" * 32,
            "agent_session_id": None,
            "source_voice_thread_id": THREAD_ID,
            "source_message_id": "message",
            "source_message_time": "2026-09-16T00:00:00+00:00",
            "workspace_id": WORKSPACE_ID,
            "idempotency_key": "launch",
            "input_hash": "sha256:" + "3" * 64,
            "semantic_fingerprint": "sha256:" + "4" * 64,
            "status_version": 1,
            "created_by": ACTOR_ID,
            "created_at": "2026-09-16T00:00:00+00:00",
            "started_at": None,
            "completed_at": None,
        },
        "thread_id": THREAD_ID,
        "thread_updated_at": "2026-09-16T00:01:00+00:00",
        "deck_id": "deck",
        "deck_display_name": "Dream Deck",
        "launch_agent_id": "voice",
        "goal": "Write a story",
        "project_story_slug": "didi-zhengzhou",
        "episode_authority": episode,
        "project_title": "滴滴郑州",
        "confirmation_accepted": False,
        "confirmation_dispatched": False,
    })


def _artifact_projection_dto():
    return StoryWorkspaceArtifactProjectionDTO(
        source_project_id="didi-zhengzhou",
        title="滴滴郑州",
        episode_count=1,
        artifact_manifest_revision="sha256:" + "b" * 64,
        script_revision="sha256:" + "b" * 64,
        script_size_bytes=12,
        artifact_status="available",
    )


def _artifact_observation():
    return StoryWorkspaceArtifactIndexObservationDTO.model_validate(
        _story_index_projection().model_dump(mode="json")
    )


def test_missing_episode_authority_returns_unbound_before_workspace_probe() -> None:
    gateway = DreamArtifactApplicationService()
    data = _ArtifactDataFake(_artifact_authority(bound=False))
    with patch.object(
        gateway,
        "_thread_workspace",
        side_effect=AssertionError("unbound authority must not probe files"),
    ) as workspace:
        result = gateway._get_episode_artifacts_sync(
            RUN_ID,
            {"actor_id": ACTOR_ID},
            data,
            "oauth",
        )
    assert result.binding_availability is StoryWorkspaceEpisodeBindingAvailability.UNBOUND
    workspace.assert_not_called()


def test_story_index_get_sends_only_normalized_projection_to_admin() -> None:
    gateway = DreamArtifactApplicationService()
    data = _ArtifactDataFake(_artifact_authority(), _artifact_observation())
    projection = _artifact_projection_dto()
    with patch.object(gateway, "_story_projection", return_value=projection):
        result = gateway._get_story_index_sync(
            RUN_ID,
            {"actor_id": ACTOR_ID},
            data,
            "oauth",
        )
    assert result.project_id == "didi-zhengzhou"
    assert len(data.inspect_calls) == 1
    sent = data.inspect_calls[0][0]
    assert sent.workflow_run_id == RUN_ID
    assert sent.projection == projection
    assert not hasattr(sent, "workspace_path")


def test_story_index_reconcile_rechecks_projection_and_uses_admin_cas() -> None:
    gateway = DreamArtifactApplicationService()
    observation = _artifact_observation()
    data = _ArtifactDataFake(_artifact_authority(), observation)
    projection = _artifact_projection_dto()
    with patch.object(gateway, "_story_projection", return_value=projection) as project:
        result = gateway._reconcile_story_index_sync(
            RUN_ID,
            StoryWorkspaceStoryIndexReconcileCommand(idempotencyKey="retry-1"),
            {"actor_id": ACTOR_ID},
            data,
            "oauth",
            f'"{observation.etag}"',
        )
    assert result.status == "missing"
    assert project.call_count == 2
    assert len(data.inspect_calls) == 2
    assert len(data.reconcile_calls) == 1
    sent = data.reconcile_calls[0][0]
    assert sent.expected_etag == observation.etag
    assert sent.projection == projection


def test_story_index_reconcile_stops_before_write_on_revision_conflict() -> None:
    gateway = DreamArtifactApplicationService()
    observation = _artifact_observation()
    data = _ArtifactDataFake(_artifact_authority(), observation)
    with patch.object(gateway, "_story_projection", return_value=_artifact_projection_dto()):
        with pytest.raises(ApiRouteError) as raised:
            gateway._reconcile_story_index_sync(
                RUN_ID,
                StoryWorkspaceStoryIndexReconcileCommand(),
                {"actor_id": ACTOR_ID},
                data,
                "oauth",
                '"sha256:' + "d" * 64 + '"',
            )
    assert raised.value.code == "story_index_revision_conflict"
    assert data.reconcile_calls == []

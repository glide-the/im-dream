"""TDD coverage for controlled Episode workflow continuation and recovery."""

from __future__ import annotations

import asyncio
import json
import sqlite3
import sys
import tempfile
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from pydantic import ValidationError


BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from routers import story_workspace  # noqa: E402
from services.deck import story_workflow_gateway as gateway_module  # noqa: E402
from services.story_workspace.episode_binding_service import (  # noqa: E402
    StoryWorkspaceEpisodeBindingContext,
    StoryWorkspaceEpisodeBindingService,
)
from services.story_workspace.episode_action_service import (  # noqa: E402
    StoryWorkspaceEpisodeActionFacts,
    StoryWorkspaceEpisodeActionService,
    StoryWorkspaceEpisodeNextActionResolver,
    story_workspace_episode_vendor_workflow,
)
from story_workspace.contracts import (  # noqa: E402
    StoryWorkspaceDreamRunContext,
    StoryWorkspaceEpisodeAction,
    StoryWorkspaceEpisodeActionDiagnostic,
    StoryWorkspaceEpisodeActionContinueCommand,
    StoryWorkspaceEpisodeArtifactAvailability,
    StoryWorkspaceEpisodeArtifactConsumer,
    StoryWorkspaceEpisodeArtifactManifestEntry,
    StoryWorkspaceEpisodeBindingRecoveryCommand,
    StoryWorkspaceEpisodeProducerAction,
    StoryWorkspaceEpisodeReviewScope,
)


RUN_ID = "run_0123456789abcdef0123456789abcdef"
THREAD_ID = "dream-thread"
ACTOR_ID = "7"
EPISODE_ID = "a" * 32
REVISION = "sha256:" + "1" * 64


_SPECS = {
    "episode-outline.md": (
        StoryWorkspaceEpisodeProducerAction.PLAN_EPISODE,
        [
            StoryWorkspaceEpisodeArtifactConsumer.EPISODE_OVERVIEW,
            StoryWorkspaceEpisodeArtifactConsumer.STORYLINE_NAVIGATOR,
            StoryWorkspaceEpisodeArtifactConsumer.NARRATIVE_WORKBENCH,
        ],
    ),
    "script.md": (
        StoryWorkspaceEpisodeProducerAction.WRITE_SCRIPT,
        [
            StoryWorkspaceEpisodeArtifactConsumer.NARRATIVE_WORKBENCH,
            StoryWorkspaceEpisodeArtifactConsumer.SHOT_INSPECTOR,
        ],
    ),
    "storyboard.yaml": (
        StoryWorkspaceEpisodeProducerAction.REGENERATE_STORYBOARD,
        [
            StoryWorkspaceEpisodeArtifactConsumer.NARRATIVE_WORKBENCH,
            StoryWorkspaceEpisodeArtifactConsumer.SHOT_INSPECTOR,
        ],
    ),
    "prompts/": (
        StoryWorkspaceEpisodeProducerAction.GENERATE_PROMPTS,
        [
            StoryWorkspaceEpisodeArtifactConsumer.SHOT_INSPECTOR,
            StoryWorkspaceEpisodeArtifactConsumer.PROMPT_VIEW,
        ],
    ),
    "renders/": (
        StoryWorkspaceEpisodeProducerAction.PREPARE_RENDER_GUIDE,
        [
            StoryWorkspaceEpisodeArtifactConsumer.SHOT_INSPECTOR,
            StoryWorkspaceEpisodeArtifactConsumer.RENDER_VIEW,
        ],
    ),
    "review-report.md": (
        StoryWorkspaceEpisodeProducerAction.REVIEW_FULL_CHAIN,
        [
            StoryWorkspaceEpisodeArtifactConsumer.REVIEW_VIEW,
            StoryWorkspaceEpisodeArtifactConsumer.SHOT_INSPECTOR,
        ],
    ),
}


def _context() -> StoryWorkspaceDreamRunContext:
    return StoryWorkspaceDreamRunContext(
        workflow_run_id=RUN_ID,
        thread_id=THREAD_ID,
        deck_id="deck-1",
        deck_plugin_id="drama-forge",
        deck_plugin_version="1.0.0",
        deck_plugin_binding_id="binding-1",
        binding_revision=1,
        deck_runtime_snapshot_id="snapshot-1",
        runtime_plugin_lock_id="lock-1",
    )


def _artifact(
    key: str,
    availability: StoryWorkspaceEpisodeArtifactAvailability,
    *,
    digit: str,
) -> StoryWorkspaceEpisodeArtifactManifestEntry:
    producer, consumers = _SPECS[key]
    available = availability is StoryWorkspaceEpisodeArtifactAvailability.AVAILABLE
    return StoryWorkspaceEpisodeArtifactManifestEntry(
        relativeKey=key,
        availability=availability,
        contentRevision=("sha256:" + digit * 64) if available else None,
        mtime="2026-08-06T00:00:00Z" if available else None,
        size=10 if available else None,
        producerAction=producer,
        consumers=consumers,
    )


def _surface(
    available: set[str],
    *,
    review_scope: StoryWorkspaceEpisodeReviewScope | None = None,
    review_source_revisions: list[object] | None = None,
    revision: str = REVISION,
) -> SimpleNamespace:
    artifacts = []
    for index, key in enumerate(_SPECS, start=1):
        artifacts.append(_artifact(
            key,
            (
                StoryWorkspaceEpisodeArtifactAvailability.AVAILABLE
                if key in available
                else StoryWorkspaceEpisodeArtifactAvailability.NOT_GENERATED
            ),
            digit=str(index),
        ))
    review = (
        SimpleNamespace(
            scope=review_scope,
            source_revisions=review_source_revisions or [],
        )
        if review_scope is not None
        else None
    )
    return SimpleNamespace(
        run_id=RUN_ID,
        opaque_episode_id=EPISODE_ID,
        manifest_revision=revision,
        artifacts=artifacts,
        auxiliary=SimpleNamespace(review=review),
    )


def _action_facts(**overrides: object) -> StoryWorkspaceEpisodeActionFacts:
    values = {
        "episode_uid": EPISODE_ID,
        "assets_revision": None,
        "storyboard_script_revision": None,
        "storyboard_assets_revision": None,
        "prompts_storyboard_revision": None,
        "full_chain_review_input_revision": None,
        "validated_input_revision": None,
        "render_input_revision": None,
    }
    values.update(overrides)
    return StoryWorkspaceEpisodeActionFacts(**values)


def test_recover_contract_accepts_only_idempotency_key() -> None:
    command = StoryWorkspaceEpisodeBindingRecoveryCommand(
        idempotencyKey="recover-1"
    )
    assert command.idempotency_key == "recover-1"

    for forbidden in ("story", "path", "root", "episodeId", "threadId"):
        with pytest.raises(ValidationError):
            StoryWorkspaceEpisodeBindingRecoveryCommand.model_validate({
                "idempotencyKey": "recover-1",
                forbidden: "attacker-controlled",
            })


def test_server_private_workflow_mapping_matches_vendor_readme_order() -> None:
    readme = (
        Path(__file__).resolve().parents[2]
        / "vendor"
        / "drama-forge"
        / "drama-forge"
        / "README.md"
    ).read_text(encoding="utf-8")
    mapping = story_workspace_episode_vendor_workflow()
    positions = [
        readme.index(evidence, readme.index("## 典型工作流"))
        for _, evidence in mapping
    ]

    assert positions == sorted(positions)
    assert [action for action, _ in mapping] == [
        StoryWorkspaceEpisodeAction.PLAN_EPISODE,
        StoryWorkspaceEpisodeAction.WRITE_SCRIPT,
        StoryWorkspaceEpisodeAction.REVIEW_SCRIPT,
        StoryWorkspaceEpisodeAction.REFRESH_ASSETS,
        StoryWorkspaceEpisodeAction.REGENERATE_STORYBOARD,
        StoryWorkspaceEpisodeAction.GENERATE_PROMPTS,
        StoryWorkspaceEpisodeAction.REVIEW_FULL_CHAIN,
        StoryWorkspaceEpisodeAction.VALIDATE_EPISODE,
        StoryWorkspaceEpisodeAction.PREPARE_RENDER_GUIDE,
    ]


def test_continue_contract_is_strict_and_guidance_is_bounded() -> None:
    command = StoryWorkspaceEpisodeActionContinueCommand(
        episodeId=EPISODE_ID,
        action="write_script",
        idempotencyKey="continue-1",
        userGuidance="保留克制氛围",
    )
    assert command.action is StoryWorkspaceEpisodeAction.WRITE_SCRIPT

    with pytest.raises(ValidationError):
        StoryWorkspaceEpisodeActionContinueCommand.model_validate({
            **command.model_dump(mode="json", by_alias=True),
            "story": "attacker-controlled",
        })
    with pytest.raises(ValidationError):
        StoryWorkspaceEpisodeActionContinueCommand(
            episodeId=EPISODE_ID,
            action="write_script",
            idempotencyKey="continue-2",
            userGuidance="x" * 2001,
        )


def test_resolver_follows_readme_order_without_inventing_business_states() -> None:
    resolver = StoryWorkspaceEpisodeNextActionResolver()

    cases = [
        (set(), _action_facts(), StoryWorkspaceEpisodeAction.PLAN_EPISODE, "ready"),
        (
            {"episode-outline.md"},
            _action_facts(),
            StoryWorkspaceEpisodeAction.WRITE_SCRIPT,
            "ready",
        ),
        (
            {"episode-outline.md", "script.md"},
            _action_facts(),
            StoryWorkspaceEpisodeAction.REVIEW_SCRIPT,
            "ready",
        ),
    ]
    for available, facts, action, diagnostic in cases:
        resolution = resolver.resolve(_surface(available), facts)
        assert resolution.action is action
        assert resolution.diagnostic.value == diagnostic

    reviewed = _surface(
        {"episode-outline.md", "script.md", "review-report.md"},
        review_scope=StoryWorkspaceEpisodeReviewScope.SCRIPT,
        review_source_revisions=[SimpleNamespace(
            source_artifact="script.md",
            source_revision="sha256:" + "2" * 64,
        )],
    )
    resolution = resolver.resolve(reviewed, _action_facts())
    assert resolution.action is StoryWorkspaceEpisodeAction.REFRESH_ASSETS
    assert resolution.diagnostic is StoryWorkspaceEpisodeActionDiagnostic.NEEDS_CONFIRMATION

    assets = _action_facts(assets_revision="sha256:" + "a" * 64)
    resolution = resolver.resolve(reviewed, assets)
    assert resolution.action is StoryWorkspaceEpisodeAction.REGENERATE_STORYBOARD
    assert resolution.diagnostic is StoryWorkspaceEpisodeActionDiagnostic.READY

    storyboard = _surface({
        "episode-outline.md", "script.md", "storyboard.yaml", "review-report.md"
    }, review_scope=StoryWorkspaceEpisodeReviewScope.SCRIPT, review_source_revisions=[
        SimpleNamespace(
            source_artifact="script.md",
            source_revision="sha256:" + "2" * 64,
        )
    ])
    current_storyboard = next(
        item for item in storyboard.artifacts if item.relative_key == "storyboard.yaml"
    ).content_revision
    current_script = next(
        item for item in storyboard.artifacts if item.relative_key == "script.md"
    ).content_revision
    current_facts = _action_facts(
        assets_revision="sha256:" + "a" * 64,
        storyboard_script_revision=current_script,
        storyboard_assets_revision="sha256:" + "a" * 64,
    )
    resolution = resolver.resolve(storyboard, current_facts)
    assert resolution.action is StoryWorkspaceEpisodeAction.GENERATE_PROMPTS
    assert resolution.diagnostic is StoryWorkspaceEpisodeActionDiagnostic.READY

    prompts = _surface({
        "episode-outline.md", "script.md", "storyboard.yaml", "prompts/",
        "review-report.md",
    }, review_scope=StoryWorkspaceEpisodeReviewScope.SCRIPT, review_source_revisions=[
        SimpleNamespace(
            source_artifact="script.md",
            source_revision="sha256:" + "2" * 64,
        )
    ])
    prompt_facts = StoryWorkspaceEpisodeActionFacts(
        **{
            **current_facts.__dict__,
            "prompts_storyboard_revision": current_storyboard,
        }
    )
    resolution = resolver.resolve(prompts, prompt_facts)
    assert resolution.action is StoryWorkspaceEpisodeAction.REVIEW_FULL_CHAIN
    assert resolution.diagnostic is StoryWorkspaceEpisodeActionDiagnostic.READY


def test_resolver_marks_ambiguous_or_stale_evidence_needs_confirmation() -> None:
    resolver = StoryWorkspaceEpisodeNextActionResolver()
    surface = _surface({"episode-outline.md", "script.md", "review-report.md"},
        review_scope=StoryWorkspaceEpisodeReviewScope.UNKNOWN)
    resolution = resolver.resolve(surface, _action_facts())
    assert resolution.action is StoryWorkspaceEpisodeAction.REVIEW_SCRIPT
    assert resolution.diagnostic is StoryWorkspaceEpisodeActionDiagnostic.NEEDS_CONFIRMATION

    invalid_outline = _surface(set())
    invalid_outline.artifacts[0] = _artifact(
        "episode-outline.md",
        StoryWorkspaceEpisodeArtifactAvailability.INVALID,
        digit="1",
    )
    resolution = resolver.resolve(invalid_outline, _action_facts())
    assert resolution.action is StoryWorkspaceEpisodeAction.PLAN_EPISODE
    assert resolution.diagnostic is StoryWorkspaceEpisodeActionDiagnostic.NEEDS_CONFIRMATION


def test_resolver_reaches_validation_render_guide_and_none_only_with_explicit_facts() -> None:
    resolver = StoryWorkspaceEpisodeNextActionResolver()
    upstream = {
        "episode-outline.md",
        "script.md",
        "storyboard.yaml",
        "prompts/",
        "review-report.md",
    }
    surface = _surface(
        upstream,
        review_scope=StoryWorkspaceEpisodeReviewScope.FULL_CHAIN,
        review_source_revisions=[SimpleNamespace(
            source_artifact="script.md",
            source_revision="sha256:" + "2" * 64,
        )],
    )
    full_chain_revision = resolver.full_chain_input_revision(surface)
    validation_revision = resolver.validation_input_revision(surface)
    facts = _action_facts(
        assets_revision="sha256:" + "a" * 64,
        storyboard_script_revision="sha256:" + "2" * 64,
        storyboard_assets_revision="sha256:" + "a" * 64,
        prompts_storyboard_revision="sha256:" + "3" * 64,
        full_chain_review_input_revision=full_chain_revision,
    )

    resolution = resolver.resolve(surface, facts)
    assert resolution.action is StoryWorkspaceEpisodeAction.VALIDATE_EPISODE
    assert resolution.diagnostic is StoryWorkspaceEpisodeActionDiagnostic.NEEDS_CONFIRMATION

    validated = StoryWorkspaceEpisodeActionFacts(
        **{**facts.__dict__, "validated_input_revision": validation_revision}
    )
    resolution = resolver.resolve(surface, validated)
    assert resolution.action is StoryWorkspaceEpisodeAction.PREPARE_RENDER_GUIDE
    assert resolution.diagnostic is StoryWorkspaceEpisodeActionDiagnostic.READY

    complete_surface = _surface(
        upstream | {"renders/"},
        review_scope=StoryWorkspaceEpisodeReviewScope.FULL_CHAIN,
        review_source_revisions=[SimpleNamespace(
            source_artifact="script.md",
            source_revision="sha256:" + "2" * 64,
        )],
    )
    complete_validation = resolver.validation_input_revision(complete_surface)
    complete = StoryWorkspaceEpisodeActionFacts(
        **{
            **validated.__dict__,
            "validated_input_revision": complete_validation,
            "render_input_revision": complete_validation,
        }
    )
    resolution = resolver.resolve(complete_surface, complete)
    assert resolution.action is StoryWorkspaceEpisodeAction.NONE_IN_SCOPE
    assert resolution.can_dispatch is False


def test_action_facts_parser_requires_exact_episode_scoped_revision_metadata() -> None:
    revision = "sha256:" + "a" * 64
    raw = {
        "story_workspace_episode_action_facts": {
            "schema": "story-workspace-episode-action-facts/v1",
            "episode_uid": EPISODE_ID,
            "assets_revision": revision,
            "storyboard_script_revision": None,
            "storyboard_assets_revision": None,
            "prompts_storyboard_revision": None,
            "full_chain_review_input_revision": None,
            "validated_input_revision": None,
            "render_input_revision": None,
        }
    }
    parsed = StoryWorkspaceEpisodeActionFacts.parse(raw, episode_uid=EPISODE_ID)
    assert parsed.assets_revision == revision

    poisoned = json.loads(json.dumps(raw))
    poisoned["story_workspace_episode_action_facts"]["episode_uid"] = "b" * 32
    assert StoryWorkspaceEpisodeActionFacts.parse(
        poisoned,
        episode_uid=EPISODE_ID,
    ) == StoryWorkspaceEpisodeActionFacts.empty(EPISODE_ID)
    poisoned = json.loads(json.dumps(raw))
    poisoned["story_workspace_episode_action_facts"]["story_path"] = "../../other"
    assert StoryWorkspaceEpisodeActionFacts.parse(
        poisoned,
        episode_uid=EPISODE_ID,
    ) == StoryWorkspaceEpisodeActionFacts.empty(EPISODE_ID)


class _IdleFactory:
    def session_snapshot(self, _thread_id: str):
        return None


class _RunningFactory(_IdleFactory):
    def session_snapshot(self, _thread_id: str):
        return {"lifecycle": "running", "current_turn_id": "turn-1"}


class TestStoryWorkspaceEpisodeActionService:
    def setup_method(self) -> None:
        self.db = sqlite3.connect(":memory:")
        self.db.row_factory = sqlite3.Row
        self.db.executescript(
            """
            CREATE TABLE chat_thread (
              id TEXT PRIMARY KEY, user_id INTEGER, deck_id TEXT, updated_at TEXT
            );
            CREATE TABLE chat_message (
              id TEXT PRIMARY KEY, thread_id TEXT, role TEXT, parts TEXT,
              metadata TEXT, created_at TEXT DEFAULT CURRENT_TIMESTAMP
            );
            INSERT INTO chat_thread (id, user_id, deck_id)
            VALUES ('dream-thread', 7, 'deck-1');
            """
        )

    def teardown_method(self) -> None:
        self.db.close()

    def _service(self, *, running: bool = False) -> StoryWorkspaceEpisodeActionService:
        return StoryWorkspaceEpisodeActionService(
            self.db,
            thread_factory=_RunningFactory() if running else _IdleFactory(),
        )

    @staticmethod
    def _continue(
        *, key: str = "continue-1", guidance: str | None = "保留克制氛围"
    ) -> StoryWorkspaceEpisodeActionContinueCommand:
        return StoryWorkspaceEpisodeActionContinueCommand(
            episodeId=EPISODE_ID,
            action="write_script",
            idempotencyKey=key,
            userGuidance=guidance,
        )

    def test_same_key_same_fingerprint_reuses_one_persisted_message(self) -> None:
        surface = _surface({"episode-outline.md"})
        with patch(
            "services.story_workspace.dream_agent_message_service."
            "story_workspace_read_dream_confirmation_fact",
            return_value=(True, True),
        ):
            accepted, pending = self._service().continue_episode(
                run_id=RUN_ID,
                actor_id=ACTOR_ID,
                context=_context(),
                surface=surface,
                action_facts=_action_facts(),
                if_match=f'"{REVISION}"',
                command=self._continue(),
            )
            replay, replay_pending = self._service().continue_episode(
                run_id=RUN_ID,
                actor_id=ACTOR_ID,
                context=_context(),
                surface=surface,
                action_facts=_action_facts(),
                if_match=f'"{REVISION}"',
                command=self._continue(),
            )

        assert accepted.message_id == replay.message_id
        assert accepted.replayed is False
        assert replay.replayed is True
        assert pending is not None
        assert replay_pending is None
        assert self.db.execute("SELECT COUNT(*) FROM chat_message").fetchone()[0] == 1
        persisted = self.db.execute("SELECT parts, metadata FROM chat_message").fetchone()
        payload = f"{persisted['parts']} {persisted['metadata']}"
        assert "/drama-" not in payload
        assert "保留克制氛围" in payload
        assert "artifact" not in accepted.model_dump_json().lower()
        assert "保留克制氛围" not in accepted.model_dump_json()

    def test_same_key_different_content_conflicts_and_different_key_is_busy(self) -> None:
        surface = _surface({"episode-outline.md"})
        with patch(
            "services.story_workspace.dream_agent_message_service."
            "story_workspace_read_dream_confirmation_fact",
            return_value=(True, True),
        ):
            self._service().continue_episode(
                run_id=RUN_ID,
                actor_id=ACTOR_ID,
                context=_context(),
                surface=surface,
                action_facts=_action_facts(),
                if_match=f'"{REVISION}"',
                command=self._continue(),
            )
            with pytest.raises(RuntimeError, match="IDEMPOTENCY_CONFLICT"):
                self._service().continue_episode(
                    run_id=RUN_ID,
                    actor_id=ACTOR_ID,
                    context=_context(),
                    surface=surface,
                    action_facts=_action_facts(),
                    if_match=f'"{REVISION}"',
                    command=self._continue(guidance="改成喜剧"),
                )
            with pytest.raises(RuntimeError, match="DREAM_AGENT_MESSAGE_BUSY"):
                self._service().continue_episode(
                    run_id=RUN_ID,
                    actor_id=ACTOR_ID,
                    context=_context(),
                    surface=surface,
                    action_facts=_action_facts(),
                    if_match=f'"{REVISION}"',
                    command=self._continue(key="continue-2"),
                )
        assert self.db.execute("SELECT COUNT(*) FROM chat_message").fetchone()[0] == 1

    def test_continue_revalidates_episode_manifest_action_and_live_turn(self) -> None:
        surface = _surface({"episode-outline.md"})
        with patch(
            "services.story_workspace.dream_agent_message_service."
            "story_workspace_read_dream_confirmation_fact",
            return_value=(True, True),
        ):
            for changed in (
                self._continue(),
                StoryWorkspaceEpisodeActionContinueCommand(
                    episodeId="b" * 32,
                    action="write_script",
                    idempotencyKey="continue-other-episode",
                ),
                StoryWorkspaceEpisodeActionContinueCommand(
                    episodeId=EPISODE_ID,
                    action="plan_episode",
                    idempotencyKey="continue-wrong-action",
                ),
            ):
                match = (
                    '"sha256:' + "9" * 64 + '"'
                    if changed.idempotency_key == "continue-1"
                    else f'"{REVISION}"'
                )
                with pytest.raises(RuntimeError):
                    self._service().continue_episode(
                        run_id=RUN_ID,
                        actor_id=ACTOR_ID,
                        context=_context(),
                        surface=surface,
                        action_facts=_action_facts(),
                        if_match=match,
                        command=changed,
                    )
            with pytest.raises(RuntimeError, match="NOT_READY"):
                self._service(running=True).continue_episode(
                    run_id=RUN_ID,
                    actor_id=ACTOR_ID,
                    context=_context(),
                    surface=surface,
                    action_facts=_action_facts(),
                    if_match=f'"{REVISION}"',
                    command=self._continue(key="live-turn"),
                )
        assert self.db.execute("SELECT COUNT(*) FROM chat_message").fetchone()[0] == 0

    def test_recover_uses_controlled_intent_and_same_claim_semantics(self) -> None:
        command = StoryWorkspaceEpisodeBindingRecoveryCommand(
            idempotencyKey="recover-1"
        )
        with patch(
            "services.story_workspace.dream_agent_message_service."
            "story_workspace_read_dream_confirmation_fact",
            return_value=(True, True),
        ):
            accepted, pending = self._service().recover_binding(
                run_id=RUN_ID,
                actor_id=ACTOR_ID,
                context=_context(),
                command=command,
            )
            replay, replay_pending = self._service().recover_binding(
                run_id=RUN_ID,
                actor_id=ACTOR_ID,
                context=_context(),
                command=command,
            )

        assert accepted.message_id == replay.message_id
        assert accepted.episode_id is None
        assert pending is not None
        assert replay_pending is None
        row = self.db.execute("SELECT parts, metadata FROM chat_message").fetchone()
        payload = f"{row['parts']} {row['metadata']}"
        assert "恢复第一集关联" in payload
        assert "story" not in accepted.model_dump_json().lower()
        assert "path" not in accepted.model_dump_json().lower()
        assert "/drama-" not in payload


class _RouteGateway:
    def __init__(self) -> None:
        self.calls: list[tuple[object, ...]] = []

    async def recover_episode_binding(self, run_id, request, *, actor):
        self.calls.append(("recover", run_id, request, actor))
        return SimpleNamespace(model_dump=lambda **_: {
            "runId": run_id,
            "episodeId": None,
            "capability": "recover_first_episode_binding",
            "messageId": "dream_agent_test",
            "accepted": True,
            "replayed": False,
        })

    async def continue_episode_action(self, run_id, request, *, actor, if_match):
        self.calls.append(("continue", run_id, request, actor, if_match))
        return SimpleNamespace(model_dump=lambda **_: {
            "runId": run_id,
            "episodeId": request.episode_id,
            "capability": request.action.value,
            "messageId": "dream_agent_test",
            "accepted": True,
            "replayed": False,
        })


def test_routes_keep_path_identity_out_of_recover_and_require_if_match() -> None:
    app = FastAPI()
    gateway = _RouteGateway()
    app.dependency_overrides[story_workspace.get_current_user] = lambda: {
        "user_id": int(ACTOR_ID),
    }
    app.dependency_overrides[story_workspace.get_story_workflow_gateway] = lambda: gateway
    app.include_router(story_workspace.router)

    with TestClient(app) as client:
        recovered = client.post(
            f"/api/story-workspace/workflow-runs/{RUN_ID}/episode-binding/recover",
            json={"idempotencyKey": "recover-route"},
        )
        forbidden = client.post(
            f"/api/story-workspace/workflow-runs/{RUN_ID}/episode-binding/recover",
            json={"idempotencyKey": "recover-route", "story": "attacker"},
        )
        missing_match = client.post(
            f"/api/story-workspace/workflow-runs/{RUN_ID}/episode-actions/continue",
            json={
                "episodeId": EPISODE_ID,
                "action": "write_script",
                "idempotencyKey": "continue-route",
            },
        )
        continued = client.post(
            f"/api/story-workspace/workflow-runs/{RUN_ID}/episode-actions/continue",
            headers={"If-Match": f'"{REVISION}"'},
            json={
                "episodeId": EPISODE_ID,
                "action": "write_script",
                "idempotencyKey": "continue-route",
            },
        )

    assert recovered.status_code == 202
    assert forbidden.status_code == 422
    assert missing_match.status_code == 422
    assert continued.status_code == 202
    assert gateway.calls[0][3] == {"actor_id": ACTOR_ID}
    assert gateway.calls[1][4] == f'"{REVISION}"'


def test_claim_lease_expiry_recovers_same_identity_without_second_message() -> None:
    db = sqlite3.connect(":memory:")
    db.row_factory = sqlite3.Row
    db.executescript(
        """
        CREATE TABLE chat_thread (
          id TEXT PRIMARY KEY, user_id INTEGER, deck_id TEXT, updated_at TEXT
        );
        CREATE TABLE chat_message (
          id TEXT PRIMARY KEY, thread_id TEXT, role TEXT, parts TEXT,
          metadata TEXT, created_at TEXT DEFAULT CURRENT_TIMESTAMP
        );
        INSERT INTO chat_thread (id, user_id, deck_id)
        VALUES ('dream-thread', 7, 'deck-1');
        """
    )
    service = StoryWorkspaceEpisodeActionService(db, thread_factory=_IdleFactory())
    command = StoryWorkspaceEpisodeBindingRecoveryCommand(idempotencyKey="recover-lease")
    with patch(
        "services.story_workspace.dream_agent_message_service."
        "story_workspace_read_dream_confirmation_fact",
        return_value=(True, True),
    ):
        accepted, pending = service.recover_binding(
            run_id=RUN_ID,
            actor_id=ACTOR_ID,
            context=_context(),
            command=command,
        )
        assert pending is not None
        metadata = json.loads(db.execute(
            "SELECT metadata FROM chat_message WHERE id = ?", (accepted.message_id,)
        ).fetchone()[0])
        old_claim = metadata["dispatch_claim_id"]
        metadata["dispatch_claim_lease_until"] = 0
        db.execute(
            "UPDATE chat_message SET metadata = ? WHERE id = ?",
            (json.dumps(metadata), accepted.message_id),
        )
        db.commit()
        replay, recovered = service.recover_binding(
            run_id=RUN_ID,
            actor_id=ACTOR_ID,
            context=_context(),
            command=command,
        )

    assert replay.message_id == accepted.message_id
    assert recovered is not None
    assert recovered.metadata["dispatch_claim_id"] != old_claim
    assert db.execute("SELECT COUNT(*) FROM chat_message").fetchone()[0] == 1
    db.close()


def test_coordinator_schedules_one_active_dispatch_per_message_identity() -> None:
    scheduled: list[str] = []

    async def exercise() -> None:
        from services.story_workspace.dream_agent_message_service import (
            StoryWorkspaceDreamAgentMessageCoordinator,
            StoryWorkspaceDreamAgentPendingDispatch,
        )

        entered = asyncio.Event()
        release = asyncio.Event()

        async def dispatch(pending):
            scheduled.append(pending.message_id)
            entered.set()
            await release.wait()

        pending = StoryWorkspaceDreamAgentPendingDispatch(
            thread_id=THREAD_ID,
            actor_id=ACTOR_ID,
            context=_context(),
            message_id="dream_agent_one",
            parts=[{"type": "text", "text": "受控意图"}],
            metadata={"dispatch_claim_id": "claim-one"},
        )
        coordinator = StoryWorkspaceDreamAgentMessageCoordinator(dispatch)
        assert coordinator.schedule(pending) is True
        await entered.wait()
        assert coordinator.schedule(pending) is False
        release.set()
        await asyncio.sleep(0)
        await asyncio.sleep(0)

    asyncio.run(exercise())
    assert scheduled == ["dream_agent_one"]


def _create_gateway_schema(db: sqlite3.Connection) -> None:
    db.executescript(
        """
        CREATE TABLE story_workspace_workspaces (id TEXT PRIMARY KEY, owner_id INTEGER);
        CREATE TABLE decks (id TEXT PRIMARY KEY, name TEXT, owner_id INTEGER, enabled INTEGER);
        CREATE TABLE workflow_preflights (
          workflow_preflight_id TEXT PRIMARY KEY, deck_id TEXT, workspace_id TEXT,
          creator_id TEXT, created_by TEXT, deck_plugin_id TEXT,
          deck_plugin_version TEXT, runtime_plugin_lock_id TEXT,
          binding_revision INTEGER, deck_runtime_snapshot_id TEXT
        );
        CREATE TABLE deck_plugin_bindings (
          deck_plugin_binding_id TEXT PRIMARY KEY, deck_id TEXT, workspace_id TEXT,
          creator_id TEXT, deck_plugin_id TEXT, deck_plugin_version TEXT,
          binding_revision INTEGER
        );
        CREATE TABLE workflow_runs (
          id TEXT PRIMARY KEY, workspace_id TEXT, deck_plugin_id TEXT,
          deck_plugin_version TEXT, workflow_definition_ref TEXT,
          deck_runtime_snapshot_id TEXT, deck_plugin_manifest_hash TEXT,
          deck_plugin_binding_id TEXT, binding_revision INTEGER,
          runtime_plugin_lock_id TEXT, workflow_preflight_id TEXT,
          source_voice_thread_id TEXT, source_message_id TEXT,
          created_by TEXT, created_at TEXT
        );
        CREATE TABLE deck_plugin_releases (
          deck_plugin_id TEXT, deck_plugin_version TEXT,
          workflow_definition_ref TEXT, manifest_hash TEXT, manifest_json TEXT
        );
        CREATE TABLE deck_runtime_plugin_locks (
          id TEXT PRIMARY KEY, deck_plugin_id TEXT, deck_plugin_version TEXT,
          deck_plugin_manifest_hash TEXT
        );
        CREATE TABLE deck_runtime_snapshots (
          deck_runtime_snapshot_id TEXT PRIMARY KEY, deck_id TEXT,
          deck_plugin_binding_id TEXT, binding_revision INTEGER
        );
        CREATE TABLE chat_thread (
          id TEXT PRIMARY KEY, user_id INTEGER, deck_id TEXT, updated_at TEXT
        );
        CREATE TABLE chat_message (
          id TEXT PRIMARY KEY, thread_id TEXT, role TEXT, parts TEXT,
          metadata TEXT, created_at TEXT DEFAULT CURRENT_TIMESTAMP
        );
        """
    )


def _seed_gateway_run(
    db: sqlite3.Connection,
    *,
    episode_uid: str | None,
) -> None:
    manifest_hash = "sha256:" + "f" * 64
    db.execute("INSERT INTO story_workspace_workspaces VALUES ('workspace-1', 7)")
    db.execute("INSERT INTO decks VALUES ('deck-1', 'Dream', 7, 1)")
    db.execute(
        "INSERT INTO workflow_preflights VALUES "
        "('pf-1', 'deck-1', 'workspace-1', '7', '7', 'drama-forge', "
        "'1.0.0', 'lock-1', 1, 'snapshot-1')"
    )
    db.execute(
        "INSERT INTO deck_plugin_bindings VALUES "
        "('binding-1', 'deck-1', 'workspace-1', '7', 'drama-forge', '1.0.0', 1)"
    )
    db.execute(
        "INSERT INTO workflow_runs VALUES (?, 'workspace-1', 'drama-forge', "
        "'1.0.0', 'deck://ink.dream/story/1.0.0/workflow.json', 'snapshot-1', ?, "
        "'binding-1', 1, 'lock-1', 'pf-1', ?, 'source-1', '7', "
        "'2026-08-06T00:00:00Z')",
        (RUN_ID, manifest_hash, THREAD_ID),
    )
    db.execute(
        "INSERT INTO deck_plugin_releases VALUES "
        "('drama-forge', '1.0.0', 'deck://ink.dream/story/1.0.0/workflow.json', ?, ?)",
        (manifest_hash, json.dumps({"surfaces": [{"name": "dream"}]})),
    )
    db.execute(
        "INSERT INTO deck_runtime_plugin_locks VALUES "
        "('lock-1', 'drama-forge', '1.0.0', ?)",
        (manifest_hash,),
    )
    db.execute(
        "INSERT INTO deck_runtime_snapshots VALUES "
        "('snapshot-1', 'deck-1', 'binding-1', 1)"
    )
    db.execute(
        "INSERT INTO chat_thread VALUES (?, 7, 'deck-1', '2026-08-06T00:00:00Z')",
        (THREAD_ID,),
    )
    source_metadata = {
        "kind": "story-workspace-dream-launch",
        "actorId": ACTOR_ID,
        "workspaceId": "workspace-1",
        "deckId": "deck-1",
        "workflowRunId": RUN_ID,
        "threadId": THREAD_ID,
        "dreamContext": {
            "workflow_run_id": RUN_ID,
            "thread_id": THREAD_ID,
            "deck_id": "deck-1",
            "deck_plugin_id": "drama-forge",
            "deck_plugin_version": "1.0.0",
            "deck_plugin_binding_id": "binding-1",
            "binding_revision": 1,
            "deck_runtime_snapshot_id": "snapshot-1",
            "runtime_plugin_lock_id": "lock-1",
        },
    }
    if episode_uid is not None:
        source_metadata["story_workspace_episode_identity"] = {
            "schema": "story-workspace-episode-authority/v1",
            "workflow_run_id": RUN_ID,
            "episode_uid": episode_uid,
            "story_slug": "demo",
            "episode_code": "EP01",
        }
    db.execute(
        "INSERT INTO chat_message "
        "(id, thread_id, role, parts, metadata, created_at) "
        "VALUES ('source-1', ?, 'user', '[]', ?, '2026-08-06T00:00:00Z')",
        (THREAD_ID, json.dumps(source_metadata)),
    )
    db.commit()


def _gateway_app(gateway, actor: dict[str, int]) -> FastAPI:
    app = FastAPI()
    app.dependency_overrides[story_workspace.get_current_user] = lambda: {
        "user_id": actor["value"],
    }
    app.dependency_overrides[story_workspace.get_story_workflow_gateway] = lambda: gateway
    app.include_router(story_workspace.router)
    return app


def test_real_gateway_continue_reauthorizes_and_returns_latest_surface_on_conflict() -> None:
    with tempfile.TemporaryDirectory() as temporary_directory:
        root = Path(temporary_directory)
        db_path = root / "episode-actions.db"
        db = sqlite3.connect(db_path)
        db.row_factory = sqlite3.Row
        _create_gateway_schema(db)
        _seed_gateway_run(db, episode_uid=EPISODE_ID)
        db.close()

        workspace_root = root / "workspaces"
        workspace = workspace_root / THREAD_ID
        episode = workspace / "stories" / "demo" / "episodes" / "EP01"
        episode.mkdir(parents=True)
        (workspace / ".dream").mkdir()
        (workspace / "stories" / "demo" / "project.yaml").write_text(
            "project_id: demo\n",
            encoding="utf-8",
        )
        binding = StoryWorkspaceEpisodeBindingService(workspace).bind_first_episode(
            StoryWorkspaceEpisodeBindingContext(
                workflow_run_id=RUN_ID,
                trusted_project_story_slug="demo",
                locked_context_story_slug="demo",
                run_provenance_story_slug="demo",
            )
        )
        assert binding.episode_uid != EPISODE_ID
        binding_payload = json.loads((
            workspace / ".dream" / "runtime" / "runs" / RUN_ID / "episode.json"
        ).read_text(encoding="utf-8"))
        binding_payload["episode_uid"] = EPISODE_ID
        (workspace / ".dream" / "runtime" / "runs" / RUN_ID / "episode.json").write_text(
            json.dumps(binding_payload),
            encoding="utf-8",
        )
        (episode / "episode-outline.md").write_text(
            "---\ntitle: Demo\n---\n# Story Goals\n- Begin\n",
            encoding="utf-8",
        )

        gateway = gateway_module.StoryWorkflowApplicationGateway()
        scheduled: list[object] = []
        gateway._dream_agent_message_coordinator = SimpleNamespace(  # noqa: SLF001
            schedule=lambda pending: scheduled.append(pending) or True
        )
        actor = {"value": int(ACTOR_ID)}
        app = _gateway_app(gateway, actor)
        with (
            patch.object(gateway_module.database, "DB_PATH", db_path),
            patch.object(
                gateway_module,
                "story_workspace_get_workspace_root",
                return_value=workspace_root,
            ),
            patch.object(
                gateway_module.StoryWorkflowApplicationGateway,
                "_dream_agent_thread_factory",
                return_value=_IdleFactory(),
            ),
            patch(
                "services.story_workspace.dream_agent_message_service."
                "story_workspace_read_dream_confirmation_fact",
                return_value=(True, True),
            ),
            TestClient(app) as client,
        ):
            current = client.get(
                f"/api/story-workspace/workflow-runs/{RUN_ID}/episode-artifacts"
            )
            etag = current.headers["etag"]
            stale = client.post(
                f"/api/story-workspace/workflow-runs/{RUN_ID}/episode-actions/continue",
                headers={"If-Match": '"sha256:' + "9" * 64 + '"'},
                json={
                    "episodeId": EPISODE_ID,
                    "action": "write_script",
                    "idempotencyKey": "stale",
                },
            )
            wrong_action = client.post(
                f"/api/story-workspace/workflow-runs/{RUN_ID}/episode-actions/continue",
                headers={"If-Match": etag},
                json={
                    "episodeId": EPISODE_ID,
                    "action": "plan_episode",
                    "idempotencyKey": "wrong-action",
                },
            )
            accepted = client.post(
                f"/api/story-workspace/workflow-runs/{RUN_ID}/episode-actions/continue",
                headers={"If-Match": etag},
                json={
                    "episodeId": EPISODE_ID,
                    "action": "write_script",
                    "idempotencyKey": "continue-real",
                },
            )
            actor["value"] = 8
            forbidden = client.post(
                f"/api/story-workspace/workflow-runs/{RUN_ID}/episode-actions/continue",
                headers={"If-Match": etag},
                json={
                    "episodeId": EPISODE_ID,
                    "action": "write_script",
                    "idempotencyKey": "attacker",
                },
            )

        assert current.status_code == 200
        assert stale.status_code == 409
        assert stale.json()["latestSurface"]["opaqueEpisodeId"] == EPISODE_ID
        assert wrong_action.status_code == 409
        assert wrong_action.json()["resolution"]["action"] == "write_script"
        assert accepted.status_code == 202
        assert accepted.json()["episodeId"] == EPISODE_ID
        assert len(scheduled) == 1
        assert forbidden.status_code == 404
        db = sqlite3.connect(db_path)
        action_count = db.execute(
            "SELECT COUNT(*) FROM chat_message WHERE id != 'source-1'"
        ).fetchone()[0]
        db.close()
        assert action_count == 1


def test_real_gateway_recovery_is_path_free_and_keeps_unproven_run_unbound() -> None:
    with tempfile.TemporaryDirectory() as temporary_directory:
        root = Path(temporary_directory)
        db_path = root / "episode-recovery.db"
        db = sqlite3.connect(db_path)
        db.row_factory = sqlite3.Row
        _create_gateway_schema(db)
        _seed_gateway_run(db, episode_uid=None)
        db.close()
        gateway = gateway_module.StoryWorkflowApplicationGateway()
        scheduled: list[object] = []
        gateway._dream_agent_message_coordinator = SimpleNamespace(  # noqa: SLF001
            schedule=lambda pending: scheduled.append(pending) or True
        )
        app = _gateway_app(gateway, {"value": int(ACTOR_ID)})
        with (
            patch.object(gateway_module.database, "DB_PATH", db_path),
            patch.object(
                gateway_module.StoryWorkflowApplicationGateway,
                "_dream_agent_thread_factory",
                return_value=_IdleFactory(),
            ),
            patch.object(
                gateway,
                "_thread_workspace",
                side_effect=AssertionError("recovery must not probe an unproven path"),
            ) as workspace_probe,
            patch(
                "services.story_workspace.dream_agent_message_service."
                "story_workspace_read_dream_confirmation_fact",
                return_value=(True, True),
            ),
            TestClient(app) as client,
        ):
            recovered = client.post(
                f"/api/story-workspace/workflow-runs/{RUN_ID}/episode-binding/recover",
                json={"idempotencyKey": "recover-real"},
            )
            still_unbound = client.get(
                f"/api/story-workspace/workflow-runs/{RUN_ID}/episode-artifacts"
            )

        assert recovered.status_code == 202
        assert recovered.json()["capability"] == "recover_first_episode_binding"
        assert recovered.json()["episodeId"] is None
        assert still_unbound.status_code == 200
        assert still_unbound.json()["bindingAvailability"] == "unbound"
        assert still_unbound.json()["opaqueEpisodeId"] is None
        assert len(scheduled) == 1
        workspace_probe.assert_not_called()

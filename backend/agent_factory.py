#!/usr/bin/env python3
# [Input] Consume Claude Agent factory/controller, PostgreSQL policy provider/refresher,
#         resource Observer/sampler/diagnostics, and the PostgreSQL latest-snapshot sink.
# [Output] Provide shared Agent factory plus isolated resource observation/synchronization singletons.
# [Pos] backend Claude Agent composition root; the only owner that resolves and refreshes desired resource policy.
# [Sync] 2026-08-27: compose capability-gated dynamic policy refresh and PostgreSQL-only resource publication.

import database
from claude_agent import ClaudeAgentThreadFactory
from claude_agent.admission import AgentAdmissionConfig, ClaudeAgentAdmissionController
from claude_agent.resource_diagnostics import (
    ClaudeAgentResourceDiagnostics,
    ClaudeAgentResourceSampler,
)
from claude_agent.resource_observer import (
    ClaudeAgentResourceObserver,
    ObservedClaudeAgentAdmissionController,
)
from claude_agent.resource_policy import (
    ClaudeAgentResourcePolicyProvider,
    ClaudeAgentResourcePolicyRefresher,
    ResourcePolicyLoadResult,
    resource_policy_refresh_interval_from_env,
)
from claude_agent.resource_postgres_sink import (
    ClaudeAgentResourcePostgresSink,
    ClaudeAgentResourcePublisher,
    ResourcePipelineMetrics,
)

claude_agent_resource_policy_provider = ClaudeAgentResourcePolicyProvider(database.get_db)
claude_agent_resource_policy = claude_agent_resource_policy_provider.load(
    AgentAdmissionConfig.from_env()
)
claude_agent_admission_config = claude_agent_resource_policy.config
claude_agent_resource_observer = ClaudeAgentResourceObserver()
claude_agent_admission_controller = ObservedClaudeAgentAdmissionController(
    ClaudeAgentAdmissionController(claude_agent_admission_config),
    claude_agent_resource_observer,
)
claude_agent_thread_factory = ClaudeAgentThreadFactory(
    admission_controller=claude_agent_admission_controller,
)
claude_agent_thread_factory.register_observer(claude_agent_resource_observer)
claude_agent_resource_sampler = ClaudeAgentResourceSampler()
claude_agent_resource_pipeline_metrics = ResourcePipelineMetrics()
claude_agent_resource_diagnostics = ClaudeAgentResourceDiagnostics(
    admission=claude_agent_admission_controller,
    observer=claude_agent_resource_observer,
    sampler=claude_agent_resource_sampler,
    policy=claude_agent_resource_policy,
    pipeline_snapshot=claude_agent_resource_pipeline_metrics.snapshot,
)


def _apply_claude_agent_resource_policy(result: ResourcePolicyLoadResult) -> None:
    """Apply valid limits, then publish one coherent immutable diagnostics state."""

    effective_config = claude_agent_admission_controller.config
    if result.status == "applied":
        claude_agent_admission_controller.replace_config(result.config)
        effective_config = result.config
    claude_agent_resource_diagnostics.update_policy(
        result,
        effective_config=effective_config,
    )


claude_agent_resource_policy_refresher = ClaudeAgentResourcePolicyRefresher(
    provider=claude_agent_resource_policy_provider,
    current_config=lambda: claude_agent_admission_controller.config,
    apply_result=_apply_claude_agent_resource_policy,
    initial_result=claude_agent_resource_policy,
    interval_seconds=resource_policy_refresh_interval_from_env(),
)
claude_agent_resource_postgres_sink = ClaudeAgentResourcePostgresSink(
    db_factory=database.get_db,
    metrics=claude_agent_resource_pipeline_metrics,
)
claude_agent_resource_publisher = ClaudeAgentResourcePublisher(
    snapshot_provider=claude_agent_resource_diagnostics.snapshot,
    sink=claude_agent_resource_postgres_sink,
)

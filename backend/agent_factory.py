#!/usr/bin/env python3
# [Input] Consume Claude Agent factory, public admission config/controller, and resource diagnostics nodes.
# [Output] Provide shared Agent factory, Observer, sampler, and diagnostics singletons for FastAPI composition.
# [Pos] backend Claude Agent composition root; performs no database or dynamic policy lookup.
# [Sync] 2026-08-27: inject transparent admission observation and process-local resource diagnostics.

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


claude_agent_admission_config = AgentAdmissionConfig.from_env()
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
claude_agent_resource_diagnostics = ClaudeAgentResourceDiagnostics(
    admission=claude_agent_admission_controller,
    observer=claude_agent_resource_observer,
    sampler=claude_agent_resource_sampler,
)

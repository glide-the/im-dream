# [Input] Native-owned original Runtime endpoint, original policy provider and iOS memory sampler.
# [Output] The production ThreadFactory with an in-process Runner and unchanged admission policy.
# [Pos] iOS composition owner; policy failures retain the original defaults/LKG and never enter a turn.
from __future__ import annotations

from claude_agent.admission import AgentAdmissionConfig, ClaudeAgentAdmissionController
from claude_agent.resource_policy import (
    ClaudeAgentResourcePolicyProvider, ClaudeAgentResourcePolicyRefresher,
    ClaudeCodeRuntimePolicyStore, resource_policy_refresh_interval_from_env,
)
from claude_agent.thread_factory import ClaudeAgentThreadFactory
from libs.claude_agent_kit.server.sdk_env import clear_server_claude_code_runtime_parent_env
from services.admin_data.resource_data import AdminResourceData

from .ios_claude_transport import create_agent_runner
from .ios_resources import read_ios_resource_snapshot


class IOSFactoryOwner:
    def __init__(self, endpoint: str):
        self.endpoint = endpoint
        clear_server_claude_code_runtime_parent_env()
        self.resource_data = AdminResourceData()
        provider = ClaudeAgentResourcePolicyProvider(self.resource_data.read_policy)
        self.policy = provider.load(AgentAdmissionConfig.from_env())
        self.runtime_policy = ClaudeCodeRuntimePolicyStore(self.policy)
        self.admission = ClaudeAgentAdmissionController(
            self.policy.config, snapshot_provider=read_ios_resource_snapshot,
        )
        self.factory = ClaudeAgentThreadFactory(
            admission_controller=self.admission,
            claude_code_runtime_env_provider=self.runtime_policy.snapshot_env,
            runner_factory=lambda: create_agent_runner(endpoint),
        )
        self.refresher = ClaudeAgentResourcePolicyRefresher(
            provider=provider, current_config=lambda: self.admission.config,
            apply_result=self._apply_policy, initial_result=self.policy,
            interval_seconds=resource_policy_refresh_interval_from_env(),
        )

    def _apply_policy(self, result, replace_required: bool):
        if replace_required:
            if result.status != "applied":
                raise ValueError("only an applied policy may replace admission config")
            self.admission.replace_config(result.config)
            self.runtime_policy.replace(result)
        elif result.status == "applied" and self.admission.config != result.config:
            raise ValueError("unchanged applied policy must match effective config")
        self.policy = result

    def start(self):
        self.factory.start()
        self.refresher.start()

    async def close(self):
        await self.refresher.stop()
        await self.factory.aclose()
        self.resource_data.close()

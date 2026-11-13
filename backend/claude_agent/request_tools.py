# [Input] Public Chat tool descriptors containing backend-owned types and managed connection names.
# [Output] Strict per-message platform and remote MCP selections; no connection configuration.
# [Pos] Chat ingress DTO; credentials, scope and permission decisions remain server-owned.
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field

from libs.claude_agent_kit.server.mobile_clock_audio import PlatformToolDescriptor


class ManagedMcpToolDescriptor(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    type: Literal["mcp"]
    server_name: str = Field(pattern=r"^[A-Za-z0-9][A-Za-z0-9._:-]{0,127}$")


ChatToolDescriptor = Annotated[
    PlatformToolDescriptor | ManagedMcpToolDescriptor, Field(discriminator="type")
]

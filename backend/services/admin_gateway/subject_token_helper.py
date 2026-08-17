"""Claude Code apiKeyHelper entry point for short-lived Gateway subjects."""

from __future__ import annotations

import os
import sys

from .config import AdminGatewayConfig, AdminGatewayConfigurationError
from .token import issue_gateway_subject_token


def main() -> int:
    """Print one fresh token and never expose configuration values on failure."""

    try:
        configuration = AdminGatewayConfig.from_environment()
        token = issue_gateway_subject_token(
            configuration,
            os.environ.get("INK_GATEWAY_CANONICAL_SUBJECT", ""),
        )
    except AdminGatewayConfigurationError:
        print("Gateway subject token helper is not safely configured", file=sys.stderr)
        return 1
    print(token)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

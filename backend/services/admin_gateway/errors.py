"""Safe Admin Gateway request errors shared by catalog and selection.

[Input] Stable Gateway error codes and optional HTTP status classification.
[Output] Value-free exceptions safe for logs and public API mapping.
[Pos] Shared Admin Gateway error boundary for current catalog/selection clients.
[Sync] 2026-08-31: remain the stable error contract after deleting the legacy inference adapter.
"""


class GatewayInferenceError(RuntimeError):
    """Value-free Gateway failure safe for logs and API mapping."""

    def __init__(self, code: str, status_code: int = 503) -> None:
        super().__init__(code)
        self.code = code
        self.status_code = status_code

# [Input] Existing mobile environment source text before resource copying.
# [Output] Fixed-message build failure when server tracing configuration is present.
# [Pos] Pure packaging guard; source files and ordinary mobile configuration stay intact.
import re


def validate_mobile_environment(body: str) -> None:
    if re.search(r"(?m)^[ \t]*(?:export[ \t]+)?(?:OTEL_|ARMS_|INK_TRACE_)[A-Z0-9_]*[ \t]*=", body):
        raise RuntimeError("Server tracing configuration must be outside mobile environment inputs")

# [Input] Mobile bridge requests and target qualification facts.
# [Output] Side-effect-free public imports for a future embedded-Python bootstrap.
# [Pos] Mobile Python package boundary; no production server startup occurs on import.
# [Sync] 2026-10-24: expose the qualification and protocol surface.

"""Side-effect-free qualification surface for embedded mobile Python."""

from .capabilities import PythonRuntimeFacts, probe_mobile_runtime
from .contract import BridgeRequest, MobileBridgeProtocolError
from .runtime import MobileRuntime, MobileRuntimeUnavailable

__all__ = [
    "BridgeRequest",
    "MobileBridgeProtocolError",
    "MobileRuntime",
    "PythonRuntimeFacts",
    "MobileRuntimeUnavailable",
    "probe_mobile_runtime",
]

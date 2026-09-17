# [Input] One Admin-issued gateway-cli grant and the public Runtime delegation client.
# [Output] Turn-owned renewal lifecycle plus a current opaque bearer snapshot.
# [Pos] Dream Runtime authorization owner; no service key, signer or database access.
# [Sync] 2026-09-16: introduce the Admin delegation owner for Gateway model execution.
from __future__ import annotations

from threading import Lock

from .delegation import AdminRuntimeClient, RuntimeGrant
from .delegation_keeper import RuntimeGrantKeeper


class AdminGatewayRuntime:
    """Own one renewable entity credential for an Agent turn."""

    def __init__(self, grant: RuntimeGrant, client: AdminRuntimeClient) -> None:
        self._client = client
        self._keeper = RuntimeGrantKeeper(grant, client)
        self._closed = False
        self._lock = Lock()

    def start(self) -> None:
        with self._lock:
            if self._closed:
                return
            self._keeper.start()

    def access_token(self) -> str:
        return self._keeper.current("gateway-cli").token

    def close(self) -> None:
        with self._lock:
            if self._closed:
                return
            self._closed = True
        try:
            self._keeper.close()
        finally:
            self._client.close()

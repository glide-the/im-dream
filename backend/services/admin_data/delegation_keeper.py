# [Input] Immutable purpose grant, bearer-only Runtime client and explicit clock/scheduling settings.
# [Output] Server-owned expiry renewal and original-ID recovery without propagating background failures.
# [Pos] Authorization lifecycle owner; does not modify Agent leases, runtime, SSE or cancellation.
# [Sync] 2026-09-14: renew before expiry, preserve maximum lifetime and never replay an absent receipt.
"""Keep one opaque grant alive while its bounded Admin authorization permits it."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import math
import threading
from typing import Callable
from uuid import uuid4

from .delegation import AdminRuntimeClient, RuntimeGrant
from .errors import AdminDataError, configuration_invalid
from .models import CommittedReceiptDTO


@dataclass(frozen=True)
class RuntimeRenewalSettings:
    advance_fraction: float = 0.5
    check_interval_seconds: float = 5.0

    def __post_init__(self):
        if (not math.isfinite(self.advance_fraction) or not 0 < self.advance_fraction < 1
            or not math.isfinite(self.check_interval_seconds) or self.check_interval_seconds <= 0):
            raise configuration_invalid()


@dataclass(frozen=True)
class RuntimeGrantDiagnostics:
    pending_request_id: str | None
    last_error_code: str | None
    expired: bool
    stopped: bool


class RuntimeGrantKeeper:
    def __init__(self, grant: RuntimeGrant, client: AdminRuntimeClient, *,
        settings: RuntimeRenewalSettings | None = None,
        clock: Callable[[], datetime] | None = None,
        request_id_factory: Callable[[], str] | None = None):
        self._grant = grant
        self._client = client
        self._settings = settings or RuntimeRenewalSettings()
        self._clock = clock or (lambda: datetime.now(timezone.utc))
        self._request_id_factory = request_id_factory or (lambda: str(uuid4()))
        self._pending_request_id: str | None = None
        self._last_error: str | None = None
        self._lock = threading.RLock()
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None
        self._renew_at = self._deadline(self._clock())

    def _deadline(self, now: datetime) -> datetime:
        if self._grant.expires_at == self._grant.maximum_expires_at:
            return self._grant.maximum_expires_at
        remaining = self._grant.expires_at - now
        return now + remaining * (1 - self._settings.advance_fraction)

    def current(self, purpose: str) -> RuntimeGrant:
        with self._lock:
            if purpose != self._grant.purpose:
                raise AdminDataError("DELEGATION_PURPOSE_MISMATCH", 403)
            if self._stop.is_set() or self._clock() >= self._grant.expires_at:
                raise AdminDataError("DELEGATION_EXPIRED", 401)
            return self._grant

    def diagnostics(self) -> RuntimeGrantDiagnostics:
        with self._lock:
            return RuntimeGrantDiagnostics(self._pending_request_id, self._last_error,
                self._clock() >= self._grant.expires_at, self._stop.is_set())

    def tick(self) -> None:
        # Serialize actions and close. Unknown writes retain one ID; receipt
        # recovery stays possible after expiry but cannot extend maximum life.
        with self._lock:
            if self._stop.is_set():
                return
            now = self._clock()
            try:
                if self._pending_request_id is not None:
                    result = self._client.receipt(self._grant, "runtime-delegation.renew", self._pending_request_id)
                    if isinstance(result, CommittedReceiptDTO):
                        self._grant = self._grant.with_renewal(result.result, self._pending_request_id)
                        self._pending_request_id = None
                        self._last_error = None
                        self._renew_at = self._deadline(now)
                    return
                if now >= self._grant.expires_at or now >= self._grant.maximum_expires_at:
                    self._last_error = "DELEGATION_EXPIRED"
                    return
                if now < self._renew_at:
                    return
                request_id = self._request_id_factory()
                self._pending_request_id = request_id
                try:
                    self._grant = self._client.renew(self._grant, request_id)
                except AdminDataError as error:
                    if not error.outcome_unknown:
                        self._pending_request_id = None
                    raise
                self._pending_request_id = None
                self._last_error = None
                self._renew_at = self._deadline(now)
            except AdminDataError as error:
                self._last_error = error.code
            except Exception:
                # Diagnostics contain a closed local code, never exception text.
                self._last_error = "DELEGATION_BACKGROUND_FAILURE"

    def start(self) -> None:
        with self._lock:
            if self._stop.is_set() or self._thread is not None:
                return
            self._thread = threading.Thread(target=self._run,
                name="dream-runtime-grant-renewal", daemon=True)
            self._thread.start()

    def _run(self) -> None:
        while not self._stop.wait(self._settings.check_interval_seconds):
            self.tick()

    def close(self) -> None:
        self._stop.set()
        thread = self._thread
        if thread is not None and thread is not threading.current_thread():
            thread.join()

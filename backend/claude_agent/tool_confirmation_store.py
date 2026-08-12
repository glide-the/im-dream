# [Input] Trusted SDK confirmation payloads and authenticated decisions for one Agent turn.
# [Output] Bounded server-owned policy + Future registration and exact atomic resolution.
# [Pos] Canonical confirmation authority below ClaudeAgentService.

"""Bounded per-turn tool-confirmation authority.

The browser submits only ``thread_id``, ``tool_call_id`` and a decision.  The
active ``turn_id`` and every validation rule come from server state.  A policy
and its Future are registered atomically before the approval frame is visible,
which closes both the fast-client race and the former Dream-only policy gap.
"""

from __future__ import annotations

import asyncio
import concurrent.futures
import hashlib
import json
import logging
import math
import re
import threading
import time
from collections import OrderedDict
from dataclasses import dataclass
from typing import Any, Literal, Optional

logger = logging.getLogger(__name__)

DEFAULT_TIMEOUT_S: float = 5.0 * 60.0
MAX_PENDING_CONFIRMATIONS = 256
MAX_SETTLED_CONFIRMATIONS = 256
SETTLED_CONFIRMATION_TTL_S = DEFAULT_TIMEOUT_S
MAX_TOOL_CALL_ID_LENGTH = 255
MAX_TOOL_NAME_LENGTH = 120
MAX_REASON_LENGTH = 500
MAX_ANSWERS = 20
MAX_ANSWERS_BYTES = 8 * 1024
MAX_QUESTIONS = 8
MAX_OPTIONS = 12
MAX_QUESTION_TEXT_LENGTH = 300
MAX_OPTION_TEXT_LENGTH = 120
MAX_ANSWER_TEXT_LENGTH = 1000
MAX_NETWORK_HOST_LENGTH = 253

ConfirmationKind = Literal[
    "approval",
    "ask_user",
    "sandbox_network",
    "reject_only",
]

_ASK_USER_TOOL_NAMES = frozenset(
    {"askuserquestion", "ask_user_question", "ask_user", "askuser"}
)
_QUESTION_TYPES = frozenset(
    {"text", "textarea", "select", "checkbox", "radio", "number"}
)
_NETWORK_POLICY_MODES = frozenset({"allowlist", "open", "deny", "unknown"})
_SAFE_NETWORK_HOST = re.compile(
    r"^(?:[A-Za-z0-9](?:[A-Za-z0-9.-]{0,251}[A-Za-z0-9])?|[A-Fa-f0-9:]+)(?::[0-9]{1,5})?$"
)


class ToolConfirmationError(RuntimeError):
    """Base typed failure for the canonical confirmation endpoint."""

    code = "TOOL_CONFIRMATION_ERROR"
    status_code = 409

    def __init__(self, message: str | None = None) -> None:
        super().__init__(message or self.code)


class ToolConfirmationNotPending(ToolConfirmationError):
    code = "TOOL_CONFIRMATION_NOT_PENDING"
    status_code = 409


class ToolConfirmationPolicyConflict(ToolConfirmationError):
    code = "TOOL_CONFIRMATION_POLICY_CONFLICT"
    status_code = 409


class ToolConfirmationCapacityExceeded(ToolConfirmationError):
    code = "TOOL_CONFIRMATION_CAPACITY_EXCEEDED"
    status_code = 503


class ToolConfirmationInvalidDecision(ToolConfirmationError):
    code = "TOOL_CONFIRMATION_INVALID"
    status_code = 422


@dataclass(frozen=True)
class ToolConfirmationIdentity:
    thread_id: str
    turn_id: str
    tool_call_id: str


@dataclass(frozen=True)
class AskUserQuestionPolicy:
    client_id: str
    runner_key: str
    question_type: str
    required: bool
    allowed_options: tuple[str, ...] = ()
    multi_select: bool = False


@dataclass(frozen=True)
class ToolConfirmationPolicy:
    """Immutable server-derived validation policy for one SDK callback."""

    identity: ToolConfirmationIdentity
    tool_name: str
    kind: ConfirmationKind
    input_fingerprint: str = ""
    questions: tuple[AskUserQuestionPolicy, ...] = ()
    network_host: str | None = None
    network_policy: str | None = None

    @property
    def fingerprint(self) -> str:
        payload = {
            "identity": self.identity.__dict__,
            "tool_name": self.tool_name,
            "kind": self.kind,
            "input_fingerprint": self.input_fingerprint,
            "questions": [question.__dict__ for question in self.questions],
            "network_host": self.network_host,
            "network_policy": self.network_policy,
        }
        encoded = json.dumps(
            payload,
            ensure_ascii=False,
            allow_nan=False,
            separators=(",", ":"),
            sort_keys=True,
        ).encode("utf-8")
        return hashlib.sha256(encoded).hexdigest()


@dataclass(frozen=True)
class ToolConfirmationResult:
    """Validated decision returned to ``agent_runner``."""

    approved: bool
    reason: Optional[str] = None
    answers: Optional[dict[str, Any]] = None


@dataclass(frozen=True)
class ToolConfirmationResolution:
    """Atomic resolution result returned to the HTTP/factory boundary."""

    result: ToolConfirmationResult
    replayed: bool = False


@dataclass
class _PendingRecord:
    policy: ToolConfirmationPolicy
    future: asyncio.Future[ToolConfirmationResult]
    owner_loop: asyncio.AbstractEventLoop
    state: Literal["pending", "settling"] = "pending"
    result: ToolConfirmationResult | None = None
    settle_ack: concurrent.futures.Future[None] | None = None


@dataclass(frozen=True)
class _SettledRecord:
    result: ToolConfirmationResult
    settled_at: float


def _is_ask_user_tool(tool_name: str) -> bool:
    normalized = tool_name.lower()
    return (
        normalized in _ASK_USER_TOOL_NAMES
        or normalized.endswith("__ask_user")
        or normalized.endswith("__askuserquestion")
    )


def _input_fingerprint(value: object) -> str:
    try:
        encoded = json.dumps(
            value,
            ensure_ascii=False,
            allow_nan=False,
            separators=(",", ":"),
            sort_keys=True,
        ).encode("utf-8")
    except (TypeError, ValueError) as exc:
        raise ToolConfirmationPolicyConflict("tool input is not JSON-safe") from exc
    return hashlib.sha256(encoded).hexdigest()


def _bounded_text(value: object, *, maximum: int) -> str | None:
    if not isinstance(value, str):
        return None
    normalized = value.strip()
    if not normalized or len(normalized) > maximum:
        return None
    return normalized


def _question_options(value: object) -> tuple[str, ...] | None:
    if value is None:
        return ()
    if not isinstance(value, list) or len(value) > MAX_OPTIONS:
        return None
    options: list[str] = []
    for option in value:
        candidate: object
        if isinstance(option, dict):
            candidate = option.get("value") or option.get("label")
        else:
            candidate = option
        text = _bounded_text(candidate, maximum=MAX_OPTION_TEXT_LENGTH)
        if text is None or text in options:
            return None
        options.append(text)
    return tuple(options)


def _ask_user_policy(tool_input: object) -> tuple[AskUserQuestionPolicy, ...] | None:
    if not isinstance(tool_input, dict):
        return None
    raw_questions = tool_input.get("questions")
    if not isinstance(raw_questions, list) or not raw_questions:
        raw_questions = [
            {
                "question": (
                    tool_input.get("question")
                    or tool_input.get("message")
                    or tool_input.get("text")
                    or tool_input.get("prompt")
                ),
                "options": tool_input.get("options") or tool_input.get("choices"),
                "type": tool_input.get("type"),
                "required": tool_input.get("required"),
                "multiSelect": tool_input.get("multiSelect"),
            }
        ]
    if not raw_questions or len(raw_questions) > MAX_QUESTIONS:
        return None

    questions: list[AskUserQuestionPolicy] = []
    runner_keys: set[str] = set()
    for index, raw in enumerate(raw_questions):
        if not isinstance(raw, dict):
            return None
        runner_key = _bounded_text(
            raw.get("question") or raw.get("label") or raw.get("header"),
            maximum=MAX_QUESTION_TEXT_LENGTH,
        )
        if runner_key is None or runner_key in runner_keys:
            return None
        runner_keys.add(runner_key)
        options = _question_options(raw.get("options"))
        if options is None:
            return None
        raw_type = raw.get("type")
        question_type = (
            raw_type
            if raw_type in _QUESTION_TYPES
            else "radio" if options else "text"
        )
        multi_select = raw.get("multiSelect") is True
        if (question_type in {"select", "radio"} or multi_select) and not options:
            return None
        questions.append(
            AskUserQuestionPolicy(
                client_id=f"q{index}",
                runner_key=runner_key,
                question_type=question_type,
                required=(raw.get("required") if isinstance(raw.get("required"), bool) else True),
                allowed_options=options,
                multi_select=multi_select,
            )
        )
    return tuple(questions)


class ToolConfirmationStore:
    """Thread-safe, per-turn store for immutable policies and owner-loop Futures."""

    # The per-turn bound prevents one callback stream from exhausting memory;
    # this process-wide bound also prevents many concurrent turns from each
    # allocating the full allowance.  Every mutation takes this lock before a
    # store's lock so cancellation and settlement cannot deadlock registration.
    _process_capacity_guard = threading.Lock()
    _process_pending = 0

    def __init__(
        self,
        *,
        thread_id: str = "",
        turn_id: str = "",
        max_pending: int = MAX_PENDING_CONFIRMATIONS,
        max_settled: int = MAX_SETTLED_CONFIRMATIONS,
    ) -> None:
        self.thread_id = thread_id
        self.turn_id = turn_id
        self._max_pending = max(1, min(int(max_pending), MAX_PENDING_CONFIRMATIONS))
        self._max_settled = max(1, min(int(max_settled), MAX_SETTLED_CONFIRMATIONS))
        self._pending: dict[ToolConfirmationIdentity, _PendingRecord] = {}
        self._settled: OrderedDict[ToolConfirmationIdentity, _SettledRecord] = OrderedDict()
        self._guard = threading.Lock()

    def policy_from_payload(self, payload: dict[str, Any]) -> ToolConfirmationPolicy:
        """Derive a bounded immutable policy solely from the trusted callback."""

        tool_call_id = payload.get("tool_call_id") or payload.get("toolCallId")
        tool_name = payload.get("tool_name") or payload.get("toolName")
        if (
            not isinstance(tool_call_id, str)
            or not tool_call_id
            or len(tool_call_id) > MAX_TOOL_CALL_ID_LENGTH
            or not isinstance(tool_name, str)
            or not tool_name
            or len(tool_name) > MAX_TOOL_NAME_LENGTH
        ):
            raise ToolConfirmationPolicyConflict("invalid callback identity")

        identity = self._identity(tool_call_id)
        input_fingerprint = _input_fingerprint(payload.get("input") or {})
        confirmation_kind = payload.get("confirmationKind")
        if confirmation_kind == "reject_only":
            return ToolConfirmationPolicy(
                identity,
                tool_name,
                "reject_only",
                input_fingerprint=input_fingerprint,
            )

        if confirmation_kind == "sandbox_network":
            network = payload.get("networkRequest")
            network = network if isinstance(network, dict) else {}
            host = network.get("host")
            policy_mode = network.get("policyMode")
            valid_host = (
                isinstance(host, str)
                and 0 < len(host) <= MAX_NETWORK_HOST_LENGTH
                and _SAFE_NETWORK_HOST.fullmatch(host) is not None
            )
            normalized_policy = (
                policy_mode if policy_mode in _NETWORK_POLICY_MODES else "unknown"
            )
            if not valid_host:
                return ToolConfirmationPolicy(
                    identity,
                    tool_name,
                    "reject_only",
                    input_fingerprint=input_fingerprint,
                )
            return ToolConfirmationPolicy(
                identity,
                tool_name,
                "sandbox_network",
                input_fingerprint=input_fingerprint,
                network_host=host.lower(),
                network_policy=normalized_policy,
            )

        if _is_ask_user_tool(tool_name):
            questions = _ask_user_policy(payload.get("input"))
            if questions is None:
                return ToolConfirmationPolicy(
                    identity,
                    tool_name,
                    "reject_only",
                    input_fingerprint=input_fingerprint,
                )
            return ToolConfirmationPolicy(
                identity,
                tool_name,
                "ask_user",
                input_fingerprint=input_fingerprint,
                questions=questions,
            )
        return ToolConfirmationPolicy(
            identity,
            tool_name,
            "approval",
            input_fingerprint=input_fingerprint,
        )

    def register_pending(self, policy: ToolConfirmationPolicy) -> bool:
        """Atomically create policy+Future; return False for an identical join."""

        self._require_store_identity(policy.identity)
        loop = asyncio.get_running_loop()
        with ToolConfirmationStore._process_capacity_guard:
            with self._guard:
                self._purge_expired_settled_locked()
                existing = self._pending.get(policy.identity)
                if existing is not None:
                    if existing.policy.fingerprint != policy.fingerprint:
                        raise ToolConfirmationPolicyConflict(
                            "duplicate callback policy mismatch"
                        )
                    return False
                if policy.identity in self._settled:
                    raise ToolConfirmationPolicyConflict(
                        "callback repeated after settlement"
                    )
                if (
                    len(self._pending) >= self._max_pending
                    or ToolConfirmationStore._process_pending
                    >= MAX_PENDING_CONFIRMATIONS
                ):
                    raise ToolConfirmationCapacityExceeded()
                self._pending[policy.identity] = _PendingRecord(
                    policy=policy,
                    future=loop.create_future(),
                    owner_loop=loop,
                )
                ToolConfirmationStore._process_pending += 1
        logger.debug(
            "Registered pending tool confirmation: thread_id=%s turn_id=%s tool_call_id=%s",
            policy.identity.thread_id,
            policy.identity.turn_id,
            policy.identity.tool_call_id,
        )
        return True

    async def await_pending(
        self,
        tool_call_id: str,
        *,
        tool_name: str = "",
        timeout_s: float = DEFAULT_TIMEOUT_S,
    ) -> ToolConfirmationResult:
        identity = self._identity(tool_call_id)
        with self._guard:
            self._purge_expired_settled_locked()
            settled = self._settled.get(identity)
            record = self._pending.get(identity)
        if settled is not None:
            return settled.result
        if record is None:
            raise RuntimeError(
                f"await_pending: no registration for tool_call_id={tool_call_id}"
            )
        try:
            return await asyncio.wait_for(
                asyncio.shield(record.future),
                timeout=timeout_s,
            )
        except asyncio.TimeoutError:
            logger.warning(
                "Tool confirmation timeout: tool_call_id=%s tool_name=%s",
                tool_call_id,
                tool_name,
            )
            self.cancel_pending(tool_call_id)
            raise TimeoutError(
                f"Tool confirmation timeout for tool_call_id={tool_call_id}"
            )
        except asyncio.CancelledError:
            self.cancel_pending(tool_call_id)
            raise

    async def resolve_exact(
        self,
        *,
        thread_id: str,
        turn_id: str,
        tool_call_id: str,
        result: ToolConfirmationResult,
    ) -> ToolConfirmationResolution:
        """Validate, compare-and-set once, and await actual owner-loop settle."""

        identity = ToolConfirmationIdentity(thread_id, turn_id, tool_call_id)
        self._require_store_identity(identity)
        with self._guard:
            self._purge_expired_settled_locked()
            settled = self._settled.get(identity)
            if settled is not None:
                self._settled.move_to_end(identity)
                return ToolConfirmationResolution(settled.result, replayed=True)
            record = self._pending.get(identity)
            if record is None:
                raise ToolConfirmationNotPending()

            validated = self._validate_result(record.policy, result)
            if record.state == "pending":
                record.state = "settling"
                record.result = validated
                record.settle_ack = concurrent.futures.Future()
                winner = True
            else:
                winner = False
            ack = record.settle_ack
            stable_result = record.result

        if winner:
            self._schedule_result(record, identity, validated)
        assert ack is not None and stable_result is not None
        # Each HTTP resolver owns only its local waiter.  Cancelling one request
        # must not cancel the shared settlement acknowledgement needed by other
        # concurrent resolvers or the owner-loop callback.
        await asyncio.shield(asyncio.wrap_future(ack))
        return ToolConfirmationResolution(stable_result, replayed=not winner)

    def cancel_pending(self, tool_call_id: str) -> bool:
        identity = self._identity(tool_call_id)
        with ToolConfirmationStore._process_capacity_guard:
            with self._guard:
                record = self._pending.pop(identity, None)
                if record is not None:
                    ToolConfirmationStore._process_pending -= 1
        if record is None:
            return False
        self._schedule_cancel(record)
        return True

    def cancel_all(self) -> int:
        """Cancel every waiter and remove policy/tombstones for turn teardown."""

        with ToolConfirmationStore._process_capacity_guard:
            with self._guard:
                records = tuple(self._pending.values())
                self._pending.clear()
                self._settled.clear()
                ToolConfirmationStore._process_pending -= len(records)
        for record in records:
            self._schedule_cancel(record)
        return len(records)

    def has_pending(self, tool_call_id: str) -> bool:
        identity = self._identity(tool_call_id)
        with self._guard:
            return identity in self._pending

    def pending_ids(self) -> list[str]:
        with self._guard:
            return [identity.tool_call_id for identity in self._pending]

    def policy_for(self, tool_call_id: str) -> ToolConfirmationPolicy | None:
        """Return immutable policy for service-side approval frame shaping."""

        identity = self._identity(tool_call_id)
        with self._guard:
            record = self._pending.get(identity)
            return record.policy if record is not None else None

    def _identity(self, tool_call_id: str) -> ToolConfirmationIdentity:
        if (
            not isinstance(tool_call_id, str)
            or not tool_call_id
            or len(tool_call_id) > MAX_TOOL_CALL_ID_LENGTH
        ):
            raise ToolConfirmationPolicyConflict("invalid tool call id")
        return ToolConfirmationIdentity(self.thread_id, self.turn_id, tool_call_id)

    def _require_store_identity(self, identity: ToolConfirmationIdentity) -> None:
        if identity.thread_id != self.thread_id or identity.turn_id != self.turn_id:
            raise ToolConfirmationNotPending("active turn changed")

    @classmethod
    def _validate_result(
        cls,
        policy: ToolConfirmationPolicy,
        result: ToolConfirmationResult,
    ) -> ToolConfirmationResult:
        if not isinstance(result.approved, bool):
            raise ToolConfirmationInvalidDecision("approved must be boolean")
        if result.reason is not None and (
            not isinstance(result.reason, str)
            or len(result.reason) > MAX_REASON_LENGTH
        ):
            raise ToolConfirmationInvalidDecision("reason exceeds bound")
        answers = result.answers
        if answers is not None:
            if not isinstance(answers, dict) or len(answers) > MAX_ANSWERS:
                raise ToolConfirmationInvalidDecision("answers exceed bound")
            try:
                encoded = json.dumps(
                    answers,
                    ensure_ascii=False,
                    allow_nan=False,
                    separators=(",", ":"),
                    sort_keys=True,
                ).encode("utf-8")
            except (TypeError, ValueError) as exc:
                raise ToolConfirmationInvalidDecision("answers are not JSON-safe") from exc
            if len(encoded) > MAX_ANSWERS_BYTES:
                raise ToolConfirmationInvalidDecision("answers exceed byte bound")

        if not result.approved:
            if answers:
                raise ToolConfirmationInvalidDecision("rejection cannot include answers")
            return ToolConfirmationResult(False, result.reason, None)
        if policy.kind == "reject_only":
            raise ToolConfirmationInvalidDecision("policy is reject-only")
        if policy.kind == "sandbox_network" and policy.network_policy in {
            "deny",
            "unknown",
        }:
            raise ToolConfirmationInvalidDecision("network policy cannot approve")
        if policy.kind != "ask_user":
            if answers:
                raise ToolConfirmationInvalidDecision("answers are not allowed")
            return ToolConfirmationResult(True, result.reason, None)

        source = answers or {}
        by_client_id = {question.client_id: question for question in policy.questions}
        by_runner_key = {question.runner_key: question for question in policy.questions}
        mapped: dict[str, Any] = {}
        seen_questions: set[str] = set()
        for key, value in source.items():
            if not isinstance(key, str):
                raise ToolConfirmationInvalidDecision("answer key must be text")
            question = by_client_id.get(key) or by_runner_key.get(key)
            if question is None or question.client_id in seen_questions:
                raise ToolConfirmationInvalidDecision("unknown or duplicate answer")
            seen_questions.add(question.client_id)
            mapped[question.runner_key] = cls._validate_answer(question, value)
        for question in policy.questions:
            if question.required and question.client_id not in seen_questions:
                raise ToolConfirmationInvalidDecision("required answer missing")
        return ToolConfirmationResult(True, result.reason, mapped or None)

    @staticmethod
    def _validate_answer(question: AskUserQuestionPolicy, value: Any) -> Any:
        if question.multi_select:
            if (
                not isinstance(value, list)
                or not value
                or any(not isinstance(item, str) for item in value)
                or len(value) != len(set(value))
                or any(item not in question.allowed_options for item in value)
            ):
                raise ToolConfirmationInvalidDecision("invalid multi-select answer")
            return value
        if question.allowed_options:
            if not isinstance(value, str) or value not in question.allowed_options:
                raise ToolConfirmationInvalidDecision("invalid option answer")
            return value
        if question.question_type == "checkbox":
            if not isinstance(value, bool):
                raise ToolConfirmationInvalidDecision("invalid checkbox answer")
            return value
        if question.question_type == "number":
            if (
                isinstance(value, bool)
                or not isinstance(value, (int, float))
                or not math.isfinite(float(value))
            ):
                raise ToolConfirmationInvalidDecision("invalid number answer")
            return value
        if (
            not isinstance(value, str)
            or len(value) > MAX_ANSWER_TEXT_LENGTH
            or (question.required and not value.strip())
        ):
            raise ToolConfirmationInvalidDecision("invalid text answer")
        return value

    def _schedule_result(
        self,
        record: _PendingRecord,
        identity: ToolConfirmationIdentity,
        result: ToolConfirmationResult,
    ) -> None:
        def settle() -> None:
            try:
                if not record.future.done():
                    record.future.set_result(result)
                self._finish_settlement(identity, record, result)
                if record.settle_ack is not None and not record.settle_ack.done():
                    record.settle_ack.set_result(None)
            except BaseException as exc:  # pragma: no cover - defensive loop edge
                if record.settle_ack is not None and not record.settle_ack.done():
                    record.settle_ack.set_exception(exc)

        if self._running_loop_or_none() is record.owner_loop:
            settle()
            return
        try:
            record.owner_loop.call_soon_threadsafe(settle)
        except RuntimeError as exc:
            if record.settle_ack is not None and not record.settle_ack.done():
                record.settle_ack.set_exception(exc)

    def _finish_settlement(
        self,
        identity: ToolConfirmationIdentity,
        record: _PendingRecord,
        result: ToolConfirmationResult,
    ) -> None:
        with ToolConfirmationStore._process_capacity_guard:
            with self._guard:
                if self._pending.get(identity) is record:
                    self._pending.pop(identity, None)
                    ToolConfirmationStore._process_pending -= 1
                    self._settled[identity] = _SettledRecord(
                        result,
                        settled_at=time.monotonic(),
                    )
                    self._settled.move_to_end(identity)
                    self._purge_expired_settled_locked()
                    while len(self._settled) > self._max_settled:
                        self._settled.popitem(last=False)

    def _purge_expired_settled_locked(self) -> None:
        """Discard replay tombstones after the bounded retry window."""

        cutoff = time.monotonic() - SETTLED_CONFIRMATION_TTL_S
        expired = [
            identity
            for identity, record in self._settled.items()
            if record.settled_at <= cutoff
        ]
        for identity in expired:
            self._settled.pop(identity, None)

    def _schedule_cancel(self, record: _PendingRecord) -> None:
        def cancel() -> None:
            if not record.future.done():
                record.future.cancel()
            if record.settle_ack is not None and not record.settle_ack.done():
                record.settle_ack.cancel()

        if self._running_loop_or_none() is record.owner_loop:
            cancel()
            return
        try:
            record.owner_loop.call_soon_threadsafe(cancel)
        except RuntimeError:
            pass

    @staticmethod
    def _running_loop_or_none() -> Optional[asyncio.AbstractEventLoop]:
        try:
            return asyncio.get_running_loop()
        except RuntimeError:
            return None


__all__ = [
    "AskUserQuestionPolicy",
    "MAX_PENDING_CONFIRMATIONS",
    "SETTLED_CONFIRMATION_TTL_S",
    "ToolConfirmationCapacityExceeded",
    "ToolConfirmationError",
    "ToolConfirmationIdentity",
    "ToolConfirmationInvalidDecision",
    "ToolConfirmationNotPending",
    "ToolConfirmationPolicy",
    "ToolConfirmationPolicyConflict",
    "ToolConfirmationResolution",
    "ToolConfirmationResult",
    "ToolConfirmationStore",
]

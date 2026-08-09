"""Strict Token-only request and response contracts for the Product BFF."""

from __future__ import annotations

from datetime import datetime
from typing import Annotated, Literal, Union

from pydantic import (
    BaseModel,
    AfterValidator,
    ConfigDict,
    Field,
    StringConstraints,
    TypeAdapter,
    model_validator,
)


MAX_SAFE_INTEGER = 9_007_199_254_740_991
NonNegativeInteger = Annotated[int, Field(ge=0, le=MAX_SAFE_INTEGER)]
PositiveInteger = Annotated[int, Field(ge=1, le=MAX_SAFE_INTEGER)]
SafeText = Annotated[str, StringConstraints(min_length=1, max_length=4_000)]
SafeIdentifier = Annotated[
    str,
    StringConstraints(
        min_length=1,
        max_length=200,
        pattern=r"^[A-Za-z0-9][A-Za-z0-9._:-]*$",
    ),
]


def _validate_iso_timestamp(value: str) -> str:
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except (TypeError, ValueError):
        raise ValueError("timestamp must be ISO-8601 with an offset") from None
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise ValueError("timestamp must include an offset")
    return value


IsoTimestamp = Annotated[
    str,
    StringConstraints(min_length=20, max_length=64),
    AfterValidator(_validate_iso_timestamp),
]

ProductAction = Literal[
    "create",
    "renew",
    "upgrade",
    "downgrade",
    "pause",
    "resume",
    "cancel",
    "revoke_cancel",
]


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)


class QueryModel(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=False)


class EmptyQuery(QueryModel):
    pass


class PlansQuery(QueryModel):
    page: Annotated[int, Field(ge=1, le=1_000_000)] = 1
    pageSize: Annotated[int, Field(ge=1, le=100)] = 20


class UsageQuery(QueryModel):
    period: Literal["current_subscription_period"] = "current_subscription_period"
    outcome: Literal["completed", "failed", "cancelled", "in_progress"] | None = None
    modelAlias: Annotated[
        str,
        StringConstraints(
            min_length=1,
            max_length=120,
            pattern=r"^[A-Za-z0-9][A-Za-z0-9._:-]*$",
        ),
    ] | None = None
    gatewayScope: Literal["messages:create", "chat:create", "models:list"] | None = None
    settlementState: Literal[
        "settled", "usage_unknown", "in_progress", "rejected"
    ] | None = None
    sort: Literal["occurredAt", "totalTokens", "modelAlias", "outcome"] = (
        "occurredAt"
    )
    order: Literal["asc", "desc"] = "desc"
    page: Annotated[int, Field(ge=1, le=1_000_000)] = 1
    pageSize: Annotated[int, Field(ge=1, le=100)] = 25


TargetPlanVersionId = Annotated[
    str,
    StringConstraints(
        min_length=1,
        max_length=100,
        pattern=r"^[A-Za-z0-9][A-Za-z0-9._:-]*$",
    ),
]


def _validate_command_target(
    action: ProductAction,
    target_plan_version_id: str | None,
    expected_version: int | None,
) -> None:
    requires_target = action in {"create", "upgrade", "downgrade"}
    if requires_target != (target_plan_version_id is not None):
        raise ValueError("targetPlanVersionId does not match the action")
    if action == "create":
        if expected_version is not None:
            raise ValueError("expectedVersion must be null for create")
    elif expected_version is None:
        raise ValueError("expectedVersion is required for this action")


class PreviewSubscriptionCommand(StrictModel):
    action: ProductAction
    phase: Literal["preview"]
    targetPlanVersionId: TargetPlanVersionId | None = None
    expectedVersion: Annotated[int, Field(ge=1, le=2_147_483_647)] | None = None

    @model_validator(mode="after")
    def validate_action_contract(self) -> "PreviewSubscriptionCommand":
        _validate_command_target(
            self.action, self.targetPlanVersionId, self.expectedVersion
        )
        return self


class ExecuteSubscriptionCommand(StrictModel):
    action: ProductAction
    phase: Literal["execute"]
    targetPlanVersionId: TargetPlanVersionId | None = None
    expectedVersion: Annotated[int, Field(ge=1, le=2_147_483_647)] | None = None
    previewId: Annotated[str, Field(pattern=r"^preview_[A-Za-z0-9_-]{22}$")]
    digest: Annotated[str, Field(pattern=r"^sha256:[A-Za-z0-9_-]{43}$")]
    expiresAt: IsoTimestamp
    reason: Annotated[str, StringConstraints(strip_whitespace=True, min_length=3, max_length=500)]

    @model_validator(mode="after")
    def validate_action_contract(self) -> "ExecuteSubscriptionCommand":
        _validate_command_target(
            self.action, self.targetPlanVersionId, self.expectedVersion
        )
        return self


SubscriptionCommand = Annotated[
    Union[PreviewSubscriptionCommand, ExecuteSubscriptionCommand],
    Field(discriminator="phase"),
]
subscription_command_adapter = TypeAdapter(SubscriptionCommand)


class ProductEntitlement(StrictModel):
    gatewayScopes: list[SafeIdentifier]
    modelAliases: list[SafeIdentifier]
    rpmLimit: NonNegativeInteger | None
    dailyTokenLimit: NonNegativeInteger | None
    storageBytes: NonNegativeInteger | None


class PlanSummary(StrictModel):
    planCode: SafeIdentifier
    planName: Annotated[str, StringConstraints(min_length=1, max_length=160)]
    planVersionId: SafeIdentifier
    version: NonNegativeInteger
    billingCycle: Literal["monthly"]
    monthlyAllowanceTokens: NonNegativeInteger
    monthlyPriceMicrousd: NonNegativeInteger
    currency: Literal["USD"]


class PlanEligibility(StrictModel):
    eligible: bool
    reasonCode: SafeIdentifier | None
    appliesAt: IsoTimestamp | None


class ProductPlan(PlanSummary):
    description: SafeText | None
    entitlements: list[ProductEntitlement]
    eligibility: PlanEligibility
    availableActions: list[ProductAction]


class Allowance(StrictModel):
    unit: Literal["tokens"]
    granted: NonNegativeInteger
    reserved: NonNegativeInteger
    consumed: NonNegativeInteger
    remaining: NonNegativeInteger
    resetsAt: IsoTimestamp

    @model_validator(mode="after")
    def validate_conservation(self) -> "Allowance":
        if self.granted != self.reserved + self.consumed + self.remaining:
            raise ValueError("Token allowance conservation failed")
        return self


class PendingChange(PlanSummary):
    appliesAt: IsoTimestamp


class Subscription(StrictModel):
    id: SafeIdentifier
    status: Literal[
        "trial",
        "active",
        "past_due",
        "paused",
        "cancel_at_period_end",
        "cancelled",
        "expired",
        "legacyUnavailable",
    ]
    version: PositiveInteger
    cycleAnchorAt: IsoTimestamp
    currentPeriodNumber: NonNegativeInteger
    currentPeriodStart: IsoTimestamp
    currentPeriodEnd: IsoTimestamp
    renewalEnabled: bool
    cancelAtPeriodEnd: bool
    pendingChange: PendingChange | None
    allowedActions: list[ProductAction]


class CanonicalUser(StrictModel):
    id: SafeIdentifier


class ContextEntitlement(StrictModel):
    gatewayScope: SafeIdentifier
    modelAliases: list[SafeIdentifier]
    rpmLimit: NonNegativeInteger | None
    dailyTokenLimit: NonNegativeInteger | None
    storageBytes: NonNegativeInteger | None


class SubscriptionContext(StrictModel):
    canonicalUser: CanonicalUser
    subscription: Subscription | None
    planVersion: PlanSummary | None
    entitlements: list[ContextEntitlement]
    allowance: Allowance | None
    asOf: IsoTimestamp


class UsagePeriod(StrictModel):
    start: IsoTimestamp
    end: IsoTimestamp
    timezone: Literal["UTC"]


class UsageSummary(StrictModel):
    requestCount: NonNegativeInteger
    inputTokens: NonNegativeInteger
    outputTokens: NonNegativeInteger
    cacheReadTokens: NonNegativeInteger
    cacheWriteTokens: NonNegativeInteger
    totalTokens: NonNegativeInteger
    unknownUsageCount: NonNegativeInteger


class UsageProjection(StrictModel):
    asOf: IsoTimestamp
    sampleWindowDays: NonNegativeInteger
    projectedExhaustionAt: IsoTimestamp | None
    projectedTokenShortfall: NonNegativeInteger | None
    confidence: Literal["insufficientData"]


class UsageItem(StrictModel):
    gatewayRequestId: SafeIdentifier
    modelAlias: SafeIdentifier
    gatewayScope: SafeIdentifier
    protocol: Literal["anthropic", "openai"]
    outcome: Literal["completed", "failed", "cancelled", "inProgress"]
    settlementState: Literal[
        "settled", "usageUnknown", "inProgress", "rejected"
    ]
    inputTokens: NonNegativeInteger
    outputTokens: NonNegativeInteger
    cacheReadTokens: NonNegativeInteger
    cacheWriteTokens: NonNegativeInteger
    totalTokens: NonNegativeInteger
    allowanceReservedTokens: NonNegativeInteger
    allowanceConsumedTokens: NonNegativeInteger
    allowanceReleasedTokens: NonNegativeInteger
    occurredAt: IsoTimestamp
    errorCategory: SafeIdentifier | None


class ProductUsage(StrictModel):
    period: UsagePeriod | None
    allowance: Allowance | None
    summary: UsageSummary
    projection: UsageProjection
    items: list[UsageItem]


class ModelEligibility(StrictModel):
    allowed: Literal[True]
    reasonCode: None
    subscriptionStatus: SafeIdentifier
    gatewayScopes: list[SafeIdentifier]
    rpmLimit: NonNegativeInteger | None
    dailyTokenLimit: NonNegativeInteger | None
    storageBytes: NonNegativeInteger | None
    monthlyTokenRemaining: NonNegativeInteger
    monthlyTokenResetAt: IsoTimestamp


class ModelLimits(StrictModel):
    contextWindow: NonNegativeInteger | None
    maxOutputTokens: NonNegativeInteger | None


class ProductModel(StrictModel):
    modelAlias: SafeIdentifier
    displayName: Annotated[str, StringConstraints(min_length=1, max_length=160)]
    description: SafeText | None
    capabilities: list[SafeIdentifier]
    contexts: list[SafeIdentifier]
    eligibility: ModelEligibility
    limits: ModelLimits
    availability: Literal["available"]
    asOf: IsoTimestamp


class ModelCatalog(StrictModel):
    items: list[ProductModel]
    asOf: IsoTimestamp


class AllowanceImpact(StrictModel):
    unit: Literal["tokens"]
    currentPeriodTokens: NonNegativeInteger | None
    nextPeriodTokens: NonNegativeInteger | None
    currentPeriodChanges: bool


class EntitlementImpact(StrictModel):
    currentModelAliases: list[SafeIdentifier]
    targetModelAliases: list[SafeIdentifier]


class GatewayImpact(StrictModel):
    callableAfterExecute: bool


class CommandPreview(StrictModel):
    action: ProductAction
    allowed: bool
    reasonCode: SafeIdentifier | None
    previewId: Annotated[str, Field(pattern=r"^preview_[A-Za-z0-9_-]{22}$")]
    digest: Annotated[str, Field(pattern=r"^sha256:[A-Za-z0-9_-]{43}$")]
    expiresAt: IsoTimestamp
    expectedVersion: PositiveInteger | None
    current: PlanSummary | None
    target: PlanSummary | None
    appliesAt: IsoTimestamp | None
    allowanceImpact: AllowanceImpact
    entitlementImpact: EntitlementImpact
    gatewayImpact: GatewayImpact
    warnings: list[SafeText]


class CommandSubscription(StrictModel):
    id: SafeIdentifier
    status: SafeIdentifier
    version: PositiveInteger
    planVersionId: SafeIdentifier
    pendingPlanVersionId: SafeIdentifier | None
    currentPeriodStart: IsoTimestamp
    currentPeriodEnd: IsoTimestamp


class ActualImpact(StrictModel):
    unit: Literal["tokens"]
    appliesAt: IsoTimestamp | None
    grantedTokens: NonNegativeInteger | None
    reservedTokens: NonNegativeInteger | None
    consumedTokens: NonNegativeInteger | None
    remainingTokens: NonNegativeInteger | None

    @model_validator(mode="after")
    def validate_conservation(self) -> "ActualImpact":
        values = (
            self.grantedTokens,
            self.reservedTokens,
            self.consumedTokens,
            self.remainingTokens,
        )
        if all(value is not None for value in values):
            granted, reserved, consumed, remaining = values
            if granted != reserved + consumed + remaining:  # type: ignore[operator]
                raise ValueError("Token command impact conservation failed")
        return self


class CommandResult(StrictModel):
    commandId: SafeIdentifier
    outcome: Literal["applied", "scheduled"]
    subscription: CommandSubscription
    actualImpact: ActualImpact
    idempotentReplay: bool


class PaymentIntentCreate(StrictModel):
    planVersionId: TargetPlanVersionId


class PaymentNextActionNone(StrictModel):
    type: Literal["none"]


class PaymentNextActionTestWebhook(StrictModel):
    type: Literal["test_webhook"]


class PaymentNextActionRedirect(StrictModel):
    type: Literal["redirect"]
    url: Annotated[str, StringConstraints(min_length=8, max_length=2_048)]


PaymentNextAction = Annotated[
    Union[
        PaymentNextActionNone,
        PaymentNextActionTestWebhook,
        PaymentNextActionRedirect,
    ],
    Field(discriminator="type"),
]


class PaymentIntent(StrictModel):
    id: Annotated[str, Field(pattern=r"^pay_[a-f0-9]{32}$")]
    planVersionId: SafeIdentifier
    subscriptionId: SafeIdentifier | None
    operation: Literal["initial_activation", "renewal"]
    amountMicrousd: PositiveInteger
    currency: Literal["USD"]
    status: Literal[
        "creating",
        "requires_action",
        "processing",
        "succeeded",
        "failed",
        "cancelled",
        "refunded",
        "reversed",
    ]
    nextAction: PaymentNextAction
    failureCode: SafeIdentifier | None
    createdAt: IsoTimestamp
    updatedAt: IsoTimestamp


class RequestMeta(StrictModel):
    requestId: SafeIdentifier


class PaginationMeta(RequestMeta):
    total: NonNegativeInteger
    page: PositiveInteger
    pageSize: PositiveInteger


class PlansEnvelope(StrictModel):
    data: list[ProductPlan]
    meta: PaginationMeta


class ContextEnvelope(StrictModel):
    data: SubscriptionContext
    meta: RequestMeta


class UsageEnvelope(StrictModel):
    data: ProductUsage
    meta: PaginationMeta


class ModelCatalogEnvelope(StrictModel):
    data: ModelCatalog
    meta: RequestMeta


class PreviewEnvelope(StrictModel):
    data: CommandPreview
    meta: RequestMeta


class CommandResultEnvelope(StrictModel):
    data: CommandResult
    meta: RequestMeta


class PaymentIntentEnvelope(StrictModel):
    data: PaymentIntent
    meta: RequestMeta


class ValidationIssue(StrictModel):
    code: SafeIdentifier
    path: list[str]
    message: SafeText


class ProductErrorDetails(StrictModel):
    field: SafeText | None = None
    issues: list[ValidationIssue] | None = None
    expectedVersion: NonNegativeInteger | None = None
    actualVersion: NonNegativeInteger | None = None
    periodEnd: IsoTimestamp | None = None
    status: SafeIdentifier | None = None
    reasonCode: SafeIdentifier | None = None
    metric: Literal["tokens"] | None = None
    unit: Literal["tokens"] | None = None
    availableTokens: NonNegativeInteger | None = None
    requiredTokens: NonNegativeInteger | None = None
    modelAlias: SafeIdentifier | None = None
    gatewayScope: SafeIdentifier | None = None
    requiredScope: SafeIdentifier | None = None
    retryable: bool | None = None
    window: SafeIdentifier | None = None
    current: NonNegativeInteger | None = None
    limit: NonNegativeInteger | None = None
    remaining: NonNegativeInteger | None = None


class ProductErrorBody(StrictModel):
    code: Annotated[str, Field(pattern=r"^[A-Z][A-Z0-9_]{1,99}$")]
    message: SafeText
    details: ProductErrorDetails | None = None


class ProductErrorMeta(RequestMeta):
    retryAfterSeconds: Annotated[int, Field(ge=0, le=86_400)] | None = None


class ProductErrorEnvelope(StrictModel):
    error: ProductErrorBody
    meta: ProductErrorMeta

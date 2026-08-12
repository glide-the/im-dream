# Dream Agent lifecycle

## Independent state domains

Dream renders three independent domains:

1. Canonical Thread turn lifecycle.
2. Dream Workflow Run lifecycle.
3. Artifact/Story projection status.

They share immutable actor/thread/run provenance but never form a bidirectional
state loop.

## Canonical Thread turn

```mermaid
stateDiagram-v2
    [*] --> idle
    idle --> submitting: user or authorized business command
    submitting --> streaming: turn accepted
    streaming --> waiting_confirmation: runtime tool/AskUserQuestion
    waiting_confirmation --> confirming: decision submitted
    confirming --> streaming: runner receives decision
    waiting_confirmation --> rejected: reject
    rejected --> failed: runner closes rejected turn
    streaming --> completed: one success terminal
    submitting --> failed: setup/output-before-start failure
    streaming --> failed: one failure terminal
    streaming --> cancelling: Stop current main turn
    waiting_confirmation --> cancelling: Stop current main turn
    cancelling --> cancelled: one cancelled terminal
    streaming --> disconnected: browser transport loss only
    waiting_confirmation --> disconnected: browser transport loss only
    disconnected --> reconnecting: same thread stream/history
    reconnecting --> streaming: turn still running
    reconnecting --> waiting_confirmation: pending decision replayed
    reconnecting --> completed: terminal/history recovered
    reconnecting --> failed: failed terminal/history recovered
    reconnecting --> cancelled: cancelled terminal/history recovered
```

There is no extra lifecycle stage between a confirmation decision and resumed
streaming. `message-final` and EOF are not terminal; one `finish` outcome closes
the turn. Exactly one of completed, failed or cancelled is observed.

Stop is available only when the factory owns a non-finished main-turn task.
Historical subagent transcripts or business activity cannot expose Stop or
block the composer.

## Workflow Run

```mermaid
stateDiagram-v2
    [*] --> preflight
    preflight --> queued: launch committed
    queued --> running: runtime activation fact
    running --> output_validating: owning output fact
    output_validating --> pending_review: valid review projection
    pending_review --> confirmed: user business CAS
    pending_review --> rejected: user business CAS
    rejected --> queued: authorized child retry/revision
    confirmed --> completed: domain completion fact
    preflight --> failed
    queued --> failed
    running --> failed
    output_validating --> failed
    pending_review --> failed
    confirmed --> failed
    queued --> cancelled
    running --> cancelled
    confirmed --> cancelled
```

Rejected Workflow Runs are terminal attempts. An authorized retry or revision
creates a new child attempt and queues that child; it never reopens the
rejected row. After business confirmation the Workflow Run remains `confirmed` while any
follow-up Agent work executes. The Thread lifecycle shows whether that work is
currently submitting, streaming, awaiting confirmation, stopped or terminal.
Only an Artifact/action owning service can move the Workflow to completed,
failed or cancelled.

## Artifact and Story projection

```mermaid
stateDiagram-v2
    [*] --> generating
    generating --> available: stable valid observation
    generating --> missing: expected output absent
    generating --> invalid: contract violation
    available --> generating: new authorized revision starts
    available --> missing: current source file absent
    available --> invalid: current source fails contract
    missing --> available: later valid revision
    invalid --> available: later valid revision
```

Storage outage or unstable observation is `unavailable/degraded`, not a durable
missing transition. Story Index independently reports syncing, indexed, stale,
missing or failed. Review is bound to a complete script revision.

## Confirmation comparison

| Concern | Runtime confirmation | Dream business confirmation |
|---|---|---|
| Owner | canonical Thread confirmation store | Workflow domain service |
| Trigger | tool policy / AskUserQuestion | reviewed Dream draft |
| Identity | thread + turn + tool call | actor + run + expected version + idempotency |
| Effect | resolve runner Future | `pending_review -> confirmed`, dispatch private Thread command once |
| UI | shared Chat confirmation | Dream business confirmation bar |
| Terminal proof | none | none; later domain fact required |

## Disconnect, refresh and switching

```mermaid
sequenceDiagram
    actor User
    participant Surface as "Chat or Dream"
    participant API as "Canonical Thread API"
    participant Business as "Dream business API"

    User->>Surface: refresh/switch with threadId
    Surface->>API: load history + status
    alt running
        Surface->>API: reconnect same Thread stream
    else terminal/idle
        API-->>Surface: persisted history/status
    end
    opt Dream surface
        Surface->>Business: load authorized workflow/artifact projection
    end
```

GET and reconnect do not start a model turn. Business projection cannot rewrite
Thread status. Thread history cannot mark Workflow complete.

## Observer lifecycle

```mermaid
stateDiagram-v2
    [*] --> unbound
    unbound --> observing: registry after-context hook + valid Dream context
    observing --> projecting: normalized event accepted
    projecting --> observing: idempotent sink success/duplicate ignored
    observing --> terminal_fenced: one business terminal observed
    projecting --> terminal_fenced: one business terminal observed
    terminal_fenced --> closed: unsubscribe/drain/close
    observing --> closed: turn/session close
    projecting --> closed: cancellation/failure close
```

Identity is `(actorId, threadId, turnId, workflowRunId, generation)`. Derived
event IDs and monotonically checked sequences make replay/duplicates idempotent.
After a business terminal fence, late business updates are ignored. Observer
errors are isolated and never alter Chat terminal or SSE delivery.

## Single-terminal rules

- EventBus atomically accepts the first Chat terminal and rejects later ones.
- Workflow service validates one legal terminal transition and idempotent replay.
- Observer may observe both domains but cannot create a Chat terminal.
- Agent/session cleanup runs in `finally`; business sink cleanup is registry
  Observer responsibility and cannot strand Thread locks.

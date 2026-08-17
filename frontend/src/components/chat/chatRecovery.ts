// [Input] Recovery request/current checkpoints and a refreshed server snapshot.
// [Output] A narrow decision for applying reconnect/stop history without overwriting a newer turn.
// [Pos] Generic Chat reconnect recovery policy; independent from React and transport details.

export interface ChatHistoryRecoveryCheckpoint {
  readonly threadId: string;
  readonly reconnectNonce: number;
  readonly turnGeneration: number;
}

export function shouldApplyChatHistoryRecoverySnapshot(
  requestedAt: ChatHistoryRecoveryCheckpoint,
  current: ChatHistoryRecoveryCheckpoint,
  snapshot: readonly unknown[] | undefined,
): boolean {
  return snapshot !== undefined
    && requestedAt.threadId === current.threadId
    && requestedAt.reconnectNonce === current.reconnectNonce
    && requestedAt.turnGeneration === current.turnGeneration;
}

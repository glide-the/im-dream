// [Input] Keyboard events from the shared Chat composer.
// [Output] Decide whether Enter submits while Shift+Enter and IME composition remain editing actions.
// [Pos] Shared Chat interaction policy used by AIInputDock.
// [Sync] 2026-09-18: align the composer with Enter-to-send and Shift+Enter newline semantics.
export interface OperationPart {
  id: string;
  type: 'step-start' | 'reasoning';
  text: string;
}

export function getVisibleOperations(
  operations: OperationPart[],
  expanded: boolean,
  defaultVisible = 3,
): OperationPart[] {
  if (expanded) {
    return operations;
  }
  return operations.slice(0, defaultVisible);
}

export function shouldShowExpandOperations(
  operations: OperationPart[],
  defaultVisible = 3,
): boolean {
  return operations.length > defaultVisible;
}

export function shouldSendMessageOnKeyDown(event: {
  key: string;
  shiftKey: boolean;
  isComposing?: boolean;
}): boolean {
  if (event.isComposing) {
    return false;
  }
  return event.key === 'Enter' && !event.shiftKey;
}

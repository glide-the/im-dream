// [Input] AskUserQuestion option/default/answer values.
// [Output] Stable option strings, string[] multi-select normalization and required validation.
// [Pos] Shared Chat/Dream AskUserQuestion answer contract.

export type QuestionOption =
  | string
  | { value: string; label: string }
  | { label: string; description?: string; value?: string };

export function questionOptionValue(option: QuestionOption): string {
  return typeof option === 'string' ? option : option.value || option.label;
}

export function normalizeMultiSelectAnswer(value: unknown): string[] {
  if (Array.isArray(value)) {
    return value.filter((item): item is string => typeof item === 'string' && item.length > 0);
  }
  return typeof value === 'string' && value.length > 0 ? [value] : [];
}

export function questionAnswerIsPresent(value: unknown, multiSelect = false): boolean {
  if (multiSelect) return normalizeMultiSelectAnswer(value).length > 0;
  if (Array.isArray(value)) return value.length > 0;
  if (typeof value === 'boolean') return value;
  return value !== undefined && value !== null && value !== '';
}

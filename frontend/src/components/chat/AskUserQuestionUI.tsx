// [Input] AskUserQuestionInput from tool part; onSubmit/onCancel callbacks from ToolMessagePart.
// [Output] Interactive question form rendered inline in the chat message list.
// [Pos] ask-user-question component node in frontend/src/components/chat
// [Sync] 2026-05-27: add null guard for undefined input at useMemo start to prevent crash when tool is in input-streaming state.
// [Sync] 2026-07-08: use the semantic on-action text token for dark-mode-safe submit buttons.
import { useCallback, useEffect, useMemo, useState, type CSSProperties } from 'react';
import { IconCheck, IconX } from './Icons';

export type QuestionOption =
  | string
  | { value: string; label: string }
  | { label: string; description?: string; value?: string };

export interface QuestionField {
  id?: string;
  question?: string;
  label?: string;
  header?: string;
  type?: 'text' | 'textarea' | 'select' | 'checkbox' | 'radio' | 'number';
  options?: QuestionOption[];
  required?: boolean;
  default?: string | number | boolean;
  placeholder?: string;
  description?: string;
  multiSelect?: boolean;
}

export interface AskUserQuestionInput {
  questions?: QuestionField[];
  question?: string;
  message?: string;
  text?: string;
  prompt?: string;
  options?: string[];
  choices?: string[];
  default?: string;
}

interface AskUserQuestionUIProps {
  input: AskUserQuestionInput;
  toolCallId: string;
  toolName: string;
  isProcessing?: boolean;
  onSubmit: (answers: Record<string, unknown>) => void;
  onCancel: () => void;
}

const fieldStyle: CSSProperties = {
  width: '100%',
  padding: '0.7rem 0.85rem',
  fontSize: '0.9rem',
  color: 'var(--color-text-primary)',
  background: 'var(--color-bg-paper)',
  border: '1px solid var(--color-border-paper)',
  borderRadius: '10px',
  boxSizing: 'border-box',
};

export default function AskUserQuestionUI({ input, toolCallId, toolName, isProcessing = false, onSubmit, onCancel }: AskUserQuestionUIProps) {
  const questions = useMemo<QuestionField[]>(() => {
    if (!input) {
      return [{ id: 'answer', question: '请回答问题', type: 'text', required: true }];
    }
    if (input.questions?.length) {
      return input.questions.map((question, index) => {
        const hasOptions = Array.isArray(question.options) && question.options.length > 0;
        return {
          id: question.id || `q${index}`,
          question: question.question || question.label || question.header || `Question ${index + 1}`,
          type: question.type || (hasOptions ? 'radio' : 'text'),
          options: question.options,
          required: question.required ?? true,
          default: question.default,
          placeholder: question.placeholder,
          description: question.description,
          multiSelect: question.multiSelect,
        };
      });
    }

    const questionText = input.question || input.message || input.text || input.prompt;
    if (questionText) {
      const options = input.options || input.choices;
      return [{ id: 'answer', question: questionText, type: options?.length ? 'radio' : 'text', options, required: true, default: input.default }];
    }

    return [{ id: 'answer', question: 'Please answer the question', type: 'text', required: true }];
  }, [input]);

  const [answers, setAnswers] = useState<Record<string, unknown>>(() => {
    const initial: Record<string, unknown> = {};
    questions.forEach((question) => {
      const key = question.question || question.id || 'answer';
      if (question.default !== undefined) initial[key] = question.default;
      else if (question.type === 'checkbox') initial[key] = false;
      else initial[key] = '';
    });
    return initial;
  });

  useEffect(() => {
    setAnswers((current) => {
      const next: Record<string, unknown> = {};
      questions.forEach((question) => {
        const key = question.question || question.id || 'answer';
        next[key] = current[key] ?? (question.default ?? (question.type === 'checkbox' ? false : ''));
      });
      return next;
    });
  }, [questions]);

  const handleChange = useCallback((questionText: string, value: unknown) => {
    setAnswers((current) => ({ ...current, [questionText]: value }));
  }, []);

  const getCleanAnswers = useCallback(() => {
    const cleaned: Record<string, unknown> = {};
    Object.entries(answers).forEach(([key, value]) => {
      if (value !== '' && value !== undefined && value !== null) {
        cleaned[key] = value;
      }
    });
    return cleaned;
  }, [answers]);

  useEffect(() => {
    const handleKeyDown = (event: KeyboardEvent) => {
      if ((event.metaKey || event.ctrlKey) && event.key === 'Enter') {
        event.preventDefault();
        onSubmit(getCleanAnswers());
      }
      if ((event.metaKey || event.ctrlKey) && event.key === 'Escape') {
        event.preventDefault();
        onCancel();
      }
    };

    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [getCleanAnswers, onCancel, onSubmit]);

  const isValid = useMemo(() => {
    return questions.every((question) => {
      if (!question.required) return true;
      const key = question.question || question.id || 'answer';
      const value = answers[key];
      return value !== undefined && value !== null && value !== '';
    });
  }, [answers, questions]);

  return (
    <div style={{ overflow: 'hidden', borderRadius: '14px', border: '1px solid var(--color-border-paper)', background: 'var(--color-bg-paper)' }}>
      <div style={{ padding: '0.95rem 1rem', borderBottom: '1px solid var(--color-border-paper)', background: 'var(--color-bg-surface)' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
          <span style={{ fontSize: '1rem' }}>❓</span>
          <h3 style={{ margin: 0, fontSize: '0.96rem', fontWeight: 600, color: 'var(--color-text-primary)' }}>Your input is needed</h3>
        </div>
        <p style={{ margin: '0.25rem 0 0', fontSize: '0.75rem', color: 'var(--color-text-muted)' }}>{toolName} · {toolCallId}</p>
      </div>

      <form onSubmit={(event) => { event.preventDefault(); onSubmit(getCleanAnswers()); }} style={{ padding: '1rem', display: 'flex', flexDirection: 'column', gap: '1rem' }}>
        {questions.map((question, index) => {
          const answerKey = question.question || question.id || `q${index}`;
          const fieldId = question.id || `q${index}`;
          const value = answers[answerKey];

          return (
            <div key={fieldId} style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem' }}>
              <label htmlFor={fieldId} style={{ fontSize: '0.9rem', fontWeight: 600, color: 'var(--color-text-primary)' }}>
                {question.question}
                {question.required ? <span style={{ color: 'var(--color-state-danger)', marginLeft: '0.25rem' }}>*</span> : null}
              </label>
              {question.description ? <p style={{ margin: 0, fontSize: '0.76rem', color: 'var(--color-text-muted)' }}>{question.description}</p> : null}

              {question.type === 'textarea' ? (
                <textarea id={fieldId} value={String(value || '')} onChange={(event) => handleChange(answerKey, event.target.value)} placeholder={question.placeholder} rows={4} style={{ ...fieldStyle, resize: 'vertical' }} required={question.required} disabled={isProcessing} />
              ) : question.type === 'select' && question.options ? (
                <select id={fieldId} value={String(value || '')} onChange={(event) => handleChange(answerKey, event.target.value)} style={fieldStyle} required={question.required} disabled={isProcessing}>
                  <option value="">Select an option…</option>
                  {question.options.map((option) => {
                    const optionValue = typeof option === 'string' ? option : option.value || option.label;
                    const optionLabel = typeof option === 'string' ? option : option.label;
                    return <option key={optionValue} value={optionValue}>{optionLabel}</option>;
                  })}
                </select>
              ) : question.type === 'radio' && question.options ? (
                <div style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem' }}>
                  {question.options.map((option) => {
                    const optionValue = typeof option === 'string' ? option : option.value || option.label;
                    const optionLabel = typeof option === 'string' ? option : option.label;
                    const optionDescription = typeof option === 'string' ? undefined : ('description' in option ? option.description : undefined);
                    return (
                      <label key={optionValue} style={{ display: 'flex', gap: '0.75rem', padding: '0.7rem 0.85rem', borderRadius: '10px', background: 'var(--color-bg-surface)', cursor: 'pointer' }}>
                        <input type="radio" name={fieldId} value={optionValue} checked={value === optionValue} onChange={(event) => handleChange(answerKey, event.target.value)} disabled={isProcessing} />
                        <span>
                          <span style={{ display: 'block', fontSize: '0.9rem', fontWeight: 500, color: 'var(--color-text-primary)' }}>{optionLabel}</span>
                          {optionDescription ? <span style={{ display: 'block', marginTop: '0.15rem', fontSize: '0.76rem', color: 'var(--color-text-muted)' }}>{optionDescription}</span> : null}
                        </span>
                      </label>
                    );
                  })}
                </div>
              ) : question.type === 'checkbox' ? (
                <label style={{ display: 'inline-flex', alignItems: 'center', gap: '0.5rem', fontSize: '0.9rem', color: 'var(--color-text-primary)', cursor: 'pointer' }}>
                  <input type="checkbox" id={fieldId} checked={Boolean(value)} onChange={(event) => handleChange(answerKey, event.target.checked)} disabled={isProcessing} />
                  Yes
                </label>
              ) : question.type === 'number' ? (
                <input type="number" id={fieldId} value={String(value || '')} onChange={(event) => handleChange(answerKey, event.target.value === '' ? '' : Number(event.target.value))} placeholder={question.placeholder} style={fieldStyle} required={question.required} disabled={isProcessing} />
              ) : (
                <input type="text" id={fieldId} value={String(value || '')} onChange={(event) => handleChange(answerKey, event.target.value)} placeholder={question.placeholder} style={fieldStyle} required={question.required} disabled={isProcessing} />
              )}
            </div>
          );
        })}

        <div style={{ display: 'flex', gap: '0.75rem', paddingTop: '0.25rem' }}>
          <button type="submit" disabled={isProcessing || !isValid} style={{ flex: 1, display: 'inline-flex', alignItems: 'center', justifyContent: 'center', gap: '0.5rem', border: 'none', borderRadius: '999px', padding: '0.8rem 1rem', background: 'var(--color-action-link)', color: 'var(--color-text-on-action)', fontSize: '0.88rem', fontWeight: 600, cursor: isProcessing || !isValid ? 'not-allowed' : 'pointer', opacity: isProcessing || !isValid ? 0.55 : 1 }}>
            <IconCheck style={{ width: '1rem', height: '1rem' }} />
            Submit
          </button>
          <button type="button" onClick={onCancel} disabled={isProcessing} style={{ flex: 1, display: 'inline-flex', alignItems: 'center', justifyContent: 'center', gap: '0.5rem', borderRadius: '999px', padding: '0.8rem 1rem', border: '1px solid var(--color-border-paper)', background: 'var(--color-bg-paper)', color: 'var(--color-text-secondary)', fontSize: '0.88rem', fontWeight: 600, cursor: isProcessing ? 'not-allowed' : 'pointer', opacity: isProcessing ? 0.55 : 1 }}>
            <IconX style={{ width: '1rem', height: '1rem' }} />
            Cancel
          </button>
        </div>
      </form>
    </div>
  );
}

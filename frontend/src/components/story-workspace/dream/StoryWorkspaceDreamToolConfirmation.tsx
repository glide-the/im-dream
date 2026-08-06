// [Input] Server-allowlisted Dream tool decision and run-bound resolve callback.
// [Output] Dream-paper approval, question and network confirmation surface.
// [Pos] Dream Agent tool-confirmation view; it never consumes generic Chat parts.

import { useEffect, useId, useMemo, useState } from 'react';
import type {
  StoryWorkspaceDreamAgentToolConfirmation,
  StoryWorkspaceDreamAgentToolConfirmationQuestion,
} from '../../../hooks/story-workspace/contracts';

interface StoryWorkspaceDreamToolConfirmationProps {
  readonly confirmation: StoryWorkspaceDreamAgentToolConfirmation;
  readonly errorMessage?: string | null;
  readonly isResolving: boolean;
  readonly onResolve: (
    approved: boolean,
    reason?: string,
    answers?: Readonly<Record<string, unknown>>,
  ) => Promise<boolean>;
}

function storyWorkspaceDreamQuestionKey(question: StoryWorkspaceDreamAgentToolConfirmationQuestion): string {
  return question.id;
}

function storyWorkspaceDreamInitialAnswers(
  questions: readonly StoryWorkspaceDreamAgentToolConfirmationQuestion[],
): Record<string, unknown> {
  return Object.fromEntries(questions.map((question) => [
    storyWorkspaceDreamQuestionKey(question),
    question.multiSelect ? [] : question.type === 'checkbox' ? false : '',
  ]));
}

function storyWorkspaceDreamToolTitle(confirmation: StoryWorkspaceDreamAgentToolConfirmation): string {
  if (confirmation.kind === 'ask_user') return 'Dream Agent 需要你的选择';
  if (confirmation.kind === 'sandbox_network') {
    return confirmation.network?.host
      ? `允许访问 ${confirmation.network.host}`
      : '允许本次网络访问';
  }
  return `允许 Dream Agent 使用 ${confirmation.toolName}`;
}

function storyWorkspaceDreamAnswersAreValid(
  questions: readonly StoryWorkspaceDreamAgentToolConfirmationQuestion[],
  answers: Readonly<Record<string, unknown>>,
): boolean {
  return questions.every((question) => {
    if (!question.required) return true;
    const value = answers[storyWorkspaceDreamQuestionKey(question)];
    return Array.isArray(value) ? value.length > 0 : value !== '' && value !== null && value !== undefined;
  });
}

export function StoryWorkspaceDreamToolConfirmation({
  confirmation,
  errorMessage,
  isResolving,
  onResolve,
}: StoryWorkspaceDreamToolConfirmationProps) {
  const questions = useMemo(
    () => confirmation.questions ?? [],
    [confirmation.questions],
  );
  const [answers, setAnswers] = useState<Record<string, unknown>>(
    () => storyWorkspaceDreamInitialAnswers(questions),
  );
  const headingId = useId();
  const title = storyWorkspaceDreamToolTitle(confirmation);
  const answersAreValid = useMemo(
    () => storyWorkspaceDreamAnswersAreValid(questions, answers),
    [answers, questions],
  );

  useEffect(() => {
    setAnswers(storyWorkspaceDreamInitialAnswers(questions));
  }, [confirmation.toolCallId, questions]);

  const updateAnswer = (question: StoryWorkspaceDreamAgentToolConfirmationQuestion, value: unknown) => {
    setAnswers((current) => ({ ...current, [storyWorkspaceDreamQuestionKey(question)]: value }));
  };

  const toggleOption = (
    question: StoryWorkspaceDreamAgentToolConfirmationQuestion,
    value: string,
    checked: boolean,
  ) => {
    const key = storyWorkspaceDreamQuestionKey(question);
    setAnswers((current) => {
      const selected = Array.isArray(current[key]) ? current[key] as string[] : [];
      return {
        ...current,
        [key]: checked
          ? [...new Set([...selected, value])]
          : selected.filter((item) => item !== value),
      };
    });
  };

  const reject = () => void onResolve(false, '用户拒绝本次工具操作');
  const approve = () => void onResolve(true);
  const submitAnswers = () => void onResolve(true, undefined, answers);

  return (
    <section
      aria-busy={isResolving}
      aria-labelledby={headingId}
      className="story-workspace-dream-tool-confirmation"
      role="region"
    >
      <header>
        <div>
          <span>待你确认</span>
          <h3 id={headingId}>{title}</h3>
        </div>
        <small>{confirmation.toolName}</small>
      </header>

      {confirmation.kind === 'ask_user' ? (
        <form onSubmit={(event) => { event.preventDefault(); submitAnswers(); }}>
          {questions.map((question) => {
            const key = storyWorkspaceDreamQuestionKey(question);
            const value = answers[key];
            const hasOptions = Boolean(question.options?.length);
            return (
              <fieldset key={question.id}>
                <legend>{question.question}{question.required ? <em aria-hidden="true"> *</em> : null}</legend>
                {hasOptions && question.multiSelect ? (
                  <div className="story-workspace-dream-tool-confirmation__options">
                    {question.options?.map((option) => (
                      <label className="story-workspace-dream-tool-confirmation__option" key={option.value}>
                        <input
                          checked={Array.isArray(value) && value.includes(option.value)}
                          disabled={isResolving}
                          onChange={(event) => toggleOption(question, option.value, event.currentTarget.checked)}
                          type="checkbox"
                        />
                        <span><strong>{option.label}</strong></span>
                      </label>
                    ))}
                  </div>
                ) : hasOptions && question.type === 'select' ? (
                  <select
                    aria-label={question.question}
                    disabled={isResolving}
                    onChange={(event) => updateAnswer(question, event.currentTarget.value)}
                    required={question.required}
                    value={String(value ?? '')}
                  >
                    <option value="">请选择</option>
                    {question.options?.map((option) => <option key={option.value} value={option.value}>{option.label}</option>)}
                  </select>
                ) : hasOptions ? (
                  <div className="story-workspace-dream-tool-confirmation__options">
                    {question.options?.map((option) => (
                      <label className="story-workspace-dream-tool-confirmation__option" key={option.value}>
                        <input
                          checked={value === option.value}
                          disabled={isResolving}
                          name={question.id}
                          onChange={() => updateAnswer(question, option.value)}
                          type="radio"
                          value={option.value}
                        />
                        <span><strong>{option.label}</strong></span>
                      </label>
                    ))}
                  </div>
                ) : question.type === 'textarea' ? (
                  <textarea
                    aria-label={question.question}
                    disabled={isResolving}
                    onChange={(event) => updateAnswer(question, event.currentTarget.value)}
                    placeholder={question.placeholder}
                    maxLength={1000}
                    required={question.required}
                    rows={3}
                    value={String(value ?? '')}
                  />
                ) : question.type === 'checkbox' ? (
                  <label className="story-workspace-dream-tool-confirmation__check">
                    <input
                      checked={Boolean(value)}
                      disabled={isResolving}
                      onChange={(event) => updateAnswer(question, event.currentTarget.checked)}
                      type="checkbox"
                    />
                    <span>确认</span>
                  </label>
                ) : (
                  <input
                    aria-label={question.question}
                    disabled={isResolving}
                    onChange={(event) => updateAnswer(
                      question,
                      question.type === 'number' && event.currentTarget.value !== ''
                        ? Number(event.currentTarget.value)
                        : event.currentTarget.value,
                    )}
                    placeholder={question.placeholder}
                    max={question.type === 'number' ? 1_000_000_000 : undefined}
                    maxLength={1000}
                    min={question.type === 'number' ? -1_000_000_000 : undefined}
                    required={question.required}
                    type={question.type === 'number' ? 'number' : 'text'}
                    value={String(value ?? '')}
                  />
                )}
              </fieldset>
            );
          })}
          <div className="story-workspace-dream-tool-confirmation__actions">
            <button disabled={isResolving} onClick={reject} type="button">取消</button>
            <button disabled={isResolving || !answersAreValid} type="submit">{isResolving ? '提交中…' : '提交选择'}</button>
          </div>
        </form>
      ) : (
        <div className="story-workspace-dream-tool-confirmation__decision">
          {confirmation.kind === 'sandbox_network' ? (
            <dl>
              <div><dt>目标</dt><dd>{confirmation.network?.host ?? '未提供主机名'}</dd></div>
              <div><dt>规则</dt><dd>{confirmation.network?.policy === 'open' ? '开放网络' : confirmation.network?.policy === 'allowlist' ? '仅允许清单内地址' : confirmation.network?.policy === 'deny' ? '网络访问受限' : '网络规则待核验'}</dd></div>
            </dl>
          ) : (
            <p>此操作需要你的明确许可。Dream 工作台不会展示原始工具参数或隐藏运行信息。</p>
          )}
          <div className="story-workspace-dream-tool-confirmation__actions">
            <button disabled={isResolving} onClick={reject} type="button">拒绝</button>
            <button disabled={isResolving} onClick={approve} type="button">{isResolving ? '处理中…' : '允许本次操作'}</button>
          </div>
        </div>
      )}
      {errorMessage ? <p className="story-workspace-dream-tool-confirmation__error" role="status">{errorMessage}</p> : null}
    </section>
  );
}

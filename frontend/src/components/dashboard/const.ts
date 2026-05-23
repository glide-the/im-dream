export interface QuickActionCardItem {
  icon: 'envelope' | 'table' | 'calendar' | 'tasks' | 'calendarAlt' | 'database';
  title: string;
  description: string;
  prompt: string;
  color: string;
}

export const QUICK_ACTION_CARDS: QuickActionCardItem[] = [
  {
    icon: 'envelope',
    title: 'Draft a follow-up',
    description: 'Generate a warm, professional follow-up note from your latest context.',
    prompt: 'Help me draft a concise, thoughtful follow-up note with a clear next step.',
    color: 'success',
  },
  {
    icon: 'table',
    title: 'Research patterns',
    description: 'Summarize comparisons, tradeoffs, or notes into a readable table.',
    prompt: 'Turn my notes into a comparison table with key patterns and opportunities.',
    color: 'warning',
  },
  {
    icon: 'calendar',
    title: 'Plan a session',
    description: 'Outline what to cover next, including goals, risks, and open questions.',
    prompt: 'Help me plan my next work session with priorities, risks, and questions.',
    color: 'voice-blue',
  },
  {
    icon: 'tasks',
    title: 'Create tasks',
    description: 'Transform loose thoughts into structured tasks with ownership and timing.',
    prompt: 'Convert these notes into a task list with next actions and owners.',
    color: 'voice-purple',
  },
  {
    icon: 'calendarAlt',
    title: 'Shape a timeline',
    description: 'Build a simple week plan around deep work, review, and communication.',
    prompt: 'Build me a balanced weekly timeline from these notes.',
    color: 'voice-pink',
  },
  {
    icon: 'database',
    title: 'Summarize sources',
    description: 'Pull key evidence, questions, and references into a compact brief.',
    prompt: 'Summarize the most important source material into a short brief.',
    color: 'voice-green',
  },
];

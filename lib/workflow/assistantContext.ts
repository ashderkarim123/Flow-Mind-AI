/** What the editor tells the AI assistant about the workflow being built (the server masks secrets again before any model sees it). */

export interface AssistantTurn { role: 'user' | 'assistant'; content: string }

export interface AssistantRun {
  status: string;
  error: string | null;
  nodeLogs: Array<{
    nodeId?: string; nodeName?: string; nodeType?: string; status?: string; error?: string | null;
    errorInfo?: unknown; attempts?: number; executionTimeMs?: number; fallbackUsed?: boolean;
  }>;
}

/** Questions that need the workflow, asked with one click. */
export const WORKFLOW_QUESTIONS = [
  'Explain this workflow',
  'Why did my last run fail?',
  'What could go wrong in this workflow?',
  'How can I make this more reliable?',
];

/** The chat so far as the server wants it: no welcome text, no error bubbles, the last 8 turns. */
export function toHistory(messages: Array<{ id: string; type: 'user' | 'assistant'; content: string }>): AssistantTurn[] {
  return messages
    .filter((m) => m.id !== 'welcome' && m.content.trim() && !(m.type === 'assistant' && m.content.startsWith('I encountered an issue')))
    .map((m) => ({ role: m.type, content: m.content }))
    .slice(-8);
}

/** The result of a run, without the step outputs (they can be large and hold customer data). */
export function toAssistantRun(execution: any): AssistantRun | null {
  if (!execution) return null;
  return {
    status: String(execution.status ?? 'unknown'),
    error: execution.error ?? null,
    nodeLogs: (execution.nodeLogs || []).map((l: any) => ({
      nodeId: l.nodeId ?? l.node_id,
      nodeName: l.nodeName ?? l.node_name,
      nodeType: l.nodeType ?? l.node_type,
      status: l.status,
      error: l.error ?? null,
      errorInfo: l.errorInfo ?? null,
      attempts: l.attempts,
      executionTimeMs: l.executionTimeMs ?? l.duration ?? l.duration_ms,
      fallbackUsed: l.fallbackUsed,
    })),
  };
}

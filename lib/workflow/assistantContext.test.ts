// Run: npx tsx --test lib/workflow/assistantContext.test.ts
import assert from 'node:assert/strict';
import { test } from 'node:test';
import { toAssistantRun, toHistory } from './assistantContext';

const msg = (id: string, type: 'user' | 'assistant', content: string) => ({ id, type, content });

test('history leaves out the welcome text, error bubbles and empty messages', () => {
  const h = toHistory([
    msg('welcome', 'assistant', 'Hello! I am your assistant'),
    msg('1', 'user', 'How do I connect APIs?'),
    msg('2', 'assistant', 'I encountered an issue: API error: 401. Please try again'),
    msg('3', 'user', '   '),
    msg('4', 'assistant', 'Use the HTTP Request node.'),
  ]);
  assert.deepEqual(h, [{ role: 'user', content: 'How do I connect APIs?' }, { role: 'assistant', content: 'Use the HTTP Request node.' }]);
});

test('history keeps only the last 8 turns, in order', () => {
  const many = Array.from({ length: 12 }, (_, i) => msg(String(i), i % 2 ? 'assistant' : 'user', `turn ${i}`));
  const h = toHistory(many);
  assert.equal(h.length, 8);
  assert.equal(h[0].content, 'turn 4');
  assert.equal(h[7].content, 'turn 11');
});

test('a run is reduced to status, error and the steps, without their outputs', () => {
  const run = toAssistantRun({
    status: 'failed', error: 'boom', output: { secret: 'x' },
    nodeLogs: [
      { nodeId: 'a', nodeName: 'Start', nodeType: 'ManualTrigger', status: 'success', output: { big: 'data' }, executionTimeMs: 3 },
      { node_id: 'b', node_name: 'Fetch', node_type: 'HttpRequest', status: 'failed', error: 'HTTP 401', attempts: 3, duration: 120, fallbackUsed: true, errorInfo: { category: 'auth' } },
    ],
  })!;
  assert.equal(run.status, 'failed');
  assert.equal(run.error, 'boom');
  assert.deepEqual(run.nodeLogs[1], { nodeId: 'b', nodeName: 'Fetch', nodeType: 'HttpRequest', status: 'failed', error: 'HTTP 401', errorInfo: { category: 'auth' }, attempts: 3, executionTimeMs: 120, fallbackUsed: true });
  assert.ok(!JSON.stringify(run).includes('big') && !JSON.stringify(run).includes('secret'));
});

test('no run means nothing is sent', () => {
  assert.equal(toAssistantRun(null), null);
  assert.equal(toAssistantRun(undefined), null);
  assert.deepEqual(toAssistantRun({ status: 'completed' }), { status: 'completed', error: null, nodeLogs: [] });
});

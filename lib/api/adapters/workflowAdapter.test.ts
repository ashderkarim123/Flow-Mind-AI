// Run: npx tsx --test lib/api/adapters/workflowAdapter.test.ts
import assert from 'node:assert/strict';
import { test } from 'node:test';
import { backendWorkflowToFrontend, prepareWorkflowForBackend, workflowToCreateRequest, workflowToUpdateRequest } from './workflowAdapter';

const base: any = {
  id: 'w1', name: 'Customer report', description: '', nodes: [], connections: [],
  settings: { timeout: 1, retryCount: 0, concurrency: 1, errorHandling: 'stop' }, createdAt: 'x', updatedAt: 'x', version: '1.0.0',
};
const variables = { customer: 'Acme', rows: 25, active: true };
const typed = { customer: { type: 'string', value: 'Acme' }, rows: { type: 'number', value: 25 }, active: { type: 'boolean', value: true } };

test('variables are sent when a workflow is created, and default to none', () => {
  assert.deepEqual(workflowToCreateRequest({ ...base, variables }).variables, typed);
  assert.deepEqual(workflowToCreateRequest(base).variables, {});
  assert.deepEqual(prepareWorkflowForBackend({ ...base, variables }).variables, typed);
});

test('variables are sent on update, and an update without them leaves the stored ones alone', () => {
  assert.deepEqual(workflowToUpdateRequest({ variables }).variables, typed);
  assert.deepEqual(workflowToUpdateRequest({ variables: {} }).variables, {});     // clearing them is an explicit choice
  assert.equal('variables' in workflowToUpdateRequest({ name: 'Renamed' }), false);
});

test('variables come back when a workflow is loaded', () => {
  const backend: any = { id: 'w1', userId: 'u', name: 'n', canBeListed: false, nodes: [], edges: [], variables: typed, status: 'draft', version: 3, createdAt: 'a', updatedAt: 'b' };
  assert.deepEqual(backendWorkflowToFrontend(backend).variables, variables);
  assert.deepEqual(backendWorkflowToFrontend({ ...backend, variables: undefined }).variables, {});
});

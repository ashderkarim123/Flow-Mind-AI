// Run: npx tsx --test lib/workflow/variables.test.ts
import assert from 'node:assert/strict';
import { test } from 'node:test';
import { parseVariableValue, variableNameProblem, variableValueText } from './variables';

test('names: letters, digits and underscores, not starting with a digit, no repeats', () => {
  assert.equal(variableNameProblem('customer_name', []), null);
  assert.equal(variableNameProblem('_x1', []), null);
  assert.match(variableNameProblem('', [])!, /name/);
  assert.match(variableNameProblem('  ', [])!, /name/);
  assert.match(variableNameProblem('1st', [])!, /letters/);
  assert.match(variableNameProblem('my var', [])!, /letters/);
  assert.match(variableNameProblem('a-b', [])!, /letters/);
  assert.match(variableNameProblem('rows', ['rows'])!, /already/);
});

test('values keep their type: booleans, numbers, JSON; everything else is text', () => {
  assert.equal(parseVariableValue('true'), true);
  assert.equal(parseVariableValue(' false '), false);
  assert.equal(parseVariableValue('25'), 25);
  assert.equal(parseVariableValue('-1.5'), -1.5);
  assert.deepEqual(parseVariableValue('{"a": 1}'), { a: 1 });
  assert.deepEqual(parseVariableValue('[1, 2]'), [1, 2]);
  assert.equal(parseVariableValue('{not json}'), '{not json}');
  assert.equal(parseVariableValue('Acme Ltd'), 'Acme Ltd');
  assert.equal(parseVariableValue(''), '');                       // an empty value stays an empty string, not 0
  assert.equal(parseVariableValue('  hello '), '  hello ');       // text is kept exactly as typed
  assert.equal(parseVariableValue('0x10'), 16);                   // Number() semantics are accepted
});

test('stored values go back into the box as the text that produced them', () => {
  for (const text of ['Acme', '25', 'true', '{"a":1}', '[1,2]']) {
    assert.equal(variableValueText(parseVariableValue(text)), text);
  }
});

import { fromBackendVariables, toBackendVariables } from './variables';

test('variables go to the server typed, JSON as text', () => {
  assert.deepEqual(toBackendVariables({ customer: 'Acme', rows: 25, active: true, filters: { a: [1] }, list: [1, 2] }), {
    customer: { type: 'string', value: 'Acme' }, rows: { type: 'number', value: 25 }, active: { type: 'boolean', value: true },
    filters: { type: 'json', value: '{"a":[1]}' }, list: { type: 'json', value: '[1,2]' },
  });
  assert.deepEqual(toBackendVariables({}), {});
});

test('typed variables come back as plain values, and the round trip is lossless', () => {
  const plain = { customer: 'Acme', rows: 25, active: false, filters: { a: [1] }, list: [1, 2], empty: '' };
  assert.deepEqual(fromBackendVariables(toBackendVariables(plain)), plain);
});

test('variables saved in the plain form before still load, and secrets are never shown', () => {
  assert.deepEqual(fromBackendVariables({ a: 'x', b: 3, c: { nested: true } }), { a: 'x', b: 3, c: { nested: true } });
  assert.deepEqual(fromBackendVariables({ k: { type: 'secret', value: null, secretRef: 'TOKEN' }, v: { type: 'string', value: 'ok' } }), { v: 'ok' });
  assert.deepEqual(fromBackendVariables(undefined), {});
  assert.deepEqual(fromBackendVariables({ j: { type: 'json', value: 'not json' } }), { j: 'not json' });
});

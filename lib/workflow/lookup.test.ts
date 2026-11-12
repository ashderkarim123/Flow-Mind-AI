// Run: npx tsx --test lib/workflow/lookup.test.ts
import assert from 'node:assert/strict';
import { test } from 'node:test';
import { HARDCODED_NODES } from './NodeRegistry';
import { getNodeDefinitionByType, NODE_DEFINITIONS } from './NodeDefinitions';

test('every node in the sidebar opens its own settings (a missing alias left Email, Schedule, Conditional and Variable Setter empty)', () => {
  for (const node of HARDCODED_NODES) {
    const def = getNodeDefinitionByType(node.type);
    assert.ok(def, `"${node.name}" (type ${node.type}) has no definition`);
    if (node.type !== 'ManualTrigger') assert.ok(def.fields.length > 0, `"${node.name}" opens an empty settings panel`);
  }
});

test('the same node found by its backend name opens the same settings as by its sidebar name', () => {
  const pairs: Array<[string, string]> = [
    ['EmailSend', 'SendEmail'], ['Scheduling', 'Schedule'], ['Conditional', 'IfCondition'], ['Variable Setter', 'SetVariable'],
    ['HTTPRequest', 'HttpRequest'], ['JSONParser', 'JsonParser'],
  ];
  for (const [sidebar, backend] of pairs) {
    assert.equal(getNodeDefinitionByType(sidebar), getNodeDefinitionByType(backend), `${sidebar} vs ${backend}`);
  }
});

test('Email settings include the provider choice', () => {
  const names = getNodeDefinitionByType('EmailSend')!.fields.map((f) => f.name);
  assert.ok(names.includes('provider') && names.includes('smtp_user') && names.includes('smtp_pass'));
});

test('every definition is reachable and keyed by the name the server uses', () => {
  for (const key of Object.keys(NODE_DEFINITIONS)) assert.equal(getNodeDefinitionByType(key), NODE_DEFINITIONS[key], key);
});

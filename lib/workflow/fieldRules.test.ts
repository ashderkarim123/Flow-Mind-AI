// Run: npx tsx --test lib/workflow/fieldRules.test.ts
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { test } from 'node:test';
import { NODE_DEFINITIONS, NodeField } from './NodeDefinitions';
import { isFieldShown, presetValues } from './fieldRules';

const def = (key: string) => NODE_DEFINITIONS[key];
const field = (node: string, name: string): NodeField => {
  const f = def(node).fields.find((x) => x.name === name);
  assert.ok(f, `${node}.${name} exists`);
  return f;
};
const shown = (node: string, config: Record<string, any>) => def(node).fields.filter((f) => isFieldShown(f, config)).map((f) => f.name);

test('a field without a rule is always shown', () => {
  assert.equal(isFieldShown({ name: 'x', label: 'X', type: 'text' }, {}), true);
});

test('showWhen follows the other field, and the default stands in while it is unset', () => {
  const rule: NodeField = { name: 'x', label: 'X', type: 'text', showWhen: { field: 'mode', in: ['a', 'b'], default: 'a' } };
  assert.equal(isFieldShown(rule, {}), true);                       // unset -> default a
  assert.equal(isFieldShown(rule, { mode: '' }), true);
  assert.equal(isFieldShown(rule, { mode: 'b' }), true);
  assert.equal(isFieldShown(rule, { mode: 'c' }), false);
  assert.equal(isFieldShown({ ...rule, showWhen: { field: 'mode', in: ['a'] } }, {}), false);   // no default -> hidden
});

test('presets fill in other settings, and nothing for an unknown choice', () => {
  const provider = field('SendEmail', 'provider');
  assert.deepEqual(presetValues(provider, 'gmail'), { smtp_host: 'smtp.gmail.com', smtp_port: 587, smtp_security: 'starttls' });
  assert.deepEqual(presetValues(provider, 'custom'), {});
  assert.deepEqual(presetValues(provider, 'nope'), {});
  assert.deepEqual(presetValues(field('SendEmail', 'smtp_user'), 'x'), {});
});

test('email: the server fields appear only for a custom server', () => {
  assert.ok(shown('SendEmail', { provider: 'custom' }).includes('smtp_host'));
  assert.ok(shown('SendEmail', {}).includes('smtp_host'));                 // nodes saved before providers existed
  assert.ok(!shown('SendEmail', { provider: 'gmail' }).includes('smtp_host'));
  assert.ok(shown('SendEmail', { provider: 'gmail' }).includes('smtp_pass'));
});

test('http: only the fields of the chosen authentication are shown', () => {
  const authFields = (c: Record<string, any>) => shown('HttpRequest', c).filter((n) => n.startsWith('auth_'));
  assert.deepEqual(authFields({}), ['auth_type']);
  assert.deepEqual(authFields({ auth_type: 'basic' }), ['auth_type', 'auth_username', 'auth_password']);
  assert.deepEqual(authFields({ auth_type: 'bearer' }), ['auth_type', 'auth_token']);
  assert.deepEqual(authFields({ auth_type: 'api_key_header' }), ['auth_type', 'auth_key_name', 'auth_key_value']);
  assert.deepEqual(authFields({ auth_type: 'api_key_query' }), ['auth_type', 'auth_key_name', 'auth_key_value']);
});

test('slack: a bot token needs a channel, a webhook does not', () => {
  assert.deepEqual(shown('SlackMessage', {}), ['mode', 'token', 'channel', 'message', 'username']);
  assert.deepEqual(shown('SlackMessage', { mode: 'webhook' }), ['mode', 'webhook_url', 'message', 'username']);
});

test('postgres: a connection string or separate details, never both', () => {
  const conn = (c: Record<string, any>) => shown('PostgresQuery', c).filter((n) => ['connection_string', 'host', 'database', 'username', 'password', 'ssl_mode'].includes(n));
  assert.deepEqual(conn({}), ['connection_string']);
  assert.deepEqual(conn({ connection_method: 'details' }), ['host', 'database', 'username', 'password', 'ssl_mode']);
});

test('every rule and preset in every node refers to something that exists', () => {
  for (const [key, node] of Object.entries(NODE_DEFINITIONS)) {
    const names = new Set(node.fields.map((f) => f.name));
    for (const f of node.fields) {
      if (f.showWhen) {
        assert.ok(names.has(f.showWhen.field), `${key}.${f.name} shows by ${f.showWhen.field}, which is not a field`);
        const controller = node.fields.find((x) => x.name === f.showWhen!.field)!;
        const values = (controller.options || []).map((o) => o.value);
        for (const v of f.showWhen.in) assert.ok(values.includes(v), `${key}.${f.name}: '${v}' is not an option of ${controller.name}`);
      }
      for (const [choice, filled] of Object.entries(f.presets || {})) {
        assert.ok((f.options || []).some((o) => o.value === choice), `${key}.${f.name} has a preset for '${choice}', which is not an option`);
        for (const target of Object.keys(filled)) assert.ok(names.has(target), `${key}.${f.name} preset '${choice}' fills ${target}, which is not a field`);
      }
      if (f.help?.url) assert.match(f.help.url, /^https:\/\//, `${key}.${f.name} help link is https`);
    }
  }
});

test('every field name is unique inside its node', () => {
  for (const [key, node] of Object.entries(NODE_DEFINITIONS)) {
    const names = node.fields.map((f) => f.name);
    assert.equal(new Set(names).size, names.length, `${key} has a repeated field name`);
  }
});

test('the editor mail presets match the ones the server uses', () => {
  const python = readFileSync('backend/nodes/actions/send_email.py', 'utf-8');
  const block = python.slice(python.indexOf('EMAIL_PROVIDERS'), python.indexOf('SECURITY_MODES'));
  const server: Record<string, { host: string; port: number; security: string }> = {};
  for (const m of block.matchAll(/"(\w+)":\s*\{"host":\s*"([^"]+)",\s*"port":\s*(\d+),\s*"security":\s*"(\w+)"\}/g)) {
    server[m[1]] = { host: m[2], port: Number(m[3]), security: m[4] };
  }
  assert.ok(Object.keys(server).length >= 5, 'found the server presets');
  const provider = field('SendEmail', 'provider');
  for (const [name, s] of Object.entries(server)) {
    assert.deepEqual(provider.presets![name], { smtp_host: s.host, smtp_port: s.port, smtp_security: s.security }, `preset ${name}`);
  }
  assert.deepEqual(Object.keys(provider.presets!).sort(), [...Object.keys(server), 'custom'].sort());
});

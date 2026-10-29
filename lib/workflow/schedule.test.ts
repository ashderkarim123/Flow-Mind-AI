// Run: npx tsx --test lib/workflow/schedule.test.ts
import assert from 'node:assert/strict';
import { test } from 'node:test';
import { describe, fromCron, Plan, toCron } from './schedule';

const plan = (over: Partial<Plan>): Plan => ({ mode: 'daily', every: 15, time: '09:00', dow: 1, dom: 1, custom: '', ...over });

test('builds the expected cron for every mode', () => {
  assert.equal(toCron(plan({ mode: 'minutes', every: 1 })), '* * * * *');
  assert.equal(toCron(plan({ mode: 'minutes', every: 5 })), '*/5 * * * *');
  assert.equal(toCron(plan({ mode: 'hours', every: 1 })), '0 * * * *');
  assert.equal(toCron(plan({ mode: 'hours', every: 6 })), '0 */6 * * *');
  assert.equal(toCron(plan({ mode: 'daily', time: '18:30' })), '30 18 * * *');
  assert.equal(toCron(plan({ mode: 'weekdays', time: '08:05' })), '5 8 * * 1-5');
  assert.equal(toCron(plan({ mode: 'weekly', dow: 5, time: '17:00' })), '0 17 * * 5');
  assert.equal(toCron(plan({ mode: 'monthly', dom: 15, time: '07:00' })), '0 7 15 * *');
  assert.equal(toCron(plan({ mode: 'custom', custom: '*/10 9-17 * * 1-5' })), '*/10 9-17 * * 1-5');
});

test('reading a cron back gives the same schedule (round trip)', () => {
  for (const cron of ['* * * * *', '*/5 * * * *', '0 * * * *', '0 */6 * * *', '30 18 * * *', '5 8 * * 1-5', '0 17 * * 5', '0 7 15 * *']) {
    assert.equal(toCron(fromCron(cron)), cron, cron);
  }
});

test('the presets the old dropdown offered are all understood', () => {
  const presets: Record<string, string> = {
    '0 9 * * *': 'Runs every day at 09:00', '0 18 * * *': 'Runs every day at 18:00',
    '0 9 * * 1': 'Runs every Monday at 09:00', '0 9 1 * *': 'Runs on day 1 of every month at 09:00',
    '*/15 * * * *': 'Runs every 15 minutes', '0 * * * *': 'Runs every hour, on the hour',
  };
  for (const [cron, text] of Object.entries(presets)) assert.equal(describe(fromCron(cron)), text);
});

test('anything unusual stays editable as a custom schedule, untouched', () => {
  for (const cron of ['*/10 9-17 * * 1-5', '0 9 1 6 *', '0 9,17 * * *', 'every morning']) {
    const p = fromCron(cron);
    assert.equal(p.mode, 'custom', cron);
    assert.equal(toCron(p), cron);
  }
});

test('an empty value defaults to every day at 9:00', () => {
  assert.equal(toCron(fromCron(undefined)), '0 9 * * *');
});

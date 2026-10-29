/**
 * Friendly schedule <-> cron conversion for the Schedule node (pure functions, unit tested).
 */

export type Mode = 'minutes' | 'hours' | 'daily' | 'weekdays' | 'weekly' | 'monthly' | 'custom';
export interface Plan { mode: Mode; every: number; time: string; dow: number; dom: number; custom: string }

export const DAYS = ['Sunday', 'Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday'];
export const pad = (n: number) => String(n).padStart(2, '0');

export function toCron(p: Plan): string {
  const [h, m] = p.time.split(':').map(Number);
  switch (p.mode) {
    case 'minutes': return p.every <= 1 ? '* * * * *' : `*/${p.every} * * * *`;
    case 'hours': return p.every <= 1 ? '0 * * * *' : `0 */${p.every} * * *`;
    case 'daily': return `${m} ${h} * * *`;
    case 'weekdays': return `${m} ${h} * * 1-5`;
    case 'weekly': return `${m} ${h} * * ${p.dow}`;
    case 'monthly': return `${m} ${h} ${p.dom} * *`;
    default: return p.custom;
  }
}

export function fromCron(cron?: string): Plan {
  const base: Plan = { mode: 'daily', every: 15, time: '09:00', dow: 1, dom: 1, custom: cron || '' };
  const f = (cron || '').trim().split(/\s+/);
  if (f.length !== 5) return cron ? { ...base, mode: 'custom' } : base;
  const [min, hour, dom, mon, dow] = f;
  const num = (s: string) => /^\d+$/.test(s);
  const time = num(min) && num(hour) ? `${pad(+hour)}:${pad(+min)}` : base.time;
  if (cron === '* * * * *') return { ...base, mode: 'minutes', every: 1 };
  if (/^\*\/\d+$/.test(min) && hour === '*' && dom === '*' && mon === '*' && dow === '*') return { ...base, mode: 'minutes', every: +min.slice(2) };
  if (min === '0' && hour === '*' && dom === '*' && mon === '*' && dow === '*') return { ...base, mode: 'hours', every: 1 };
  if (min === '0' && /^\*\/\d+$/.test(hour) && dom === '*' && mon === '*' && dow === '*') return { ...base, mode: 'hours', every: +hour.slice(2) };
  if (num(min) && num(hour) && mon === '*') {
    if (dom === '*' && dow === '*') return { ...base, mode: 'daily', time };
    if (dom === '*' && dow === '1-5') return { ...base, mode: 'weekdays', time };
    if (dom === '*' && num(dow)) return { ...base, mode: 'weekly', time, dow: +dow };
    if (num(dom) && dow === '*') return { ...base, mode: 'monthly', time, dom: +dom };
  }
  return { ...base, mode: 'custom' };
}

export function describe(p: Plan): string {
  switch (p.mode) {
    case 'minutes': return p.every <= 1 ? 'Runs every minute' : `Runs every ${p.every} minutes`;
    case 'hours': return p.every <= 1 ? 'Runs every hour, on the hour' : `Runs every ${p.every} hours`;
    case 'daily': return `Runs every day at ${p.time}`;
    case 'weekdays': return `Runs Monday to Friday at ${p.time}`;
    case 'weekly': return `Runs every ${DAYS[p.dow]} at ${p.time}`;
    case 'monthly': return `Runs on day ${p.dom} of every month at ${p.time}`;
    default: return 'Runs on a custom schedule';
  }
}


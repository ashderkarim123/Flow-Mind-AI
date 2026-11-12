'use client';

import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Textarea } from '@/components/ui/textarea';
import { Switch } from '@/components/ui/switch';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';

/** What the engine understands under a node's config._settings (see backend executor/engine.py). */
export interface NodeSettingsValue {
  retry_on_fail?: boolean;
  max_tries?: number;
  wait_ms?: number;
  timeout_s?: number;
  on_error?: 'stop' | 'continue' | 'fallback';
  fallback_value?: string;
  notes?: string;
}

const row = 'flex items-center justify-between gap-4';
const hint = 'text-xs text-gray-400 mt-1';
const item = 'text-white hover:bg-slate-800 focus:bg-slate-800 focus:text-white';

/** The n8n-style "Settings" block of a node: retry on fail, what to do on error, and a note. */
export default function NodeSettings({ value, onChange }: { value?: NodeSettingsValue; onChange: (v: NodeSettingsValue) => void }) {
  const s = value || {};
  const set = (patch: NodeSettingsValue) => onChange({ ...s, ...patch });

  return (
    <details className="rounded-lg border border-slate-700 bg-slate-800/40 group" open={!!(s.retry_on_fail || s.timeout_s || (s.on_error && s.on_error !== 'stop') || s.notes)}>
      <summary className="cursor-pointer select-none px-4 py-3 text-sm font-semibold text-white">Node settings</summary>
      <div className="space-y-5 px-4 pb-4">
        <div>
          <div className={row}>
            <Label className="text-white">Retry if this step fails</Label>
            <Switch checked={!!s.retry_on_fail} onCheckedChange={(on) => set({ retry_on_fail: on })} />
          </div>
          <p className={hint}>Tries again after a short wait. Useful for steps that call other services.</p>
          {s.retry_on_fail && (
            <div className="mt-3 grid grid-cols-2 gap-3">
              <div>
                <Label className="text-gray-300 text-xs">Max tries (1–5)</Label>
                <Input type="number" min={1} max={5} value={s.max_tries ?? 3}
                  onChange={(e) => set({ max_tries: Number(e.target.value) })} className="bg-slate-800 border-slate-700 text-white" />
              </div>
              <div>
                <Label className="text-gray-300 text-xs">Wait between tries (ms)</Label>
                <Input type="number" min={0} max={60000} step={100} value={s.wait_ms ?? 1000}
                  onChange={(e) => set({ wait_ms: Number(e.target.value) })} className="bg-slate-800 border-slate-700 text-white" />
              </div>
            </div>
          )}
        </div>

        <div>
          <Label className="text-white">If this step fails</Label>
          <Select value={s.on_error || 'stop'} onValueChange={(v) => set({ on_error: v as 'stop' | 'continue' | 'fallback' })}>
            <SelectTrigger className="mt-2 bg-slate-800 border-slate-700 text-white"><SelectValue /></SelectTrigger>
            <SelectContent className="bg-slate-900 border-slate-700 text-white">
              <SelectItem value="stop" className={item}>Stop the workflow</SelectItem>
              <SelectItem value="continue" className={item}>Carry on (the error is passed on as this step&apos;s output)</SelectItem>
              <SelectItem value="fallback" className={item}>Use a fallback value and carry on</SelectItem>
            </SelectContent>
          </Select>
          {s.on_error === 'fallback' && (
            <div className="mt-3">
              <Label className="text-gray-300 text-xs">Fallback value</Label>
              <Input value={s.fallback_value ?? ''} placeholder="for example: no data  or  {&quot;price&quot;: 0}"
                onChange={(e) => set({ fallback_value: e.target.value })} className="bg-slate-800 border-slate-700 text-white" />
              <p className={hint}>Later steps read it as {'{{$node.<id>.result}}'}. Numbers, true/false and JSON keep their type.</p>
            </div>
          )}
          <p className={hint}>
            {s.on_error === 'fallback' || s.on_error === 'continue'
              ? 'The failure is still recorded in the run, so you can see it on the Executions page.'
              : 'The run stops and shows what went wrong and how to fix it.'}
          </p>
        </div>

        <div>
          <Label className="text-white">Time limit for this step (seconds)</Label>
          <Input type="number" min={0} max={600} value={s.timeout_s ?? 0}
            onChange={(e) => set({ timeout_s: Number(e.target.value) })} className="mt-2 bg-slate-800 border-slate-700 text-white" />
          <p className={hint}>0 means no limit of its own (the workspace time limit still applies).</p>
        </div>

        <div>
          <Label className="text-white">Notes</Label>
          <Textarea rows={2} value={s.notes || ''} onChange={(e) => set({ notes: e.target.value })}
            placeholder="What does this step do? (only for you and your team)" className="mt-2 bg-slate-800 border-slate-700 text-white" />
        </div>
      </div>
    </details>
  );
}

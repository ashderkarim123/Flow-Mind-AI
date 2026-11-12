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
  on_error?: 'stop' | 'continue';
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
    <details className="rounded-lg border border-slate-700 bg-slate-800/40 group" open={!!(s.retry_on_fail || s.on_error === 'continue' || s.notes)}>
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
          <Select value={s.on_error || 'stop'} onValueChange={(v) => set({ on_error: v as 'stop' | 'continue' })}>
            <SelectTrigger className="mt-2 bg-slate-800 border-slate-700 text-white"><SelectValue /></SelectTrigger>
            <SelectContent className="bg-slate-900 border-slate-700 text-white">
              <SelectItem value="stop" className={item}>Stop the workflow</SelectItem>
              <SelectItem value="continue" className={item}>Carry on (the error is passed on as this step&apos;s output)</SelectItem>
            </SelectContent>
          </Select>
          <p className={hint}>With "carry on", later steps can read {'{{$node.<id>.error}}'}.</p>
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

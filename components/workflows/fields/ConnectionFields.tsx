'use client';

/**
 * Beginner-friendly config fields for the node settings window:
 *   LocalModelField   dropdown of the models installed on the local Ollama server
 *   McpServerField    pick a connected tool server           McpServersField  tick several (for AI steps)
 *   McpToolField      pick one of that server's tools         McpArgsField     auto-built form for the tool's inputs
 *   SchedulePicker    "every day at 9:00" instead of a cron expression
 */

import { useCallback, useEffect, useMemo, useState } from 'react';
import Link from 'next/link';
import { Loader2, RefreshCw } from 'lucide-react';
import { aiToolsApi, LocalStatus, McpServerInfo, McpTool } from '@/lib/api/aiTools';
import { DAYS, describe, fromCron, Mode, Plan, toCron } from '@/lib/workflow/schedule';

const control = 'w-full rounded-md border border-slate-700 bg-slate-800 px-3 py-2 text-sm text-white focus:outline-none focus:ring-2 focus:ring-[#1D4ED8]/40';

// ---------------------------------------------------------------------------
// Local model picker
// ---------------------------------------------------------------------------

export function LocalModelField({ value, onChange, baseUrl }: { value?: string; onChange: (v: string) => void; baseUrl?: string }) {
  const [status, setStatus] = useState<LocalStatus | null>(null);
  const [loading, setLoading] = useState(true);

  const load = useCallback(() => {
    setLoading(true);
    aiToolsApi.localModels(baseUrl).then(setStatus).catch((e) => setStatus({ baseUrl: baseUrl ?? '', reachable: false, models: [], error: e.message })).finally(() => setLoading(false));
  }, [baseUrl]);
  useEffect(load, [load]);

  const models = status?.models ?? [];
  const missing = !!value && status?.reachable && models.length > 0 && !models.includes(value);

  return (
    <div className="w-full space-y-1.5">
      <div className="flex gap-2">
        {status?.reachable && models.length > 0 ? (
          <select className={control} value={value || ''} onChange={(e) => onChange(e.target.value)}>
            {!value && <option value="">Choose a model…</option>}
            {missing && <option value={value}>{value} (not installed)</option>}
            {models.map((m) => <option key={m} value={m}>{m}</option>)}
          </select>
        ) : (
          <input className={control} value={value || ''} onChange={(e) => onChange(e.target.value)} placeholder="e.g. qwen2.5:7b" />
        )}
        <button type="button" onClick={load} title="Refresh the list" className="rounded-md border border-slate-700 px-2 text-slate-400 hover:text-white">
          {loading ? <Loader2 className="h-4 w-4 animate-spin" /> : <RefreshCw className="h-4 w-4" />}
        </button>
      </div>
      {!loading && status && !status.reachable && <p className="text-xs text-amber-300">{status.error} Type the model name instead.</p>}
      {!loading && status?.reachable && models.length === 0 && (
        <p className="text-xs text-amber-300">No models installed yet — run <code>ollama pull qwen2.5:7b</code> (see <Link href="/connections" className="underline">Connections</Link>).</p>
      )}
      {missing && <p className="text-xs text-amber-300">Install it first: <code>ollama pull {value}</code></p>}
    </div>
  );
}

// ---------------------------------------------------------------------------
// MCP pickers
// ---------------------------------------------------------------------------

function useMcpServers() {
  const [servers, setServers] = useState<McpServerInfo[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  useEffect(() => { aiToolsApi.mcp.list().then(setServers).catch((e) => setError(e.message)); }, []);
  return { servers, error };
}

const NO_SERVERS = (
  <p className="text-xs text-amber-300">
    No tool servers connected yet. <Link href="/connections" className="underline">Add one on the Connections page</Link>, then come back.
  </p>
);

export function McpServerField({ value, onChange }: { value?: string; onChange: (v: string) => void }) {
  const { servers, error } = useMcpServers();
  if (error) return <p className="text-xs text-red-300">{error}</p>;
  if (!servers) return <Loader2 className="h-4 w-4 animate-spin text-slate-400" />;
  if (servers.length === 0) return NO_SERVERS;
  return (
    <select className={control} value={value || ''} onChange={(e) => onChange(e.target.value)}>
      <option value="">Choose a tool server…</option>
      {servers.map((s) => <option key={s.id} value={s.name}>{s.name}</option>)}
    </select>
  );
}

export function McpServersField({ value, onChange }: { value?: string[] | string; onChange: (v: string[]) => void }) {
  const { servers, error } = useMcpServers();
  const selected = useMemo(() => (Array.isArray(value) ? value : (value || '').split(',').map((s) => s.trim()).filter(Boolean)), [value]);
  if (error) return <p className="text-xs text-red-300">{error}</p>;
  if (!servers) return <Loader2 className="h-4 w-4 animate-spin text-slate-400" />;
  if (servers.length === 0) return NO_SERVERS;
  return (
    <div className="w-full space-y-2">
      {servers.map((s) => (
        <label key={s.id} className="flex cursor-pointer items-center gap-2 text-sm text-slate-200">
          <input type="checkbox" checked={selected.includes(s.name)}
            onChange={(e) => onChange(e.target.checked ? [...selected, s.name] : selected.filter((n) => n !== s.name))} />
          {s.name}
        </label>
      ))}
      <p className="text-xs text-slate-400">The AI decides when to use these tools. Works best with models that support tools (e.g. qwen2.5, llama3.1).</p>
    </div>
  );
}

const toolCache = new Map<string, { at: number; tools: McpTool[] }>();   // # ponytail: 60 s cache; spawning stdio servers is slow

function useMcpTools(serverName?: string) {
  const { servers } = useMcpServers();
  const [tools, setTools] = useState<McpTool[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const id = servers?.find((s) => s.name === serverName)?.id;

  useEffect(() => {
    setTools(null); setError(null);
    if (!serverName) return;
    if (servers && !id) { setError(`"${serverName}" is not connected any more.`); return; }
    if (!id) return;
    const hit = toolCache.get(id);
    if (hit && Date.now() - hit.at < 60_000) { setTools(hit.tools); return; }
    let live = true;
    aiToolsApi.mcp.tools(id)
      .then((t) => { toolCache.set(id, { at: Date.now(), tools: t }); if (live) setTools(t); })
      .catch((e) => live && setError(e.message));
    return () => { live = false; };
  }, [serverName, id, servers]);
  return { tools, error };
}

export function McpToolField({ server, value, onChange }: { server?: string; value?: string; onChange: (v: string) => void }) {
  const { tools, error } = useMcpTools(server);
  if (!server) return <p className="text-xs text-slate-400">Choose a tool server first.</p>;
  if (error) return <p className="text-xs text-red-300">{error}</p>;
  if (!tools) return <span className="flex items-center gap-2 text-xs text-slate-400"><Loader2 className="h-4 w-4 animate-spin" />Asking the server what it can do…</span>;
  const current = tools.find((t) => t.name === value);
  return (
    <div className="w-full space-y-1.5">
      <select className={control} value={value || ''} onChange={(e) => onChange(e.target.value)}>
        <option value="">Choose a tool…</option>
        {tools.map((t) => <option key={t.name} value={t.name}>{t.name}</option>)}
      </select>
      {current?.description && <p className="text-xs text-slate-400">{current.description.slice(0, 300)}</p>}
    </div>
  );
}

type ArgTypes = Record<string, string>;
const TYPED = new Set(['integer', 'number', 'boolean', 'object', 'array']);

export function McpArgsField({ server, tool, value, onChange }: {
  server?: string; tool?: string; value?: Record<string, any> | string;
  onChange: (args: Record<string, any>, types: ArgTypes) => void;
}) {
  const { tools } = useMcpTools(server);
  const schema = tools?.find((t) => t.name === tool)?.inputSchema;
  const props = schema?.properties ?? {};
  const required = new Set(schema?.required ?? []);
  const args: Record<string, any> = value && typeof value === 'object' ? value : {};

  if (!tool) return <p className="text-xs text-slate-400">Choose a tool to see what it needs.</p>;
  if (!schema) return null;
  if (Object.keys(props).length === 0) return <p className="text-xs text-slate-400">This tool needs no inputs.</p>;

  const types: ArgTypes = Object.fromEntries(Object.entries(props).filter(([, p]: [string, any]) => TYPED.has(p.type)).map(([k, p]: [string, any]) => [k, p.type]));
  // empty fields are not sent, so optional inputs keep the tool's own defaults
  const update = (key: string, v: any) => {
    const next = { ...args, [key]: v };
    if (v === '' || v === undefined) delete next[key];
    onChange(next, types);
  };

  return (
    <div className="w-full space-y-4">
      {Object.entries(props).map(([key, prop]: [string, any]) => (
        <div key={key}>
          <label className="mb-1 block text-sm font-medium text-slate-200">
            {prop.title || key}{required.has(key) && <span className="text-red-400"> *</span>}
          </label>
          {prop.description && <p className="mb-1 text-xs italic text-slate-400">{prop.description}</p>}
          {prop.enum ? (
            <select className={control} value={args[key] ?? ''} onChange={(e) => update(key, e.target.value)}>
              <option value="">—</option>
              {prop.enum.map((o: string) => <option key={o} value={o}>{o}</option>)}
            </select>
          ) : prop.type === 'boolean' ? (
            <label className="flex items-center gap-2 text-sm text-slate-200">
              <input type="checkbox" checked={args[key] === true || args[key] === 'true'} onChange={(e) => update(key, e.target.checked)} /> Yes
            </label>
          ) : prop.type === 'object' || prop.type === 'array' ? (
            <textarea className={`${control} font-mono`} rows={3} value={typeof args[key] === 'string' ? args[key] : args[key] ? JSON.stringify(args[key]) : ''}
              placeholder={prop.type === 'array' ? '["a", "b"]' : '{"key": "value"}'} onChange={(e) => update(key, e.target.value)} />
          ) : (
            <input className={control} value={args[key] ?? ''} placeholder={prop.default !== undefined ? `default: ${prop.default}` : prop.type === 'string' ? 'text, or use {{…}} from an earlier step' : ''}
              onChange={(e) => update(key, e.target.value)} />
          )}
        </div>
      ))}
    </div>
  );
}

// ---------------------------------------------------------------------------
// Schedule picker
// ---------------------------------------------------------------------------

export function SchedulePicker({ value, onChange }: { value?: string; onChange: (cron: string) => void }) {
  const [plan, setPlan] = useState<Plan>(() => fromCron(value));
  const set = (patch: Partial<Plan>) => {
    const next = { ...plan, ...patch };
    setPlan(next);
    onChange(toCron(next));
  };
  const number = (key: 'every' | 'dom', min: number, max: number) => (
    <input type="number" min={min} max={max} className={`${control} w-24`} value={plan[key]}
      onChange={(e) => set({ [key]: Math.min(max, Math.max(min, parseInt(e.target.value) || min)) } as Partial<Plan>)} />
  );
  const time = <input type="time" className={`${control} w-36`} value={plan.time} onChange={(e) => set({ time: e.target.value || '09:00' })} />;

  return (
    <div className="w-full space-y-2">
      <select className={control} value={plan.mode} onChange={(e) => set({ mode: e.target.value as Mode })}>
        <option value="minutes">Every few minutes</option>
        <option value="hours">Every few hours</option>
        <option value="daily">Every day</option>
        <option value="weekdays">Every weekday (Mon–Fri)</option>
        <option value="weekly">Once a week</option>
        <option value="monthly">Once a month</option>
        <option value="custom">Custom (advanced)</option>
      </select>
      <div className="flex flex-wrap items-center gap-2 text-sm text-slate-300">
        {plan.mode === 'minutes' && <>Every {number('every', 1, 59)} minute(s)</>}
        {plan.mode === 'hours' && <>Every {number('every', 1, 23)} hour(s)</>}
        {(plan.mode === 'daily' || plan.mode === 'weekdays') && <>At {time}</>}
        {plan.mode === 'weekly' && <>
          On <select className={`${control} w-40`} value={plan.dow} onChange={(e) => set({ dow: +e.target.value })}>{DAYS.map((d, i) => <option key={d} value={i}>{d}</option>)}</select> at {time}
        </>}
        {plan.mode === 'monthly' && <>On day {number('dom', 1, 28)} at {time}</>}
        {plan.mode === 'custom' && <input className={`${control} font-mono`} value={plan.custom} placeholder="*/10 * * * *" onChange={(e) => set({ custom: e.target.value })} />}
      </div>
      <p className="text-xs text-slate-400">{describe(plan)}{plan.mode !== 'custom' && <span className="opacity-60"> · {toCron(plan)}</span>}</p>
    </div>
  );
}

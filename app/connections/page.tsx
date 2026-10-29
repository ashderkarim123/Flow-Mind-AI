'use client';

import { useCallback, useEffect, useState } from 'react';
import {
  AlertTriangle, Check, CheckCircle2, Copy, Cpu, Globe, Loader2, Plug, Plus, RefreshCw, Terminal, Trash2, XCircle,
} from 'lucide-react';
import DashboardLayout from '@/components/dashboard/DashboardLayout';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Textarea } from '@/components/ui/textarea';
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle } from '@/components/ui/dialog';
import { aiToolsApi, AiStatus, McpCatalogEntry, McpServerInfo, McpServerInput } from '@/lib/api/aiTools';

const RECOMMENDED = [
  { model: 'qwen2.5:7b', note: 'Great all-rounder; follows instructions and uses tools well', size: '≈ 4.7 GB' },
  { model: 'llama3.2:3b', note: 'Small and fast — fine for simple tasks on a modest PC', size: '≈ 2 GB' },
  { model: 'qwen3:8b', note: 'Newer and stronger reasoning, needs a bit more memory', size: '≈ 5 GB' },
];

function CopyCommand({ command }: { command: string }) {
  const [copied, setCopied] = useState(false);
  return (
    <button
      type="button"
      onClick={() => { navigator.clipboard.writeText(command); setCopied(true); setTimeout(() => setCopied(false), 1500); }}
      className="group flex w-full items-center justify-between gap-3 rounded-lg border border-white/10 bg-black/40 px-3 py-2 text-left font-mono text-sm text-white/80 hover:border-white/25"
    >
      <span className="truncate"><Terminal className="mr-2 inline w-3.5 h-3.5 text-white/40" />{command}</span>
      {copied ? <Check className="w-4 h-4 text-green-400" /> : <Copy className="w-4 h-4 text-white/30 group-hover:text-white/70" />}
    </button>
  );
}

function Card({ title, icon: Icon, children, action }: { title: string; icon: any; children: React.ReactNode; action?: React.ReactNode }) {
  return (
    <section className="rounded-2xl border border-white/[0.06] bg-white/[0.03] p-6">
      <div className="mb-4 flex items-center justify-between gap-3">
        <h2 className="flex items-center gap-2 text-lg font-semibold text-white"><Icon className="w-5 h-5 text-blue-400" />{title}</h2>
        {action}
      </div>
      {children}
    </section>
  );
}

// ---------------------------------------------------------------------------
// Add-server dialog
// ---------------------------------------------------------------------------

function AddServerDialog({ open, onOpenChange, onAdded }: { open: boolean; onOpenChange: (o: boolean) => void; onAdded: () => void }) {
  const [catalog, setCatalog] = useState<{ servers: McpCatalogEntry[]; canAddStdio: boolean; stdioEnabled: boolean } | null>(null);
  const [picked, setPicked] = useState<McpCatalogEntry | null>(null);
  const [name, setName] = useState('');
  const [url, setUrl] = useState('');
  const [headerName, setHeaderName] = useState('Authorization');
  const [headerValue, setHeaderValue] = useState('');
  const [command, setCommand] = useState('');
  const [args, setArgs] = useState('');
  const [env, setEnv] = useState('');
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!open) return;
    setPicked(null); setError(null);
    aiToolsApi.mcp.catalog().then(setCatalog).catch((e) => setError(e.message));
  }, [open]);

  const choose = (entry: McpCatalogEntry) => {
    setPicked(entry); setName(entry.key === 'remote' ? '' : entry.name); setUrl(entry.url ?? '');
    setCommand(entry.command ?? ''); setArgs((entry.args ?? []).join('\n')); setEnv(''); setHeaderValue(''); setError(null);
  };

  const save = async () => {
    if (!picked) return;
    setBusy(true); setError(null);
    const input: McpServerInput = { name: name.trim(), transport: picked.transport };
    if (picked.transport === 'http') {
      input.url = url.trim();
      if (headerValue.trim()) input.headers = { [headerName.trim() || 'Authorization']: headerValue.trim() };
    } else {
      input.command = command.trim();
      input.args = args.split('\n').map((a) => a.trim()).filter(Boolean);
      input.env = Object.fromEntries(env.split('\n').map((l) => l.trim()).filter((l) => l.includes('=')).map((l) => [l.slice(0, l.indexOf('=')), l.slice(l.indexOf('=') + 1)]));
    }
    try {
      await aiToolsApi.mcp.add(input);
      onAdded();
      onOpenChange(false);
    } catch (e: any) {
      setError(e.message || 'Could not add the server.');
    } finally {
      setBusy(false);
    }
  };

  const field = 'bg-white/5 border-white/10 text-white';
  return (
    <Dialog open={open} onOpenChange={(o) => !busy && onOpenChange(o)}>
      <DialogContent className="max-w-2xl bg-[#120d09] border-white/10 text-white">
        <DialogHeader>
          <DialogTitle>{picked ? `Connect: ${picked.name}` : 'Add a tool server'}</DialogTitle>
          <DialogDescription className="text-white/60">
            {picked ? picked.description : 'Pick something to connect. Your AI and workflows can then use its tools.'}
          </DialogDescription>
        </DialogHeader>

        {!picked ? (
          <div className="grid gap-3 sm:grid-cols-2">
            {catalog?.servers.map((entry) => {
              const blocked = entry.transport === 'stdio' && !catalog.canAddStdio;
              return (
                <button key={entry.key} type="button" disabled={blocked} onClick={() => choose(entry)}
                  className="rounded-xl border border-white/10 bg-white/[0.03] p-4 text-left transition hover:border-blue-500/40 disabled:cursor-not-allowed disabled:opacity-45">
                  <p className="flex items-center gap-2 font-medium">
                    {entry.transport === 'http' ? <Globe className="w-4 h-4 text-blue-400" /> : <Terminal className="w-4 h-4 text-blue-400" />}{entry.name}
                  </p>
                  <p className="mt-1 text-sm text-white/60">{entry.description}</p>
                  {entry.requires && <p className="mt-2 text-xs text-white/40">Needs {entry.requires} on the server</p>}
                  {blocked && (
                    <p className="mt-2 text-xs text-amber-300">
                      {catalog.stdioEnabled ? 'Only administrators can add these.' : 'Turned off by the server administrator (MCP_ALLOW_STDIO).'}
                    </p>
                  )}
                </button>
              );
            }) ?? <p className="text-sm text-white/50"><Loader2 className="inline w-4 h-4 mr-2 animate-spin" />Loading…</p>}
          </div>
        ) : (
          <div className="space-y-4">
            <label className="block text-sm">Name
              <Input value={name} onChange={(e) => setName(e.target.value)} placeholder="e.g. Web search" className={`mt-1 ${field}`} />
            </label>
            {picked.transport === 'http' ? (
              <>
                <label className="block text-sm">Server address
                  <Input value={url} onChange={(e) => setUrl(e.target.value)} placeholder="https://example.com/mcp" className={`mt-1 ${field}`} />
                </label>
                <details className="rounded-lg border border-white/10 p-3 text-sm">
                  <summary className="cursor-pointer text-white/70">Needs a password or API key? (optional)</summary>
                  <div className="mt-3 grid gap-3 sm:grid-cols-2">
                    <label>Header name<Input value={headerName} onChange={(e) => setHeaderName(e.target.value)} className={`mt-1 ${field}`} /></label>
                    <label>Value<Input type="password" value={headerValue} onChange={(e) => setHeaderValue(e.target.value)} placeholder="Bearer sk-…" className={`mt-1 ${field}`} /></label>
                  </div>
                  <p className="mt-2 text-xs text-white/40">Stored encrypted and never shown again.</p>
                </details>
              </>
            ) : (
              <>
                <label className="block text-sm">Command
                  <Input value={command} onChange={(e) => setCommand(e.target.value)} className={`mt-1 font-mono ${field}`} />
                </label>
                <label className="block text-sm">Arguments <span className="text-white/40">(one per line)</span>
                  <Textarea rows={3} value={args} onChange={(e) => setArgs(e.target.value)} className={`mt-1 font-mono ${field}`} />
                </label>
                <label className="block text-sm">Environment variables <span className="text-white/40">(optional, NAME=value per line — stored encrypted)</span>
                  <Textarea rows={2} value={env} onChange={(e) => setEnv(e.target.value)} className={`mt-1 font-mono ${field}`} />
                </label>
              </>
            )}
            {picked.hint && <p className="text-xs text-white/50">{picked.hint}</p>}
          </div>
        )}

        {error && <p className="rounded-lg border border-red-500/30 bg-red-500/10 p-3 text-sm text-red-300">{error}</p>}
        <DialogFooter>
          {picked && <Button variant="ghost" className="text-white/70" onClick={() => setPicked(null)} disabled={busy}>Back</Button>}
          {picked && (
            <Button className="bg-[#1D4ED8] hover:bg-[#1E40AF] text-white" onClick={save} disabled={busy || !name.trim()}>
              {busy && <Loader2 className="w-4 h-4 mr-2 animate-spin" />}Connect
            </Button>
          )}
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

// ---------------------------------------------------------------------------
// Page
// ---------------------------------------------------------------------------

type TestState = { busy?: boolean; ok?: boolean; message?: string };

export default function ConnectionsPage() {
  const [status, setStatus] = useState<AiStatus | null>(null);
  const [servers, setServers] = useState<McpServerInfo[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [adding, setAdding] = useState(false);
  const [tests, setTests] = useState<Record<string, TestState>>({});

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const [s, list] = await Promise.all([aiToolsApi.status(), aiToolsApi.mcp.list()]);
      setStatus(s); setServers(list); setError(null);
    } catch (e: any) {
      setError(e.message || 'Could not load connections');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { load(); }, [load]);

  const test = async (id: string) => {
    setTests((t) => ({ ...t, [id]: { busy: true } }));
    try {
      const r = await aiToolsApi.mcp.test(id);
      setTests((t) => ({ ...t, [id]: { ok: r.ok, message: r.ok ? `Working — ${r.toolCount} tool${r.toolCount === 1 ? '' : 's'}: ${r.tools.slice(0, 6).join(', ')}${r.toolCount > 6 ? '…' : ''}` : r.error ?? 'Failed' } }));
    } catch (e: any) {
      setTests((t) => ({ ...t, [id]: { ok: false, message: e.message } }));
    }
  };

  const remove = async (server: McpServerInfo) => {
    if (!window.confirm(`Disconnect "${server.name}"? Workflows that use it will stop working until you add it again.`)) return;
    try { await aiToolsApi.mcp.remove(server.id); await load(); } catch (e: any) { setError(e.message); }
  };

  const local = status?.local;
  return (
    <DashboardLayout>
      <div className="mx-auto max-w-5xl space-y-6 p-6 lg:p-8">
        <div className="flex items-end justify-between gap-4">
          <div>
            <h1 className="flex items-center gap-3 text-3xl font-bold text-white"><Plug className="w-8 h-8 text-blue-400" />Connections</h1>
            <p className="mt-1 text-white/60">Connect the AI models and tools your workflows can use.</p>
          </div>
          <Button variant="ghost" className="text-white/60 hover:text-white" onClick={load}><RefreshCw className={`w-4 h-4 mr-2 ${loading ? 'animate-spin' : ''}`} />Refresh</Button>
        </div>
        {error && <p className="rounded-lg border border-red-500/30 bg-red-500/10 p-3 text-sm text-red-300">{error}</p>}

        {/* ---- AI models ---- */}
        <Card title="AI models" icon={Cpu}>
          <div className="space-y-5">
            <div className="flex items-start gap-3 rounded-xl border border-white/10 bg-black/20 p-4">
              {status?.assistant.ready ? <CheckCircle2 className="mt-0.5 w-5 h-5 text-green-400" /> : <AlertTriangle className="mt-0.5 w-5 h-5 text-amber-400" />}
              <div className="text-sm">
                <p className="font-medium text-white">
                  AI helper (builds workflows from your description): {status?.assistant.ready ? 'ready' : 'not ready'}
                </p>
                <p className="text-white/60">
                  {status?.assistant.ready
                    ? `Using ${status.assistant.model} (${status.assistant.provider === 'local' ? 'on this server — works offline' : status.assistant.provider}).`
                    : status?.assistant.problem ?? 'Checking…'}
                </p>
              </div>
            </div>

            <div>
              <p className="mb-2 flex items-center gap-2 text-sm font-medium text-white">
                Local AI (Ollama) — free, private, works without internet
                <span className={`rounded-full px-2 py-0.5 text-xs ${local?.reachable ? 'bg-green-500/15 text-green-400' : 'bg-amber-500/15 text-amber-300'}`}>
                  {local?.reachable ? 'running' : 'not running'}
                </span>
              </p>
              {local?.reachable ? (
                <div className="flex flex-wrap gap-2">
                  {local.models.length === 0 && <p className="text-sm text-white/60">Ollama is running but has no models yet — install one below.</p>}
                  {local.models.map((m) => <span key={m} className="rounded-lg border border-white/10 bg-white/5 px-3 py-1 text-sm text-white/80">{m}</span>)}
                </div>
              ) : (
                <p className="text-sm text-white/60">{local?.error}</p>
              )}
              <details className="mt-4 rounded-xl border border-white/10 p-4 text-sm" open={!!local && (!local.reachable || local.models.length === 0)}>
                <summary className="cursor-pointer font-medium text-white">How to set up a local model</summary>
                <ol className="mt-3 list-decimal space-y-3 pl-5 text-white/70">
                  <li>Install Ollama from <span className="text-white">ollama.com</span> on the computer that runs FlowMind&apos;s server.</li>
                  <li>Download a model (pick one):
                    <div className="mt-2 space-y-2">
                      {RECOMMENDED.map((r) => (
                        <div key={r.model}>
                          <CopyCommand command={`ollama pull ${r.model}`} />
                          <p className="mt-1 text-xs text-white/40">{r.note} · {r.size}</p>
                        </div>
                      ))}
                    </div>
                  </li>
                  <li>In your workflow, add the <span className="text-white">Local LLM (Ollama)</span> step and choose the model from the list.</li>
                </ol>
              </details>
            </div>

            <div>
              <p className="mb-2 text-sm font-medium text-white">Cloud AI keys on this server</p>
              <div className="flex flex-wrap gap-2 text-sm">
                {status && Object.entries(status.cloudKeys).map(([provider, set]) => (
                  <span key={provider} className={`flex items-center gap-1.5 rounded-lg border px-3 py-1 capitalize ${set ? 'border-green-500/30 bg-green-500/10 text-green-300' : 'border-white/10 text-white/40'}`}>
                    {set ? <CheckCircle2 className="w-3.5 h-3.5" /> : <XCircle className="w-3.5 h-3.5" />}{provider}
                  </span>
                ))}
              </div>
              <p className="mt-2 text-xs text-white/40">You can also paste your own key into a step, or save it under Credentials.</p>
            </div>
          </div>
        </Card>

        {/* ---- MCP ---- */}
        <Card title="Tools (MCP)" icon={Plug}
          action={<Button className="bg-[#1D4ED8] hover:bg-[#1E40AF] text-white" onClick={() => setAdding(true)}><Plus className="w-4 h-4 mr-2" />Add a tool server</Button>}>
          <p className="mb-4 text-sm text-white/60">
            Tool servers give your workflows and AI new abilities — browse the web, read files, use other apps. They follow an open
            standard called MCP, so thousands exist. Add one, then use the <span className="text-white">MCP Tool</span> step, or
            let an AI step choose tools by itself.
          </p>
          {servers.length === 0 ? (
            <p className="rounded-xl border border-dashed border-white/10 p-8 text-center text-sm text-white/50">No tool servers connected yet.</p>
          ) : (
            <ul className="space-y-3">
              {servers.map((server) => {
                const t = tests[server.id];
                return (
                  <li key={server.id} className="rounded-xl border border-white/10 bg-black/20 p-4">
                    <div className="flex flex-wrap items-center justify-between gap-3">
                      <div>
                        <p className="flex items-center gap-2 font-medium text-white">
                          {server.name}
                          <span className="rounded-full bg-white/10 px-2 py-0.5 text-xs text-white/60">{server.transport === 'http' ? 'remote' : 'local command'}</span>
                          {server.headerNames.length > 0 && <span className="rounded-full bg-white/10 px-2 py-0.5 text-xs text-white/60">secured</span>}
                        </p>
                        <p className="truncate font-mono text-xs text-white/40">{server.transport === 'http' ? server.url : `${server.command} ${server.args.join(' ')}`}</p>
                      </div>
                      <div className="flex gap-2">
                        <Button variant="outline" size="sm" className="border-white/15 text-white/80" onClick={() => test(server.id)} disabled={t?.busy}>
                          {t?.busy ? <Loader2 className="w-4 h-4 mr-2 animate-spin" /> : <RefreshCw className="w-4 h-4 mr-2" />}Test
                        </Button>
                        <Button variant="ghost" size="sm" className="text-red-400/80 hover:text-red-400" onClick={() => remove(server)}><Trash2 className="w-4 h-4" /></Button>
                      </div>
                    </div>
                    {t?.message && (
                      <p className={`mt-3 flex items-start gap-2 text-sm ${t.ok ? 'text-green-300' : 'text-red-300'}`}>
                        {t.ok ? <CheckCircle2 className="mt-0.5 w-4 h-4 shrink-0" /> : <XCircle className="mt-0.5 w-4 h-4 shrink-0" />}{t.message}
                      </p>
                    )}
                  </li>
                );
              })}
            </ul>
          )}
        </Card>
      </div>
      <AddServerDialog open={adding} onOpenChange={setAdding} onAdded={load} />
    </DashboardLayout>
  );
}

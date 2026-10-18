'use client';

import { useCallback, useEffect, useState } from 'react';
import Link from 'next/link';
import DashboardLayout from '@/components/dashboard/DashboardLayout';
import { Button } from '@/components/ui/button';
import { Activity, CheckCircle, Clock, Download, Loader2, Play, RefreshCw, Webhook, Zap } from 'lucide-react';
import apiClient from '@/lib/api/client';
import { ExecutionSummary, formatDuration, StatusBadge } from '@/components/executions/ExecutionStatus';

const TRIGGER_ICON = { manual: Play, schedule: Clock, webhook: Webhook } as const;

const STATUS_FILTERS = ['', 'running', 'completed', 'failed'] as const;
const TRIGGER_FILTERS = ['', 'manual', 'schedule', 'webhook'] as const;

export default function ExecutionsPage() {
  const [executions, setExecutions] = useState<ExecutionSummary[]>([]);
  const [total, setTotal] = useState(0);
  const [status, setStatus] = useState<string>('');
  const [trigger, setTrigger] = useState<string>('');
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    try {
      const { data } = await apiClient.get('/api/v1/workflows/executions/all', {
        params: { limit: 200, status: status || undefined, trigger: trigger || undefined },
      });
      setExecutions(data.executions);
      setTotal(data.total);
      setError(null);
    } catch (e: any) {
      setError(e.message || 'Failed to load executions');
    } finally {
      setLoading(false);
    }
  }, [status, trigger]);

  useEffect(() => {
    setLoading(true);
    load();
  }, [load]);

  // Live monitoring: refresh every 3s while something is running, otherwise every 15s
  const anyRunning = executions.some((e) => e.status === 'running');
  useEffect(() => {
    const t = setInterval(load, anyRunning ? 3000 : 15000);
    return () => clearInterval(t);
  }, [load, anyRunning]);

  const finished = executions.filter((e) => e.status !== 'running');
  const succeeded = finished.filter((e) => e.status === 'completed').length;
  const stats = [
    { label: 'Runs shown', value: executions.length, icon: Activity },
    { label: 'Running now', value: executions.length - finished.length, icon: Loader2 },
    { label: 'Success rate', value: finished.length ? `${((succeeded / finished.length) * 100).toFixed(0)}%` : '—', icon: CheckCircle },
    { label: 'Tokens used', value: executions.reduce((s, e) => s + (e.metadata?.tokensUsed || 0), 0).toLocaleString(), icon: Zap },
  ];

  const exportCsv = async () => {
    const res = await apiClient.get('/api/v1/analytics/events/export', {
      params: { timeRange: '30d', format: 'csv' },
      responseType: 'blob',
    });
    const url = URL.createObjectURL(res.data);
    const a = document.createElement('a');
    a.href = url;
    a.download = 'flowmind-executions.csv';
    a.click();
    URL.revokeObjectURL(url);
  };

  return (
    <DashboardLayout>
      <div className="p-6 lg:p-8 space-y-6 max-w-7xl mx-auto">
        <div className="flex flex-col md:flex-row md:items-end md:justify-between gap-4">
          <div>
            <h1 className="text-3xl font-bold text-white flex items-center gap-3">
              <Activity className="w-8 h-8 text-blue-400" /> Executions
            </h1>
            <p className="text-white/60 mt-1">
              Every run of your workflows — manual, scheduled and webhook — updated live.
            </p>
          </div>
          <div className="flex gap-2">
            <Button variant="ghost" className="text-white/60 hover:text-white" onClick={exportCsv}>
              <Download className="w-4 h-4 mr-2" /> Export CSV
            </Button>
            <Button variant="ghost" className="text-white/60 hover:text-white" onClick={load}>
              <RefreshCw className="w-4 h-4 mr-2" /> Refresh
            </Button>
          </div>
        </div>

        <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
          {stats.map(({ label, value, icon: Icon }) => (
            <div key={label} className="bg-white/[0.03] border border-white/[0.06] rounded-2xl p-5">
              <div className="flex items-center justify-between text-white/50 text-sm">
                {label} <Icon className="w-4 h-4" />
              </div>
              <div className="text-2xl font-bold text-white mt-2">{value}</div>
            </div>
          ))}
        </div>

        <div className="flex flex-wrap gap-4 text-sm">
          <div className="flex gap-1 items-center">
            <span className="text-white/40 mr-1">Status</span>
            {STATUS_FILTERS.map((s) => (
              <Button key={s || 'all'} size="sm" variant={status === s ? 'default' : 'ghost'}
                className={status === s ? 'bg-blue-600 hover:bg-blue-700' : 'text-white/60'} onClick={() => setStatus(s)}>
                {s || 'All'}
              </Button>
            ))}
          </div>
          <div className="flex gap-1 items-center">
            <span className="text-white/40 mr-1">Trigger</span>
            {TRIGGER_FILTERS.map((t) => (
              <Button key={t || 'all'} size="sm" variant={trigger === t ? 'default' : 'ghost'}
                className={trigger === t ? 'bg-blue-600 hover:bg-blue-700' : 'text-white/60'} onClick={() => setTrigger(t)}>
                {t || 'All'}
              </Button>
            ))}
          </div>
        </div>

        <div className="bg-white/[0.03] border border-white/[0.06] rounded-2xl overflow-hidden">
          {error && <p className="text-red-400 text-sm p-4">{error}</p>}
          {loading && executions.length === 0 ? (
            <div className="p-12 text-center text-white/50"><Loader2 className="w-6 h-6 animate-spin mx-auto" /></div>
          ) : executions.length === 0 ? (
            <div className="p-12 text-center text-white/50">
              No executions yet. Run a workflow from the <Link href="/workflows" className="text-blue-400 underline">Workflows</Link> page.
            </div>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead className="text-white/40 text-left border-b border-white/[0.06]">
                  <tr>
                    <th className="p-4 font-medium">Workflow</th>
                    <th className="p-4 font-medium">Trigger</th>
                    <th className="p-4 font-medium">Status</th>
                    <th className="p-4 font-medium">Started</th>
                    <th className="p-4 font-medium text-right">Duration</th>
                    <th className="p-4 font-medium text-right">Steps</th>
                    <th className="p-4 font-medium text-right">Tokens</th>
                  </tr>
                </thead>
                <tbody>
                  {executions.map((e) => {
                    const TriggerIcon = TRIGGER_ICON[e.trigger] || Play;
                    return (
                      <tr key={e.id} className="border-b border-white/[0.04] hover:bg-white/[0.03]">
                        <td className="p-4">
                          <Link href={`/workflows/execution/${e.id}`} className="text-white hover:text-blue-300 font-medium">
                            {e.workflowName || e.workflowId}
                          </Link>
                          {e.status === 'failed' && e.error && (
                            <div className="text-red-400/80 text-xs truncate max-w-xs" title={e.error}>{e.error}</div>
                          )}
                        </td>
                        <td className="p-4 text-white/60"><span className="inline-flex items-center gap-1.5"><TriggerIcon className="w-3.5 h-3.5" />{e.trigger}</span></td>
                        <td className="p-4"><StatusBadge status={e.status} /></td>
                        <td className="p-4 text-white/60">{new Date(e.startTime).toLocaleString()}</td>
                        <td className="p-4 text-white/80 text-right">{formatDuration(e.duration)}</td>
                        <td className="p-4 text-white/60 text-right">{e.stepsCompleted ?? '—'}/{e.totalSteps ?? '—'}</td>
                        <td className="p-4 text-white/60 text-right">{e.metadata?.tokensUsed || 0}</td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          )}
          {total > executions.length && (
            <p className="text-white/30 text-xs p-3 text-center">Showing the latest {executions.length} of {total} runs.</p>
          )}
        </div>
      </div>
    </DashboardLayout>
  );
}

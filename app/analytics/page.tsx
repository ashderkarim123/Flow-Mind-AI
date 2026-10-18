'use client';

import { useCallback, useEffect, useState } from 'react';
import DashboardLayout from '@/components/dashboard/DashboardLayout';
import { Button } from '@/components/ui/button';
import { Activity, AlertTriangle, BarChart3, CheckCircle, Loader2, Timer, Zap } from 'lucide-react';
import {
  Bar, BarChart, CartesianGrid, Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis,
} from 'recharts';
import apiClient from '@/lib/api/client';
import { formatDuration } from '@/components/executions/ExecutionStatus';

type Range = '7d' | '30d' | '90d';
interface Point { timestamp: string; value: number }
interface NodeMetric { endpoint: string; totalCalls: number; failedCalls: number; avgLatency: number; p95Latency: number; errorRate: number }
interface WorkflowRate { workflowId: string; workflowName: string; successRate: number; totalExecutions: number; avgExecutionTime: number }
interface Bottleneck { workflowName: string; stepName: string; avgStepDuration: number; percentageOfTotalTime: number; failureRate: number; recommendedAction: string }

// Chart styling — one series per chart, recessive grid/axes, text in ink tokens
const SERIES = '#3B82F6';
const AXIS = { stroke: 'rgba(255,255,255,0.35)', fontSize: 11, tickLine: false, axisLine: false } as const;
const GRID = 'rgba(255,255,255,0.06)';
const TOOLTIP = {
  contentStyle: { background: '#0b0b0f', border: '1px solid rgba(255,255,255,0.12)', borderRadius: 8, color: '#fff', fontSize: 12 },
  labelStyle: { color: 'rgba(255,255,255,0.6)' },
  cursor: { fill: 'rgba(255,255,255,0.04)', stroke: 'rgba(255,255,255,0.2)' },
};
const day = (iso: string) => new Date(iso).toLocaleDateString(undefined, { month: 'short', day: 'numeric' });

function ChartCard({ title, subtitle, children }: { title: string; subtitle?: string; children: React.ReactNode }) {
  return (
    <div className="bg-white/[0.03] border border-white/[0.06] rounded-2xl p-5">
      <h3 className="text-white font-semibold">{title}</h3>
      {subtitle && <p className="text-white/40 text-xs mb-3">{subtitle}</p>}
      <div className="h-56">{children}</div>
    </div>
  );
}

export default function AnalyticsPage() {
  const [range, setRange] = useState<Range>('30d');
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [overview, setOverview] = useState<any>(null);
  const [runs, setRuns] = useState<Point[]>([]);
  const [successRate, setSuccessRate] = useState<Point[]>([]);
  const [tokens, setTokens] = useState<Point[]>([]);
  const [nodes, setNodes] = useState<NodeMetric[]>([]);
  const [workflows, setWorkflows] = useState<WorkflowRate[]>([]);
  const [bottlenecks, setBottlenecks] = useState<Bottleneck[]>([]);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    const params = { timeRange: range };
    const trend = (metric: string) =>
      apiClient.get('/api/v1/analytics/dashboard/trends', { params: { ...params, metric } }).then((r) => r.data.dataPoints as Point[]);
    try {
      const [ov, r, s, t, n, w, b] = await Promise.all([
        apiClient.get('/api/v1/analytics/workflows/overview', { params }).then((x) => x.data.overview),
        trend('executions'),
        trend('success_rate'),
        trend('tokens'),
        apiClient.get('/api/v1/analytics/workflows/node-metrics', { params }).then((x) => x.data.metrics as NodeMetric[]),
        apiClient.get('/api/v1/analytics/workflows/success-rate', { params }).then((x) => x.data.successRates as WorkflowRate[]),
        apiClient.get('/api/v1/analytics/workflows/bottlenecks', { params }).then((x) => x.data.bottlenecks as Bottleneck[]),
      ]);
      setOverview(ov);
      setRuns(r);
      // Days without runs have no success rate — drop them instead of plotting a false 0%
      setSuccessRate(s.filter((p, i) => r[i]?.value > 0));
      setTokens(t);
      setNodes(n);
      setWorkflows(w);
      setBottlenecks(b);
    } catch (e: any) {
      setError(e.message || 'Failed to load analytics');
    } finally {
      setLoading(false);
    }
  }, [range]);

  useEffect(() => {
    load();
  }, [load]);

  const kpis = [
    { label: 'Executions', value: overview?.totalExecutions ?? '—', icon: Activity },
    { label: 'Success rate', value: overview ? `${overview.successRate.toFixed(1)}%` : '—', icon: CheckCircle },
    { label: 'Avg duration', value: overview ? formatDuration(overview.avgExecutionTimeMs) : '—', icon: Timer },
    { label: 'Tokens used', value: overview ? overview.totalTokens.toLocaleString() : '—', icon: Zap },
  ];

  return (
    <DashboardLayout>
      <div className="p-6 lg:p-8 space-y-6 max-w-7xl mx-auto">
        <div className="flex flex-col md:flex-row md:items-end md:justify-between gap-4">
          <div>
            <h1 className="text-3xl font-bold text-white flex items-center gap-3">
              <BarChart3 className="w-8 h-8 text-blue-400" /> Analytics
            </h1>
            <p className="text-white/60 mt-1">Performance, reliability and AI usage of your workflows.</p>
          </div>
          <div className="flex gap-1">
            {(['7d', '30d', '90d'] as Range[]).map((r) => (
              <Button key={r} size="sm" variant={range === r ? 'default' : 'ghost'}
                className={range === r ? 'bg-blue-600 hover:bg-blue-700' : 'text-white/60'} onClick={() => setRange(r)}>
                Last {r}
              </Button>
            ))}
          </div>
        </div>

        {error && <p className="text-red-400 text-sm">{error}</p>}
        {loading && !overview && <div className="py-16 text-center text-white/50"><Loader2 className="w-6 h-6 animate-spin mx-auto" /></div>}

        <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
          {kpis.map(({ label, value, icon: Icon }) => (
            <div key={label} className="bg-white/[0.03] border border-white/[0.06] rounded-2xl p-5">
              <div className="flex items-center justify-between text-white/50 text-sm">{label} <Icon className="w-4 h-4" /></div>
              <div className="text-3xl font-bold text-white mt-2">{value}</div>
            </div>
          ))}
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
          <ChartCard title="Executions per day">
            <ResponsiveContainer>
              <BarChart data={runs} margin={{ top: 8, right: 8, left: -16, bottom: 0 }}>
                <CartesianGrid vertical={false} stroke={GRID} />
                <XAxis dataKey="timestamp" tickFormatter={day} {...AXIS} minTickGap={24} />
                <YAxis allowDecimals={false} {...AXIS} />
                <Tooltip {...TOOLTIP} labelFormatter={day} formatter={(v: number) => [v, 'Runs']} />
                <Bar dataKey="value" fill={SERIES} radius={[4, 4, 0, 0]} maxBarSize={18} />
              </BarChart>
            </ResponsiveContainer>
          </ChartCard>
          <ChartCard title="Success rate" subtitle="Days with at least one run">
            <ResponsiveContainer>
              <LineChart data={successRate} margin={{ top: 8, right: 8, left: -16, bottom: 0 }}>
                <CartesianGrid vertical={false} stroke={GRID} />
                <XAxis dataKey="timestamp" tickFormatter={day} {...AXIS} minTickGap={24} />
                <YAxis domain={[0, 100]} tickFormatter={(v) => `${v}%`} {...AXIS} />
                <Tooltip {...TOOLTIP} labelFormatter={day} formatter={(v: number) => [`${v.toFixed(1)}%`, 'Success rate']} />
                <Line dataKey="value" stroke={SERIES} strokeWidth={2} dot={{ r: 4 }} activeDot={{ r: 5 }} />
              </LineChart>
            </ResponsiveContainer>
          </ChartCard>
          <ChartCard title="LLM tokens per day">
            <ResponsiveContainer>
              <BarChart data={tokens} margin={{ top: 8, right: 8, left: -8, bottom: 0 }}>
                <CartesianGrid vertical={false} stroke={GRID} />
                <XAxis dataKey="timestamp" tickFormatter={day} {...AXIS} minTickGap={24} />
                <YAxis allowDecimals={false} {...AXIS} />
                <Tooltip {...TOOLTIP} labelFormatter={day} formatter={(v: number) => [v.toLocaleString(), 'Tokens']} />
                <Bar dataKey="value" fill={SERIES} radius={[4, 4, 0, 0]} maxBarSize={18} />
              </BarChart>
            </ResponsiveContainer>
          </ChartCard>
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
          <div className="bg-white/[0.03] border border-white/[0.06] rounded-2xl p-5">
            <h3 className="text-white font-semibold">Node &amp; AI provider latency</h3>
            <p className="text-white/40 text-xs mb-3">Average time per call, per node type — compares models on real runs</p>
            {nodes.length === 0 ? <p className="text-white/40 text-sm py-6">No node runs in this period.</p> : (
              <>
                <div style={{ height: Math.max(120, nodes.length * 30) }}>
                  <ResponsiveContainer>
                    <BarChart data={nodes} layout="vertical" margin={{ top: 0, right: 16, left: 8, bottom: 0 }}>
                      <CartesianGrid horizontal={false} stroke={GRID} />
                      <XAxis type="number" tickFormatter={(v) => formatDuration(v)} {...AXIS} />
                      <YAxis type="category" dataKey="endpoint" width={110} {...AXIS} />
                      <Tooltip {...TOOLTIP} formatter={(v: number) => [formatDuration(v), 'Avg latency']} />
                      <Bar dataKey="avgLatency" fill={SERIES} radius={[0, 4, 4, 0]} maxBarSize={16} />
                    </BarChart>
                  </ResponsiveContainer>
                </div>
                <table className="w-full text-xs mt-4">
                  <thead className="text-white/40 text-left"><tr>
                    <th className="py-1 font-medium">Node type</th><th className="py-1 font-medium text-right">Calls</th>
                    <th className="py-1 font-medium text-right">Avg</th><th className="py-1 font-medium text-right">p95</th>
                    <th className="py-1 font-medium text-right">Errors</th>
                  </tr></thead>
                  <tbody className="text-white/80">
                    {nodes.map((n) => (
                      <tr key={n.endpoint} className="border-t border-white/[0.05]">
                        <td className="py-1.5">{n.endpoint}</td>
                        <td className="py-1.5 text-right">{n.totalCalls}</td>
                        <td className="py-1.5 text-right">{formatDuration(n.avgLatency)}</td>
                        <td className="py-1.5 text-right">{formatDuration(n.p95Latency)}</td>
                        <td className="py-1.5 text-right">{n.errorRate.toFixed(0)}%</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </>
            )}
          </div>

          <div className="bg-white/[0.03] border border-white/[0.06] rounded-2xl p-5">
            <h3 className="text-white font-semibold">Workflows</h3>
            <p className="text-white/40 text-xs mb-3">Success rate and average duration per workflow</p>
            {workflows.length === 0 ? <p className="text-white/40 text-sm py-6">No runs in this period.</p> : (
              <table className="w-full text-sm">
                <thead className="text-white/40 text-left text-xs"><tr>
                  <th className="py-1 font-medium">Workflow</th><th className="py-1 font-medium text-right">Runs</th>
                  <th className="py-1 font-medium text-right">Success</th><th className="py-1 font-medium text-right">Avg duration</th>
                </tr></thead>
                <tbody className="text-white/80">
                  {workflows.map((w) => (
                    <tr key={w.workflowId} className="border-t border-white/[0.05]">
                      <td className="py-2">{w.workflowName}</td>
                      <td className="py-2 text-right">{w.totalExecutions}</td>
                      <td className="py-2 text-right">{w.successRate.toFixed(0)}%</td>
                      <td className="py-2 text-right">{formatDuration(w.avgExecutionTime)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )}
          </div>
        </div>

        <div className="bg-white/[0.03] border border-white/[0.06] rounded-2xl p-5">
          <h3 className="text-white font-semibold flex items-center gap-2"><AlertTriangle className="w-4 h-4 text-amber-400" /> Bottlenecks</h3>
          <p className="text-white/40 text-xs mb-3">Slowest and most failure-prone steps, with a suggested fix</p>
          {bottlenecks.length === 0 ? <p className="text-white/40 text-sm py-4">Nothing to flag yet.</p> : (
            <table className="w-full text-sm">
              <thead className="text-white/40 text-left text-xs"><tr>
                <th className="py-1 font-medium">Step</th><th className="py-1 font-medium">Workflow</th>
                <th className="py-1 font-medium text-right">Avg</th><th className="py-1 font-medium text-right">Share of run</th>
                <th className="py-1 font-medium text-right">Failures</th><th className="py-1 font-medium pl-4">Suggestion</th>
              </tr></thead>
              <tbody className="text-white/80">
                {bottlenecks.map((b, i) => (
                  <tr key={i} className="border-t border-white/[0.05] align-top">
                    <td className="py-2">{b.stepName}</td>
                    <td className="py-2 text-white/60">{b.workflowName}</td>
                    <td className="py-2 text-right">{formatDuration(b.avgStepDuration)}</td>
                    <td className="py-2 text-right">{b.percentageOfTotalTime.toFixed(0)}%</td>
                    <td className="py-2 text-right">{b.failureRate.toFixed(0)}%</td>
                    <td className="py-2 pl-4 text-white/60 text-xs">{b.recommendedAction}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>
      </div>
    </DashboardLayout>
  );
}

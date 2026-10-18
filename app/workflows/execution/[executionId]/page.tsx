'use client';

import { use, useCallback, useEffect, useState } from 'react';
import Link from 'next/link';
import DashboardLayout from '@/components/dashboard/DashboardLayout';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { ArrowLeft, Calendar, Cpu, Loader2, RotateCcw, Timer, XCircle, Zap } from 'lucide-react';
import apiClient from '@/lib/api/client';
import { ExecutionSummary, formatDuration, StatusBadge } from '@/components/executions/ExecutionStatus';

interface NodeLog {
  nodeId: string;
  nodeName?: string;
  nodeType: string;
  status: string;
  output?: unknown;
  error?: string | null;
  executionTimeMs?: number;
  startedAt?: string;
  completedAt?: string;
}

interface ExecutionRecord extends ExecutionSummary {
  input?: unknown;
  output?: unknown;
  nodeLogs?: NodeLog[];
}

const pretty = (value: unknown) => JSON.stringify(value ?? {}, null, 2);

export default function ExecutionPage({ params }: { params: Promise<{ executionId: string }> }) {
  const { executionId } = use(params);
  const [execution, setExecution] = useState<ExecutionRecord | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    try {
      const { data } = await apiClient.get(`/api/v1/workflows/executions/${executionId}`);
      setExecution(data);
      setError(null);
    } catch (e: any) {
      // apiClient rejects with { status, message } (see lib/api/client.ts)
      setError(e.status === 404 ? 'Execution not found' : e.message || 'Failed to load execution');
    } finally {
      setLoading(false);
    }
  }, [executionId]);

  useEffect(() => {
    load();
  }, [load]);

  // Live view: poll while the run is still in progress
  const running = execution?.status === 'running';
  useEffect(() => {
    if (!running) return;
    const t = setInterval(load, 2000);
    return () => clearInterval(t);
  }, [running, load]);

  if (loading) {
    return (
      <DashboardLayout>
        <div className="flex items-center justify-center py-32 text-white/60">
          <Loader2 className="w-8 h-8 animate-spin mr-3" /> Loading execution…
        </div>
      </DashboardLayout>
    );
  }

  if (error || !execution) {
    return (
      <DashboardLayout>
        <div className="text-center py-32">
          <XCircle className="h-12 w-12 text-red-500 mx-auto mb-4" />
          <h1 className="text-2xl font-bold text-white mb-2">{error || 'Execution not found'}</h1>
          <Link href="/executions" className="text-blue-400 underline">Back to executions</Link>
        </div>
      </DashboardLayout>
    );
  }

  const logs = execution.nodeLogs || [];
  const overview = [
    { label: 'Duration', value: running ? 'Running…' : formatDuration(execution.duration), icon: Timer },
    { label: 'Steps', value: `${execution.stepsCompleted ?? logs.length}/${execution.totalSteps ?? logs.length}`, icon: Cpu },
    { label: 'Tokens used', value: (execution.metadata?.tokensUsed || 0).toLocaleString(), icon: Zap },
    { label: 'Trigger', value: execution.trigger || 'manual', icon: Calendar },
  ];

  return (
    <DashboardLayout>
      <div className="p-6 lg:p-8 space-y-6 max-w-6xl mx-auto">
        <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-4">
          <div>
            <Link href="/executions" className="text-white/50 hover:text-white text-sm inline-flex items-center gap-1 mb-2">
              <ArrowLeft className="w-4 h-4" /> All executions
            </Link>
            <h1 className="text-3xl font-bold text-white">{execution.workflowName || 'Workflow execution'}</h1>
            <p className="text-white/40 text-xs font-mono mt-1">
              {execution.id} · started {new Date(execution.startTime).toLocaleString()}
            </p>
          </div>
          <div className="flex items-center gap-2">
            <StatusBadge status={execution.status} />
            <Button variant="outline" size="sm" onClick={load} className="border-white/20 text-white hover:bg-white/10">
              <RotateCcw className="h-4 w-4 mr-2" /> Refresh
            </Button>
          </div>
        </div>

        <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
          {overview.map(({ label, value, icon: Icon }) => (
            <Card key={label} className="bg-black/40 border border-white/10">
              <CardHeader className="flex flex-row items-center justify-between pb-2">
                <CardTitle className="text-sm font-medium text-white/70">{label}</CardTitle>
                <Icon className="h-4 w-4 text-white/50" />
              </CardHeader>
              <CardContent><div className="text-2xl font-bold text-white capitalize">{value}</div></CardContent>
            </Card>
          ))}
        </div>

        {execution.error && (
          <Alert className="bg-red-500/15 border-red-500/30 text-red-400">
            <XCircle className="h-4 w-4" />
            <AlertDescription><strong>Error:</strong> {execution.error}</AlertDescription>
          </Alert>
        )}

        {execution.metadata?.models?.length ? (
          <p className="text-white/50 text-sm">Models used: {execution.metadata.models.join(', ')}</p>
        ) : null}

        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          {(['input', 'output'] as const).map((key) => (
            <Card key={key} className="bg-black/40 border border-white/10">
              <CardHeader><CardTitle className="text-white capitalize">{key}</CardTitle></CardHeader>
              <CardContent>
                <pre className="bg-white/5 border border-white/10 p-3 rounded text-xs overflow-auto max-h-64 text-white/80">
                  {pretty(execution[key])}
                </pre>
              </CardContent>
            </Card>
          ))}
        </div>

        <Card className="bg-black/40 border border-white/10">
          <CardHeader>
            <CardTitle className="text-white">Node execution log</CardTitle>
            <p className="text-sm text-white/60">
              {logs.length} node(s) executed{running ? ' so far — updating live' : ''}
            </p>
          </CardHeader>
          <CardContent className="space-y-3">
            {logs.length === 0 && <p className="text-white/40 text-sm">{running ? 'Waiting for the first node…' : 'No nodes ran.'}</p>}
            {logs.map((log, index) => (
              <details key={`${log.nodeId}-${index}`} className="border border-white/10 rounded-lg bg-white/5 group" open={log.status === 'failed'}>
                <summary className="flex items-center justify-between p-4 cursor-pointer list-none">
                  <div className="flex items-center gap-2">
                    <span className="text-xs text-white/40">#{index + 1}</span>
                    <span className="font-medium text-white">{log.nodeName || log.nodeType}</span>
                    <Badge className="text-xs bg-white/10 text-white/70 border-white/20">{log.nodeType}</Badge>
                  </div>
                  <div className="flex items-center gap-3">
                    <StatusBadge status={log.status} />
                    <span className="text-sm text-white/60 w-16 text-right">{formatDuration(log.executionTimeMs)}</span>
                  </div>
                </summary>
                <div className="px-4 pb-4 space-y-2">
                  {log.error && (
                    <Alert className="bg-red-500/15 border-red-500/30 text-red-400">
                      <AlertDescription>{log.error}</AlertDescription>
                    </Alert>
                  )}
                  <pre className="bg-black/30 border border-white/10 p-2 rounded text-xs overflow-auto max-h-64 text-white/80">
                    {pretty(log.output)}
                  </pre>
                </div>
              </details>
            ))}
          </CardContent>
        </Card>
      </div>
    </DashboardLayout>
  );
}

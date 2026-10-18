'use client';

import { Badge } from '@/components/ui/badge';
import { CheckCircle, Loader2, XCircle } from 'lucide-react';

export interface ExecutionSummary {
  id: string;
  workflowId: string;
  workflowName?: string;
  trigger: 'manual' | 'schedule' | 'webhook';
  status: 'running' | 'completed' | 'failed';
  startTime: number;
  endTime?: number;
  duration?: number;
  error?: string | null;
  stepsCompleted?: number;
  totalSteps?: number;
  metadata?: { tokensUsed?: number; models?: string[] };
}

export const formatDuration = (ms?: number | null) => {
  if (ms == null) return '—';
  if (ms < 1000) return `${Math.round(ms)}ms`;
  if (ms < 60000) return `${(ms / 1000).toFixed(1)}s`;
  return `${(ms / 60000).toFixed(1)}m`;
};

export function StatusBadge({ status }: { status: string }) {
  const styles: Record<string, string> = {
    completed: 'bg-green-500/15 text-green-400 border-green-500/30',
    success: 'bg-green-500/15 text-green-400 border-green-500/30',
    failed: 'bg-red-500/15 text-red-400 border-red-500/30',
    running: 'bg-blue-500/15 text-blue-300 border-blue-500/30',
  };
  const Icon = status === 'failed' ? XCircle : status === 'running' ? Loader2 : CheckCircle;
  return (
    <Badge className={`gap-1 border ${styles[status] || 'bg-white/10 text-white/70 border-white/20'}`}>
      <Icon className={`h-3 w-3 ${status === 'running' ? 'animate-spin' : ''}`} />
      {status.charAt(0).toUpperCase() + status.slice(1)}
    </Badge>
  );
}

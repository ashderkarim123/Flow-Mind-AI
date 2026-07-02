"use client";

import { useEffect, useState } from "react";
import { workflowManager } from "@/lib/workflow/WorkflowManager";
import { WorkflowExecution } from "@/lib/workflow/types";
import { X, RotateCcw, Calendar, Timer, Zap, DollarSign, CheckCircle, XCircle, Clock, Play, AlertTriangle } from "lucide-react";

interface ExecutionModalProps {
  executionId: string | null;
  open: boolean;
  onClose: () => void;
}

export default function ExecutionModal({ executionId, open, onClose }: ExecutionModalProps) {
  const [execution, setExecution] = useState<WorkflowExecution | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (open && executionId) {
      load();
    }
  }, [open, executionId]);

  const load = async () => {
    try {
      setLoading(true);
      setError(null);
      if (!executionId) return;
      const exec = await workflowManager.getExecution(executionId);
      if (!exec) {
        setError("Execution not found");
      }
      setExecution(exec);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to load execution");
    } finally {
      setLoading(false);
    }
  };

  const statusIcon = (status: string) => {
    switch (status) {
      case "completed":
        return <CheckCircle className="h-4 w-4 text-green-400" />;
      case "failed":
        return <XCircle className="h-4 w-4 text-red-400" />;
      case "running":
        return <Play className="h-4 w-4 text-blue-400" />;
      case "pending":
        return <Clock className="h-4 w-4 text-yellow-400" />;
      default:
        return <Clock className="h-4 w-4 text-white/70" />;
    }
  };

  const fmtDur = (ms?: number) => {
    if (!ms && ms !== 0) return "N/A";
    if (ms < 1000) return `${ms}ms`;
    if (ms < 60000) return `${(ms / 1000).toFixed(1)}s`;
    return `${(ms / 60000).toFixed(1)}m`;
  };

  const fmtTs = (t?: number) => (t ? new Date(t).toLocaleString() : "N/A");

  if (!open) return null;

  const closeOnBackdrop = (e: React.MouseEvent<HTMLDivElement>) => {
    if (e.target === e.currentTarget) onClose();
  };

  return (
    <div className="fixed inset-0 z-50 flex items-start md:items-center justify-center bg-black/70 backdrop-blur-sm p-4" onClick={closeOnBackdrop}>
      <div className="w-full max-w-6xl bg-zinc-950/95 border border-zinc-800 rounded-2xl shadow-2xl overflow-hidden">
        {/* Accent bar */}
        <div className="h-0.5 bg-gradient-to-r from-[#1D4ED8] via-white/20 to-transparent" />

        {/* Header (sticky) */}
        <div className="sticky top-0 z-10 flex items-center justify-between px-6 py-4 bg-zinc-950/90 backdrop-blur border-b border-zinc-800">
          <div className="flex items-center gap-3">
            <div className="w-2 h-2 rounded-full bg-[#1D4ED8]" />
            <div>
              <h3 className="text-base font-semibold text-white">Workflow Execution</h3>
              {execution?.id && (
                <div className="text-[11px] text-white/50 font-mono">ID: {execution.id}</div>
              )}
            </div>
            {execution?.status && (
              <div className="ml-2 inline-flex items-center gap-1 text-xs px-2 py-1 rounded-full border border-white/15 bg-white/5 text-white/80">
                {statusIcon(execution.status)}
                <span className="capitalize">{execution.status}</span>
              </div>
            )}
          </div>
          <div className="flex items-center gap-2">
            <button onClick={load} className="text-white/90 hover:text-white inline-flex items-center gap-1 text-xs px-3 py-1.5 rounded-lg border border-white/15 bg-white/5">
              <RotateCcw className="w-4 h-4" /> Refresh
            </button>
            <button onClick={onClose} className="text-white/80 hover:text-white">
              <X className="w-5 h-5" />
            </button>
          </div>
        </div>

        {/* Body */}
        <div className="p-6 space-y-6 max-h-[80vh] overflow-auto">
          {loading && (
            <div className="flex items-center justify-center py-16">
              <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-[#1D4ED8]"></div>
            </div>
          )}

          {!loading && error && (
            <div className="text-red-300 bg-black/80 border border-red-500/40 rounded-lg p-4 text-sm">{error}</div>
          )}

          {!loading && execution && (
            <>
              {/* Top metrics */}
              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
                {[
                  { label: 'Status', value: execution.status, icon: statusIcon(execution.status), valueClass: 'capitalize' },
                  { label: 'Duration', value: fmtDur(execution.duration), icon: <Timer className="w-4 h-4 text-white/70" /> },
                  { label: 'Tokens Used', value: execution.metadata.tokensUsed.toLocaleString(), icon: <Zap className="w-4 h-4 text-white/70" /> },
                  { label: 'Cost', value: `$${execution.metadata.cost.toFixed(4)}`, icon: <DollarSign className="w-4 h-4 text-white/70" /> },
                ].map((m, i) => (
                  <div key={i} className="bg-white/5 border border-white/10 rounded-xl px-4 py-3 flex items-center justify-between">
                    <div>
                      <div className="text-[11px] uppercase tracking-wide text-white/60">{m.label}</div>
                      <div className={`text-white text-lg font-semibold ${m.valueClass || ''}`}>{m.value}</div>
                    </div>
                    <div className="opacity-80">{m.icon}</div>
                  </div>
                ))}
              </div>

              {/* Details row */}
              <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
                <div className="bg-white/5 border border-white/10 rounded-xl p-4">
                  <div className="flex items-center gap-2 text-white mb-3">
                    <Calendar className="w-4 h-4 text-[#1D4ED8]" />
                    <div className="font-semibold">Execution Details</div>
                  </div>
                  <div className="grid grid-cols-2 gap-4 text-sm">
                    <div>
                      <div className="text-white/70">Workflow ID</div>
                      <div className="text-white/90 font-mono text-xs break-all">{execution.workflowId}</div>
                    </div>
                    <div>
                      <div className="text-white/70">Started</div>
                      <div className="text-white/90">{fmtTs(execution.startTime)}</div>
                    </div>
                    <div>
                      <div className="text-white/70">Ended</div>
                      <div className="text-white/90">{fmtTs(execution.endTime)}</div>
                    </div>
                    <div>
                      <div className="text-white/70">Duration</div>
                      <div className="text-white/90">{fmtDur(execution.duration)}</div>
                    </div>
                  </div>
                </div>
                <div className="bg-white/5 border border-white/10 rounded-xl p-4">
                  <div className="text-white font-semibold mb-2">Input / Output</div>
                  <div className="space-y-3 text-xs">
                    <div>
                      <div className="text-white/70 mb-1">Input</div>
                      <pre className="bg-black/60 border border-white/10 rounded p-2 text-white/80 max-h-40 overflow-auto">{JSON.stringify(execution.input, null, 2)}</pre>
                    </div>
                    {execution.output && (
                      <div>
                        <div className="text-white/70 mb-1">Output</div>
                        <pre className="bg-black/60 border border-white/10 rounded p-2 text-white/80 max-h-40 overflow-auto">{JSON.stringify(execution.output, null, 2)}</pre>
                      </div>
                    )}
                  </div>
                </div>
              </div>

              {/* Logs timeline */}
              <div className="bg-white/5 border border-white/10 rounded-xl p-4">
                <div className="text-white font-semibold mb-3">Node Execution Timeline</div>
                <div className="space-y-3">
                  {execution.nodeLogs.map((log, idx) => (
                    <div key={`${log.nodeId}-${idx}`} className="relative pl-8">
                      <div className="absolute left-3 top-2 w-2 h-2 rounded-full bg-[#1D4ED8]" />
                      {idx < execution.nodeLogs.length - 1 && (
                        <div className="absolute left-3 top-4 bottom-0 w-px bg-white/10" />
                      )}
                      <div className="border border-white/10 rounded-lg p-3 bg-black/40">
                        <div className="flex items-center justify-between">
                          <div className="flex items-center gap-2">
                            <span className="text-white/60 text-xs font-mono">#{idx + 1}</span>
                            <div className="text-white font-medium">{log.nodeName}</div>
                            <div className="text-white/60 text-xs border border-white/15 rounded px-2 py-0.5">{log.nodeType}</div>
                          </div>
                          <div className="inline-flex items-center gap-2 text-xs px-2 py-1 rounded-full border border-white/15 bg-white/5 text-white/80">
                            {statusIcon(log.status)}
                            <span className="capitalize">{log.status}</span>
                            <span className="text-white/60">• {fmtDur(log.duration)}</span>
                          </div>
                        </div>
                        {log.status === "failed" && (
                          <div className="mt-4 border border-red-500/30 bg-red-950/20 rounded-xl p-4 space-y-3 text-left">
                            <div className="flex items-center gap-2 text-red-400 text-xs font-semibold">
                              <AlertTriangle className="w-3.5 h-3.5 flex-shrink-0" />
                              <span>Node Execution Failed</span>
                            </div>
                            <div className="grid grid-cols-1 md:grid-cols-2 gap-4 text-[11px]">
                              <div>
                                <span className="text-white/40 block mb-0.5">Error Message</span>
                                <span className="text-red-300 font-mono break-all">{log.error || "Unknown execution error"}</span>
                              </div>
                              <div>
                                <span className="text-white/40 block mb-0.5">Duration / Time</span>
                                <span className="text-white/70">{fmtDur(log.duration)} ({fmtTs(log.endTime)})</span>
                              </div>
                            </div>
                            <div className="pt-2 flex gap-2">
                              <button
                                onClick={async () => {
                                  try {
                                    const backendUrl = process.env.NEXT_PUBLIC_BACKEND_API_URL || 'http://localhost:8000';
                                    const token = localStorage.getItem('backend_auth_token');
                                    const res = await fetch(`${backendUrl}/api/v1/workflows/executions/${execution.id}/retry`, {
                                      method: 'POST',
                                      headers: { 
                                        'Authorization': `Bearer ${token}`,
                                        'Content-Type': 'application/json'
                                      }
                                    });
                                    if (res.ok) {
                                      load();
                                    } else {
                                      alert("Failed to trigger execution retry");
                                    }
                                  } catch (e) {
                                    console.error(e);
                                    alert("Error retrying execution");
                                  }
                                }}
                                className="flex items-center gap-1.5 bg-red-950/50 hover:bg-red-900/40 border border-red-500/30 text-red-200 text-[10px] font-medium px-2.5 py-1.5 rounded-lg transition-colors cursor-pointer"
                              >
                                <RotateCcw className="w-3 h-3 animate-pulse" /> Retry Execution
                              </button>
                            </div>
                          </div>
                        )}
                      </div>
                    </div>
                  ))}
                </div>
              </div>

              {/* Footer */}
              <div className="flex justify-end gap-2 pt-2">
                <button onClick={onClose} className="px-3 py-2 text-sm rounded-lg border border-white/15 bg-white/5 text-white/90 hover:bg-white/10">Close</button>
              </div>
            </>
          )}
        </div>
      </div>
    </div>
  );
}
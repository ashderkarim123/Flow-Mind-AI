"use client";

import { useCallback, useEffect, useState } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { Ban, CheckCircle2, Clock, Eye, EyeOff, Globe, Loader2, RefreshCw, Trash2, Workflow } from "lucide-react";
import apiClient from "@/lib/api/client";

interface AdminWorkflow {
  id: string;
  name: string;
  ownerEmail: string;
  nodeCount: number;
  triggers: string[];
  executionCount: number;
  lastExecutedAt: string | null;
  isPublic: boolean;
  disabled: boolean;
  disabledReason?: string | null;
  scheduled: boolean;
}

interface Summary { total: number; disabled: number; public: number; scheduled: number }

const FILTERS = [
  { value: "", label: "All" },
  { value: "active", label: "Active" },
  { value: "disabled", label: "Disabled" },
  { value: "public", label: "Public" },
  { value: "scheduled", label: "Scheduled" },
];

export default function AdminWorkflowsPage() {
  const [rows, setRows] = useState<AdminWorkflow[]>([]);
  const [summary, setSummary] = useState<Summary | null>(null);
  const [search, setSearch] = useState("");
  const [filter, setFilter] = useState("");
  const [loading, setLoading] = useState(true);
  const [busyId, setBusyId] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const { data } = await apiClient.get("/api/v1/admin/workflows", {
        params: { search: search || undefined, status: filter || undefined },
      });
      setRows(data.workflows);
      setSummary(data.summary);
    } catch (e: any) {
      setError(e.message || "Failed to load workflows");
    } finally {
      setLoading(false);
    }
  }, [search, filter]);

  useEffect(() => {
    const t = setTimeout(load, 250); // debounce typing in the search box
    return () => clearTimeout(t);
  }, [load]);

  const moderate = async (wf: AdminWorkflow, body: Record<string, unknown>) => {
    setBusyId(wf.id);
    try {
      await apiClient.patch(`/api/v1/admin/workflows/${wf.id}`, body);
      await load();
    } catch (e: any) {
      setError(e.message || "Update failed");
    } finally {
      setBusyId(null);
    }
  };

  const remove = async (wf: AdminWorkflow) => {
    if (!window.confirm(`Permanently delete "${wf.name}" owned by ${wf.ownerEmail || "unknown"}?`)) return;
    setBusyId(wf.id);
    try {
      await apiClient.delete(`/api/v1/admin/workflows/${wf.id}`);
      await load();
    } catch (e: any) {
      setError(e.message || "Delete failed");
    } finally {
      setBusyId(null);
    }
  };

  const cards = [
    { label: "Total workflows", value: summary?.total, icon: Workflow },
    { label: "Public", value: summary?.public, icon: Globe },
    { label: "Scheduled", value: summary?.scheduled, icon: Clock },
    { label: "Disabled", value: summary?.disabled, icon: Ban },
  ];

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-white">Workflows</h1>
        <p className="text-white/60 text-sm">
          Every workflow on the platform. Disabling a workflow blocks manual runs, its schedule and its webhook.
        </p>
      </div>

      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        {cards.map(({ label, value, icon: Icon }) => (
          <Card key={label} className="bg-[#1a1410]/80 border border-white/5 rounded-2xl">
            <CardHeader className="pb-2 flex flex-row items-center justify-between">
              <CardTitle className="text-white/70 text-sm font-medium">{label}</CardTitle>
              <Icon className="w-4 h-4 text-white/40" />
            </CardHeader>
            <CardContent>
              <span className="text-2xl font-bold text-white">{value ?? "—"}</span>
            </CardContent>
          </Card>
        ))}
      </div>

      <Card className="bg-[#1a1410]/80 border border-white/5 rounded-2xl">
        <CardHeader className="flex flex-col md:flex-row md:items-center gap-3 md:justify-between">
          <div className="flex flex-wrap gap-2">
            {FILTERS.map((f) => (
              <Button
                key={f.value}
                size="sm"
                variant={filter === f.value ? "default" : "ghost"}
                className={filter === f.value ? "bg-blue-600 hover:bg-blue-700" : "text-white/60 hover:text-white"}
                onClick={() => setFilter(f.value)}
              >
                {f.label}
              </Button>
            ))}
          </div>
          <div className="flex gap-2">
            <Input
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              placeholder="Search name or owner email…"
              className="bg-white/5 border-white/10 text-white w-64"
            />
            <Button size="icon" variant="ghost" onClick={load} className="text-white/60 hover:text-white">
              <RefreshCw className={`w-4 h-4 ${loading ? "animate-spin" : ""}`} />
            </Button>
          </div>
        </CardHeader>
        <CardContent>
          {error && <p className="text-red-400 text-sm mb-3">{error}</p>}
          <div className="overflow-x-auto">
            <Table>
              <TableHeader>
                <TableRow className="border-white/10">
                  <TableHead className="text-white/50">Workflow</TableHead>
                  <TableHead className="text-white/50">Owner</TableHead>
                  <TableHead className="text-white/50">Triggers</TableHead>
                  <TableHead className="text-white/50 text-right">Runs</TableHead>
                  <TableHead className="text-white/50">Last run</TableHead>
                  <TableHead className="text-white/50">Status</TableHead>
                  <TableHead className="text-white/50 text-right">Actions</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {!loading && rows.length === 0 && (
                  <TableRow>
                    <TableCell colSpan={7} className="text-center text-white/40 py-10">No workflows match.</TableCell>
                  </TableRow>
                )}
                {rows.map((wf) => (
                  <TableRow key={wf.id} className="border-white/5">
                    <TableCell>
                      <div className="text-white font-medium">{wf.name}</div>
                      <div className="text-white/30 text-xs font-mono">{wf.id} · {wf.nodeCount} nodes</div>
                    </TableCell>
                    <TableCell className="text-white/70 text-sm">{wf.ownerEmail || "—"}</TableCell>
                    <TableCell className="text-white/60 text-xs">{wf.triggers.join(", ") || "—"}</TableCell>
                    <TableCell className="text-white text-right">{wf.executionCount}</TableCell>
                    <TableCell className="text-white/60 text-xs">
                      {wf.lastExecutedAt ? new Date(wf.lastExecutedAt).toLocaleString() : "Never"}
                    </TableCell>
                    <TableCell>
                      <div className="flex flex-wrap gap-1">
                        {wf.disabled ? (
                          <Badge className="bg-red-500/15 text-red-400 border-red-500/30" title={wf.disabledReason || ""}>Disabled</Badge>
                        ) : (
                          <Badge className="bg-emerald-500/15 text-emerald-400 border-emerald-500/30">Active</Badge>
                        )}
                        {wf.isPublic && <Badge className="bg-blue-500/15 text-blue-300 border-blue-500/30">Public</Badge>}
                        {wf.scheduled && <Badge className="bg-amber-500/15 text-amber-300 border-amber-500/30">Scheduled</Badge>}
                      </div>
                    </TableCell>
                    <TableCell className="text-right">
                      {busyId === wf.id ? (
                        <Loader2 className="w-4 h-4 animate-spin text-white/60 inline" />
                      ) : (
                        <div className="flex justify-end gap-1">
                          <Button
                            size="sm" variant="ghost" className="text-white/60 hover:text-white"
                            title={wf.disabled ? "Enable" : "Disable"}
                            onClick={() => {
                              if (wf.disabled) return moderate(wf, { disabled: false });
                              const reason = window.prompt("Reason shown to the owner (optional):") ?? undefined;
                              moderate(wf, { disabled: true, reason });
                            }}
                          >
                            {wf.disabled ? <CheckCircle2 className="w-4 h-4" /> : <Ban className="w-4 h-4" />}
                          </Button>
                          <Button
                            size="sm" variant="ghost" className="text-white/60 hover:text-white"
                            title={wf.isPublic ? "Unlist from public gallery" : "List publicly"}
                            onClick={() => moderate(wf, { isPublic: !wf.isPublic })}
                          >
                            {wf.isPublic ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
                          </Button>
                          <Button
                            size="sm" variant="ghost" className="text-red-400/70 hover:text-red-400"
                            title="Delete" onClick={() => remove(wf)}
                          >
                            <Trash2 className="w-4 h-4" />
                          </Button>
                        </div>
                      )}
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}

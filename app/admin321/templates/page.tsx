"use client";

import { useCallback, useEffect, useState } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { CheckCircle2, LayoutTemplate, Loader2, PowerOff, RefreshCw, Star, StarOff, Trash2 } from "lucide-react";
import apiClient from "@/lib/api/client";

interface AdminTemplate {
  id: string;
  name: string;
  category: string;
  difficulty: string;
  authorName?: string | null;
  nodeCount: number;
  usageCount: number;
  rating: number;
  reviewCount: number;
  isActive: boolean;
  isFeatured: boolean;
}

interface Summary { total: number; active: number; featured: number }

export default function AdminTemplatesPage() {
  const [rows, setRows] = useState<AdminTemplate[]>([]);
  const [summary, setSummary] = useState<Summary | null>(null);
  const [search, setSearch] = useState("");
  const [loading, setLoading] = useState(true);
  const [busyId, setBusyId] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const { data } = await apiClient.get("/api/v1/admin/templates", { params: { search: search || undefined } });
      setRows(data.templates);
      setSummary(data.summary);
    } catch (e: any) {
      setError(e.message || "Failed to load templates");
    } finally {
      setLoading(false);
    }
  }, [search]);

  useEffect(() => {
    const t = setTimeout(load, 250);
    return () => clearTimeout(t);
  }, [load]);

  const act = async (tpl: AdminTemplate, request: () => Promise<unknown>) => {
    setBusyId(tpl.id);
    try {
      await request();
      await load();
    } catch (e: any) {
      setError(e.message || "Action failed");
    } finally {
      setBusyId(null);
    }
  };

  const cards = [
    { label: "Templates", value: summary?.total },
    { label: "Active", value: summary?.active },
    { label: "Featured", value: summary?.featured },
  ];

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-white flex items-center gap-2">
          <LayoutTemplate className="w-6 h-6 text-blue-400" /> Templates
        </h1>
        <p className="text-white/60 text-sm">
          Moderate the workflow template gallery. Inactive templates are hidden from users; featured ones appear first.
        </p>
      </div>

      <div className="grid grid-cols-3 gap-4">
        {cards.map(({ label, value }) => (
          <Card key={label} className="bg-[#1a1410]/80 border border-white/5 rounded-2xl">
            <CardHeader className="pb-2"><CardTitle className="text-white/70 text-sm font-medium">{label}</CardTitle></CardHeader>
            <CardContent><span className="text-2xl font-bold text-white">{value ?? "—"}</span></CardContent>
          </Card>
        ))}
      </div>

      <Card className="bg-[#1a1410]/80 border border-white/5 rounded-2xl">
        <CardHeader className="flex flex-row items-center justify-end gap-2">
          <Input
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            placeholder="Search name, category or author…"
            className="bg-white/5 border-white/10 text-white w-72"
          />
          <Button size="icon" variant="ghost" onClick={load} className="text-white/60 hover:text-white">
            <RefreshCw className={`w-4 h-4 ${loading ? "animate-spin" : ""}`} />
          </Button>
        </CardHeader>
        <CardContent>
          {error && <p className="text-red-400 text-sm mb-3">{error}</p>}
          <div className="overflow-x-auto">
            <Table>
              <TableHeader>
                <TableRow className="border-white/10">
                  <TableHead className="text-white/50">Template</TableHead>
                  <TableHead className="text-white/50">Category</TableHead>
                  <TableHead className="text-white/50">Author</TableHead>
                  <TableHead className="text-white/50 text-right">Uses</TableHead>
                  <TableHead className="text-white/50 text-right">Rating</TableHead>
                  <TableHead className="text-white/50">Status</TableHead>
                  <TableHead className="text-white/50 text-right">Actions</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {!loading && rows.length === 0 && (
                  <TableRow>
                    <TableCell colSpan={7} className="text-center text-white/40 py-10">No templates yet.</TableCell>
                  </TableRow>
                )}
                {rows.map((tpl) => (
                  <TableRow key={tpl.id} className="border-white/5">
                    <TableCell>
                      <div className="text-white font-medium">{tpl.name}</div>
                      <div className="text-white/30 text-xs">{tpl.nodeCount} nodes · {tpl.difficulty || "—"}</div>
                    </TableCell>
                    <TableCell className="text-white/70 text-sm">{tpl.category || "—"}</TableCell>
                    <TableCell className="text-white/70 text-sm">{tpl.authorName || "—"}</TableCell>
                    <TableCell className="text-white text-right">{tpl.usageCount}</TableCell>
                    <TableCell className="text-white text-right">
                      {tpl.rating.toFixed(1)} <span className="text-white/30 text-xs">({tpl.reviewCount})</span>
                    </TableCell>
                    <TableCell>
                      <div className="flex gap-1">
                        {tpl.isActive ? (
                          <Badge className="bg-emerald-500/15 text-emerald-400 border-emerald-500/30">Active</Badge>
                        ) : (
                          <Badge className="bg-white/10 text-white/50 border-white/20">Inactive</Badge>
                        )}
                        {tpl.isFeatured && <Badge className="bg-amber-500/15 text-amber-300 border-amber-500/30">Featured</Badge>}
                      </div>
                    </TableCell>
                    <TableCell className="text-right">
                      {busyId === tpl.id ? (
                        <Loader2 className="w-4 h-4 animate-spin text-white/60 inline" />
                      ) : (
                        <div className="flex justify-end gap-1">
                          <Button
                            size="sm" variant="ghost" className="text-white/60 hover:text-white"
                            title={tpl.isActive ? "Deactivate" : "Activate"}
                            onClick={() => act(tpl, () => apiClient.patch(`/api/v1/admin/templates/${tpl.id}`, { isActive: !tpl.isActive }))}
                          >
                            {tpl.isActive ? <PowerOff className="w-4 h-4" /> : <CheckCircle2 className="w-4 h-4" />}
                          </Button>
                          <Button
                            size="sm" variant="ghost" className="text-white/60 hover:text-white"
                            title={tpl.isFeatured ? "Unfeature" : "Feature"}
                            onClick={() => act(tpl, () => apiClient.patch(`/api/v1/admin/templates/${tpl.id}`, { isFeatured: !tpl.isFeatured }))}
                          >
                            {tpl.isFeatured ? <StarOff className="w-4 h-4" /> : <Star className="w-4 h-4" />}
                          </Button>
                          <Button
                            size="sm" variant="ghost" className="text-red-400/70 hover:text-red-400" title="Delete"
                            onClick={() => {
                              if (window.confirm(`Delete template "${tpl.name}"?`)) {
                                act(tpl, () => apiClient.delete(`/api/v1/admin/templates/${tpl.id}`));
                              }
                            }}
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

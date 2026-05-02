'use client';

import { useState } from 'react';
import { motion } from 'framer-motion';
import { Save, Play, MoreHorizontal, Brain, Workflow, CheckCircle2, Loader2 } from 'lucide-react';
import { Button } from '@/components/ui/button';
import Link from 'next/link';

interface WorkflowToolbarProps {
  workflowName: string;
  nodeCount: number;
  edgeCount: number;
  saving?: boolean;
  onSave?: () => void;
  onRun?: () => void;
}

export function WorkflowToolbar({
  workflowName,
  nodeCount,
  edgeCount,
  saving = false,
  onSave,
  onRun,
}: WorkflowToolbarProps) {
  const [justSaved, setJustSaved] = useState(false);

  const handleSave = async () => {
    onSave?.();
    setJustSaved(true);
    setTimeout(() => setJustSaved(false), 2000);
  };

  return (
    <div
      className="flex items-center justify-between px-4 py-2.5 shrink-0"
      style={{
        background: 'rgba(10,10,26,0.9)',
        borderBottom: '1px solid rgba(124,58,237,0.1)',
        backdropFilter: 'blur(20px)',
      }}
    >
      {/* Left: brand + workflow name */}
      <div className="flex items-center gap-4">
        <Link href="/dashboard" className="flex items-center gap-2 group">
          <div
            className="w-7 h-7 rounded-lg flex items-center justify-center"
            style={{ background: 'rgba(124,58,237,0.15)', border: '1px solid rgba(124,58,237,0.2)' }}
          >
            <Brain className="w-3.5 h-3.5 text-violet-400" />
          </div>
          <span className="text-xs font-medium text-white/40 group-hover:text-white/60 font-inter transition-colors">
            FlowMind AI
          </span>
        </Link>

        <div
          className="h-4 w-px"
          style={{ background: 'rgba(255,255,255,0.08)' }}
        />

        <div className="flex items-center gap-2">
          <Workflow className="w-3.5 h-3.5 text-violet-400" />
          <span className="text-sm font-semibold text-white font-outfit">{workflowName}</span>
        </div>

        {/* Stats */}
        <div className="flex items-center gap-3 text-[10px] text-white/30 font-inter">
          <span>{nodeCount} nodes</span>
          <span className="w-1 h-1 rounded-full bg-white/15" />
          <span>{edgeCount} connections</span>
        </div>
      </div>

      {/* Right: actions */}
      <div className="flex items-center gap-2">
        {/* Save */}
        <Button
          onClick={handleSave}
          disabled={saving}
          size="sm"
          variant="outline"
          className="h-8 px-3 rounded-lg border-white/10 bg-white/4 text-white/70 hover:text-white hover:bg-white/8 text-xs font-inter"
        >
          {saving ? (
            <Loader2 size={13} className="mr-1.5 animate-spin" />
          ) : justSaved ? (
            <CheckCircle2 size={13} className="mr-1.5 text-emerald-400" />
          ) : (
            <Save size={13} className="mr-1.5" />
          )}
          {justSaved ? 'Saved!' : 'Save'}
        </Button>

        {/* Run */}
        <Button
          onClick={onRun}
          size="sm"
          className="h-8 px-3 rounded-lg text-xs font-semibold font-outfit text-white"
          style={{
            background: 'linear-gradient(135deg, #7C3AED, #5B21B6)',
            boxShadow: '0 2px 12px rgba(124,58,237,0.3)',
          }}
        >
          <Play size={12} className="mr-1.5 fill-white" />
          Run
        </Button>
      </div>
    </div>
  );
}

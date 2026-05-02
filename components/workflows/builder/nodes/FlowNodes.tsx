'use client';

import { memo } from 'react';
import { Handle, Position, NodeProps } from '@xyflow/react';
import { Brain, GitFork, Zap, Database, Terminal, Globe, CheckSquare, Clock } from 'lucide-react';

/* ─── Node type config ─────────────────────────────────────────── */
export const NODE_TYPES_CONFIG = {
  trigger: {
    label: 'Trigger',
    icon: Zap,
    color: '#F59E0B',
    bg: 'rgba(245,158,11,0.08)',
    border: 'rgba(245,158,11,0.3)',
    glow: 'rgba(245,158,11,0.2)',
    category: 'trigger',
  },
  ai_prompt: {
    label: 'AI Prompt',
    icon: Brain,
    color: '#9D6EFF',
    bg: 'rgba(124,58,237,0.1)',
    border: 'rgba(124,58,237,0.35)',
    glow: 'rgba(124,58,237,0.25)',
    category: 'ai',
  },
  condition: {
    label: 'Condition',
    icon: GitFork,
    color: '#22D3EE',
    bg: 'rgba(6,182,212,0.08)',
    border: 'rgba(6,182,212,0.3)',
    glow: 'rgba(6,182,212,0.15)',
    category: 'logic',
  },
  action: {
    label: 'Action',
    icon: Terminal,
    color: '#34D399',
    bg: 'rgba(16,185,129,0.08)',
    border: 'rgba(16,185,129,0.3)',
    glow: 'rgba(16,185,129,0.15)',
    category: 'action',
  },
  database: {
    label: 'Database',
    icon: Database,
    color: '#60A5FA',
    bg: 'rgba(59,130,246,0.08)',
    border: 'rgba(59,130,246,0.3)',
    glow: 'rgba(59,130,246,0.15)',
    category: 'data',
  },
  http: {
    label: 'HTTP Request',
    icon: Globe,
    color: '#F472B6',
    bg: 'rgba(244,114,182,0.08)',
    border: 'rgba(244,114,182,0.3)',
    glow: 'rgba(244,114,182,0.15)',
    category: 'integration',
  },
  output: {
    label: 'Output',
    icon: CheckSquare,
    color: '#10B981',
    bg: 'rgba(16,185,129,0.08)',
    border: 'rgba(16,185,129,0.35)',
    glow: 'rgba(16,185,129,0.2)',
    category: 'output',
  },
  delay: {
    label: 'Delay',
    icon: Clock,
    color: '#A78BFA',
    bg: 'rgba(167,139,250,0.08)',
    border: 'rgba(167,139,250,0.3)',
    glow: 'rgba(167,139,250,0.15)',
    category: 'logic',
  },
} as const;

export type NodeTypeKey = keyof typeof NODE_TYPES_CONFIG;
export type NodeCategory = 'trigger' | 'ai' | 'logic' | 'action' | 'data' | 'integration' | 'output';

/* ─── Base node component ──────────────────────────────────────── */
interface FlowNodeData {
  type: NodeTypeKey;
  label: string;
  config?: Record<string, unknown>;
  description?: string;
}

const FlowNode = memo(({ data, selected }: NodeProps & { data: FlowNodeData }) => {
  const nodeType = data.type as NodeTypeKey;
  const config = NODE_TYPES_CONFIG[nodeType] || NODE_TYPES_CONFIG.action;
  const Icon = config.icon;
  const isOutput = nodeType === 'output';
  const isTrigger = nodeType === 'trigger';

  return (
    <div
      className="workflow-node relative min-w-[160px] rounded-xl overflow-visible cursor-pointer select-none"
      style={{
        background: config.bg,
        border: `1.5px solid ${selected ? config.color : config.border}`,
        backdropFilter: 'blur(20px)',
        boxShadow: selected
          ? `0 0 0 1px ${config.color}, 0 8px 32px ${config.glow}`
          : `0 4px 16px rgba(0,0,0,0.3), 0 0 0 0 transparent`,
        transition: 'box-shadow 0.2s ease, border-color 0.2s ease',
      }}
    >
      {/* Top accent line */}
      <div
        className="absolute top-0 left-4 right-4 h-0.5 rounded-full"
        style={{ background: config.color, opacity: 0.8 }}
      />

      {/* Input handle (all except trigger) */}
      {!isTrigger && (
        <Handle
          type="target"
          position={Position.Left}
          style={{
            width: 10,
            height: 10,
            background: config.color,
            border: `2px solid ${config.bg}`,
            boxShadow: `0 0 8px ${config.glow}`,
            left: -6,
          }}
        />
      )}

      {/* Node content */}
      <div className="px-4 py-3">
        <div className="flex items-center gap-2 mb-1">
          <div
            className="w-6 h-6 rounded-lg flex items-center justify-center shrink-0"
            style={{ background: `${config.color}20` }}
          >
            <Icon className="w-3.5 h-3.5" style={{ color: config.color }} />
          </div>
          <span className="text-xs font-semibold text-white font-outfit">{config.label}</span>
        </div>
        <p className="text-[10px] text-white/50 font-inter leading-relaxed pl-8 truncate max-w-[130px]">
          {data.label || data.description || config.label}
        </p>
      </div>

      {/* Pulse animation for selected */}
      {selected && (
        <div
          className="absolute -inset-1 rounded-xl animate-node-pulse pointer-events-none"
          style={{ background: 'transparent' }}
        />
      )}

      {/* Output handle (all except pure output) */}
      {!isOutput && (
        <Handle
          type="source"
          position={Position.Right}
          style={{
            width: 10,
            height: 10,
            background: config.color,
            border: `2px solid ${config.bg}`,
            boxShadow: `0 0 8px ${config.glow}`,
            right: -6,
          }}
        />
      )}

      {/* Condition gets a second source handle (false branch) */}
      {nodeType === 'condition' && (
        <Handle
          id="false"
          type="source"
          position={Position.Bottom}
          style={{
            width: 10,
            height: 10,
            background: '#EF4444',
            border: `2px solid ${config.bg}`,
            boxShadow: '0 0 8px rgba(239,68,68,0.3)',
            bottom: -6,
          }}
        />
      )}
    </div>
  );
});

FlowNode.displayName = 'FlowNode';
export default FlowNode;

/* ─── React Flow node type map ─────────────────────────────────── */
export const nodeTypes = Object.fromEntries(
  Object.keys(NODE_TYPES_CONFIG).map((key) => [key, FlowNode]),
) as Record<NodeTypeKey, typeof FlowNode>;

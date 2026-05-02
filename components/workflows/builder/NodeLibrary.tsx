'use client';

import { useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { NODE_TYPES_CONFIG, NodeTypeKey, NodeCategory } from './nodes/FlowNodes';
import { Search, ChevronDown, ChevronRight } from 'lucide-react';

const CATEGORY_LABELS: Record<NodeCategory, string> = {
  trigger: 'Triggers',
  ai: 'AI / Language Models',
  logic: 'Logic & Flow',
  action: 'Actions',
  data: 'Data',
  integration: 'Integrations',
  output: 'Outputs',
};

const CATEGORY_ORDER: NodeCategory[] = ['trigger', 'ai', 'logic', 'action', 'data', 'integration', 'output'];

interface NodeCardProps {
  nodeType: NodeTypeKey;
  onDragStart: (event: React.DragEvent, nodeType: NodeTypeKey) => void;
}

function NodeCard({ nodeType, onDragStart }: NodeCardProps) {
  const config = NODE_TYPES_CONFIG[nodeType];
  const Icon = config.icon;

  return (
    <div
      draggable
      onDragStart={(e) => onDragStart(e, nodeType)}
      className="flex items-center gap-2.5 px-3 py-2.5 rounded-xl cursor-grab active:cursor-grabbing transition-all hover:scale-[1.01]"
      style={{
        background: config.bg,
        border: `1px solid ${config.border}`,
      }}
    >
      <div
        className="w-7 h-7 rounded-lg flex items-center justify-center shrink-0"
        style={{ background: `${config.color}18` }}
      >
        <Icon className="w-3.5 h-3.5" style={{ color: config.color }} />
      </div>
      <div className="min-w-0">
        <p className="text-xs font-medium text-white font-outfit">{config.label}</p>
        <p className="text-[9px] text-white/35 font-inter capitalize">{config.category}</p>
      </div>
      <div
        className="ml-auto text-[9px] px-1.5 py-0.5 rounded font-inter font-medium"
        style={{ background: `${config.color}15`, color: config.color }}
      >
        drag
      </div>
    </div>
  );
}

interface NodeLibraryProps {
  onDragStart: (event: React.DragEvent, nodeType: NodeTypeKey) => void;
}

export function NodeLibrary({ onDragStart }: NodeLibraryProps) {
  const [search, setSearch] = useState('');
  const [collapsed, setCollapsed] = useState<Set<NodeCategory>>(new Set());

  const toggleCategory = (cat: NodeCategory) => {
    setCollapsed((prev) => {
      const next = new Set(prev);
      next.has(cat) ? next.delete(cat) : next.add(cat);
      return next;
    });
  };

  const grouped = CATEGORY_ORDER.reduce<Record<NodeCategory, NodeTypeKey[]>>(
    (acc, cat) => {
      acc[cat] = (Object.keys(NODE_TYPES_CONFIG) as NodeTypeKey[]).filter(
        (k) =>
          NODE_TYPES_CONFIG[k].category === cat &&
          (search === '' ||
            NODE_TYPES_CONFIG[k].label.toLowerCase().includes(search.toLowerCase())),
      );
      return acc;
    },
    {} as Record<NodeCategory, NodeTypeKey[]>,
  );

  return (
    <div
      className="w-64 h-full flex flex-col"
      style={{
        background: 'rgba(10,10,26,0.85)',
        borderRight: '1px solid rgba(124,58,237,0.12)',
        backdropFilter: 'blur(20px)',
      }}
    >
      {/* Header */}
      <div className="px-4 py-4" style={{ borderBottom: '1px solid rgba(255,255,255,0.05)' }}>
        <h3 className="text-sm font-semibold text-white font-outfit mb-3">Node Library</h3>
        <div className="relative">
          <Search className="absolute left-2.5 top-1/2 -translate-y-1/2 h-3.5 w-3.5 text-white/30" />
          <input
            className="w-full pl-8 pr-3 py-2 bg-white/4 border border-white/8 rounded-lg text-xs text-white placeholder:text-white/25 focus:outline-none focus:border-violet-500/50 font-inter"
            placeholder="Search nodes..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
          />
        </div>
      </div>

      {/* Categories */}
      <div className="flex-1 overflow-y-auto admin-scroll py-2">
        {CATEGORY_ORDER.map((cat) => {
          const nodes = grouped[cat];
          if (!nodes || nodes.length === 0) return null;
          const isCollapsed = collapsed.has(cat);

          return (
            <div key={cat} className="mb-1">
              <button
                onClick={() => toggleCategory(cat)}
                className="w-full flex items-center justify-between px-4 py-2 text-[10px] font-semibold text-white/40 font-inter uppercase tracking-wider hover:text-white/60 transition-colors"
              >
                {CATEGORY_LABELS[cat]}
                {isCollapsed ? <ChevronRight size={10} /> : <ChevronDown size={10} />}
              </button>

              <AnimatePresence>
                {!isCollapsed && (
                  <motion.div
                    initial={{ opacity: 0, height: 0 }}
                    animate={{ opacity: 1, height: 'auto' }}
                    exit={{ opacity: 0, height: 0 }}
                    transition={{ duration: 0.2 }}
                    className="px-3 space-y-1.5 mb-2"
                  >
                    {nodes.map((nodeType) => (
                      <NodeCard key={nodeType} nodeType={nodeType} onDragStart={onDragStart} />
                    ))}
                  </motion.div>
                )}
              </AnimatePresence>
            </div>
          );
        })}
      </div>

      {/* Footer tip */}
      <div
        className="px-4 py-3 text-[10px] text-white/25 font-inter"
        style={{ borderTop: '1px solid rgba(255,255,255,0.04)' }}
      >
        Drag nodes onto the canvas to build your workflow
      </div>
    </div>
  );
}

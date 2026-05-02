'use client';

import { memo } from 'react';
import { motion } from 'framer-motion';
import { Node } from '@xyflow/react';
import { NODE_TYPES_CONFIG, NodeTypeKey } from './nodes/FlowNodes';
import { Trash2, X, Settings, Brain, Zap, AlertCircle } from 'lucide-react';
import { Button } from '@/components/ui/button';

interface NodeConfigPanelProps {
  node: Node;
  onChange: (nodeId: string, updates: Partial<Node['data']>) => void;
  onDelete: (nodeId: string) => void;
}

function ConfigField({
  label,
  children,
}: {
  label: string;
  children: React.ReactNode;
}) {
  return (
    <div className="space-y-1.5">
      <label className="block text-[10px] font-semibold text-white/40 font-inter uppercase tracking-wider">
        {label}
      </label>
      {children}
    </div>
  );
}

const inputClass =
  'w-full px-3 py-2 bg-white/4 border border-white/8 rounded-lg text-xs text-white placeholder:text-white/20 focus:outline-none focus:border-violet-500/50 focus:ring-1 focus:ring-violet-500/20 font-inter transition-all';

const textareaClass =
  'w-full px-3 py-2 bg-white/4 border border-white/8 rounded-lg text-xs text-white placeholder:text-white/20 focus:outline-none focus:border-violet-500/50 focus:ring-1 focus:ring-violet-500/20 font-inter transition-all resize-none';

export const NodeConfigPanel = memo(({ node, onChange, onDelete }: NodeConfigPanelProps) => {
  const nodeType = node.type as NodeTypeKey;
  const config = NODE_TYPES_CONFIG[nodeType] || NODE_TYPES_CONFIG.action;
  const Icon = config.icon;
  const data = node.data as any;

  return (
    <motion.div
      key={node.id}
      initial={{ opacity: 0, x: 20 }}
      animate={{ opacity: 1, x: 0 }}
      exit={{ opacity: 0, x: 20 }}
      transition={{ duration: 0.2 }}
      className="w-72 h-full flex flex-col"
      style={{
        background: 'rgba(10,10,26,0.9)',
        borderLeft: '1px solid rgba(124,58,237,0.12)',
        backdropFilter: 'blur(20px)',
      }}
    >
      {/* Header */}
      <div
        className="px-4 py-4 flex items-center gap-3"
        style={{ borderBottom: '1px solid rgba(255,255,255,0.05)' }}
      >
        <div
          className="w-8 h-8 rounded-lg flex items-center justify-center shrink-0"
          style={{ background: `${config.color}18` }}
        >
          <Icon className="w-4 h-4" style={{ color: config.color }} />
        </div>
        <div className="flex-1 min-w-0">
          <p className="text-sm font-semibold text-white font-outfit">{config.label}</p>
          <p className="text-[10px] text-white/35 font-inter">Node configuration</p>
        </div>
        <div
          className="w-2 h-2 rounded-full shrink-0"
          style={{ background: config.color, boxShadow: `0 0 6px ${config.color}` }}
        />
      </div>

      {/* Config fields */}
      <div className="flex-1 overflow-y-auto admin-scroll p-4 space-y-4">
        {/* Common: Label */}
        <ConfigField label="Node Label">
          <input
            className={inputClass}
            placeholder="Node label..."
            value={data.label || ''}
            onChange={(e) => onChange(node.id, { label: e.target.value })}
          />
        </ConfigField>

        {/* Common: Description */}
        <ConfigField label="Description">
          <textarea
            className={textareaClass}
            rows={2}
            placeholder="What does this node do?"
            value={data.description || ''}
            onChange={(e) => onChange(node.id, { description: e.target.value })}
          />
        </ConfigField>

        {/* ── Type-specific fields ── */}
        {nodeType === 'ai_prompt' && (
          <>
            <ConfigField label="AI Model">
              <select
                className={inputClass}
                value={data.config?.model || 'gpt-4o'}
                onChange={(e) => onChange(node.id, { config: { ...data.config, model: e.target.value } })}
              >
                <option value="gpt-4o">GPT-4o</option>
                <option value="gpt-4-turbo">GPT-4 Turbo</option>
                <option value="claude-3-5-sonnet">Claude 3.5 Sonnet</option>
                <option value="gemini-1.5-pro">Gemini 1.5 Pro</option>
              </select>
            </ConfigField>
            <ConfigField label="System Prompt">
              <textarea
                className={textareaClass}
                rows={4}
                placeholder="You are a helpful assistant..."
                value={data.config?.system_prompt || ''}
                onChange={(e) => onChange(node.id, { config: { ...data.config, system_prompt: e.target.value } })}
              />
            </ConfigField>
            <ConfigField label="User Prompt Template">
              <textarea
                className={textareaClass}
                rows={3}
                placeholder="Process this: {{input}}"
                value={data.config?.prompt_template || ''}
                onChange={(e) => onChange(node.id, { config: { ...data.config, prompt_template: e.target.value } })}
              />
            </ConfigField>
            <ConfigField label="Temperature">
              <input
                type="range" min="0" max="1" step="0.1"
                className="w-full accent-violet-500"
                value={data.config?.temperature ?? 0.7}
                onChange={(e) => onChange(node.id, { config: { ...data.config, temperature: parseFloat(e.target.value) } })}
              />
              <p className="text-[10px] text-white/35 font-inter text-right">{data.config?.temperature ?? 0.7}</p>
            </ConfigField>
          </>
        )}

        {nodeType === 'condition' && (
          <>
            <ConfigField label="Condition Expression">
              <textarea
                className={textareaClass}
                rows={3}
                placeholder="{{output}} contains 'error'"
                value={data.config?.expression || ''}
                onChange={(e) => onChange(node.id, { config: { ...data.config, expression: e.target.value } })}
              />
            </ConfigField>
            <div className="flex gap-2 text-[10px] font-inter">
              <div className="flex items-center gap-1.5 text-emerald-400">
                <span className="w-1.5 h-1.5 rounded-full bg-emerald-400" /> True → right handle
              </div>
              <div className="flex items-center gap-1.5 text-red-400">
                <span className="w-1.5 h-1.5 rounded-full bg-red-400" /> False → bottom handle
              </div>
            </div>
          </>
        )}

        {nodeType === 'http' && (
          <>
            <ConfigField label="Method">
              <select
                className={inputClass}
                value={data.config?.method || 'GET'}
                onChange={(e) => onChange(node.id, { config: { ...data.config, method: e.target.value } })}
              >
                {['GET', 'POST', 'PUT', 'PATCH', 'DELETE'].map((m) => (
                  <option key={m} value={m}>{m}</option>
                ))}
              </select>
            </ConfigField>
            <ConfigField label="URL">
              <input
                className={inputClass}
                placeholder="https://api.example.com/endpoint"
                value={data.config?.url || ''}
                onChange={(e) => onChange(node.id, { config: { ...data.config, url: e.target.value } })}
              />
            </ConfigField>
            <ConfigField label="Request Body (JSON)">
              <textarea
                className={textareaClass}
                rows={3}
                placeholder='{"key": "{{value}}"}'
                value={data.config?.body || ''}
                onChange={(e) => onChange(node.id, { config: { ...data.config, body: e.target.value } })}
              />
            </ConfigField>
          </>
        )}

        {nodeType === 'delay' && (
          <ConfigField label="Delay (seconds)">
            <input
              type="number" min="1"
              className={inputClass}
              placeholder="5"
              value={data.config?.delay_seconds || ''}
              onChange={(e) => onChange(node.id, { config: { ...data.config, delay_seconds: parseInt(e.target.value) } })}
            />
          </ConfigField>
        )}

        {nodeType === 'trigger' && (
          <ConfigField label="Trigger Type">
            <select
              className={inputClass}
              value={data.config?.trigger_type || 'manual'}
              onChange={(e) => onChange(node.id, { config: { ...data.config, trigger_type: e.target.value } })}
            >
              <option value="manual">Manual (API call)</option>
              <option value="schedule">Scheduled (cron)</option>
              <option value="webhook">Webhook</option>
              <option value="event">Event-based</option>
            </select>
          </ConfigField>
        )}

        {nodeType === 'output' && (
          <ConfigField label="Output Variable Name">
            <input
              className={inputClass}
              placeholder="result"
              value={data.config?.output_var || ''}
              onChange={(e) => onChange(node.id, { config: { ...data.config, output_var: e.target.value } })}
            />
          </ConfigField>
        )}

        {/* Node ID (debug) */}
        <div
          className="px-3 py-2 rounded-lg text-[10px] font-inter text-white/20"
          style={{ background: 'rgba(255,255,255,0.02)', border: '1px solid rgba(255,255,255,0.04)' }}
        >
          Node ID: <span className="text-white/35">{node.id}</span>
        </div>
      </div>

      {/* Delete footer */}
      <div className="p-4" style={{ borderTop: '1px solid rgba(255,255,255,0.05)' }}>
        <Button
          onClick={() => onDelete(node.id)}
          variant="outline"
          className="w-full h-9 rounded-xl border-red-500/20 bg-red-500/5 text-red-400 hover:bg-red-500/10 hover:text-red-300 text-xs font-inter"
        >
          <Trash2 size={13} className="mr-2" />
          Delete Node
        </Button>
      </div>
    </motion.div>
  );
});

NodeConfigPanel.displayName = 'NodeConfigPanel';

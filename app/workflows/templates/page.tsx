'use client';

import { useState } from 'react';
import { useRouter } from 'next/navigation';
import DashboardLayout from '@/components/dashboard/DashboardLayout';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import {
  Search, ArrowLeft, Zap, Bot, Mail, Globe, Database,
  ShoppingCart, MessageSquare, FileText, Sparkles, Clock,
  ArrowRight, Star, Users, TrendingUp, Shield, Layers
} from 'lucide-react';
import Link from 'next/link';

/* ────────── Template Data ────────── */
interface WorkflowTemplate {
  id: string;
  name: string;
  description: string;
  category: string;
  difficulty: 'Beginner' | 'Intermediate' | 'Advanced';
  nodeCount: number;
  estimatedTime: string;
  tags: string[];
  icon: React.ReactNode;
  popular?: boolean;
  nodes: Array<{
    id: string;
    type: string;
    name: string;
    config: Record<string, any>;
    position: { x: number; y: number };
  }>;
  connections: Array<{
    id: string;
    from: string;
    to: string;
  }>;
}

const TEMPLATES: WorkflowTemplate[] = [
  {
    id: 'tpl-email-auto',
    name: 'AI Email Responder',
    description: 'Automatically generate and send professional email responses using AI. Triggered manually, processes input through OpenAI, and sends via email.',
    category: 'Communication',
    difficulty: 'Beginner',
    nodeCount: 3,
    estimatedTime: '5 min',
    tags: ['email', 'ai', 'automation'],
    icon: <Mail className="w-6 h-6" />,
    popular: true,
    nodes: [
      { id: 'trigger_1', type: 'ManualTrigger', name: 'Manual Trigger', config: {}, position: { x: 100, y: 200 } },
      { id: 'ai_1', type: 'OpenAI', name: 'Generate Response', config: { model: 'gpt-4', prompt: 'Write a professional email response to: {{input}}', temperature: 0.7 }, position: { x: 400, y: 200 } },
      { id: 'email_1', type: 'EmailSend', name: 'Send Email', config: { subject: 'Re: {{subject}}', body: '{{ai_1.output}}' }, position: { x: 700, y: 200 } },
    ],
    connections: [
      { id: 'conn_1', from: 'trigger_1', to: 'ai_1' },
      { id: 'conn_2', from: 'ai_1', to: 'email_1' },
    ],
  },
  {
    id: 'tpl-content-gen',
    name: 'Content Generator Pipeline',
    description: 'Generate blog posts, social media content, or marketing copy using multiple AI models and compare outputs for the best result.',
    category: 'AI/ML',
    difficulty: 'Intermediate',
    nodeCount: 5,
    estimatedTime: '10 min',
    tags: ['content', 'ai', 'multi-model'],
    icon: <Sparkles className="w-6 h-6" />,
    popular: true,
    nodes: [
      { id: 'trigger_1', type: 'ManualTrigger', name: 'Start', config: {}, position: { x: 100, y: 250 } },
      { id: 'ai_openai', type: 'OpenAI', name: 'OpenAI Draft', config: { model: 'gpt-4', prompt: 'Write a blog post about: {{topic}}', temperature: 0.8 }, position: { x: 400, y: 150 } },
      { id: 'ai_claude', type: 'ClaudeAI', name: 'Claude Draft', config: { model: 'claude-3-sonnet', prompt: 'Write a blog post about: {{topic}}', temperature: 0.7 }, position: { x: 400, y: 350 } },
      { id: 'formatter', type: 'DataFormatter', name: 'Compare & Format', config: { template: 'OpenAI:\n{{ai_openai.output}}\n\nClaude:\n{{ai_claude.output}}' }, position: { x: 700, y: 250 } },
      { id: 'logger', type: 'Logger', name: 'Log Results', config: { level: 'info' }, position: { x: 1000, y: 250 } },
    ],
    connections: [
      { id: 'conn_1', from: 'trigger_1', to: 'ai_openai' },
      { id: 'conn_2', from: 'trigger_1', to: 'ai_claude' },
      { id: 'conn_3', from: 'ai_openai', to: 'formatter' },
      { id: 'conn_4', from: 'ai_claude', to: 'formatter' },
      { id: 'conn_5', from: 'formatter', to: 'logger' },
    ],
  },
  {
    id: 'tpl-data-pipeline',
    name: 'Data Processing Pipeline',
    description: 'Fetch data from an API, parse JSON, apply conditional logic, and store results. Perfect for ETL-style workflows.',
    category: 'Data',
    difficulty: 'Intermediate',
    nodeCount: 5,
    estimatedTime: '8 min',
    tags: ['data', 'api', 'etl'],
    icon: <Database className="w-6 h-6" />,
    nodes: [
      { id: 'trigger_1', type: 'ManualTrigger', name: 'Start Pipeline', config: {}, position: { x: 100, y: 200 } },
      { id: 'http_1', type: 'HTTPRequest', name: 'Fetch Data', config: { method: 'GET', url: 'https://api.example.com/data' }, position: { x: 350, y: 200 } },
      { id: 'json_1', type: 'JSONParser', name: 'Parse Response', config: { path: '$.data' }, position: { x: 600, y: 200 } },
      { id: 'condition_1', type: 'Conditional', name: 'Check Status', config: { field: 'status', operator: 'equals', value: 'active' }, position: { x: 850, y: 200 } },
      { id: 'logger_1', type: 'Logger', name: 'Log Results', config: { level: 'info' }, position: { x: 1100, y: 200 } },
    ],
    connections: [
      { id: 'conn_1', from: 'trigger_1', to: 'http_1' },
      { id: 'conn_2', from: 'http_1', to: 'json_1' },
      { id: 'conn_3', from: 'json_1', to: 'condition_1' },
      { id: 'conn_4', from: 'condition_1', to: 'logger_1' },
    ],
  },
  {
    id: 'tpl-slack-notify',
    name: 'Scheduled Slack Notifier',
    description: 'Send automated status updates or reminders to your Slack channels on a schedule. Great for daily standups or weekly reports.',
    category: 'Communication',
    difficulty: 'Beginner',
    nodeCount: 3,
    estimatedTime: '3 min',
    tags: ['slack', 'schedule', 'notifications'],
    icon: <MessageSquare className="w-6 h-6" />,
    nodes: [
      { id: 'trigger_1', type: 'Scheduling', name: 'Daily at 9AM', config: { cron: '0 9 * * *', timezone: 'UTC' }, position: { x: 100, y: 200 } },
      { id: 'ai_1', type: 'OpenAI', name: 'Generate Update', config: { model: 'gpt-4', prompt: 'Generate a brief motivational morning message for a development team.', temperature: 0.9 }, position: { x: 400, y: 200 } },
      { id: 'slack_1', type: 'SlackMessage', name: 'Post to Slack', config: { channel: '#general', message: '{{ai_1.output}}' }, position: { x: 700, y: 200 } },
    ],
    connections: [
      { id: 'conn_1', from: 'trigger_1', to: 'ai_1' },
      { id: 'conn_2', from: 'ai_1', to: 'slack_1' },
    ],
  },
  {
    id: 'tpl-webhook-processor',
    name: 'Webhook Event Processor',
    description: 'Listen for incoming webhook events, process the payload with conditional branching, and trigger appropriate actions based on event type.',
    category: 'Integration',
    difficulty: 'Advanced',
    nodeCount: 5,
    estimatedTime: '12 min',
    tags: ['webhook', 'api', 'events'],
    icon: <Globe className="w-6 h-6" />,
    nodes: [
      { id: 'webhook_1', type: 'Webhook', name: 'Receive Event', config: { path: '/events' }, position: { x: 100, y: 250 } },
      { id: 'json_1', type: 'JSONParser', name: 'Parse Payload', config: { path: '$.body' }, position: { x: 350, y: 250 } },
      { id: 'condition_1', type: 'Conditional', name: 'Route by Type', config: { field: 'event_type', operator: 'equals', value: 'order.created' }, position: { x: 600, y: 250 } },
      { id: 'email_1', type: 'EmailSend', name: 'Send Notification', config: { subject: 'New Order Received' }, position: { x: 900, y: 150 } },
      { id: 'logger_1', type: 'Logger', name: 'Log Event', config: { level: 'info' }, position: { x: 900, y: 350 } },
    ],
    connections: [
      { id: 'conn_1', from: 'webhook_1', to: 'json_1' },
      { id: 'conn_2', from: 'json_1', to: 'condition_1' },
      { id: 'conn_3', from: 'condition_1', to: 'email_1' },
      { id: 'conn_4', from: 'condition_1', to: 'logger_1' },
    ],
  },
  {
    id: 'tpl-ai-chatbot',
    name: 'AI Chatbot Pipeline',
    description: 'Build a conversational AI pipeline using chat input, AI processing with context, and structured response formatting.',
    category: 'AI/ML',
    difficulty: 'Intermediate',
    nodeCount: 4,
    estimatedTime: '7 min',
    tags: ['chatbot', 'ai', 'conversation'],
    icon: <Bot className="w-6 h-6" />,
    popular: true,
    nodes: [
      { id: 'trigger_1', type: 'ManualTrigger', name: 'Start Chat', config: {}, position: { x: 100, y: 200 } },
      { id: 'chat_1', type: 'ChatInput', name: 'User Message', config: {}, position: { x: 350, y: 200 } },
      { id: 'ai_1', type: 'Gemini', name: 'Gemini Response', config: { model: 'gemini-pro', systemPrompt: 'You are a helpful assistant for FlowMind AI.', temperature: 0.7 }, position: { x: 600, y: 200 } },
      { id: 'formatter_1', type: 'DataFormatter', name: 'Format Reply', config: { template: '**Assistant:** {{ai_1.output}}' }, position: { x: 900, y: 200 } },
    ],
    connections: [
      { id: 'conn_1', from: 'trigger_1', to: 'chat_1' },
      { id: 'conn_2', from: 'chat_1', to: 'ai_1' },
      { id: 'conn_3', from: 'ai_1', to: 'formatter_1' },
    ],
  },
];

const CATEGORIES = ['All', 'AI/ML', 'Communication', 'Data', 'Integration'];

const DIFFICULTY_COLORS = {
  Beginner: 'text-green-400 bg-green-400/10 border-green-400/20',
  Intermediate: 'text-blue-400 bg-blue-400/10 border-blue-400/20',
  Advanced: 'text-purple-400 bg-purple-400/10 border-purple-400/20',
};

/* ────────── Page Component ────────── */
export default function TemplatesPage() {
  const router = useRouter();
  const [search, setSearch] = useState('');
  const [category, setCategory] = useState('All');

  const filtered = TEMPLATES.filter(t => {
    const matchSearch = !search || t.name.toLowerCase().includes(search.toLowerCase()) || t.description.toLowerCase().includes(search.toLowerCase()) || t.tags.some(tag => tag.includes(search.toLowerCase()));
    const matchCategory = category === 'All' || t.category === category;
    return matchSearch && matchCategory;
  });

  const handleUseTemplate = (template: WorkflowTemplate) => {
    // Store template data in sessionStorage so the editor can load it
    sessionStorage.setItem('workflow-template', JSON.stringify({
      name: template.name,
      nodes: template.nodes,
      connections: template.connections,
    }));
    router.push('/workflows/new?template=true');
  };

  return (
    <DashboardLayout>
      <div className="p-6 lg:p-8 space-y-8 max-w-7xl mx-auto">
        {/* Header */}
        <div className="flex items-center gap-4 mb-2">
          <Link href="/workflows">
            <Button variant="ghost" size="sm" className="text-white/60 hover:text-white">
              <ArrowLeft className="w-4 h-4 mr-2" /> Back to Workflows
            </Button>
          </Link>
        </div>

        <div>
          <h1 className="text-3xl lg:text-4xl font-bold text-white flex items-center gap-3">
            <Layers className="w-8 h-8 text-blue-400" />
            Workflow Templates
          </h1>
          <p className="text-white/60 text-lg mt-2">
            Start with a pre-built template and customize it to fit your needs
          </p>
        </div>

        {/* Stats Row */}
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          {[
            { label: 'Templates', value: TEMPLATES.length, icon: <Layers className="w-5 h-5" />, color: 'text-blue-400' },
            { label: 'Categories', value: CATEGORIES.length - 1, icon: <Shield className="w-5 h-5" />, color: 'text-purple-400' },
            { label: 'AI-Powered', value: TEMPLATES.filter(t => t.category === 'AI/ML').length, icon: <Bot className="w-5 h-5" />, color: 'text-emerald-400' },
            { label: 'Popular', value: TEMPLATES.filter(t => t.popular).length, icon: <Star className="w-5 h-5" />, color: 'text-amber-400' },
          ].map((stat) => (
            <div key={stat.label} className="bg-white/[0.03] border border-white/[0.06] rounded-xl p-4 flex items-center gap-4">
              <div className={`${stat.color} bg-white/5 p-2.5 rounded-lg`}>{stat.icon}</div>
              <div>
                <p className="text-2xl font-bold text-white">{stat.value}</p>
                <p className="text-xs text-white/50">{stat.label}</p>
              </div>
            </div>
          ))}
        </div>

        {/* Filters */}
        <div className="flex flex-col sm:flex-row items-start sm:items-center gap-4">
          <div className="relative flex-1 w-full">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-white/40" />
            <Input
              value={search}
              onChange={e => setSearch(e.target.value)}
              placeholder="Search templates..."
              className="pl-10 bg-white/5 border-white/10 text-white placeholder:text-white/40 h-10"
            />
          </div>
          <div className="flex gap-1 bg-white/[0.03] border border-white/[0.06] rounded-xl p-1">
            {CATEGORIES.map(cat => (
              <button
                key={cat}
                onClick={() => setCategory(cat)}
                className={`px-4 py-1.5 rounded-lg text-sm font-medium transition-colors ${
                  category === cat ? 'bg-blue-600 text-white' : 'text-white/50 hover:text-white'
                }`}
              >
                {cat}
              </button>
            ))}
          </div>
        </div>

        {/* Template Grid */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {filtered.map(template => (
            <div
              key={template.id}
              className="group relative bg-white/[0.03] border border-white/[0.06] hover:border-blue-500/30 rounded-2xl overflow-hidden transition-all duration-300 hover:-translate-y-1 hover:shadow-xl hover:shadow-blue-500/5"
            >
              {/* Top gradient bar */}
              <div className="h-1 bg-gradient-to-r from-blue-500 via-blue-600 to-indigo-600 opacity-0 group-hover:opacity-100 transition-opacity" />

              {template.popular && (
                <div className="absolute top-4 right-4 z-10">
                  <span className="flex items-center gap-1 text-xs font-medium text-amber-400 bg-amber-400/10 border border-amber-400/20 px-2 py-1 rounded-full">
                    <Star className="w-3 h-3 fill-current" /> Popular
                  </span>
                </div>
              )}

              <div className="p-6">
                {/* Icon + Category */}
                <div className="flex items-center gap-3 mb-4">
                  <div className="w-11 h-11 bg-blue-500/10 border border-blue-500/20 rounded-xl flex items-center justify-center text-blue-400">
                    {template.icon}
                  </div>
                  <div>
                    <span className="text-xs text-white/40 font-medium uppercase tracking-wider">{template.category}</span>
                  </div>
                </div>

                {/* Title + Description */}
                <h3 className="text-lg font-semibold text-white mb-2 group-hover:text-blue-300 transition-colors">
                  {template.name}
                </h3>
                <p className="text-sm text-white/50 line-clamp-2 mb-4 leading-relaxed">
                  {template.description}
                </p>

                {/* Tags */}
                <div className="flex flex-wrap gap-1.5 mb-4">
                  {template.tags.map(tag => (
                    <span key={tag} className="text-xs text-white/40 bg-white/5 px-2 py-0.5 rounded-full">
                      #{tag}
                    </span>
                  ))}
                </div>

                {/* Metadata Row */}
                <div className="flex items-center gap-4 text-xs text-white/40 mb-5">
                  <span className={`px-2 py-0.5 rounded-full border ${DIFFICULTY_COLORS[template.difficulty]}`}>
                    {template.difficulty}
                  </span>
                  <span className="flex items-center gap-1"><Zap className="w-3 h-3" /> {template.nodeCount} nodes</span>
                  <span className="flex items-center gap-1"><Clock className="w-3 h-3" /> {template.estimatedTime}</span>
                </div>

                {/* Action */}
                <Button
                  onClick={() => handleUseTemplate(template)}
                  className="w-full bg-blue-600 hover:bg-blue-700 text-white font-medium py-2.5 rounded-xl transition-all group-hover:shadow-lg group-hover:shadow-blue-500/20"
                >
                  Use Template <ArrowRight className="w-4 h-4 ml-2" />
                </Button>
              </div>
            </div>
          ))}
        </div>

        {filtered.length === 0 && (
          <div className="text-center py-16">
            <Search className="w-12 h-12 text-white/20 mx-auto mb-4" />
            <h3 className="text-xl font-medium text-white mb-2">No templates found</h3>
            <p className="text-white/50">Try adjusting your search or category filter</p>
          </div>
        )}
      </div>
    </DashboardLayout>
  );
}

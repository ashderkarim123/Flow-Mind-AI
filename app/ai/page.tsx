'use client';

import { useState, useRef } from 'react';
import DashboardLayout from '@/components/dashboard/DashboardLayout';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import {
  Bot, Send, Sparkles, Cpu, Zap, Settings2, RotateCcw,
  Copy, Check, ChevronDown, Loader2, Brain, Thermometer,
  Hash, MessageSquare, ArrowLeftRight, AlertCircle
} from 'lucide-react';

/* ────────── Model Definitions ────────── */
interface AIModel {
  id: string;
  name: string;
  provider: string;
  icon: string;
  description: string;
  color: string;
  maxTokens: number;
  defaultTemp: number;
}

const AI_MODELS: AIModel[] = [
  {
    id: 'gpt-4',
    name: 'GPT-4',
    provider: 'OpenAI',
    icon: '/assets/canvas/openai.svg',
    description: 'Most capable model for complex tasks, reasoning, and analysis',
    color: '#10A37F',
    maxTokens: 8192,
    defaultTemp: 0.7,
  },
  {
    id: 'gpt-3.5-turbo',
    name: 'GPT-3.5 Turbo',
    provider: 'OpenAI',
    icon: '/assets/canvas/openai.svg',
    description: 'Fast and efficient for most everyday tasks',
    color: '#10A37F',
    maxTokens: 4096,
    defaultTemp: 0.7,
  },
  {
    id: 'claude-3-sonnet',
    name: 'Claude 3 Sonnet',
    provider: 'Anthropic',
    icon: '/assets/canvas/claude.svg',
    description: 'Balanced intelligence and speed for enterprise workloads',
    color: '#D97706',
    maxTokens: 4096,
    defaultTemp: 0.7,
  },
  {
    id: 'gemini-pro',
    name: 'Gemini Pro',
    provider: 'Google',
    icon: '/assets/canvas/gemini-2.svg',
    description: 'Google\'s advanced multi-modal AI model — free tier available',
    color: '#4285F4',
    maxTokens: 8192,
    defaultTemp: 0.7,
  },
  {
    id: 'llama-3-70b',
    name: 'Llama 3 70B',
    provider: 'Groq',
    icon: '/assets/canvas/groq-4.svg',
    description: 'Ultra-fast open-source inference via Groq — free tier',
    color: '#F55036',
    maxTokens: 4096,
    defaultTemp: 0.7,
  },
];

/* ────────── Component ────────── */
interface ModelConfig {
  modelId: string;
  temperature: number;
  maxTokens: number;
  systemPrompt: string;
}

interface ModelResponse {
  modelId: string;
  content: string;
  tokens: number;
  latency: number;
  status: 'idle' | 'loading' | 'done' | 'error';
  error?: string;
}

export default function AIIntegrationPage() {
  const [prompt, setPrompt] = useState('');
  const [selectedModels, setSelectedModels] = useState<string[]>(['gpt-4', 'claude-3-sonnet']);
  const [showSettings, setShowSettings] = useState(false);
  const [configs, setConfigs] = useState<Record<string, ModelConfig>>(() => {
    const initial: Record<string, ModelConfig> = {};
    AI_MODELS.forEach(m => {
      initial[m.id] = {
        modelId: m.id,
        temperature: m.defaultTemp,
        maxTokens: Math.min(m.maxTokens, 2048),
        systemPrompt: 'You are a helpful AI assistant.',
      };
    });
    return initial;
  });
  const [responses, setResponses] = useState<Record<string, ModelResponse>>({});
  const [isComparing, setIsComparing] = useState(false);
  const [copiedId, setCopiedId] = useState<string | null>(null);
  const promptRef = useRef<HTMLTextAreaElement>(null);

  const toggleModel = (modelId: string) => {
    setSelectedModels(prev =>
      prev.includes(modelId)
        ? prev.filter(id => id !== modelId)
        : [...prev, modelId]
    );
  };

  const updateConfig = (modelId: string, key: keyof ModelConfig, value: any) => {
    setConfigs(prev => ({
      ...prev,
      [modelId]: { ...prev[modelId], [key]: value },
    }));
  };

  const handleCompare = async () => {
    if (!prompt.trim() || selectedModels.length === 0) return;

    setIsComparing(true);
    const newResponses: Record<string, ModelResponse> = {};

    // Set all selected models to loading
    selectedModels.forEach(id => {
      newResponses[id] = { modelId: id, content: '', tokens: 0, latency: 0, status: 'loading' };
    });
    setResponses({ ...newResponses });

    // Simulate parallel API calls (in production, these would hit real AI APIs via your backend)
    const promises = selectedModels.map(async (modelId) => {
      const config = configs[modelId];
      const model = AI_MODELS.find(m => m.id === modelId)!;
      const startTime = Date.now();

      try {
        // Simulated response — in production, call your backend /api/v1/ai/generate
        await new Promise(resolve => setTimeout(resolve, 1500 + Math.random() * 2000));

        const simulatedContent = generateSimulatedResponse(model.name, prompt, config);
        const latency = Date.now() - startTime;
        const tokens = Math.floor(simulatedContent.length / 4);

        setResponses(prev => ({
          ...prev,
          [modelId]: {
            modelId,
            content: simulatedContent,
            tokens,
            latency,
            status: 'done',
          },
        }));
      } catch (err: any) {
        setResponses(prev => ({
          ...prev,
          [modelId]: {
            modelId,
            content: '',
            tokens: 0,
            latency: Date.now() - startTime,
            status: 'error',
            error: err.message || 'Failed to generate response',
          },
        }));
      }
    });

    await Promise.all(promises);
    setIsComparing(false);
  };

  const copyToClipboard = (text: string, modelId: string) => {
    navigator.clipboard.writeText(text);
    setCopiedId(modelId);
    setTimeout(() => setCopiedId(null), 2000);
  };

  const resetAll = () => {
    setResponses({});
    setPrompt('');
    setIsComparing(false);
  };

  return (
    <DashboardLayout>
      <div className="p-6 lg:p-8 space-y-6 max-w-7xl mx-auto">
        {/* Header */}
        <div>
          <h1 className="text-3xl lg:text-4xl font-bold text-white flex items-center gap-3">
            <Brain className="w-8 h-8 text-blue-400" />
            AI Integration
          </h1>
          <p className="text-white/60 text-lg mt-2">
            Configure AI models, compare outputs side-by-side, and build intelligent workflows
          </p>
        </div>

        {/* Model Selector */}
        <div className="bg-white/[0.03] border border-white/[0.06] rounded-2xl p-6">
          <div className="flex items-center justify-between mb-4">
            <h2 className="text-lg font-semibold text-white flex items-center gap-2">
              <Cpu className="w-5 h-5 text-blue-400" /> Select Models
            </h2>
            <button
              onClick={() => setShowSettings(!showSettings)}
              className="flex items-center gap-2 text-sm text-white/50 hover:text-white transition-colors"
            >
              <Settings2 className="w-4 h-4" /> {showSettings ? 'Hide' : 'Show'} Settings
            </button>
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-5 gap-3">
            {AI_MODELS.map(model => {
              const isSelected = selectedModels.includes(model.id);
              return (
                <button
                  key={model.id}
                  onClick={() => toggleModel(model.id)}
                  className={`relative p-4 rounded-xl border transition-all duration-200 text-left ${
                    isSelected
                      ? 'bg-blue-500/10 border-blue-500/30 shadow-lg shadow-blue-500/5'
                      : 'bg-white/[0.02] border-white/[0.06] hover:border-white/15'
                  }`}
                >
                  {isSelected && (
                    <div className="absolute top-2 right-2">
                      <Check className="w-4 h-4 text-blue-400" />
                    </div>
                  )}
                  <div className="flex items-center gap-3 mb-2">
                    <div className="w-8 h-8 rounded-lg bg-black/30 flex items-center justify-center overflow-hidden">
                      <img src={model.icon} alt={model.name} className="w-5 h-5 object-contain" />
                    </div>
                    <div>
                      <p className="text-sm font-medium text-white">{model.name}</p>
                      <p className="text-xs text-white/40">{model.provider}</p>
                    </div>
                  </div>
                  <p className="text-xs text-white/40 line-clamp-2">{model.description}</p>
                </button>
              );
            })}
          </div>

          {/* Model Settings (Collapsible) */}
          {showSettings && selectedModels.length > 0 && (
            <div className="mt-6 pt-6 border-t border-white/[0.06] grid grid-cols-1 md:grid-cols-2 gap-6">
              {selectedModels.map(modelId => {
                const model = AI_MODELS.find(m => m.id === modelId)!;
                const config = configs[modelId];
                return (
                  <div key={modelId} className="bg-white/[0.02] border border-white/[0.06] rounded-xl p-5">
                    <div className="flex items-center gap-2 mb-4">
                      <img src={model.icon} alt={model.name} className="w-5 h-5" />
                      <h3 className="text-sm font-semibold text-white">{model.name} Settings</h3>
                    </div>

                    {/* Temperature */}
                    <div className="mb-4">
                      <label className="flex items-center gap-2 text-xs text-white/50 mb-1.5">
                        <Thermometer className="w-3.5 h-3.5" /> Temperature: {config.temperature}
                      </label>
                      <input
                        type="range"
                        min="0"
                        max="2"
                        step="0.1"
                        value={config.temperature}
                        onChange={e => updateConfig(modelId, 'temperature', parseFloat(e.target.value))}
                        className="w-full h-1.5 bg-white/10 rounded-full appearance-none cursor-pointer accent-blue-500"
                      />
                      <div className="flex justify-between text-xs text-white/30 mt-1">
                        <span>Precise</span>
                        <span>Creative</span>
                      </div>
                    </div>

                    {/* Max Tokens */}
                    <div className="mb-4">
                      <label className="flex items-center gap-2 text-xs text-white/50 mb-1.5">
                        <Hash className="w-3.5 h-3.5" /> Max Tokens
                      </label>
                      <Input
                        type="number"
                        value={config.maxTokens}
                        onChange={e => updateConfig(modelId, 'maxTokens', parseInt(e.target.value) || 256)}
                        min={64}
                        max={model.maxTokens}
                        className="bg-white/5 border-white/10 text-white h-8 text-sm"
                      />
                    </div>

                    {/* System Prompt */}
                    <div>
                      <label className="flex items-center gap-2 text-xs text-white/50 mb-1.5">
                        <MessageSquare className="w-3.5 h-3.5" /> System Prompt
                      </label>
                      <textarea
                        value={config.systemPrompt}
                        onChange={e => updateConfig(modelId, 'systemPrompt', e.target.value)}
                        rows={2}
                        className="w-full bg-white/5 border border-white/10 text-white text-sm rounded-lg p-2.5 resize-none focus:border-blue-500/50 focus:outline-none"
                        placeholder="You are a helpful assistant..."
                      />
                    </div>
                  </div>
                );
              })}
            </div>
          )}
        </div>

        {/* Prompt Input */}
        <div className="bg-white/[0.03] border border-white/[0.06] rounded-2xl p-6">
          <h2 className="text-lg font-semibold text-white flex items-center gap-2 mb-4">
            <Sparkles className="w-5 h-5 text-blue-400" /> Prompt
          </h2>
          <div className="relative">
            <textarea
              ref={promptRef}
              value={prompt}
              onChange={e => setPrompt(e.target.value)}
              placeholder="Enter your prompt here... e.g. 'Explain quantum computing in simple terms'"
              rows={4}
              className="w-full bg-white/[0.03] border border-white/[0.08] text-white rounded-xl p-4 pr-24 resize-none focus:border-blue-500/50 focus:outline-none placeholder:text-white/30 text-sm leading-relaxed"
              onKeyDown={e => {
                if (e.key === 'Enter' && (e.metaKey || e.ctrlKey)) {
                  handleCompare();
                }
              }}
            />
            <div className="absolute bottom-3 right-3 flex gap-2">
              <Button
                onClick={resetAll}
                variant="ghost"
                size="sm"
                className="text-white/40 hover:text-white h-8"
              >
                <RotateCcw className="w-3.5 h-3.5" />
              </Button>
              <Button
                onClick={handleCompare}
                disabled={!prompt.trim() || selectedModels.length === 0 || isComparing}
                className="bg-blue-600 hover:bg-blue-700 text-white h-8 px-4 text-sm disabled:opacity-50"
              >
                {isComparing ? (
                  <><Loader2 className="w-3.5 h-3.5 mr-1.5 animate-spin" /> Running...</>
                ) : (
                  <><ArrowLeftRight className="w-3.5 h-3.5 mr-1.5" /> Compare ({selectedModels.length})</>
                )}
              </Button>
            </div>
          </div>
          <p className="text-xs text-white/30 mt-2">Press Ctrl+Enter to run comparison</p>
        </div>

        {/* Response Comparison Grid */}
        {Object.keys(responses).length > 0 && (
          <div className="space-y-4">
            <h2 className="text-lg font-semibold text-white flex items-center gap-2">
              <ArrowLeftRight className="w-5 h-5 text-blue-400" /> Comparison Results
            </h2>

            <div className={`grid gap-6 ${
              selectedModels.length === 1 ? 'grid-cols-1' :
              selectedModels.length === 2 ? 'grid-cols-1 lg:grid-cols-2' :
              'grid-cols-1 lg:grid-cols-2 xl:grid-cols-3'
            }`}>
              {selectedModels.map(modelId => {
                const model = AI_MODELS.find(m => m.id === modelId)!;
                const response = responses[modelId];
                if (!response) return null;

                return (
                  <div
                    key={modelId}
                    className="bg-white/[0.03] border border-white/[0.06] rounded-2xl overflow-hidden flex flex-col"
                  >
                    {/* Model Header */}
                    <div className="p-4 border-b border-white/[0.06] flex items-center justify-between">
                      <div className="flex items-center gap-3">
                        <div className="w-8 h-8 rounded-lg bg-black/30 flex items-center justify-center">
                          <img src={model.icon} alt={model.name} className="w-5 h-5 object-contain" />
                        </div>
                        <div>
                          <p className="text-sm font-semibold text-white">{model.name}</p>
                          <p className="text-xs text-white/40">{model.provider}</p>
                        </div>
                      </div>

                      {response.status === 'done' && (
                        <div className="flex items-center gap-3 text-xs text-white/40">
                          <span>{response.tokens} tokens</span>
                          <span>{(response.latency / 1000).toFixed(1)}s</span>
                          <button
                            onClick={() => copyToClipboard(response.content, modelId)}
                            className="p-1.5 rounded-md hover:bg-white/10 transition-colors"
                          >
                            {copiedId === modelId ? (
                              <Check className="w-3.5 h-3.5 text-green-400" />
                            ) : (
                              <Copy className="w-3.5 h-3.5" />
                            )}
                          </button>
                        </div>
                      )}
                    </div>

                    {/* Response Body */}
                    <div className="p-4 flex-1 min-h-[200px]">
                      {response.status === 'loading' && (
                        <div className="flex items-center justify-center h-full">
                          <div className="text-center">
                            <Loader2 className="w-8 h-8 text-blue-400 animate-spin mx-auto mb-3" />
                            <p className="text-sm text-white/50">Generating response...</p>
                          </div>
                        </div>
                      )}

                      {response.status === 'done' && (
                        <div className="text-sm text-white/80 leading-relaxed whitespace-pre-wrap">
                          {response.content}
                        </div>
                      )}

                      {response.status === 'error' && (
                        <div className="flex items-center gap-3 text-red-400 bg-red-400/10 p-4 rounded-xl">
                          <AlertCircle className="w-5 h-5 flex-shrink-0" />
                          <p className="text-sm">{response.error}</p>
                        </div>
                      )}
                    </div>

                    {/* Footer Stats */}
                    {response.status === 'done' && (
                      <div className="px-4 py-3 border-t border-white/[0.06] bg-white/[0.02] flex items-center gap-4 text-xs text-white/30">
                        <span>Temp: {configs[modelId].temperature}</span>
                        <span>Max: {configs[modelId].maxTokens}</span>
                        <span className="ml-auto text-green-400/60">✓ Complete</span>
                      </div>
                    )}
                  </div>
                );
              })}
            </div>
          </div>
        )}

        {/* Empty State */}
        {Object.keys(responses).length === 0 && (
          <div className="bg-white/[0.02] border border-white/[0.04] rounded-2xl p-12 text-center">
            <Bot className="w-16 h-16 text-white/10 mx-auto mb-4" />
            <h3 className="text-xl font-medium text-white/60 mb-2">Ready to Compare</h3>
            <p className="text-sm text-white/30 max-w-md mx-auto">
              Select your AI models above, enter a prompt, and click Compare to see
              side-by-side responses from multiple models.
            </p>
          </div>
        )}
      </div>
    </DashboardLayout>
  );
}

/* ────────── Simulated Response Generator ────────── */
function generateSimulatedResponse(modelName: string, prompt: string, config: ModelConfig): string {
  const topic = prompt.toLowerCase();
  
  const responses: Record<string, string> = {
    'GPT-4': `Here's a comprehensive analysis based on your prompt:\n\n${prompt}\n\n**Key Points:**\n\n1. **Context Understanding**: The query relates to a complex topic that requires careful consideration of multiple factors and perspectives.\n\n2. **Analysis**: Based on current research and understanding, there are several important aspects to consider when approaching this subject.\n\n3. **Recommendations**: I would suggest starting with a foundational understanding before diving into the more nuanced details.\n\n4. **Conclusion**: This topic continues to evolve, and staying updated with the latest developments is essential for a complete understanding.\n\n*Generated by GPT-4 with temperature ${config.temperature}*`,
    
    'GPT-3.5 Turbo': `Based on your question about "${prompt.slice(0, 60)}...":\n\nThis is an interesting topic! Here are the main points:\n\n• First, it's important to understand the basic concepts involved.\n• Second, there are practical applications that make this relevant.\n• Third, ongoing research continues to expand our knowledge.\n\nWould you like me to elaborate on any of these points?\n\n*Generated by GPT-3.5 Turbo with temperature ${config.temperature}*`,
    
    'Claude 3 Sonnet': `I'd be happy to help with your question.\n\n**Understanding "${prompt.slice(0, 50)}..."**\n\nLet me break this down into clear, digestible parts:\n\n**Foundation:**\nThis subject involves several interconnected concepts that build upon each other. Understanding the fundamentals is crucial before exploring advanced aspects.\n\n**Practical Application:**\nIn real-world scenarios, this knowledge can be applied in various ways, from academic research to industry applications.\n\n**Current State:**\nThe field is actively evolving, with new discoveries and methodologies emerging regularly. Staying informed about recent developments provides a competitive advantage.\n\n**Key Takeaway:**\nThe most important thing to remember is that this is a multifaceted topic that benefits from a holistic approach to understanding.\n\n*Generated by Claude 3 Sonnet with temperature ${config.temperature}*`,
    
    'Gemini Pro': `## Response to: "${prompt.slice(0, 50)}..."\n\nGreat question! Let me provide a well-structured response:\n\n### Overview\nThis topic spans multiple domains and has significant implications across various fields.\n\n### Key Aspects\n1. **Theoretical Foundation** — The underlying principles are well-established and supported by extensive research.\n2. **Practical Implementation** — There are numerous real-world applications that demonstrate the value of this knowledge.\n3. **Future Directions** — Emerging trends suggest exciting developments on the horizon.\n\n### Summary\nUnderstanding this topic opens doors to innovative solutions and deeper insights. I recommend exploring both the theoretical and practical dimensions for a complete picture.\n\n*Generated by Gemini Pro with temperature ${config.temperature}*`,
    
    'Llama 3 70B': `Here's my take on "${prompt.slice(0, 50)}...":\n\nThis is a fascinating area that has seen tremendous growth and interest in recent years.\n\n**What You Should Know:**\n\n→ The fundamentals are straightforward but the applications are vast\n→ There are open-source resources available for deeper exploration\n→ Community-driven development has accelerated progress significantly\n→ Practical experimentation is the best way to build understanding\n\n**My Recommendation:**\nStart with hands-on experimentation. Theory is important, but practical experience will solidify your understanding much faster.\n\n*Generated by Llama 3 70B (via Groq) with temperature ${config.temperature}*`,
  };

  return responses[modelName] || `Response from ${modelName} for prompt: "${prompt.slice(0, 100)}..."`;
}

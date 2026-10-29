/**
 * Typed wrappers for the AI / MCP endpoints (see backend/app/api/v1/ai.py and mcp.py).
 * apiClient rejects with { status, message }, so callers can show `e.message` directly.
 */

import apiClient from '@/lib/api/client';

export interface LocalStatus {
  baseUrl: string;
  reachable: boolean;
  models: string[];
  error: string | null;
}

export interface AiStatus {
  assistant: { provider: string | null; model: string | null; ready: boolean; problem: string | null };
  local: LocalStatus;
  cloudKeys: Record<'openai' | 'anthropic' | 'gemini' | 'groq', boolean>;
  mcp: { stdioEnabled: boolean };
}

export interface GeneratedWorkflow {
  name: string;
  description: string;
  nodes: Record<string, any>[];
  edges: Record<string, any>[];
  steps: { id: string; name: string; type: string }[];
  warnings: string[];
  todo: { nodeId: string; nodeName: string; field: string; label: string }[];
  model: string;
  provider: string;
}

export interface McpServerInfo {
  id: string;
  name: string;
  transport: 'http' | 'stdio';
  url: string;
  command: string;
  args: string[];
  headerNames: string[];
  envNames: string[];
  createdAt: string | null;
}

export interface McpServerInput {
  name: string;
  transport: 'http' | 'stdio';
  url?: string;
  headers?: Record<string, string>;
  command?: string;
  args?: string[];
  env?: Record<string, string>;
}

export interface McpCatalogEntry {
  key: string;
  name: string;
  description: string;
  transport: 'http' | 'stdio';
  command?: string;
  args?: string[];
  url?: string;
  requires: string | null;
  hint?: string;
}

export interface McpTool {
  name: string;
  description: string;
  inputSchema: { type?: string; properties?: Record<string, any>; required?: string[] };
}

export const aiToolsApi = {
  status: () => apiClient.get<AiStatus>('/api/v1/ai/status').then((r) => r.data),

  localModels: (baseUrl?: string) =>
    apiClient.get<LocalStatus>('/api/v1/ai/local-models', { params: { base_url: baseUrl || undefined } }).then((r) => r.data),

  // Local models on CPU can take minutes to draft a workflow
  generateWorkflow: (prompt: string) =>
    apiClient.post<GeneratedWorkflow>('/api/v1/ai/generate-workflow', { prompt }, { timeout: 330_000 }).then((r) => r.data),

  assist: (question: string, currentState?: unknown) =>
    apiClient
      .post<{ answer: string }>('/api/v1/ai/assist', { question, current_state: currentState ?? null }, { timeout: 330_000 })
      .then((r) => r.data),

  mcp: {
    catalog: () =>
      apiClient
        .get<{ servers: McpCatalogEntry[]; stdioEnabled: boolean; canAddStdio: boolean }>('/api/v1/mcp/catalog')
        .then((r) => r.data),
    list: () => apiClient.get<{ servers: McpServerInfo[] }>('/api/v1/mcp/servers').then((r) => r.data.servers),
    add: (server: McpServerInput) => apiClient.post<McpServerInfo>('/api/v1/mcp/servers', server).then((r) => r.data),
    remove: (id: string) => apiClient.delete(`/api/v1/mcp/servers/${id}`).then((r) => r.data),
    // first run of `npx`/`uvx` servers downloads packages, so allow a long test
    test: (id: string) =>
      apiClient
        .post<{ ok: boolean; toolCount: number; tools: string[]; error: string | null }>(`/api/v1/mcp/servers/${id}/test`, undefined, { timeout: 90_000 })
        .then((r) => r.data),
    tools: (id: string) =>
      apiClient.get<{ tools: McpTool[] }>(`/api/v1/mcp/servers/${id}/tools`, { timeout: 90_000 }).then((r) => r.data.tools),
  },
};

/** Save a generated draft through the normal create-workflow endpoint and return its id. */
export async function saveGeneratedWorkflow(draft: GeneratedWorkflow): Promise<string> {
  const { data } = await apiClient.post('/api/v1/workflows', {
    name: draft.name,
    description: draft.description,
    nodes: draft.nodes,
    edges: draft.edges,
    variables: {},
  });
  return data.workflow.id as string;
}

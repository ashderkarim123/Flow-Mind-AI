export type UserRole = 'admin' | 'editor' | 'viewer'

export type FlowMindNodeType =
  | 'input'
  | 'prompt'
  | 'ai_model'
  | 'condition'
  | 'output'
  | 'webhook'

export interface FlowMindNodePosition {
  x: number
  y: number
}

export interface FlowMindNodeData {
  label: string
  description?: string
  provider?: string
  model?: string
  promptTemplate?: string
  temperature?: number
  maxTokens?: number
  compareMode?: boolean
  config?: Record<string, unknown>
}

export interface FlowMindNode {
  id: string
  type: FlowMindNodeType
  position: FlowMindNodePosition
  data: FlowMindNodeData
}

export interface FlowMindEdge {
  id: string
  source: string
  target: string
  condition?: string
}

export interface FlowMindWorkflow {
  id?: string
  name: string
  description?: string
  status?: 'draft' | 'published'
  nodes: FlowMindNode[]
  edges: FlowMindEdge[]
  createdAt?: string
  updatedAt?: string
}

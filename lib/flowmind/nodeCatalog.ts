import type { FlowMindNodeType } from './types'

export interface NodeCatalogItem {
  type: FlowMindNodeType
  title: string
  description: string
}

export const FLOWMIND_NODE_CATALOG: NodeCatalogItem[] = [
  {
    type: 'input',
    title: 'Input Node',
    description: 'Collects or injects structured input into the workflow.',
  },
  {
    type: 'prompt',
    title: 'Prompt Node',
    description: 'Builds the prompt template before sending it to a model.',
  },
  {
    type: 'ai_model',
    title: 'AI Model Node',
    description: 'Calls a configured AI provider and model.',
  },
  {
    type: 'condition',
    title: 'Condition Node',
    description: 'Branches workflow logic based on rules or output values.',
  },
  {
    type: 'output',
    title: 'Output Node',
    description: 'Displays or returns the final workflow result.',
  },
  {
    type: 'webhook',
    title: 'Webhook Node',
    description: 'Sends or receives data using webhook-based integration.',
  },
]

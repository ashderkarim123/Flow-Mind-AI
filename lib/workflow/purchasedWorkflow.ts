import { Workflow } from '@/lib/workflow/types';
import { getNodeMapping, convertCanvasNodeToWorkflowNode } from '@/lib/workflow/utils/NodeMapping';

/**
 * A purchased marketplace workflow ({ name, nodes, connections }, as exported by the editor) → the
 * Workflow the editor's own Save would have stored, so it can be saved straight into "My Workflows".
 */
export function purchasedToWorkflow(data: Record<string, any>, fallbackName: string): Workflow {
  const now = new Date().toISOString();
  const nodes = (data.nodes || []).map((n: any) => {
    const config = n.config || {};
    const canvasNode = { id: n.id, type: n.type, name: n.name, x: n.position?.x || 0, y: n.position?.y || 0, config, data: { type: n.type, name: n.name, config } };
    const mapping = getNodeMapping(n.type);
    if (mapping) return convertCanvasNodeToWorkflowNode(canvasNode, mapping);
    return {
      id: n.id, type: n.type, category: 'action' as any, name: n.name || n.type, description: `Node: ${n.type}`,
      position: { x: canvasNode.x, y: canvasNode.y }, config, inputs: [], outputs: [], version: '1.0.0', enabled: true, tags: [],
      createdAt: now, updatedAt: now,
    };
  });

  return {
    id: `workflow_${Date.now()}`,   // the backend replaces it with the real id on save
    name: data.name || fallbackName || 'Purchased workflow',
    description: 'Deployed from the marketplace',
    nodes,
    connections: (data.connections || []).map((c: any) => ({
      id: c.id, sourceNodeId: c.from, sourcePortId: 'output', targetNodeId: c.to, targetPortId: 'input',
      condition: c.condition ?? undefined, type: 'default' as any, enabled: true,
    })),
    settings: { timeout: 300000, retryCount: 3, concurrency: 1, errorHandling: 'stop' },
    createdAt: now,
    updatedAt: now,
    version: '1.0.0',
  } as Workflow;
}

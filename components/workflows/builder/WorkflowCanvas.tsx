'use client';

import { useCallback, useRef, useState } from 'react';
import {
  ReactFlow, Background, Controls, MiniMap, addEdge,
  useNodesState, useEdgesState, Connection, BackgroundVariant,
  Panel, Node, Edge,
} from '@xyflow/react';
import '@xyflow/react/dist/style.css';
import { nodeTypes, NodeTypeKey, NODE_TYPES_CONFIG } from './nodes/FlowNodes';
import { NodeLibrary } from './NodeLibrary';
import { NodeConfigPanel } from './NodeConfigPanel';
import { WorkflowToolbar } from './WorkflowToolbar';

const INITIAL_NODES: Node[] = [
  {
    id: 'trigger-1',
    type: 'trigger',
    position: { x: 80, y: 200 },
    data: { type: 'trigger', label: 'Workflow Start', description: 'Triggered manually' },
  },
];

const INITIAL_EDGES: Edge[] = [];

let nodeIdCounter = 100;
function getNewNodeId() {
  return `node-${++nodeIdCounter}`;
}

interface WorkflowCanvasProps {
  workflowName?: string;
  initialNodes?: Node[];
  initialEdges?: Edge[];
  onSave?: (nodes: Node[], edges: Edge[]) => Promise<void>;
}

export function WorkflowCanvas({
  workflowName = 'Untitled Workflow',
  initialNodes = INITIAL_NODES,
  initialEdges = INITIAL_EDGES,
  onSave,
}: WorkflowCanvasProps) {
  const reactFlowWrapper = useRef<HTMLDivElement>(null);
  const [nodes, setNodes, onNodesChange] = useNodesState(initialNodes);
  const [edges, setEdges, onEdgesChange] = useEdgesState(initialEdges);
  const [selectedNode, setSelectedNode] = useState<Node | null>(null);
  const [saving, setSaving] = useState(false);
  const [reactFlowInstance, setReactFlowInstance] = useState<any>(null);

  /* ── Connect two nodes ── */
  const onConnect = useCallback(
    (connection: Connection) =>
      setEdges((eds) =>
        addEdge(
          {
            ...connection,
            animated: true,
            style: { stroke: '#7C3AED', strokeWidth: 2 },
          },
          eds,
        ),
      ),
    [setEdges],
  );

  /* ── Drop new node from library ── */
  const onDrop = useCallback(
    (event: React.DragEvent) => {
      event.preventDefault();
      const nodeType = event.dataTransfer.getData('application/flowmind-node') as NodeTypeKey;
      if (!nodeType || !reactFlowInstance || !reactFlowWrapper.current) return;

      const bounds = reactFlowWrapper.current.getBoundingClientRect();
      const position = reactFlowInstance.screenToFlowPosition({
        x: event.clientX - bounds.left,
        y: event.clientY - bounds.top,
      });

      const config = NODE_TYPES_CONFIG[nodeType];
      const newNode: Node = {
        id: getNewNodeId(),
        type: nodeType,
        position,
        data: {
          type: nodeType,
          label: config.label,
          description: '',
          config: {},
        },
      };

      setNodes((nds) => nds.concat(newNode));
    },
    [reactFlowInstance, setNodes],
  );

  const onDragOver = useCallback((event: React.DragEvent) => {
    event.preventDefault();
    event.dataTransfer.dropEffect = 'move';
  }, []);

  const onDragStart = useCallback((event: React.DragEvent, nodeType: NodeTypeKey) => {
    event.dataTransfer.setData('application/flowmind-node', nodeType);
    event.dataTransfer.effectAllowed = 'move';
  }, []);

  /* ── Node selection ── */
  const onNodeClick = useCallback((_: React.MouseEvent, node: Node) => {
    setSelectedNode(node);
  }, []);

  const onPaneClick = useCallback(() => {
    setSelectedNode(null);
  }, []);

  /* ── Update selected node config ── */
  const onNodeConfigChange = useCallback(
    (nodeId: string, updates: Partial<Node['data']>) => {
      setNodes((nds) =>
        nds.map((n) => (n.id === nodeId ? { ...n, data: { ...n.data, ...updates } } : n)),
      );
      setSelectedNode((prev) =>
        prev?.id === nodeId ? { ...prev, data: { ...prev.data, ...updates } } : prev,
      );
    },
    [setNodes],
  );

  /* ── Delete selected node ── */
  const onDeleteNode = useCallback(
    (nodeId: string) => {
      setNodes((nds) => nds.filter((n) => n.id !== nodeId));
      setEdges((eds) => eds.filter((e) => e.source !== nodeId && e.target !== nodeId));
      setSelectedNode(null);
    },
    [setNodes, setEdges],
  );

  /* ── Save workflow ── */
  const handleSave = useCallback(async () => {
    if (!onSave) return;
    setSaving(true);
    try {
      await onSave(nodes, edges);
    } finally {
      setSaving(false);
    }
  }, [onSave, nodes, edges]);

  /* ── Run workflow ── */
  const handleRun = useCallback(() => {
    console.log('Running workflow:', { nodes, edges });
    // TODO: trigger backend execution
  }, [nodes, edges]);

  return (
    <div
      className="flex h-full w-full"
      style={{ background: 'var(--fm-bg-deep)' }}
    >
      {/* Left: Node Library */}
      <NodeLibrary onDragStart={onDragStart} />

      {/* Center: Canvas */}
      <div className="flex-1 flex flex-col">
        {/* Toolbar */}
        <WorkflowToolbar
          workflowName={workflowName}
          nodeCount={nodes.length}
          edgeCount={edges.length}
          saving={saving}
          onSave={handleSave}
          onRun={handleRun}
        />

        {/* React Flow */}
        <div ref={reactFlowWrapper} className="flex-1">
          <ReactFlow
            nodes={nodes}
            edges={edges}
            onNodesChange={onNodesChange}
            onEdgesChange={onEdgesChange}
            onConnect={onConnect}
            onDrop={onDrop}
            onDragOver={onDragOver}
            onNodeClick={onNodeClick}
            onPaneClick={onPaneClick}
            onInit={setReactFlowInstance}
            nodeTypes={nodeTypes as any}
            fitView
            attributionPosition="bottom-right"
            deleteKeyCode="Delete"
            defaultEdgeOptions={{
              animated: true,
              style: { stroke: '#7C3AED', strokeWidth: 2 },
            }}
          >
            <Background
              variant={BackgroundVariant.Dots}
              gap={24}
              size={1}
              color="rgba(124,58,237,0.2)"
              style={{ background: 'var(--fm-bg-deep)' }}
            />
            <Controls
              position="bottom-left"
              showInteractive={false}
            />
            <MiniMap
              position="bottom-right"
              nodeColor={(n) => {
                const type = n.type as NodeTypeKey;
                return NODE_TYPES_CONFIG[type]?.color || '#7C3AED';
              }}
              maskColor="rgba(5,5,15,0.8)"
            />

            {/* Empty state */}
            {nodes.length <= 1 && (
              <Panel position="top-center">
                <div
                  className="mt-16 px-5 py-3 rounded-xl text-center"
                  style={{
                    background: 'rgba(124,58,237,0.06)',
                    border: '1px dashed rgba(124,58,237,0.2)',
                  }}
                >
                  <p className="text-xs text-white/40 font-inter">
                    Drag nodes from the library onto the canvas to build your workflow
                  </p>
                </div>
              </Panel>
            )}
          </ReactFlow>
        </div>
      </div>

      {/* Right: Config Panel */}
      {selectedNode && (
        <NodeConfigPanel
          node={selectedNode}
          onChange={onNodeConfigChange}
          onDelete={onDeleteNode}
        />
      )}
    </div>
  );
}

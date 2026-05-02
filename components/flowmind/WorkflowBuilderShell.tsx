'use client'

import { useMemo, useState } from 'react'
import { FLOWMIND_NODE_CATALOG } from '@/lib/flowmind/nodeCatalog'
import type { FlowMindNode, FlowMindWorkflow } from '@/lib/flowmind/types'

function createNode(type: FlowMindNode['type'], index: number): FlowMindNode {
  return {
    id: `${type}-${Date.now()}-${index}`,
    type,
    position: { x: 80 + index * 20, y: 100 + index * 20 },
    data: {
      label: `${type.replace('_', ' ')} node`,
      description: 'Configure this node from the properties panel.',
    },
  }
}

export default function WorkflowBuilderShell() {
  const [workflow, setWorkflow] = useState<FlowMindWorkflow>({
    name: 'Untitled FlowMind Workflow',
    description: 'Draft workflow for FlowMind AI',
    nodes: [],
    edges: [],
  })

  const totalNodes = workflow.nodes.length

  const summary = useMemo(() => {
    return `${workflow.nodes.length} nodes, ${workflow.edges.length} edges`
  }, [workflow])

  const addNode = (type: FlowMindNode['type']) => {
    setWorkflow((current) => ({
      ...current,
      nodes: [...current.nodes, createNode(type, current.nodes.length + 1)],
    }))
  }

  return (
    <div className="min-h-screen bg-zinc-950 text-white">
      <div className="border-b border-white/10 px-6 py-4 flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-semibold">FlowMind AI Builder</h1>
          <p className="text-sm text-zinc-400">Design AI workflows visually and prepare them for execution.</p>
        </div>
        <div className="text-sm text-zinc-400">{summary}</div>
      </div>

      <div className="grid grid-cols-12 min-h-[calc(100vh-81px)]">
        <aside className="col-span-3 border-r border-white/10 p-5 space-y-4 bg-zinc-900/40">
          <div>
            <h2 className="text-lg font-medium">Node Palette</h2>
            <p className="text-sm text-zinc-400">Add core modules for Module 2 and Module 3 workflows.</p>
          </div>

          <div className="space-y-3">
            {FLOWMIND_NODE_CATALOG.map((item) => (
              <button
                key={item.type}
                onClick={() => addNode(item.type)}
                className="w-full rounded-xl border border-white/10 bg-zinc-950 p-3 text-left hover:border-orange-500/40 hover:bg-zinc-900"
              >
                <div className="font-medium">{item.title}</div>
                <div className="mt-1 text-xs text-zinc-400">{item.description}</div>
              </button>
            ))}
          </div>
        </aside>

        <main className="col-span-6 p-6">
          <div className="rounded-2xl border border-dashed border-white/15 bg-zinc-900/30 min-h-[70vh] p-6">
            <div className="mb-4 flex items-center justify-between">
              <div>
                <h2 className="text-lg font-medium">Canvas</h2>
                <p className="text-sm text-zinc-400">This is the initial revamp shell for the drag-and-drop builder.</p>
              </div>
              <div className="text-xs text-zinc-500">Prototype Canvas</div>
            </div>

            {totalNodes === 0 ? (
              <div className="rounded-xl border border-white/10 bg-black/20 p-8 text-center text-zinc-400">
                No nodes added yet. Start by adding an Input, Prompt, or AI Model node.
              </div>
            ) : (
              <div className="grid gap-3">
                {workflow.nodes.map((node) => (
                  <div key={node.id} className="rounded-xl border border-white/10 bg-zinc-950 p-4">
                    <div className="flex items-center justify-between">
                      <div className="font-medium">{node.data.label}</div>
                      <span className="text-xs uppercase tracking-wide text-orange-400">{node.type}</span>
                    </div>
                    <div className="mt-2 text-sm text-zinc-400">{node.data.description}</div>
                  </div>
                ))}
              </div>
            )}
          </div>
        </main>

        <aside className="col-span-3 border-l border-white/10 p-5 bg-zinc-900/40">
          <h2 className="text-lg font-medium">Workflow Summary</h2>
          <div className="mt-4 space-y-3 text-sm text-zinc-300">
            <div><span className="text-zinc-500">Name:</span> {workflow.name}</div>
            <div><span className="text-zinc-500">Description:</span> {workflow.description}</div>
            <div><span className="text-zinc-500">Nodes:</span> {workflow.nodes.length}</div>
            <div><span className="text-zinc-500">Edges:</span> {workflow.edges.length}</div>
          </div>
        </aside>
      </div>
    </div>
  )
}

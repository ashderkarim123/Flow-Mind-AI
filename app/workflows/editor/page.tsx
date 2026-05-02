'use client';

import dynamic from 'next/dynamic';
import { useParams } from 'next/navigation';

// Dynamically import to avoid SSR issues with React Flow
const WorkflowCanvas = dynamic(
  () => import('@/components/workflows/builder/WorkflowCanvas').then((m) => m.WorkflowCanvas),
  { ssr: false, loading: () => (
    <div className="flex-1 flex items-center justify-center bg-gradient-auth">
      <div className="text-center space-y-3">
        <div className="w-10 h-10 border-2 border-violet-500/30 border-t-violet-500 rounded-full animate-spin mx-auto" />
        <p className="text-white/40 text-sm font-inter">Loading workflow editor...</p>
      </div>
    </div>
  ) }
);

export default function WorkflowEditorPage() {
  const params = useParams();
  const workflowId = params?.id as string | undefined;

  const handleSave = async (nodes: unknown[], edges: unknown[]) => {
    const backendUrl = process.env.NEXT_PUBLIC_BACKEND_API_URL || 'http://localhost:8000';
    // TODO: save to backend
    console.log('Saving workflow...', { nodes, edges, workflowId });
  };

  return (
    <div className="h-screen w-full flex flex-col overflow-hidden bg-fm-deep">
      <WorkflowCanvas
        workflowName={workflowId ? 'My Workflow' : 'New Workflow'}
        onSave={handleSave}
      />
    </div>
  );
}

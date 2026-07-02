'use client';

import { Suspense } from 'react';
import { useAuth } from '@/lib/AuthContext';
import WorkflowEditor from '@/components/workflows/WorkflowEditor';
import { Button } from '@/components/ui/button';

export default function NewWorkflowPage() {
  const { user, loading } = useAuth();

  if (loading) return null;

  if (!user) {
    return (
      <div className="min-h-screen bg-black flex items-center justify-center p-6">
        <div className="w-full max-w-md bg-zinc-950 border border-zinc-800 rounded-2xl p-6 text-white shadow-2xl">
          <h1 className="text-2xl font-bold mb-2">Sign in required</h1>
          <p className="text-white/70 mb-6">You need to sign in to create and save workflows.</p>
          <div className="flex gap-3">
            <Button
              className="bg-[#1D4ED8] hover:bg-[#1E40AF] text-white flex-1"
              onClick={() => { window.location.href = '/sign-in'; }}
            >
              Sign in to continue
            </Button>
            <Button
              variant="ghost"
              className="text-white/80 flex-1"
              onClick={() => { window.location.href = '/'; }}
            >
              Cancel
            </Button>
          </div>
        </div>
      </div>
    );
  }

  return (
    <Suspense fallback={
      <div className="min-h-screen bg-black flex items-center justify-center p-6">
        <div className="text-center space-y-3">
          <div className="w-10 h-10 border-2 border-violet-500/30 border-t-violet-500 rounded-full animate-spin mx-auto" />
          <p className="text-white/40 text-sm font-inter">Loading workflow editor...</p>
        </div>
      </div>
    }>
      <WorkflowEditor />
    </Suspense>
  );
}

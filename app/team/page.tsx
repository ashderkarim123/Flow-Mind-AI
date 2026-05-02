'use client';

import { useRequireAuth } from '@/lib/AuthContext';
import DashboardLayout from '@/components/dashboard/DashboardLayout';
import TeamView from '@/components/team/TeamView';

export default function TeamPageWrapper() {
  const { user, loading } = useRequireAuth();
  
  if (loading) {
    return (
      <DashboardLayout>
        <div className="p-6 lg:p-8 flex items-center justify-center min-h-screen">
          <div className="text-white">Loading Team Data...</div>
        </div>
      </DashboardLayout>
    );
  }

  return (
    <DashboardLayout>
      <div className="p-6 lg:p-8 space-y-8 max-w-7xl mx-auto">
        <TeamView />
      </div>
    </DashboardLayout>
  );
}

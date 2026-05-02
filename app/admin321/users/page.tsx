'use client';

import { useState, useCallback, useEffect } from 'react';
import { motion } from 'framer-motion';
import { 
  Users, UserCheck, UserX, Shield, Brain,
  Activity, TrendingUp, ArrowLeft, UserPlus
} from 'lucide-react';
import { StatsCard } from '@/components/admin/StatsCard';
import { UserTable } from '@/components/admin/UserTable';
import { AddMemberModal } from '@/components/admin/AddMemberModal';
import Link from 'next/link';

interface UserRow {
  uid: string; email: string; display_name?: string;
  role: string; disabled: boolean; email_verified: boolean;
  created_at?: string; workflow_count?: number;
}

interface Stats {
  total_users: number; active_users: number; admin_users: number;
  disabled_users: number; new_users_today: number; new_users_this_week: number;
}

export default function AdminUsersPage() {
  const [users, setUsers] = useState<UserRow[]>([]);
  const [stats, setStats] = useState<Stats | null>(null);
  const [loading, setLoading] = useState(true);
  const [page, setPage] = useState(1);
  const [total, setTotal] = useState(0);
  const [search, setSearch] = useState('');
  const [isAddModalOpen, setIsAddModalOpen] = useState(false);
  const PAGE_SIZE = 20;

  const backendUrl = process.env.NEXT_PUBLIC_BACKEND_API_URL || 'http://localhost:8000';

  const fetchStats = useCallback(async () => {
    try {
      const token = localStorage.getItem('backend_session_token') || '';
      const res = await fetch(`${backendUrl}/api/v1/users/stats`, {
        headers: { Authorization: `Bearer ${token}` },
      });
      if (res.ok) setStats(await res.json());
    } catch (e) { console.error('Stats fetch error', e); }
  }, [backendUrl]);

  const fetchUsers = useCallback(async (p = 1, q = '') => {
    setLoading(true);
    try {
      const token = localStorage.getItem('backend_session_token') || '';
      const params = new URLSearchParams({ page: String(p), page_size: String(PAGE_SIZE) });
      if (q) params.set('search', q);
      const res = await fetch(`${backendUrl}/api/v1/users?${params}`, {
        headers: { Authorization: `Bearer ${token}` },
      });
      if (res.ok) {
        const data = await res.json();
        setUsers(data.users || []);
        setTotal(data.total || 0);
      }
    } catch (e) { console.error('Users fetch error', e); } 
    finally { setLoading(false); }
  }, [backendUrl]);

  useEffect(() => {
    fetchStats();
    fetchUsers(1, '');
  }, [fetchStats, fetchUsers]);

  const handleSearch = useCallback((q: string) => {
    setSearch(q);
    setPage(1);
    fetchUsers(1, q);
  }, [fetchUsers]);

  const handlePageChange = useCallback((p: number) => {
    setPage(p);
    fetchUsers(p, search);
  }, [fetchUsers, search]);

  const handleRoleChange = async (uid: string, role: string) => {
    const token = localStorage.getItem('backend_session_token') || '';
    const res = await fetch(`${backendUrl}/api/v1/users/${uid}/role`, {
      method: 'PATCH',
      headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${token}` },
      body: JSON.stringify({ role }),
    });
    if (!res.ok) throw new Error('Failed to update role');
    setUsers((prev) => prev.map((u) => u.uid === uid ? { ...u, role } : u));
    fetchStats();
  };

  const handleStatusToggle = async (uid: string, disabled: boolean) => {
    const token = localStorage.getItem('backend_session_token') || '';
    const res = await fetch(`${backendUrl}/api/v1/users/${uid}/status`, {
      method: 'PATCH',
      headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${token}` },
      body: JSON.stringify({ disabled }),
    });
    if (!res.ok) throw new Error('Failed to update status');
    setUsers((prev) => prev.map((u) => u.uid === uid ? { ...u, disabled } : u));
    fetchStats();
  };

  return (
    <div className="min-h-screen text-white p-6 font-inter" style={{ background: 'var(--fm-bg-deep)' }}>
      <div className="max-w-7xl mx-auto">
        <div className="flex items-center gap-4 mb-8">
          <Link href="/admin321"
            className="w-9 h-9 rounded-xl bg-white/4 border border-white/8 flex items-center justify-center text-white/40 hover:text-white hover:bg-white/8 transition-all">
            <ArrowLeft size={16} />
          </Link>
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-violet-600 to-cyan-500 flex items-center justify-center"
              style={{ boxShadow: '0 0 20px rgba(124,58,237,0.4)' }}>
              <Brain className="w-5 h-5 text-white" />
            </div>
            <div>
              <h1 className="text-xl font-bold text-white font-outfit">User Management</h1>
              <p className="text-xs text-white/40">Manage roles, status, and permissions</p>
            </div>
          </div>
        </div>

        {stats && (
          <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-4 mb-8">
            <StatsCard title="Total Users" value={stats.total_users} icon={Users} color="violet" delay={0} />
            <StatsCard title="Active" value={stats.active_users} icon={UserCheck} color="emerald" delay={0.05} />
            <StatsCard title="Disabled" value={stats.disabled_users} icon={UserX} color="red" delay={0.1} />
            <StatsCard title="Admins" value={stats.admin_users} icon={Shield} color="violet" delay={0.15} />
            <StatsCard title="New Today" value={stats.new_users_today} icon={TrendingUp} color="cyan" delay={0.2} />
            <StatsCard title="This Week" value={stats.new_users_this_week} icon={Activity} color="amber" delay={0.25} />
          </div>
        )}

        <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.3 }}>
          <div className="flex items-center justify-between mb-4">
            <div className="flex items-center gap-3">
              <h2 className="text-base font-semibold text-white font-outfit">All Users</h2>
              <span className="text-xs text-white/35 font-inter bg-white/5 px-2 py-1 rounded-full">{total} total</span>
            </div>
            <button
              onClick={() => setIsAddModalOpen(true)}
              className="px-4 py-2 bg-[#1D4ED8] hover:bg-[#1E40AF] text-white text-sm font-medium rounded-xl flex items-center gap-2 transition-colors"
            >
              <UserPlus className="w-4 h-4" />
              Add Member
            </button>
          </div>
          <UserTable
            users={users}
            loading={loading}
            onRoleChange={handleRoleChange}
            onStatusToggle={handleStatusToggle}
            page={page}
            pageSize={PAGE_SIZE}
            total={total}
            onPageChange={handlePageChange}
            onSearch={handleSearch}
            onRefresh={() => fetchUsers(page, search)}
          />
        </motion.div>
      </div>

      <AddMemberModal
        isOpen={isAddModalOpen}
        onClose={() => setIsAddModalOpen(false)}
        onSuccess={() => {
          fetchStats();
          fetchUsers(1, search);
        }}
      />
    </div>
  );
}

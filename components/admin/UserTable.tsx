'use client';

import { useState, useCallback, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import {
  Search, Shield, User, Briefcase, MoreVertical,
  Power, PowerOff, ChevronLeft, ChevronRight, RefreshCw,
  Mail, Calendar, Activity
} from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { RoleAssignModal } from '@/components/admin/RoleAssignModal';

interface UserRow {
  uid: string;
  email: string;
  display_name?: string;
  role: string;
  disabled: boolean;
  email_verified: boolean;
  created_at?: string;
  workflow_count?: number;
}

const ROLE_BADGE: Record<string, { label: string; color: string; bg: string; icon: React.ReactNode }> = {
  admin: {
    label: 'Admin',
    color: 'text-violet-300',
    bg: 'rgba(124,58,237,0.15)',
    icon: <Shield size={10} />,
  },
  manager: {
    label: 'Manager',
    color: 'text-cyan-300',
    bg: 'rgba(6,182,212,0.12)',
    icon: <Briefcase size={10} />,
  },
  user: {
    label: 'User',
    color: 'text-white/60',
    bg: 'rgba(255,255,255,0.06)',
    icon: <User size={10} />,
  },
};

function RoleBadge({ role }: { role: string }) {
  const conf = ROLE_BADGE[role] || ROLE_BADGE.user;
  return (
    <span
      className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[10px] font-semibold font-inter"
      style={{ color: conf.color, background: conf.bg }}
    >
      {conf.icon} {conf.label}
    </span>
  );
}

function StatusDot({ disabled }: { disabled: boolean }) {
  return (
    <span className="inline-flex items-center gap-1.5 text-xs font-inter">
      <span
        className="w-1.5 h-1.5 rounded-full"
        style={{ background: disabled ? '#6B7280' : '#10B981' }}
      />
      <span style={{ color: disabled ? '#6B7280' : '#6EE7B7' }}>
        {disabled ? 'Disabled' : 'Active'}
      </span>
    </span>
  );
}

interface UserTableProps {
  users: UserRow[];
  loading?: boolean;
  onRoleChange: (uid: string, role: string) => Promise<void>;
  onStatusToggle: (uid: string, disabled: boolean) => Promise<void>;
  page: number;
  pageSize: number;
  total: number;
  onPageChange: (page: number) => void;
  onSearch: (q: string) => void;
  onRefresh: () => void;
}

export function UserTable({
  users,
  loading = false,
  onRoleChange,
  onStatusToggle,
  page,
  pageSize,
  total,
  onPageChange,
  onSearch,
  onRefresh,
}: UserTableProps) {
  const [search, setSearch] = useState('');
  const [modalUser, setModalUser] = useState<UserRow | null>(null);
  const [openMenu, setOpenMenu] = useState<string | null>(null);

  const totalPages = Math.ceil(total / pageSize);

  const handleSearch = useCallback(
    (e: React.ChangeEvent<HTMLInputElement>) => {
      setSearch(e.target.value);
      onSearch(e.target.value);
    },
    [onSearch],
  );

  return (
    <div>
      {/* Table header controls */}
      <div className="flex items-center gap-3 mb-4">
        <div className="relative flex-1">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-white/30" />
          <Input
            placeholder="Search by email or name..."
            value={search}
            onChange={handleSearch}
            className="pl-10 h-10 bg-white/4 border border-white/8 rounded-xl text-white text-sm placeholder:text-white/25 focus:border-violet-500 focus:ring-1 focus:ring-violet-500/30 font-inter"
          />
        </div>
        <button
          onClick={onRefresh}
          className="w-10 h-10 rounded-xl border border-white/8 bg-white/4 flex items-center justify-center text-white/40 hover:text-white hover:bg-white/8 transition-all"
        >
          <RefreshCw size={15} className={loading ? 'animate-spin' : ''} />
        </button>
      </div>

      {/* Table */}
      <div
        className="rounded-2xl overflow-hidden"
        style={{ border: '1px solid rgba(124,58,237,0.12)', background: 'rgba(17,17,42,0.6)', backdropFilter: 'blur(20px)' }}
      >
        {/* Header */}
        <div
          className="grid grid-cols-[2fr_1fr_1fr_1fr_80px] gap-4 px-5 py-3 text-xs font-semibold font-inter text-white/40 uppercase tracking-wider"
          style={{ borderBottom: '1px solid rgba(255,255,255,0.05)' }}
        >
          <span>User</span>
          <span>Role</span>
          <span>Status</span>
          <span>Workflows</span>
          <span />
        </div>

        {/* Rows */}
        {loading ? (
          <div className="py-16 text-center text-white/30 text-sm font-inter">
            <div className="w-6 h-6 border-2 border-violet-500/30 border-t-violet-500 rounded-full animate-spin mx-auto mb-3" />
            Loading users...
          </div>
        ) : users.length === 0 ? (
          <div className="py-16 text-center text-white/30 text-sm font-inter">No users found.</div>
        ) : (
          <AnimatePresence>
            {users.map((user, i) => (
              <motion.div
                key={user.uid}
                initial={{ opacity: 0, y: 8 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: i * 0.04 }}
                className="grid grid-cols-[2fr_1fr_1fr_1fr_80px] gap-4 px-5 py-4 hover:bg-white/[0.02] transition-colors relative"
                style={{ borderBottom: i < users.length - 1 ? '1px solid rgba(255,255,255,0.04)' : 'none' }}
              >
                {/* User info */}
                <div className="flex items-center gap-3 min-w-0">
                  <div
                    className="w-8 h-8 rounded-full flex items-center justify-center text-xs font-bold font-outfit shrink-0"
                    style={{ background: 'rgba(124,58,237,0.2)', color: '#9D6EFF' }}
                  >
                    {(user.display_name || user.email).charAt(0).toUpperCase()}
                  </div>
                  <div className="min-w-0">
                    <p className="text-sm font-medium text-white font-outfit truncate">
                      {user.display_name || '—'}
                    </p>
                    <p className="text-xs text-white/40 font-inter truncate">{user.email}</p>
                  </div>
                </div>

                {/* Role */}
                <div className="flex items-center">
                  <RoleBadge role={user.role} />
                </div>

                {/* Status */}
                <div className="flex items-center">
                  <StatusDot disabled={user.disabled} />
                </div>

                {/* Workflow count */}
                <div className="flex items-center">
                  <span className="text-sm text-white/50 font-inter">{user.workflow_count ?? 0}</span>
                </div>

                {/* Actions */}
                <div className="flex items-center justify-end">
                  <div className="relative">
                    <button
                      onClick={() => setOpenMenu(openMenu === user.uid ? null : user.uid)}
                      className="w-7 h-7 rounded-lg flex items-center justify-center text-white/30 hover:text-white/70 hover:bg-white/5 transition-all"
                    >
                      <MoreVertical size={14} />
                    </button>

                    <AnimatePresence>
                      {openMenu === user.uid && (
                        <motion.div
                          initial={{ opacity: 0, scale: 0.9, y: -4 }}
                          animate={{ opacity: 1, scale: 1, y: 0 }}
                          exit={{ opacity: 0, scale: 0.9 }}
                          className="absolute right-0 top-8 w-44 rounded-xl z-20 overflow-hidden"
                          style={{
                            background: 'rgba(17,17,42,0.97)',
                            border: '1px solid rgba(124,58,237,0.2)',
                            boxShadow: '0 16px 40px rgba(0,0,0,0.5)',
                          }}
                        >
                          <button
                            className="w-full flex items-center gap-2 px-3 py-2.5 text-xs text-white/70 hover:text-white hover:bg-white/5 transition-all font-inter"
                            onClick={() => { setModalUser(user); setOpenMenu(null); }}
                          >
                            <Shield size={12} className="text-violet-400" /> Change Role
                          </button>
                          <div className="h-px bg-white/5" />
                          <button
                            className={`w-full flex items-center gap-2 px-3 py-2.5 text-xs transition-all font-inter ${
                              user.disabled
                                ? 'text-emerald-400 hover:bg-emerald-500/5'
                                : 'text-red-400 hover:bg-red-500/5'
                            }`}
                            onClick={() => { onStatusToggle(user.uid, !user.disabled); setOpenMenu(null); }}
                          >
                            {user.disabled ? <Power size={12} /> : <PowerOff size={12} />}
                            {user.disabled ? 'Enable Account' : 'Disable Account'}
                          </button>
                        </motion.div>
                      )}
                    </AnimatePresence>
                  </div>
                </div>
              </motion.div>
            ))}
          </AnimatePresence>
        )}
      </div>

      {/* Pagination */}
      {total > pageSize && (
        <div className="flex items-center justify-between mt-4">
          <p className="text-xs text-white/35 font-inter">
            Showing {Math.min((page - 1) * pageSize + 1, total)}–{Math.min(page * pageSize, total)} of {total} users
          </p>
          <div className="flex items-center gap-2">
            <button
              onClick={() => onPageChange(page - 1)}
              disabled={page <= 1}
              className="w-8 h-8 rounded-lg flex items-center justify-center text-white/40 hover:text-white disabled:opacity-30 hover:bg-white/5 transition-all"
            >
              <ChevronLeft size={14} />
            </button>
            <span className="text-xs text-white/50 font-inter px-2">
              {page} / {totalPages}
            </span>
            <button
              onClick={() => onPageChange(page + 1)}
              disabled={page >= totalPages}
              className="w-8 h-8 rounded-lg flex items-center justify-center text-white/40 hover:text-white disabled:opacity-30 hover:bg-white/5 transition-all"
            >
              <ChevronRight size={14} />
            </button>
          </div>
        </div>
      )}

      {/* Role assign modal */}
      <RoleAssignModal
        open={!!modalUser}
        user={modalUser}
        onConfirm={async (uid, role) => { await onRoleChange(uid, role); }}
        onClose={() => setModalUser(null)}
      />

      {/* Close menu on outside click */}
      {openMenu && (
        <div className="fixed inset-0 z-10" onClick={() => setOpenMenu(null)} />
      )}
    </div>
  );
}

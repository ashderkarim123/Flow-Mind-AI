'use client';

import { useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { Button } from '@/components/ui/button';
import { Shield, User, Briefcase, AlertCircle, CheckCircle2, X } from 'lucide-react';

interface RoleOption {
  value: string;
  label: string;
  description: string;
  icon: React.ReactNode;
  color: string;
  bg: string;
  border: string;
}

const ROLES: RoleOption[] = [
  {
    value: 'user',
    label: 'User',
    description: 'Can create and run their own workflows',
    icon: <User className="w-4 h-4" />,
    color: 'text-white/70',
    bg: 'rgba(255,255,255,0.04)',
    border: 'rgba(255,255,255,0.1)',
  },
  {
    value: 'manager',
    label: 'Manager',
    description: 'Can view and manage team workflows',
    icon: <Briefcase className="w-4 h-4" />,
    color: 'text-cyan-400',
    bg: 'rgba(6,182,212,0.06)',
    border: 'rgba(6,182,212,0.2)',
  },
  {
    value: 'admin',
    label: 'Administrator',
    description: 'Full system access including user management',
    icon: <Shield className="w-4 h-4" />,
    color: 'text-violet-400',
    bg: 'rgba(124,58,237,0.08)',
    border: 'rgba(124,58,237,0.25)',
  },
];

interface RoleAssignModalProps {
  open: boolean;
  user: { uid: string; email: string; display_name?: string; role: string } | null;
  onConfirm: (uid: string, role: string) => Promise<void>;
  onClose: () => void;
}

export function RoleAssignModal({ open, user, onConfirm, onClose }: RoleAssignModalProps) {
  const [selectedRole, setSelectedRole] = useState(user?.role || 'user');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  if (!open || !user) return null;

  const handleConfirm = async () => {
    if (selectedRole === user.role) { onClose(); return; }
    setLoading(true);
    setError('');
    try {
      await onConfirm(user.uid, selectedRole);
      onClose();
    } catch (err: any) {
      setError(err?.message || 'Failed to update role');
    } finally {
      setLoading(false);
    }
  };

  return (
    <AnimatePresence>
      {open && (
        <>
          {/* Backdrop */}
          <motion.div
            initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}
            className="fixed inset-0 bg-black/60 backdrop-blur-sm z-50"
            onClick={onClose}
          />

          {/* Modal */}
          <motion.div
            initial={{ opacity: 0, scale: 0.9, y: 20 }}
            animate={{ opacity: 1, scale: 1, y: 0 }}
            exit={{ opacity: 0, scale: 0.9, y: 20 }}
            transition={{ duration: 0.25, type: 'spring', stiffness: 300, damping: 30 }}
            className="fixed left-1/2 top-1/2 -translate-x-1/2 -translate-y-1/2 z-50 w-full max-w-sm px-4"
          >
            <div
              className="relative rounded-2xl overflow-hidden"
              style={{
                background: 'rgba(17,17,42,0.95)',
                border: '1px solid rgba(124,58,237,0.2)',
                backdropFilter: 'blur(24px)',
                boxShadow: '0 24px 64px rgba(0,0,0,0.6), 0 0 40px rgba(124,58,237,0.1)',
              }}
            >
              {/* Top accent */}
              <div className="h-0.5 bg-gradient-to-r from-violet-600 via-violet-400 to-cyan-500" />

              <div className="p-6">
                {/* Header */}
                <div className="flex items-start justify-between mb-5">
                  <div>
                    <h3 className="text-base font-semibold text-white font-outfit">Assign Role</h3>
                    <p className="text-xs text-white/45 font-inter mt-0.5">
                      {user.display_name || user.email}
                    </p>
                  </div>
                  <button onClick={onClose}
                    className="w-7 h-7 rounded-lg flex items-center justify-center text-white/30 hover:text-white/70 hover:bg-white/5 transition-all">
                    <X size={14} />
                  </button>
                </div>

                {/* Error */}
                <AnimatePresence>
                  {error && (
                    <motion.div initial={{ opacity: 0, y: -8 }} animate={{ opacity: 1, y: 0 }}
                      className="flex items-center gap-2 text-red-400 bg-red-500/10 border border-red-500/20 p-2.5 rounded-xl mb-4">
                      <AlertCircle size={13} className="shrink-0" />
                      <span className="text-xs font-inter">{error}</span>
                    </motion.div>
                  )}
                </AnimatePresence>

                {/* Role options */}
                <div className="space-y-2 mb-5">
                  {ROLES.map((role) => (
                    <button
                      key={role.value}
                      onClick={() => setSelectedRole(role.value)}
                      className="w-full flex items-start gap-3 p-3 rounded-xl text-left transition-all"
                      style={{
                        background: selectedRole === role.value ? role.bg : 'rgba(255,255,255,0.02)',
                        border: `1px solid ${selectedRole === role.value ? role.border : 'rgba(255,255,255,0.06)'}`,
                      }}
                    >
                      <div className={`mt-0.5 ${role.color}`}>{role.icon}</div>
                      <div className="flex-1 min-w-0">
                        <div className="flex items-center justify-between">
                          <span className={`text-sm font-medium font-outfit ${role.color}`}>{role.label}</span>
                          {selectedRole === role.value && (
                            <CheckCircle2 size={13} className="text-violet-400 shrink-0" />
                          )}
                        </div>
                        <p className="text-xs text-white/40 font-inter mt-0.5">{role.description}</p>
                      </div>
                    </button>
                  ))}
                </div>

                {/* Actions */}
                <div className="flex gap-2">
                  <Button
                    variant="outline"
                    onClick={onClose}
                    className="flex-1 h-9 rounded-xl border-white/10 bg-white/4 text-white/60 hover:text-white text-sm font-inter"
                  >
                    Cancel
                  </Button>
                  <Button
                    onClick={handleConfirm}
                    disabled={loading || selectedRole === user.role}
                    className="flex-1 h-9 rounded-xl text-sm font-semibold font-outfit text-white"
                    style={{
                      background: 'linear-gradient(135deg, #7C3AED, #5B21B6)',
                      boxShadow: '0 4px 16px rgba(124,58,237,0.3)',
                    }}
                  >
                    {loading ? (
                      <div className="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin" />
                    ) : 'Apply Role'}
                  </Button>
                </div>
              </div>
            </div>
          </motion.div>
        </>
      )}
    </AnimatePresence>
  );
}

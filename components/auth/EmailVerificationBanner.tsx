'use client';

import { useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { MailCheck, X, RefreshCw } from 'lucide-react';
import { useAuth } from '@/lib/AuthContext';

interface EmailVerificationBannerProps {
  email: string;
  onDismiss?: () => void;
}

export function EmailVerificationBanner({ email, onDismiss }: EmailVerificationBannerProps) {
  const { user } = useAuth();
  const [resending, setResending] = useState(false);
  const [resent, setResent] = useState(false);
  const [dismissed, setDismissed] = useState(false);

  const handleResend = async () => {
    if (!user || resending) return;
    setResending(true);
    try {
      // Firebase sendEmailVerification
      const { sendEmailVerification } = await import('firebase/auth');
      await sendEmailVerification(user as any);
      setResent(true);
      setTimeout(() => setResent(false), 5000);
    } catch (err) {
      console.error('Failed to resend verification email:', err);
    } finally {
      setResending(false);
    }
  };

  const handleDismiss = () => {
    setDismissed(true);
    onDismiss?.();
  };

  return (
    <AnimatePresence>
      {!dismissed && (
        <motion.div
          initial={{ opacity: 0, y: -16 }}
          animate={{ opacity: 1, y: 0 }}
          exit={{ opacity: 0, y: -16 }}
          transition={{ duration: 0.3 }}
          className="relative flex items-start gap-3 p-4 rounded-xl border font-inter"
          style={{
            background: 'rgba(124, 58, 237, 0.08)',
            borderColor: 'rgba(124, 58, 237, 0.25)',
          }}
        >
          {/* Icon */}
          <div className="shrink-0 w-8 h-8 rounded-lg bg-violet-500/15 flex items-center justify-center mt-0.5">
            <MailCheck className="w-4 h-4 text-violet-400" />
          </div>

          {/* Content */}
          <div className="flex-1 min-w-0">
            <p className="text-sm font-semibold text-white mb-0.5">Verify your email address</p>
            <p className="text-xs text-white/55 leading-relaxed">
              We sent a verification link to{' '}
              <span className="text-violet-300 font-medium truncate">{email}</span>.
              Check your inbox to unlock all features.
            </p>

            {resent && (
              <motion.p
                initial={{ opacity: 0 }} animate={{ opacity: 1 }}
                className="text-xs text-emerald-400 mt-1.5"
              >
                ✓ Verification email resent successfully
              </motion.p>
            )}

            <button
              onClick={handleResend}
              disabled={resending || resent}
              className="mt-2 flex items-center gap-1.5 text-xs text-violet-400 hover:text-violet-300 font-medium transition-colors disabled:opacity-50"
            >
              <RefreshCw size={11} className={resending ? 'animate-spin' : ''} />
              {resending ? 'Sending...' : resent ? 'Email sent!' : 'Resend verification email'}
            </button>
          </div>

          {/* Dismiss */}
          <button
            onClick={handleDismiss}
            className="shrink-0 w-6 h-6 rounded flex items-center justify-center text-white/30 hover:text-white/70 hover:bg-white/5 transition-all"
          >
            <X size={13} />
          </button>
        </motion.div>
      )}
    </AnimatePresence>
  );
}

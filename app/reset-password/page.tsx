'use client';

import { useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { useAuth } from '@/lib/AuthContext';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Mail, ArrowLeft, CheckCircle2, AlertCircle, Brain, KeyRound } from 'lucide-react';
import Link from 'next/link';

function FloatingNode({ x, y, delay, size = 5 }: { x: number; y: number; delay: number; size?: number }) {
  return (
    <motion.div
      className="absolute rounded-full pointer-events-none"
      style={{
        left: `${x}%`, top: `${y}%`, width: size, height: size,
        background: 'radial-gradient(circle, #9D6EFF, #7C3AED)',
        boxShadow: `0 0 ${size * 2}px rgba(124,58,237,0.5)`,
      }}
      animate={{ opacity: [0.2, 0.8, 0.2], scale: [1, 1.4, 1], y: [0, -14, 0] }}
      transition={{ duration: 4 + delay, repeat: Infinity, delay, ease: 'easeInOut' }}
    />
  );
}

const NODES = [
  { x: 8, y: 20, delay: 0, size: 5 }, { x: 90, y: 15, delay: 1, size: 4 },
  { x: 5, y: 70, delay: 1.5, size: 4 }, { x: 92, y: 75, delay: 0.5, size: 5 },
  { x: 50, y: 5, delay: 0.8, size: 4 }, { x: 50, y: 95, delay: 2, size: 4 },
];

type Step = 'enter-email' | 'email-sent';

export default function ResetPasswordPage() {
  const { resetPassword } = useAuth();
  const [step, setStep] = useState<Step>('enter-email');
  const [email, setEmail] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');
    setLoading(true);
    try {
      await resetPassword(email);
      setStep('email-sent');
    } catch (err: any) {
      const code = err?.code || '';
      if (code.includes('user-not-found')) {
        // Don't reveal whether email exists — go to success state anyway (security)
        setStep('email-sent');
      } else {
        setError(err?.message || 'Failed to send reset email. Please try again.');
      }
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen relative overflow-hidden flex items-center justify-center bg-gradient-auth">
      {/* Background */}
      <div className="absolute inset-0 overflow-hidden pointer-events-none">
        {NODES.map((n, i) => <FloatingNode key={i} {...n} />)}
        <div className="absolute top-1/4 left-1/4 w-80 h-80 rounded-full blur-3xl opacity-60"
          style={{ background: 'radial-gradient(circle, rgba(124,58,237,0.1) 0%, transparent 70%)' }} />
        <div className="absolute bottom-1/4 right-1/4 w-64 h-64 rounded-full blur-3xl opacity-60"
          style={{ background: 'radial-gradient(circle, rgba(6,182,212,0.08) 0%, transparent 70%)' }} />
        <div className="absolute inset-0 opacity-[0.025]"
          style={{
            backgroundImage: 'linear-gradient(rgba(124,58,237,1) 1px, transparent 1px), linear-gradient(90deg, rgba(124,58,237,1) 1px, transparent 1px)',
            backgroundSize: '60px 60px',
          }} />
      </div>

      <div className="relative z-10 w-full max-w-sm px-4">
        {/* Logo */}
        <motion.div
          initial={{ opacity: 0, y: -20 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.6 }}
          className="text-center mb-8"
        >
          <div className="inline-flex items-center gap-3 mb-2">
            <div className="relative w-10 h-10">
              <div className="absolute inset-0 rounded-lg bg-gradient-to-br from-violet-600 to-cyan-500 opacity-20 blur-md" />
              <div className="relative w-10 h-10 rounded-lg bg-gradient-to-br from-violet-600 to-cyan-500 flex items-center justify-center"
                style={{ boxShadow: '0 0 20px rgba(124,58,237,0.5)' }}>
                <Brain className="w-5 h-5 text-white" />
              </div>
            </div>
            <div className="text-left">
              <h1 className="text-xl font-bold text-white font-outfit tracking-tight">FlowMind AI</h1>
              <p className="text-xs text-violet-400 font-medium">Intelligent Workflow Automation</p>
            </div>
          </div>
        </motion.div>

        <motion.div
          initial={{ opacity: 0, y: 24, scale: 0.96 }}
          animate={{ opacity: 1, y: 0, scale: 1 }}
          transition={{ duration: 0.7, delay: 0.2 }}
          className="relative"
        >
          <div className="absolute -inset-1 rounded-2xl opacity-25 blur-lg"
            style={{ background: 'linear-gradient(135deg, #7C3AED, #06B6D4)' }} />

          <div className="relative glass-card rounded-2xl overflow-hidden">
            <div className="h-0.5 w-full bg-gradient-to-r from-violet-600 via-violet-400 to-cyan-500" />

            <div className="p-7">
              <AnimatePresence mode="wait">
                {step === 'enter-email' ? (
                  <motion.div key="enter"
                    initial={{ opacity: 0, x: -20 }} animate={{ opacity: 1, x: 0 }} exit={{ opacity: 0, x: 20 }}
                  >
                    {/* Header */}
                    <div className="flex items-center gap-3 mb-5">
                      <div className="w-10 h-10 rounded-xl bg-violet-500/10 border border-violet-500/20 flex items-center justify-center shrink-0">
                        <KeyRound className="w-5 h-5 text-violet-400" />
                      </div>
                      <div>
                        <h2 className="text-lg font-semibold text-white font-outfit">Forgot password?</h2>
                        <p className="text-xs text-white/45 font-inter">We'll send a reset link to your email</p>
                      </div>
                    </div>

                    {/* Error */}
                    <AnimatePresence>
                      {error && (
                        <motion.div
                          initial={{ opacity: 0, y: -8 }} animate={{ opacity: 1, y: 0 }}
                          className="flex items-center gap-2 text-red-400 bg-red-500/10 border border-red-500/20 p-3 rounded-xl mb-4"
                        >
                          <AlertCircle size={14} className="shrink-0" />
                          <span className="text-xs font-inter">{error}</span>
                        </motion.div>
                      )}
                    </AnimatePresence>

                    <form onSubmit={handleSubmit} className="space-y-4">
                      <div className="space-y-1.5">
                        <Label htmlFor="reset-email" className="text-white/80 text-xs font-medium font-inter">
                          Email Address
                        </Label>
                        <div className="relative group">
                          <Mail className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-white/30 group-focus-within:text-violet-400 transition-colors" />
                          <Input
                            id="reset-email"
                            type="email"
                            placeholder="you@example.com"
                            value={email}
                            onChange={(e) => setEmail(e.target.value)}
                            className="pl-10 h-11 bg-white/5 border border-white/10 rounded-xl text-white placeholder:text-white/25 focus:border-violet-500 focus:ring-1 focus:ring-violet-500/40 transition-all text-sm font-inter"
                            required
                          />
                        </div>
                      </div>

                      <Button
                        type="submit"
                        id="reset-submit"
                        disabled={loading}
                        className="w-full h-11 rounded-xl text-sm font-semibold font-outfit text-white transition-all relative overflow-hidden group"
                        style={{
                          background: 'linear-gradient(135deg, #7C3AED 0%, #5B21B6 100%)',
                          boxShadow: '0 4px 24px rgba(124,58,237,0.35)',
                        }}
                      >
                        <span className="absolute inset-0 bg-gradient-to-r from-violet-500 to-violet-700 opacity-0 group-hover:opacity-100 transition-opacity" />
                        <span className="relative flex items-center justify-center gap-2">
                          {loading ? (
                            <><div className="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin" />Sending...</>
                          ) : 'Send Reset Link'}
                        </span>
                      </Button>
                    </form>
                  </motion.div>
                ) : (
                  <motion.div key="sent"
                    initial={{ opacity: 0, x: 20 }} animate={{ opacity: 1, x: 0 }}
                    className="text-center py-3"
                  >
                    <motion.div
                      initial={{ scale: 0 }} animate={{ scale: 1 }}
                      transition={{ type: 'spring', stiffness: 200, delay: 0.2 }}
                      className="w-16 h-16 rounded-full bg-emerald-500/10 border border-emerald-500/30 flex items-center justify-center mx-auto mb-4"
                    >
                      <CheckCircle2 className="w-8 h-8 text-emerald-400" />
                    </motion.div>
                    <h2 className="text-lg font-semibold text-white font-outfit mb-2">Check your inbox</h2>
                    <p className="text-sm text-white/55 font-inter leading-relaxed mb-1">
                      If an account exists for
                    </p>
                    <p className="text-sm text-violet-400 font-medium font-inter mb-4">{email}</p>
                    <p className="text-xs text-white/40 font-inter">
                      You'll receive a password reset link shortly. Check your spam folder if you don't see it.
                    </p>
                    <Button
                      onClick={() => setStep('enter-email')}
                      variant="outline"
                      className="mt-5 w-full h-10 rounded-xl border-white/10 bg-white/5 text-white/70 hover:text-white hover:bg-white/10 text-sm font-inter"
                    >
                      Try a different email
                    </Button>
                  </motion.div>
                )}
              </AnimatePresence>

              {/* Back to sign in */}
              <div className="mt-5 text-center">
                <Link
                  href="/sign-in"
                  className="inline-flex items-center gap-1.5 text-xs text-white/40 hover:text-violet-400 font-inter transition-colors"
                >
                  <ArrowLeft size={12} />
                  Back to Sign In
                </Link>
              </div>
            </div>
          </div>
        </motion.div>
      </div>
    </div>
  );
}
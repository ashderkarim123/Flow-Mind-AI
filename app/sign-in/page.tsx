'use client';

import { useState, useEffect } from 'react';
import { useRouter } from 'next/navigation';
import { motion, AnimatePresence } from 'framer-motion';
import { useAuth } from '@/lib/AuthContext';
import { useBackendAuth } from '@/lib/contexts/BackendAuthContext';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import {
  AlertCircle, Mail, Lock, Eye, EyeOff, ArrowRight,
  Shield, AlertTriangle, Zap, Brain, Workflow, Bot
} from 'lucide-react';
import Link from 'next/link';
import { MFAVerify } from '@/components/mfa/MFAVerify';

/* ─── Floating particle node for background ─── */
function FloatingNode({ x, y, delay, size = 6 }: { x: number; y: number; delay: number; size?: number }) {
  return (
    <motion.div
      className="absolute rounded-full"
      style={{
        left: `${x}%`,
        top: `${y}%`,
        width: size,
        height: size,
        background: `radial-gradient(circle, #9D6EFF, #7C3AED)`,
        boxShadow: `0 0 ${size * 2}px rgba(124,58,237,0.6)`,
      }}
      animate={{
        opacity: [0.3, 1, 0.3],
        scale: [1, 1.4, 1],
        y: [0, -20, 0],
      }}
      transition={{ duration: 4 + delay, repeat: Infinity, delay, ease: 'easeInOut' }}
    />
  );
}

/* ─── Animated connection line between two nodes ─── */
function ConnectionLine({ x1, y1, x2, y2, delay }: { x1: number; y1: number; x2: number; y2: number; delay: number }) {
  return (
    <motion.div
      className="absolute"
      style={{
        left: `${Math.min(x1, x2)}%`,
        top: `${Math.min(y1, y2)}%`,
        width: `${Math.abs(x2 - x1)}%`,
        height: 1,
        background: `linear-gradient(90deg, transparent, rgba(124,58,237,0.3), rgba(6,182,212,0.3), transparent)`,
        transformOrigin: 'left center',
        rotate: Math.atan2(y2 - y1, x2 - x1) * (180 / Math.PI),
      }}
      animate={{ opacity: [0, 0.6, 0] }}
      transition={{ duration: 3, repeat: Infinity, delay, ease: 'easeInOut' }}
    />
  );
}

const NODES = [
  { x: 8, y: 15, delay: 0, size: 5 }, { x: 15, y: 70, delay: 1.2, size: 4 },
  { x: 25, y: 35, delay: 0.5, size: 7 }, { x: 5, y: 50, delay: 2, size: 4 },
  { x: 92, y: 20, delay: 0.8, size: 6 }, { x: 85, y: 60, delay: 1.5, size: 5 },
  { x: 75, y: 85, delay: 0.3, size: 4 }, { x: 95, y: 75, delay: 2.2, size: 7 },
  { x: 50, y: 5, delay: 1, size: 5 }, { x: 50, y: 95, delay: 1.8, size: 4 },
];

const LINES = [
  { x1: 8, y1: 15, x2: 25, y2: 35, delay: 0 },
  { x1: 25, y1: 35, x2: 15, y2: 70, delay: 1 },
  { x1: 92, y1: 20, x2: 85, y2: 60, delay: 0.5 },
  { x1: 85, y1: 60, x2: 75, y2: 85, delay: 1.5 },
  { x1: 50, y1: 5, x2: 92, y2: 20, delay: 0.8 },
];

export default function SignInPage() {
  const router = useRouter();
  const { user: firebaseUser, loading: authLoading, signIn, signInWithGoogle } = useAuth();
  const { isAuthenticated: backendAuthenticated, loading: backendLoading } = useBackendAuth();

  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [showPassword, setShowPassword] = useState(false);
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);
  const [showVerificationWarning, setShowVerificationWarning] = useState(false);
  const [showMFA, setShowMFA] = useState(false);
  const [mfaUid, setMfaUid] = useState<string | null>(null);
  const [accountLocked, setAccountLocked] = useState(false);

  useEffect(() => {
    if (showMFA) return;
    const hasSessionToken = typeof window !== 'undefined' && localStorage.getItem('backend_session_token');
    if (!authLoading && !backendLoading && (firebaseUser || backendAuthenticated)) {
      if (!hasSessionToken && firebaseUser) return;
      const email = firebaseUser?.email;
      let redirect = email === 'admin@gmail.com' ? '/admin321' : '/dashboard';
      try {
        const isAdmin = localStorage.getItem('user_is_admin') === 'true';
        const adminRedirect = localStorage.getItem('admin_redirect_url');
        if (isAdmin && adminRedirect) redirect = adminRedirect;
      } catch { /* ignore */ }
      router.replace(redirect);
    }
  }, [authLoading, backendLoading, firebaseUser, backendAuthenticated, router, showMFA]);

  const handleEmailSignIn = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');
    setShowVerificationWarning(false);
    setAccountLocked(false);
    setLoading(true);
    try {
      const authUser = await signIn(email, password) as any;
      if (authUser?.requiresMFA) {
        setMfaUid(authUser.uid);
        setShowMFA(true);
        setLoading(false);
        return;
      }
      if (authUser && !authUser.emailVerified) setShowVerificationWarning(true);
      router.push(email === 'admin@gmail.com' ? '/admin321' : '/dashboard');
    } catch (err: any) {
      const code = err?.code || '';
      if (code.includes('wrong-password') || code.includes('user-not-found') || code.includes('invalid-credential')) {
        setError('Invalid email or password. Please try again.');
      } else if (code.includes('too-many-requests')) {
        setAccountLocked(true);
        setError('Too many failed attempts. Account temporarily locked.');
      } else {
        setError(err?.message || 'Login failed. Please try again.');
      }
    } finally {
      setLoading(false);
    }
  };

  const handleGoogleSignIn = async () => {
    setError('');
    setLoading(true);
    try {
      const result = await signInWithGoogle();
      setTimeout(() => {
        router.push(result?.email === 'admin@gmail.com' ? '/admin321' : '/dashboard');
      }, 200);
    } catch (err: any) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen relative overflow-hidden flex items-center justify-center bg-gradient-auth">
      {/* ── Neural network background ── */}
      <div className="absolute inset-0 overflow-hidden pointer-events-none">
        {NODES.map((n, i) => <FloatingNode key={i} {...n} />)}
        {LINES.map((l, i) => <ConnectionLine key={i} {...l} />)}

        {/* Large ambient glows */}
        <div className="absolute top-0 left-1/4 w-96 h-96 rounded-full blur-3xl"
          style={{ background: 'radial-gradient(circle, rgba(124,58,237,0.15) 0%, transparent 70%)' }} />
        <div className="absolute bottom-0 right-1/4 w-80 h-80 rounded-full blur-3xl"
          style={{ background: 'radial-gradient(circle, rgba(6,182,212,0.1) 0%, transparent 70%)' }} />

        {/* Grid overlay */}
        <div className="absolute inset-0 opacity-[0.03]"
          style={{
            backgroundImage: 'linear-gradient(rgba(124,58,237,1) 1px, transparent 1px), linear-gradient(90deg, rgba(124,58,237,1) 1px, transparent 1px)',
            backgroundSize: '60px 60px',
          }} />
      </div>

      <div className="relative z-10 w-full max-w-md px-4 py-8">
        {/* ── Logo & Header ── */}
        <motion.div
          initial={{ opacity: 0, y: -24 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.6 }}
          className="text-center mb-8"
        >
          {/* Logo mark */}
          <div className="inline-flex items-center gap-3 mb-4">
            <div className="relative w-12 h-12">
              <div className="absolute inset-0 rounded-xl bg-gradient-to-br from-violet-600 to-cyan-500 opacity-20 blur-md" />
              <div className="relative w-12 h-12 rounded-xl bg-gradient-to-br from-violet-600 to-cyan-500 flex items-center justify-center shadow-lg"
                style={{ boxShadow: '0 0 24px rgba(124,58,237,0.5)' }}>
                <Brain className="w-6 h-6 text-white" />
              </div>
            </div>
            <div className="text-left">
              <h1 className="text-2xl font-bold text-white font-outfit tracking-tight">FlowMind AI</h1>
              <p className="text-xs text-violet-400 font-medium">Intelligent Workflow Automation</p>
            </div>
          </div>
        </motion.div>

        {/* ── Auth Card ── */}
        <motion.div
          initial={{ opacity: 0, y: 24, scale: 0.96 }}
          animate={{ opacity: 1, y: 0, scale: 1 }}
          transition={{ duration: 0.7, delay: 0.2 }}
          className="relative"
        >
          {/* Card glow */}
          <div className="absolute -inset-1 rounded-2xl opacity-30 blur-lg"
            style={{ background: 'linear-gradient(135deg, #7C3AED, #06B6D4)' }} />

          <div className="relative glass-card rounded-2xl overflow-hidden">
            {/* Gradient top accent */}
            <div className="h-0.5 w-full bg-gradient-to-r from-violet-600 via-violet-400 to-cyan-500" />

            <div className="p-7">
              {/* Card heading */}
              <div className="mb-6 text-center">
                <h2 className="text-xl font-semibold text-white font-outfit">Welcome back</h2>
                <p className="text-sm text-white/50 mt-1 font-inter">Sign in to continue your automation journey</p>
              </div>

              {/* ── Alerts ── */}
              <AnimatePresence mode="wait">
                {error && !accountLocked && (
                  <motion.div key="error"
                    initial={{ opacity: 0, y: -8 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0, y: -8 }}
                    className="flex items-center gap-2 text-red-400 bg-red-500/10 border border-red-500/20 p-3 rounded-xl mb-4"
                  >
                    <AlertCircle size={15} className="shrink-0" />
                    <span className="text-xs font-medium font-inter">{error}</span>
                  </motion.div>
                )}
                {accountLocked && (
                  <motion.div key="locked"
                    initial={{ opacity: 0, y: -8 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0 }}
                    className="flex items-start gap-2 text-amber-400 bg-amber-500/10 border border-amber-500/20 p-3 rounded-xl mb-4"
                  >
                    <Shield size={15} className="shrink-0 mt-0.5" />
                    <div>
                      <p className="text-xs font-semibold mb-0.5">Account Temporarily Locked</p>
                      <p className="text-xs text-amber-300/70 font-inter">Too many failed attempts. Please wait a few minutes before trying again.</p>
                    </div>
                  </motion.div>
                )}
                {showVerificationWarning && (
                  <motion.div key="verify"
                    initial={{ opacity: 0, y: -8 }} animate={{ opacity: 1, y: 0 }}
                    className="flex items-start gap-2 text-blue-400 bg-blue-500/10 border border-blue-500/20 p-3 rounded-xl mb-4"
                  >
                    <AlertTriangle size={15} className="shrink-0 mt-0.5" />
                    <p className="text-xs font-inter">Please verify your email to access all features.</p>
                  </motion.div>
                )}
              </AnimatePresence>

              {/* ── MFA Step ── */}
              {showMFA && mfaUid ? (
                <div className="space-y-4">
                  <MFAVerify
                    uid={mfaUid}
                    onVerify={async (code: string) => {
                      try {
                        const backendUrl = process.env.NEXT_PUBLIC_BACKEND_API_URL || 'http://localhost:8000';
                        const res = await fetch(`${backendUrl}/api/v1/auth/mfa/verify-login`, {
                          method: 'POST',
                          headers: { 'Content-Type': 'application/json' },
                          body: JSON.stringify({ uid: mfaUid, code }),
                        });
                        if (!res.ok) {
                          const err = await res.json();
                          throw new Error(err.detail || 'Invalid verification code');
                        }
                        const data = await res.json();
                        if (data.access_token) localStorage.setItem('backend_session_token', data.access_token);
                        setShowMFA(false);
                        router.push(data.metadata?.redirect_to || '/dashboard');
                      } catch (err: any) {
                        setError(err.message || 'Invalid verification code');
                      }
                    }}
                    error={error}
                  />
                </div>
              ) : (
                <>
                  {/* ── Email / Password form ── */}
                  <form onSubmit={handleEmailSignIn} className="space-y-4">
                    {/* Email */}
                    <div className="space-y-1.5">
                      <Label htmlFor="signin-email" className="text-white/80 text-xs font-medium font-inter">
                        Email Address
                      </Label>
                      <div className="relative group">
                        <Mail className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-white/30 group-focus-within:text-violet-400 transition-colors" />
                        <Input
                          id="signin-email"
                          type="email"
                          placeholder="you@example.com"
                          value={email}
                          onChange={(e) => setEmail(e.target.value)}
                          className="pl-10 h-11 bg-white/5 border border-white/10 rounded-xl text-white placeholder:text-white/25 focus:border-violet-500 focus:ring-1 focus:ring-violet-500/40 focus:bg-white/8 transition-all text-sm font-inter"
                          required
                        />
                      </div>
                    </div>

                    {/* Password */}
                    <div className="space-y-1.5">
                      <div className="flex items-center justify-between">
                        <Label htmlFor="signin-password" className="text-white/80 text-xs font-medium font-inter">
                          Password
                        </Label>
                        <Link href="/reset-password"
                          className="text-xs text-violet-400 hover:text-violet-300 font-medium transition-colors font-inter">
                          Forgot password?
                        </Link>
                      </div>
                      <div className="relative group">
                        <Lock className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-white/30 group-focus-within:text-violet-400 transition-colors" />
                        <Input
                          id="signin-password"
                          type={showPassword ? 'text' : 'password'}
                          placeholder="••••••••"
                          value={password}
                          onChange={(e) => setPassword(e.target.value)}
                          className="pl-10 pr-10 h-11 bg-white/5 border border-white/10 rounded-xl text-white placeholder:text-white/25 focus:border-violet-500 focus:ring-1 focus:ring-violet-500/40 transition-all text-sm font-inter"
                          required
                        />
                        <button
                          type="button"
                          onClick={() => setShowPassword(!showPassword)}
                          className="absolute right-3 top-1/2 -translate-y-1/2 text-white/30 hover:text-white/70 transition-colors"
                        >
                          {showPassword ? <EyeOff size={15} /> : <Eye size={15} />}
                        </button>
                      </div>
                    </div>

                    {/* Submit */}
                    <Button
                      type="submit"
                      id="signin-submit"
                      disabled={loading}
                      className="w-full h-11 rounded-xl text-sm font-semibold font-outfit text-white transition-all duration-300 relative overflow-hidden group"
                      style={{
                        background: 'linear-gradient(135deg, #7C3AED 0%, #5B21B6 100%)',
                        boxShadow: '0 4px 24px rgba(124,58,237,0.35)',
                      }}
                    >
                      <span className="absolute inset-0 bg-gradient-to-r from-violet-500 to-violet-700 opacity-0 group-hover:opacity-100 transition-opacity" />
                      <span className="relative flex items-center justify-center gap-2">
                        {loading ? (
                          <>
                            <div className="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin" />
                            Signing in...
                          </>
                        ) : (
                          <>
                            Sign In
                            <ArrowRight className="w-4 h-4 group-hover:translate-x-1 transition-transform" />
                          </>
                        )}
                      </span>
                    </Button>
                  </form>

                  {/* ── Divider ── */}
                  <div className="relative my-5">
                    <div className="absolute inset-0 flex items-center">
                      <span className="w-full border-t border-white/10" />
                    </div>
                    <div className="relative flex justify-center text-xs">
                      <span className="px-3 text-white/40 font-inter" style={{ background: 'rgba(17,17,42,0.7)' }}>
                        or continue with
                      </span>
                    </div>
                  </div>

                  {/* ── Google ── */}
                  <Button
                    id="google-signin"
                    onClick={handleGoogleSignIn}
                    disabled={loading}
                    variant="outline"
                    className="w-full h-10 rounded-xl bg-white/5 border border-white/10 text-white/80 hover:bg-white/8 hover:border-white/20 hover:text-white text-sm font-medium font-inter transition-all duration-300"
                  >
                    <svg className="mr-2 h-4 w-4" viewBox="0 0 24 24">
                      <path fill="#4285F4" d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z" />
                      <path fill="#34A853" d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z" />
                      <path fill="#FBBC05" d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l2.85-2.22.81-.62z" />
                      <path fill="#EA4335" d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z" />
                    </svg>
                    Continue with Google
                  </Button>

                  {/* ── Sign up link ── */}
                  <p className="text-center mt-5 text-white/50 text-sm font-inter">
                    New to FlowMind AI?{' '}
                    <Link href="/sign-up" className="text-violet-400 hover:text-violet-300 font-semibold transition-colors">
                      Create an account
                    </Link>
                  </p>
                </>
              )}
            </div>
          </div>
        </motion.div>

        {/* ── Feature badges ── */}
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ duration: 0.8, delay: 0.8 }}
          className="mt-6 flex items-center justify-center gap-6 text-white/30 text-xs font-inter"
        >
          {[
            { icon: <Zap size={10} />, label: 'AI-Powered' },
            { icon: <Workflow size={10} />, label: 'Visual Builder' },
            { icon: <Bot size={10} />, label: 'Smart Automation' },
          ].map((b) => (
            <div key={b.label} className="flex items-center gap-1.5">
              <span className="text-violet-500">{b.icon}</span>
              {b.label}
            </div>
          ))}
        </motion.div>
      </div>
    </div>
  );
}
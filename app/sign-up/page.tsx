'use client';

import { useState } from 'react';
import { useRouter } from 'next/navigation';
import { useAuth } from '@/lib/AuthContext';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { PasswordStrength } from '@/components/auth/PasswordStrength';
import {
  AlertCircle, Mail, Lock, Eye, EyeOff, ArrowRight,
  User, CheckCircle2, Brain, Workflow, Bot, Zap
} from 'lucide-react';
import Link from 'next/link';

/* ─── Background node ─────────────────────────────── */
function FloatingNode({ x, y, size = 5 }: { x: number; y: number; size?: number }) {
  return (
    <div
      className="absolute rounded-full pointer-events-none opacity-80"
      style={{
        left: `${x}%`, top: `${y}%`, width: size, height: size,
        background: 'radial-gradient(circle, rgba(157,110,255,0.35), rgba(124,58,237,0.2))',
        boxShadow: `0 0 ${size * 2}px rgba(124,58,237,0.25)`,
      }}
    />
  );
}

const NODES = [
  { x: 6, y: 20, delay: 0, size: 4 }, { x: 12, y: 65, delay: 1.3, size: 6 },
  { x: 90, y: 15, delay: 0.6, size: 5 }, { x: 88, y: 70, delay: 1.8, size: 4 },
  { x: 50, y: 3, delay: 1, size: 5 }, { x: 3, y: 45, delay: 2.2, size: 3 },
  { x: 96, y: 45, delay: 0.4, size: 4 }, { x: 50, y: 97, delay: 1.6, size: 5 },
];

export default function SignUpPage() {
  const router = useRouter();
  const { signUp, signInWithGoogle } = useAuth();

  const [fullName, setFullName] = useState('');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [showPassword, setShowPassword] = useState(false);
  const [showConfirm, setShowConfirm] = useState(false);
  const [agreed, setAgreed] = useState(false);
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);
  const [success, setSuccess] = useState(false);

  const handleSignUp = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');

    if (password !== confirmPassword) {
      setError('Passwords do not match.');
      return;
    }
    if (password.length < 8) {
      setError('Password must be at least 8 characters.');
      return;
    }
    if (!agreed) {
      setError('Please accept the Terms of Service to continue.');
      return;
    }

    setLoading(true);
    try {
      await signUp(email, password, fullName || undefined);
      setSuccess(true);
    } catch (err: any) {
      const code = err?.code || '';
      if (code.includes('email-already-in-use')) {
        setError('An account with this email already exists.');
      } else if (code.includes('weak-password')) {
        setError('Please choose a stronger password.');
      } else {
        setError(err?.message || 'Failed to create account. Please try again.');
      }
    } finally {
      setLoading(false);
    }
  };

  const handleGoogleSignUp = async () => {
    setError('');
    setLoading(true);
    try {
      const result = await signInWithGoogle();
      setTimeout(() => router.push('/dashboard'), 200);
    } catch (err: any) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  /* ── Success state ── */
  if (success) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gradient-auth relative overflow-hidden">
        <div className="absolute inset-0 pointer-events-none">
          {NODES.map((n, i) => <FloatingNode key={i} {...n} />)}
        </div>
        <div className="relative z-10 glass-card rounded-2xl p-10 max-w-sm mx-4 text-center">
          <div className="h-0.5 w-full bg-gradient-to-r from-violet-600 via-violet-400 to-cyan-500 absolute top-0 left-0 rounded-t-2xl" />
          <div className="w-16 h-16 rounded-full bg-emerald-500/10 border border-emerald-500/30 flex items-center justify-center mx-auto mb-4">
            <CheckCircle2 className="w-8 h-8 text-emerald-400" />
          </div>
          <h2 className="text-xl font-bold text-white font-outfit mb-2">Account Created!</h2>
          <p className="text-white/60 text-sm font-inter mb-6 leading-relaxed">
            A verification email has been sent to <span className="text-violet-400 font-medium">{email}</span>.
            Please check your inbox to activate your account.
          </p>
          <Button
            onClick={() => router.push('/sign-in')}
            className="w-full h-10 rounded-xl text-sm font-semibold font-outfit text-white"
            style={{ background: 'linear-gradient(135deg, #7C3AED, #5B21B6)', boxShadow: '0 4px 20px rgba(124,58,237,0.3)' }}
          >
            Go to Sign In
          </Button>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen relative overflow-hidden flex items-center justify-center bg-gradient-auth py-6">
      {/* Background */}
      <div className="absolute inset-0 overflow-hidden pointer-events-none">
        {NODES.map((n, i) => <FloatingNode key={i} {...n} />)}
        <div className="absolute top-0 left-1/4 w-96 h-96 rounded-full blur-3xl"
          style={{ background: 'radial-gradient(circle, rgba(124,58,237,0.12) 0%, transparent 70%)' }} />
        <div className="absolute bottom-0 right-1/4 w-80 h-80 rounded-full blur-3xl"
          style={{ background: 'radial-gradient(circle, rgba(6,182,212,0.08) 0%, transparent 70%)' }} />
        <div className="absolute inset-0 opacity-[0.025]"
          style={{
            backgroundImage: 'linear-gradient(rgba(124,58,237,1) 1px, transparent 1px), linear-gradient(90deg, rgba(124,58,237,1) 1px, transparent 1px)',
            backgroundSize: '60px 60px',
          }} />
      </div>

      <div className="relative z-10 w-full max-w-md px-4">
        {/* Logo */}
        <div className="text-center mb-6">
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
        </div>

        {/* Card */}
        <div className="relative">
          <div className="absolute -inset-1 rounded-2xl opacity-25 blur-lg"
            style={{ background: 'linear-gradient(135deg, #7C3AED, #06B6D4)' }} />

          <div className="relative glass-card rounded-2xl overflow-hidden">
            <div className="h-0.5 w-full bg-gradient-to-r from-violet-600 via-violet-400 to-cyan-500" />

            <div className="p-7">
              <div className="mb-5 text-center">
                <h2 className="text-xl font-semibold text-white font-outfit">Create your account</h2>
                <p className="text-sm text-white/50 mt-1 font-inter">Start automating with AI in minutes</p>
              </div>

              {/* Error */}
              {error && (
                <div className="flex items-center gap-2 text-red-400 bg-red-500/10 border border-red-500/20 p-3 rounded-xl mb-4">
                  <AlertCircle size={15} className="shrink-0" />
                  <span className="text-xs font-medium font-inter">{error}</span>
                </div>
              )}

              <form onSubmit={handleSignUp} className="space-y-3.5">
                {/* Full name */}
                <div className="space-y-1.5">
                  <Label htmlFor="signup-name" className="text-white/80 text-xs font-medium font-inter">Full Name</Label>
                  <div className="relative group">
                    <User className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-white/30 group-focus-within:text-violet-400 transition-colors" />
                    <Input
                      id="signup-name"
                      type="text"
                      placeholder="Your name"
                      value={fullName}
                      onChange={(e) => setFullName(e.target.value)}
                      className="pl-10 h-11 bg-white/5 border border-white/10 rounded-xl text-white placeholder:text-white/25 focus:border-violet-500 focus:ring-1 focus:ring-violet-500/40 transition-all text-sm font-inter"
                    />
                  </div>
                </div>

                {/* Email */}
                <div className="space-y-1.5">
                  <Label htmlFor="signup-email" className="text-white/80 text-xs font-medium font-inter">Email Address</Label>
                  <div className="relative group">
                    <Mail className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-white/30 group-focus-within:text-violet-400 transition-colors" />
                    <Input
                      id="signup-email"
                      type="email"
                      placeholder="you@example.com"
                      value={email}
                      onChange={(e) => setEmail(e.target.value)}
                      className="pl-10 h-11 bg-white/5 border border-white/10 rounded-xl text-white placeholder:text-white/25 focus:border-violet-500 focus:ring-1 focus:ring-violet-500/40 transition-all text-sm font-inter"
                      required
                    />
                  </div>
                </div>

                {/* Password */}
                <div className="space-y-1.5">
                  <Label htmlFor="signup-password" className="text-white/80 text-xs font-medium font-inter">Password</Label>
                  <div className="relative group">
                    <Lock className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-white/30 group-focus-within:text-violet-400 transition-colors" />
                    <Input
                      id="signup-password"
                      type={showPassword ? 'text' : 'password'}
                      placeholder="Min 8 characters"
                      value={password}
                      onChange={(e) => setPassword(e.target.value)}
                      className="pl-10 pr-10 h-11 bg-white/5 border border-white/10 rounded-xl text-white placeholder:text-white/25 focus:border-violet-500 focus:ring-1 focus:ring-violet-500/40 transition-all text-sm font-inter"
                      required
                    />
                    <button type="button" onClick={() => setShowPassword(!showPassword)}
                      className="absolute right-3 top-1/2 -translate-y-1/2 text-white/30 hover:text-white/70 transition-colors">
                      {showPassword ? <EyeOff size={15} /> : <Eye size={15} />}
                    </button>
                  </div>
                  <PasswordStrength password={password} />
                </div>

                {/* Confirm Password */}
                <div className="space-y-1.5">
                  <Label htmlFor="signup-confirm" className="text-white/80 text-xs font-medium font-inter">Confirm Password</Label>
                  <div className="relative group">
                    <Lock className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-white/30 group-focus-within:text-violet-400 transition-colors" />
                    <Input
                      id="signup-confirm"
                      type={showConfirm ? 'text' : 'password'}
                      placeholder="Re-enter password"
                      value={confirmPassword}
                      onChange={(e) => setConfirmPassword(e.target.value)}
                      className={`pl-10 pr-10 h-11 bg-white/5 border rounded-xl text-white placeholder:text-white/25 focus:ring-1 transition-all text-sm font-inter ${
                        confirmPassword && confirmPassword !== password
                          ? 'border-red-500/50 focus:border-red-500 focus:ring-red-500/30'
                          : confirmPassword && confirmPassword === password
                          ? 'border-emerald-500/50 focus:border-emerald-500 focus:ring-emerald-500/30'
                          : 'border-white/10 focus:border-violet-500 focus:ring-violet-500/40'
                      }`}
                      required
                    />
                    <button type="button" onClick={() => setShowConfirm(!showConfirm)}
                      className="absolute right-3 top-1/2 -translate-y-1/2 text-white/30 hover:text-white/70 transition-colors">
                      {showConfirm ? <EyeOff size={15} /> : <Eye size={15} />}
                    </button>
                  </div>
                  {confirmPassword && confirmPassword === password && (
                    <p className="flex items-center gap-1 text-[10px] text-emerald-400 font-inter mt-1">
                      <CheckCircle2 size={10} /> Passwords match
                    </p>
                  )}
                </div>

                {/* Terms */}
                <div className="flex items-start gap-2.5 pt-1">
                  <button
                    type="button"
                    id="tos-checkbox"
                    onClick={() => setAgreed(!agreed)}
                    className={`mt-0.5 w-4 h-4 rounded border flex items-center justify-center shrink-0 transition-all ${
                      agreed
                        ? 'bg-violet-600 border-violet-600'
                        : 'bg-white/5 border-white/20 hover:border-violet-500'
                    }`}
                  >
                    {agreed && <CheckCircle2 size={10} className="text-white" />}
                  </button>
                  <p className="text-[11px] text-white/45 font-inter leading-relaxed">
                    I agree to the{' '}
                    <Link href="#" className="text-violet-400 hover:text-violet-300 underline">Terms of Service</Link>
                    {' '}and{' '}
                    <Link href="#" className="text-violet-400 hover:text-violet-300 underline">Privacy Policy</Link>
                  </p>
                </div>

                {/* Submit */}
                <Button
                  type="submit"
                  id="signup-submit"
                  disabled={loading}
                  className="w-full h-11 rounded-xl text-sm font-semibold font-outfit text-white transition-all duration-300 relative overflow-hidden group mt-1"
                  style={{
                    background: 'linear-gradient(135deg, #7C3AED 0%, #5B21B6 100%)',
                    boxShadow: '0 4px 24px rgba(124,58,237,0.35)',
                  }}
                >
                  <span className="absolute inset-0 bg-gradient-to-r from-violet-500 to-violet-700 opacity-0 group-hover:opacity-100 transition-opacity" />
                  <span className="relative flex items-center justify-center gap-2">
                    {loading ? (
                      <><div className="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin" />Creating Account...</>
                    ) : (
                      <>Create Account <ArrowRight className="w-4 h-4 group-hover:translate-x-1 transition-transform" /></>
                    )}
                  </span>
                </Button>
              </form>

              {/* Divider */}
              <div className="relative my-4">
                <div className="absolute inset-0 flex items-center">
                  <span className="w-full border-t border-white/10" />
                </div>
                <div className="relative flex justify-center text-xs">
                  <span className="px-3 text-white/40 font-inter" style={{ background: 'rgba(17,17,42,0.7)' }}>
                    or sign up with
                  </span>
                </div>
              </div>

              {/* Google */}
              <Button
                id="google-signup"
                onClick={handleGoogleSignUp}
                disabled={loading}
                variant="outline"
                className="w-full h-10 rounded-xl bg-white/5 border border-white/10 text-white/80 hover:bg-white/8 hover:border-white/20 hover:text-white text-sm font-medium font-inter transition-all"
              >
                <svg className="mr-2 h-4 w-4" viewBox="0 0 24 24">
                  <path fill="#4285F4" d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z" />
                  <path fill="#34A853" d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z" />
                  <path fill="#FBBC05" d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l2.85-2.22.81-.62z" />
                  <path fill="#EA4335" d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z" />
                </svg>
                Continue with Google
              </Button>

              <p className="text-center mt-4 text-white/50 text-sm font-inter">
                Already have an account?{' '}
                <Link href="/sign-in" className="text-violet-400 hover:text-violet-300 font-semibold transition-colors">
                  Sign in
                </Link>
              </p>
            </div>
          </div>
        </div>

        {/* Feature badges */}
        <div className="mt-5 flex items-center justify-center gap-6 text-white/30 text-xs font-inter">
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
        </div>
      </div>
    </div>
  );
}
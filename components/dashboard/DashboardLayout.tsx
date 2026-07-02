"use client";

import { useState, useEffect } from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { useAuth } from "@/lib/AuthContext";
import { Button } from "@/components/ui/button";
import { Avatar, AvatarFallback, AvatarImage } from "@/components/ui/avatar";
import { DropdownMenu, DropdownMenuContent, DropdownMenuItem, DropdownMenuLabel, DropdownMenuSeparator, DropdownMenuTrigger } from "@/components/ui/dropdown-menu";
import { LogOut, User as UserIcon, Settings, AlertTriangle, MailCheck, X, Menu, ChevronRight, Brain, Bell } from "lucide-react";
import Image from "next/image";

interface DashboardLayoutProps {
  children: React.ReactNode;
}

// Custom icon component for SVG icons
const SvgIcon = ({ src, className }: { src: string; className?: string }) => (
  <Image src={src} alt="" width={24} height={24} className={className} />
);

const sidebarItems = [
  { name: "Dashboard", iconSrc: "/assets/dashboard/dasboard.svg", href: "/dashboard" },
  { name: "Workflows", iconSrc: "/assets/dashboard/workflow.svg", href: "/workflows" },
  { name: "AI Studio", iconSrc: "/assets/dashboard/workflow.svg", href: "/ai" },
  { name: "Credentials", iconSrc: "/assets/dashboard/token.svg", href: "/credentials" },
  { name: "Marketplace", iconSrc: "/assets/dashboard/marketPlace.svg", href: "/marketplace" },
  { name: "Profile", iconSrc: "/assets/dashboard/profile.svg", href: "/profile" },
  { name: "Team", iconSrc: "/assets/dashboard/profile.svg", href: "/team" },
  { name: "Settings", iconSrc: "/assets/dashboard/setting.svg", href: "/settings" },
];

export default function DashboardLayout({ children }: DashboardLayoutProps) {
  const [isSidebarOpen, setIsSidebarOpen] = useState(false);
  const [showVerificationBanner, setShowVerificationBanner] = useState(true);
  const [resendLoading, setResendLoading] = useState(false);
  const [resendSuccess, setResendSuccess] = useState(false);
  const [notifications, setNotifications] = useState<any[]>([]);
  const [showNotifDropdown, setShowNotifDropdown] = useState(false);
  const [notifLoading, setNotifLoading] = useState(false);
  const pathname = usePathname();
  const { user, loading, signOut, sendVerificationEmail } = useAuth();

  const fetchNotifications = async () => {
    if (!user) return;
    setNotifLoading(true);
    try {
      const token = localStorage.getItem('backend_auth_token') || await (user as any).getIdToken();
      const backendUrl = process.env.NEXT_PUBLIC_BACKEND_API_URL || 'http://localhost:8000';
      const res = await fetch(`${backendUrl}/api/v1/notifications`, {
        headers: { 'Authorization': `Bearer ${token}` }
      });
      if (res.ok) {
        const data = await res.json();
        setNotifications(data.notifications || data.items || []);
      }
    } catch (e) {
      console.error("Failed to fetch notifications:", e);
    } finally {
      setNotifLoading(false);
    }
  };

  const markAllRead = async () => {
    if (!user) return;
    try {
      const token = localStorage.getItem('backend_auth_token') || await (user as any).getIdToken();
      const backendUrl = process.env.NEXT_PUBLIC_BACKEND_API_URL || 'http://localhost:8000';
      const res = await fetch(`${backendUrl}/api/v1/notifications/mark-all-read`, {
        method: 'POST',
        headers: { 'Authorization': `Bearer ${token}` }
      });
      if (res.ok) {
        setNotifications(prev => prev.map(n => ({ ...n, read: true })));
      }
    } catch (e) {
      console.error("Failed to mark notifications as read:", e);
    }
  };

  useEffect(() => {
    if (user) {
      fetchNotifications();
    }
  }, [user]);

  // Show loading spinner while checking authentication
  if (loading) {
    return (
      <div className="min-h-screen bg-black flex items-center justify-center">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-[#1D4ED8] mx-auto mb-4"></div>
          <p className="text-white/70">Loading...</p>
        </div>
      </div>
    );
  }

  // Redirect to sign-in if not authenticated (handled by useEffect in pages)
  if (!user) {
    return (
      <div className="min-h-screen bg-black flex items-center justify-center">
        <div className="text-center">
          <p className="text-white/70">Redirecting to sign in...</p>
        </div>
      </div>
    );
  }

  const handleSignOut = async () => {
    try {
      await signOut();
      window.location.href = '/sign-in';
    } catch (error) {
      console.error('Error signing out:', error);
    }
  };

  const getUserInitials = () => {
    if (!user) return 'U';
    if (user.displayName) {
      return user.displayName.split(' ').map(n => n[0]).join('').toUpperCase();
    }
    return user.email?.charAt(0).toUpperCase() || 'U';
  };

  const handleResendVerification = async () => {
    setResendLoading(true);
    setResendSuccess(false);
    try {
      await sendVerificationEmail();
      setResendSuccess(true);
      setTimeout(() => setResendSuccess(false), 5000);
    } catch (error) {
      console.error('Failed to resend verification email:', error);
    } finally {
      setResendLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-black text-white flex">
      {/* Sidebar */}
      <aside
        className={`fixed lg:fixed left-0 top-0 z-30 h-full w-64 bg-black/40 backdrop-blur-xl border-r border-white/10 flex flex-col transform transition-transform duration-300 overflow-y-auto
        ${isSidebarOpen ? "translate-x-0" : "-translate-x-full lg:translate-x-0"}`}
      >
        {/* Logo */}
        <div className="p-6">
          <Link href="/dashboard" className="flex items-center gap-3 group">
            <div className="flex items-center gap-2">
              <div className="bg-blue-600 p-1.5 rounded-lg shadow-lg shadow-blue-600/30">
                <Brain className="w-5 h-5 text-white" />
              </div>
              <span className="text-xl font-bold text-white tracking-tight" style={{ fontFamily: 'Outfit, sans-serif' }}>
                FlowMind AI
              </span>
            </div>
          </Link>
          {/* <p className="text-xs text-white/50 mt-2 font-montserrat">AI Workspace</p> */}
        </div>

        {/* Navigation */}
        <nav className="flex-1 px-4 py-4">
          <ul className="space-y-2">
            {sidebarItems.map((item) => {
              const isActive = pathname === item.href;

              return (
                <li key={item.name}>
                  <Link
                    href={item.href}
                    onClick={() => setIsSidebarOpen(false)}
                    className={`w-full flex items-center gap-3 px-4 py-3 rounded-xl transition-all duration-300 group ${
                      isActive
                        ? "bg-gradient-to-r from-[#1D4ED8] to-[#C22C00] text-white"
                        : "text-white/70 hover:text-white hover:bg-white/10"
                    }`}
                  >
                    <SvgIcon
                      src={item.iconSrc}
                      className={`w-5 h-5 transition-all ${isActive ? '' : 'opacity-80 group-hover:opacity-100'}`}
                    />
                    <span className="font-montserrat font-medium">{item.name}</span>
                    {isActive && (
                      <ChevronRight className="w-4 h-4 ml-auto text-white" />
                    )}
                  </Link>
                </li>
              );
            })}
          </ul>
        </nav>

        {/* User Section */}
        <div className="p-4 border-t border-white/10">
          <DropdownMenu>
            <DropdownMenuTrigger className="w-full">
              <div className="flex items-center gap-3 p-3 rounded-xl bg-white/5 hover:bg-white/10 transition-colors">
                <Avatar className="w-8 h-8">
                  <AvatarImage src={user?.photoURL || ''} />
                  <AvatarFallback className="bg-gradient-to-br from-[#1D4ED8] to-[#3B82F6] text-white text-xs">
                    {getUserInitials()}
                  </AvatarFallback>
                </Avatar>
                <div className="flex-1 text-left">
                  <p className="text-sm font-montserrat font-medium text-white">{user?.displayName || user?.email}</p>
                  <p className="text-xs font-montserrat text-white/50">Manage Account</p>
                </div>
              </div>
            </DropdownMenuTrigger>
            <DropdownMenuContent className="w-56 bg-black/90 backdrop-blur-xl border-white/10" align="end">
              <DropdownMenuLabel className="text-white">{user?.email}</DropdownMenuLabel>
              <DropdownMenuSeparator className="bg-white/10" />
              <DropdownMenuItem asChild className="text-white hover:bg-white/10">
                <Link href="/profile" className="flex items-center gap-2">
                  <UserIcon className="w-4 h-4" />
                  Profile
                </Link>
              </DropdownMenuItem>
              <DropdownMenuItem asChild className="text-white hover:bg-white/10">
                <Link href="/settings" className="flex items-center gap-2">
                  <Settings className="w-4 h-4" />
                  Settings
                </Link>
              </DropdownMenuItem>
              <DropdownMenuSeparator className="bg-white/10" />
              <DropdownMenuItem onClick={handleSignOut} className="text-red-400 hover:bg-red-400/10">
                <LogOut className="w-4 h-4 mr-2" />
                Sign Out
              </DropdownMenuItem>
            </DropdownMenuContent>
          </DropdownMenu>
        </div>
      </aside>

      {/* Mobile Overlay */}
      {isSidebarOpen && (
        <div
          className="fixed inset-0 bg-black/50 backdrop-blur-sm z-20 lg:hidden"
          onClick={() => setIsSidebarOpen(false)}
        />
      )}

      {/* Main Content */}
      <div className="flex-1 flex flex-col min-h-screen lg:ml-64 relative">
        {/* Global dashboard background */}
        <div className="pointer-events-none fixed inset-0 z-0">
          {/* Top-left background */}
          <div className="absolute -top-10 -left-10 md:-top-16 md:-left-8 opacity-40 md:opacity-60">
            <Image
              src="/assets/dashboard/BG-left.svg"
              alt=""
              width={700}
              height={700}
              className="max-w-none select-none"
              priority
            />
          </div>

          {/* Right-aligned background */}
          <div className="absolute top-10 right-0 md:-top-4 opacity-40 md:opacity-70">
            <Image
              src="/assets/dashboard/BG-right.svg"
              alt=""
              width={600}
              height={600}
              className="max-w-none select-none"
              priority
            />
          </div>
        </div>

        {/* Header */}
        <header className="sticky top-0 z-10 bg-black/40 backdrop-blur-xl border-b border-white/10">
          <div className="flex items-center justify-between px-4 lg:px-8 py-4">
            {/* Mobile Menu Button */}
            <button
              onClick={() => setIsSidebarOpen(!isSidebarOpen)}
              className="lg:hidden text-white hover:text-[#1D4ED8] transition-colors duration-300"
            >
              {isSidebarOpen ? (
                <X className="w-6 h-6" />
              ) : (
                <Menu className="w-6 h-6" />
              )}
            </button>

            <Link href="/dashboard" className="lg:hidden flex items-center gap-2">
              <div className="bg-blue-600 p-1 rounded-md">
                <Brain className="w-4 h-4 text-white" />
              </div>
              <span className="text-lg font-bold text-white tracking-tight">FlowMind</span>
            </Link>

            {/* Notifications Bell */}
            <div className="relative ml-auto">
              <button
                onClick={() => {
                  setShowNotifDropdown(!showNotifDropdown);
                  if (!showNotifDropdown) fetchNotifications();
                }}
                className="relative p-2 text-white/70 hover:text-white hover:bg-white/10 rounded-xl transition-all"
              >
                <Bell className="w-5 h-5" />
                {notifications.filter(n => !n.read).length > 0 && (
                  <span className="absolute top-1.5 right-1.5 w-2 h-2 bg-blue-500 rounded-full" />
                )}
              </button>

              {showNotifDropdown && (
                <>
                  <div className="fixed inset-0 z-30" onClick={() => setShowNotifDropdown(false)} />
                  <div className="absolute right-0 mt-2 w-80 bg-zinc-950/95 border border-zinc-800 rounded-2xl shadow-2xl overflow-hidden z-40">
                    <div className="flex items-center justify-between px-4 py-3 border-b border-zinc-800">
                      <span className="text-sm font-semibold text-white">Notifications</span>
                      {notifications.filter(n => !n.read).length > 0 && (
                        <button
                          onClick={markAllRead}
                          className="text-xs text-blue-500 hover:text-blue-400 font-medium"
                        >
                          Mark all as read
                        </button>
                      )}
                    </div>
                    <div className="max-h-60 overflow-y-auto divide-y divide-zinc-900">
                      {notifLoading ? (
                        <div className="p-4 text-center text-xs text-white/50 animate-pulse">Loading...</div>
                      ) : notifications.length === 0 ? (
                        <div className="p-6 text-center text-xs text-white/40">No notifications</div>
                      ) : (
                        notifications.map((n) => (
                          <div key={n.id || Math.random().toString()} className={`p-4 hover:bg-white/5 transition-colors text-left ${!n.read ? 'bg-blue-500/5' : ''}`}>
                            <p className="text-xs font-semibold text-white">{n.title || 'Notification'}</p>
                            <p className="text-[11px] text-white/60 mt-1">{n.message || n.body}</p>
                            <p className="text-[9px] text-white/40 mt-1">
                              {n.createdAt ? new Date(n.createdAt).toLocaleTimeString() : 'Just now'}
                            </p>
                          </div>
                        ))
                      )}
                    </div>
                  </div>
                </>
              )}
            </div>

          </div>
        </header>

        {/* Email Verification Banner */}
        {user && !user.emailVerified && showVerificationBanner && (
          <div className="sticky top-[73px] z-10 bg-amber-500/10 border-b border-amber-500/20 backdrop-blur-sm">
            <div className="px-4 lg:px-8 py-3">
              <div className="flex items-center justify-between gap-4">
                <div className="flex items-start gap-3 flex-1">
                  <AlertTriangle className="w-5 h-5 text-amber-400 flex-shrink-0 mt-0.5" />
                  <div className="flex-1">
                    <p className="text-sm font-medium text-amber-400 mb-1">
                      Please verify your email address
                    </p>
                    <p className="text-xs text-amber-300/80">
                      We've sent a verification link to <span className="font-semibold">{user.email}</span>. 
                      Please check your inbox and click the link to verify your account.
                    </p>
                    {resendSuccess && (
                      <p className="text-xs text-green-400 mt-2">
                        ✓ Verification email sent successfully!
                      </p>
                    )}
                  </div>
                </div>
                <div className="flex items-center gap-2">
                  <Button
                    onClick={handleResendVerification}
                    disabled={resendLoading}
                    variant="outline"
                    size="sm"
                    className="bg-amber-500/10 border-amber-500/30 text-amber-400 hover:bg-amber-500/20 hover:border-amber-500/50 text-xs h-8"
                  >
                    {resendLoading ? (
                      <>
                        <div className="w-3 h-3 border-2 border-amber-400/20 border-t-amber-400 rounded-full animate-spin mr-2" />
                        Sending...
                      </>
                    ) : (
                      <>
                        <MailCheck className="w-3 h-3 mr-1.5" />
                        Resend
                      </>
                    )}
                  </Button>
                  <button
                    onClick={() => setShowVerificationBanner(false)}
                    className="text-amber-400/60 hover:text-amber-400 transition-colors p-1"
                  >
                    <X className="w-4 h-4" />
                  </button>
                </div>
              </div>
            </div>
          </div>
        )}

        {/* Page Content */}
        <main className="flex-1 relative z-10">{children}</main>
      </div>
    </div>
  );
}

"use client";

import React, { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { useAuth } from "@/lib/AuthContext";
import AdminLayout from "@/components/admin/AdminLayout";
import apiClient from "@/lib/api/client";

export default function AdminAppLayout({ children }: { children: React.ReactNode }) {
  const { user, loading } = useAuth();
  const router = useRouter();
  // null = still checking with the backend
  const [isAdmin, setIsAdmin] = useState<boolean | null>(null);

  useEffect(() => {
    if (loading) return;

    // Not logged in -> go to sign-in
    if (!user) {
      router.replace("/sign-in");
      return;
    }

    // Role comes from the backend (Firestore role / admin claim), not from the client
    let cancelled = false;
    apiClient
      .get("/api/v1/admin/whoami")
      .then((res) => {
        if (cancelled) return;
        // Admins and managers (read-only) may open the panel; actions stay admin-only on the backend
        const allowed = !!res.data?.canAccessAdmin;
        setIsAdmin(allowed);
        if (!allowed) router.replace("/dashboard");
      })
      .catch(() => {
        if (cancelled) return;
        setIsAdmin(false);
        router.replace("/dashboard");
      });
    return () => {
      cancelled = true;
    };
  }, [user, loading, router]);

  // While checking, or while redirecting away, render nothing to avoid flicker
  if (loading || !user || !isAdmin) {
    return null;
  }

  return <AdminLayout>{children}</AdminLayout>;
}

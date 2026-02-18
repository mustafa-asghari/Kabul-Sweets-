'use client';

import React, { createContext, useCallback, useContext, useEffect, useState } from 'react';
import { usePathname, useRouter } from 'next/navigation';
import { PATH_AUTH } from '@/routes';

export interface AuthUser {
  id: string;
  email: string;
  full_name: string;
  phone: string | null;
  role: string;
  is_active: boolean;
  is_verified: boolean;
  created_at: string;
  last_login: string | null;
}

interface AuthContextType {
  user: AuthUser | null;
  isAuthenticated: boolean;
  isLoading: boolean;
  login: (email: string, password: string) => Promise<{ success: boolean; error?: string }>;
  logout: () => Promise<void>;
  refreshUser: () => Promise<boolean>;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [user, setUser] = useState<AuthUser | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const router = useRouter();
  const pathname = usePathname();

  const refreshUser = useCallback(async () => {
    try {
      const res = await fetch('/api/auth/me', {
        credentials: 'include',
      });
      if (res.ok) {
        const json = await res.json();
        if (json.succeeded && json.data) {
          setUser(json.data);
          return true;
        }
      }
      setUser(null);
      return false;
    } catch {
      setUser(null);
      return false;
    }
  }, []);

  useEffect(() => {
    refreshUser().finally(() => setIsLoading(false));
  }, [refreshUser]);

  useEffect(() => {
    if (isLoading || user || !pathname) {
      return;
    }

    if (pathname.startsWith('/auth/')) {
      return;
    }

    const callbackUrl = encodeURIComponent(pathname);
    router.replace(`${PATH_AUTH.signin}?callbackUrl=${callbackUrl}`);
  }, [isLoading, pathname, router, user]);

  const login = useCallback(
    async (email: string, password: string) => {
      try {
        const res = await fetch('/api/auth/login', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ email, password }),
          credentials: 'include',
        });

        const json = await res.json();

        if (!res.ok || !json.succeeded) {
          return { success: false, error: json.message || 'Login failed' };
        }

        const isAuthenticated = await refreshUser();
        if (!isAuthenticated) {
          return {
            success: false,
            error: 'Login succeeded, but session could not be established',
          };
        }
        return { success: true };
      } catch {
        return { success: false, error: 'Could not connect to server' };
      }
    },
    [refreshUser]
  );

  const logout = useCallback(async () => {
    try {
      await fetch('/api/auth/logout', {
        method: 'POST',
        credentials: 'include',
      });
    } catch {
      // Clear state even if backend call fails
    }
    setUser(null);
    router.push(PATH_AUTH.signin);
  }, [router]);

  return (
    <AuthContext.Provider
      value={{
        user,
        isAuthenticated: !!user,
        isLoading,
        login,
        logout,
        refreshUser,
      }}
    >
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const context = useContext(AuthContext);
  if (context === undefined) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
}

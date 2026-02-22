"use client";

import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useRef,
  useState,
} from "react";
import { useAuth as useClerkAuth, useClerk } from "@clerk/nextjs";
import { ApiError, apiRequest } from "@/lib/api-client";

const ACCESS_TOKEN_KEY = "kabul_access_token";
const REFRESH_TOKEN_KEY = "kabul_refresh_token";
const CLERK_USER_ID_KEY = "kabul_clerk_user_id";

interface TokenResponse {
  access_token: string;
  refresh_token: string;
}

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

export interface AuthContextValue {
  user: AuthUser | null;
  isAuthenticated: boolean;
  loading: boolean;
  accessToken: string | null;
  authError: string | null;
  logout: () => Promise<void>;
  refreshUser: () => Promise<void>;
  updateProfile: (payload: { full_name?: string; phone?: string }) => Promise<void>;
}

const AuthContext = createContext<AuthContextValue | undefined>(undefined);

function isBrowser() {
  return typeof window !== "undefined";
}

function readStoredTokens() {
  if (!isBrowser()) {
    return { accessToken: null as string | null, refreshToken: null as string | null };
  }
  return {
    accessToken: window.localStorage.getItem(ACCESS_TOKEN_KEY),
    refreshToken: window.localStorage.getItem(REFRESH_TOKEN_KEY),
  };
}

function persistTokens(tokens: { accessToken: string; refreshToken: string; clerkUserId?: string } | null) {
  if (!isBrowser()) return;

  if (!tokens) {
    window.localStorage.removeItem(ACCESS_TOKEN_KEY);
    window.localStorage.removeItem(REFRESH_TOKEN_KEY);
    window.localStorage.removeItem(CLERK_USER_ID_KEY);
    window.dispatchEvent(new Event("auth-changed"));
    return;
  }

  window.localStorage.setItem(ACCESS_TOKEN_KEY, tokens.accessToken);
  window.localStorage.setItem(REFRESH_TOKEN_KEY, tokens.refreshToken);
  if (tokens.clerkUserId) {
    window.localStorage.setItem(CLERK_USER_ID_KEY, tokens.clerkUserId);
  }
  window.dispatchEvent(new Event("auth-changed"));
}

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const clerkAuth = useClerkAuth();
  const clerk = useClerk();

  const [user, setUser] = useState<AuthUser | null>(null);
  const [accessToken, setAccessToken] = useState<string | null>(null);
  const [internalLoading, setInternalLoading] = useState(true);
  const [authError, setAuthError] = useState<string | null>(null);

  // Track the last Clerk sign-in state we processed to avoid redundant exchanges
  const lastClerkSignedIn = useRef<boolean | undefined>(undefined);

  const clearSession = useCallback(() => {
    setUser(null);
    setAccessToken(null);
    persistTokens(null);
  }, []);

  // React to Clerk auth state changes (sign-in / sign-out)
  useEffect(() => {
    if (!clerkAuth.isLoaded) return;

    // Skip if the sign-in state hasn't changed since last run
    if (lastClerkSignedIn.current === clerkAuth.isSignedIn) return;
    lastClerkSignedIn.current = clerkAuth.isSignedIn;

    const run = async () => {
      setInternalLoading(true);
      setAuthError(null);

      try {
        if (!clerkAuth.isSignedIn) {
          clearSession();
          return;
        }

        // Try stored backend token first (avoids a round-trip on page reload),
        // but ONLY if it was issued for the same Clerk user that is currently signed in.
        const stored = readStoredTokens();
        const storedClerkUserId = isBrowser()
          ? window.localStorage.getItem(CLERK_USER_ID_KEY)
          : null;
        if (stored.accessToken && storedClerkUserId === clerkAuth.userId) {
          try {
            const profile = await apiRequest<AuthUser>("/api/v1/auth/me", {
              token: stored.accessToken,
            });
            setUser(profile);
            setAccessToken(stored.accessToken);
            return;
          } catch {
            // Token expired or invalid — fall through to Clerk exchange
          }
        }

        // Exchange Clerk session token for a backend JWT
        const clerkToken = await clerkAuth.getToken();
        if (!clerkToken) {
          clearSession();
          return;
        }

        const tokens = await apiRequest<TokenResponse>("/api/v1/auth/clerk-exchange", {
          method: "POST",
          body: { session_token: clerkToken },
        });

        setAccessToken(tokens.access_token);
        persistTokens({
          accessToken: tokens.access_token,
          refreshToken: tokens.refresh_token,
          clerkUserId: clerkAuth.userId ?? undefined,
        });

        const profile = await apiRequest<AuthUser>("/api/v1/auth/me", {
          token: tokens.access_token,
        });
        setUser(profile);
      } catch (err) {
        const message = err instanceof ApiError ? err.detail : "Authentication failed";
        setAuthError(message);
        clearSession();
      } finally {
        setInternalLoading(false);
      }
    };

    run();
  }, [clerkAuth.isLoaded, clerkAuth.isSignedIn, clerkAuth.getToken, clearSession]);

  const logout = useCallback(async () => {
    try {
      if (accessToken) {
        await apiRequest<{ message: string }>("/api/v1/auth/logout", {
          method: "POST",
          token: accessToken,
        });
      }
    } catch {
      // Ignore transport failures
    }
    clearSession();
    await clerk.signOut();
  }, [accessToken, clearSession, clerk]);

  const refreshUser = useCallback(async () => {
    if (!accessToken) {
      setUser(null);
      return;
    }
    try {
      const profile = await apiRequest<AuthUser>("/api/v1/auth/me", { token: accessToken });
      setUser(profile);
      setAuthError(null);
    } catch (error) {
      if (error instanceof ApiError && error.status === 401) {
        clearSession();
        await clerk.signOut();
      }
    }
  }, [accessToken, clearSession, clerk]);

  const updateProfile = useCallback(
    async (payload: { full_name?: string; phone?: string }) => {
      if (!accessToken) {
        throw new ApiError(401, "Login required");
      }
      const updatedUser = await apiRequest<AuthUser>("/api/v1/users/me", {
        method: "PATCH",
        token: accessToken,
        body: payload,
      });
      setUser(updatedUser);
    },
    [accessToken]
  );

  const loading = !clerkAuth.isLoaded || internalLoading;
  const isAuthenticated = Boolean(clerkAuth.isSignedIn) && !!accessToken && !!user;

  const value = useMemo<AuthContextValue>(
    () => ({
      user,
      isAuthenticated,
      loading,
      accessToken,
      authError,
      logout,
      refreshUser,
      updateProfile,
    }),
    [user, isAuthenticated, loading, accessToken, authError, logout, refreshUser, updateProfile]
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth() {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error("useAuth must be used within AuthProvider");
  }
  return context;
}

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
const AUTH_REQUEST_TIMEOUT_MS = 12000;

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
  } else {
    window.localStorage.removeItem(CLERK_USER_ID_KEY);
  }
  window.dispatchEvent(new Event("auth-changed"));
}

async function withTimeout<T>(promise: Promise<T>, timeoutMs: number, message: string): Promise<T> {
  let timeoutId: number | undefined;
  const timeoutPromise = new Promise<T>((_, reject) => {
    timeoutId = window.setTimeout(() => {
      reject(new ApiError(408, message));
    }, timeoutMs);
  });

  try {
    return await Promise.race([promise, timeoutPromise]);
  } finally {
    if (timeoutId) {
      window.clearTimeout(timeoutId);
    }
  }
}

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const clerkAuth = useClerkAuth();
  const clerk = useClerk();
  const {
    isLoaded: clerkLoaded,
    isSignedIn: clerkSignedIn,
    userId: clerkUserId,
    getToken: getClerkToken,
  } = clerkAuth;

  const [user, setUser] = useState<AuthUser | null>(null);
  const [accessToken, setAccessToken] = useState<string | null>(null);
  const [internalLoading, setInternalLoading] = useState(true);
  const [authError, setAuthError] = useState<string | null>(null);

  // Track the last Clerk identity we processed so account switching is handled.
  const lastProcessedIdentity = useRef<string | undefined>(undefined);
  const bootstrapDone = useRef(false);

  const clearSession = useCallback(() => {
    setUser(null);
    setAccessToken(null);
    persistTokens(null);
  }, []);

  // Fast bootstrap from stored backend token so UI is not blocked by Clerk loading.
  useEffect(() => {
    let cancelled = false;

    const bootstrap = async () => {
      const stored = readStoredTokens();
      if (!stored.accessToken) {
        bootstrapDone.current = true;
        setInternalLoading(false);
        return;
      }

      try {
        const profile = await withTimeout(
          apiRequest<AuthUser>("/api/v1/auth/me", {
            token: stored.accessToken,
          }),
          AUTH_REQUEST_TIMEOUT_MS,
          "Authentication is taking too long. Please refresh and try again."
        );
        if (cancelled) return;
        setUser(profile);
        setAccessToken(stored.accessToken);
        setAuthError(null);
      } catch {
        if (cancelled) return;
        clearSession();
      } finally {
        if (cancelled) return;
        bootstrapDone.current = true;
        setInternalLoading(false);
      }
    };

    bootstrap();
    return () => {
      cancelled = true;
    };
  }, [clearSession]);

  // React to Clerk auth state changes (sign-in / sign-out)
  useEffect(() => {
    if (!clerkLoaded) return;

    const identity = clerkSignedIn
      ? `signed-in:${clerkUserId ?? "unknown"}`
      : "signed-out";
    if (lastProcessedIdentity.current === identity) return;
    lastProcessedIdentity.current = identity;

    const run = async () => {
      if (!bootstrapDone.current || (!user && !accessToken)) {
        setInternalLoading(true);
      }
      setAuthError(null);

      try {
        if (!clerkSignedIn) {
          clearSession();
          return;
        }

        if (!clerkUserId) {
          clearSession();
          return;
        }

        // Try stored backend token first (avoids a round-trip on page reload),
        // but only if it belongs to the same Clerk user.
        const stored = readStoredTokens();
        const storedClerkUserId = isBrowser()
          ? window.localStorage.getItem(CLERK_USER_ID_KEY)
          : null;
        if (stored.accessToken && storedClerkUserId === clerkUserId) {
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
        const clerkToken = await withTimeout(
          getClerkToken(),
          AUTH_REQUEST_TIMEOUT_MS,
          "Clerk is taking too long to respond. Please try again."
        );
        if (!clerkToken) {
          clearSession();
          return;
        }

        const tokens = await withTimeout(
          apiRequest<TokenResponse>("/api/v1/auth/clerk-exchange", {
            method: "POST",
            body: { session_token: clerkToken },
          }),
          AUTH_REQUEST_TIMEOUT_MS,
          "Sign-in verification timed out. Please try again."
        );

        setAccessToken(tokens.access_token);
        persistTokens({
          accessToken: tokens.access_token,
          refreshToken: tokens.refresh_token,
          clerkUserId,
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
  }, [clerkLoaded, clerkSignedIn, clerkUserId, getClerkToken, clearSession, user, accessToken]);

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

  const loading = internalLoading;
  const isAuthenticated = !!accessToken && !!user;

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

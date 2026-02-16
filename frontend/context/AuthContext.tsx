"use client";

import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
} from "react";
import { ApiError, apiRequest } from "@/lib/api-client";

const ACCESS_TOKEN_KEY = "kabul_access_token";
const REFRESH_TOKEN_KEY = "kabul_refresh_token";

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

interface RegisterPayload {
  email: string;
  password: string;
  fullName: string;
  phone?: string;
}

interface AuthContextValue {
  user: AuthUser | null;
  isAuthenticated: boolean;
  loading: boolean;
  accessToken: string | null;
  authError: string | null;
  login: (email: string, password: string) => Promise<void>;
  register: (payload: RegisterPayload) => Promise<void>;
  logout: () => Promise<void>;
  refreshUser: () => Promise<void>;
  requestPasswordReset: (email: string) => Promise<string>;
  resetPassword: (payload: { token: string; newPassword: string }) => Promise<string>;
  updateProfile: (payload: { full_name?: string; phone?: string }) => Promise<void>;
  changePassword: (payload: { current_password: string; new_password: string }) => Promise<void>;
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

function persistTokens(tokens: { accessToken: string; refreshToken: string } | null) {
  if (!isBrowser()) {
    return;
  }

  if (!tokens) {
    window.localStorage.removeItem(ACCESS_TOKEN_KEY);
    window.localStorage.removeItem(REFRESH_TOKEN_KEY);
    window.dispatchEvent(new Event("auth-changed"));
    return;
  }

  window.localStorage.setItem(ACCESS_TOKEN_KEY, tokens.accessToken);
  window.localStorage.setItem(REFRESH_TOKEN_KEY, tokens.refreshToken);
  window.dispatchEvent(new Event("auth-changed"));
}

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [user, setUser] = useState<AuthUser | null>(null);
  const [accessToken, setAccessToken] = useState<string | null>(null);
  const [refreshToken, setRefreshToken] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [authError, setAuthError] = useState<string | null>(null);

  const clearSession = useCallback(() => {
    setUser(null);
    setAccessToken(null);
    setRefreshToken(null);
    persistTokens(null);
  }, []);

  const fetchUserWithToken = useCallback(
    async (token: string) => {
      const profile = await apiRequest<AuthUser>("/api/v1/auth/me", { token });
      setUser(profile);
      return profile;
    },
    []
  );

  const refreshWithRefreshToken = useCallback(async () => {
    if (!refreshToken) {
      return null;
    }

    try {
      const nextTokens = await apiRequest<TokenResponse>("/api/v1/auth/refresh", {
        method: "POST",
        body: { refresh_token: refreshToken },
      });
      setAccessToken(nextTokens.access_token);
      setRefreshToken(nextTokens.refresh_token);
      persistTokens({
        accessToken: nextTokens.access_token,
        refreshToken: nextTokens.refresh_token,
      });
      return nextTokens.access_token;
    } catch {
      clearSession();
      return null;
    }
  }, [clearSession, refreshToken]);

  const refreshUser = useCallback(async () => {
    if (!accessToken) {
      setUser(null);
      return;
    }

    try {
      await fetchUserWithToken(accessToken);
      setAuthError(null);
    } catch (error) {
      if (error instanceof ApiError && error.status === 401) {
        const refreshedToken = await refreshWithRefreshToken();
        if (refreshedToken) {
          await fetchUserWithToken(refreshedToken);
          setAuthError(null);
          return;
        }
      }
      clearSession();
      setAuthError("Your session has expired. Please log in again.");
    }
  }, [accessToken, clearSession, fetchUserWithToken, refreshWithRefreshToken]);

  useEffect(() => {
    const stored = readStoredTokens();
    setAccessToken(stored.accessToken);
    setRefreshToken(stored.refreshToken);

    if (!stored.accessToken) {
      setLoading(false);
      return;
    }

    fetchUserWithToken(stored.accessToken)
      .catch(async (error) => {
        if (error instanceof ApiError && error.status === 401 && stored.refreshToken) {
          try {
            const nextTokens = await apiRequest<TokenResponse>("/api/v1/auth/refresh", {
              method: "POST",
              body: { refresh_token: stored.refreshToken },
            });
            setAccessToken(nextTokens.access_token);
            setRefreshToken(nextTokens.refresh_token);
            persistTokens({
              accessToken: nextTokens.access_token,
              refreshToken: nextTokens.refresh_token,
            });
            await fetchUserWithToken(nextTokens.access_token);
            return;
          } catch {
            clearSession();
          }
        } else {
          clearSession();
        }
      })
      .finally(() => {
        setLoading(false);
      });
  }, [clearSession, fetchUserWithToken]);

  const login = useCallback(
    async (email: string, password: string) => {
      setAuthError(null);
      const tokens = await apiRequest<TokenResponse>("/api/v1/auth/login", {
        method: "POST",
        body: { email, password },
      });

      setAccessToken(tokens.access_token);
      setRefreshToken(tokens.refresh_token);
      persistTokens({
        accessToken: tokens.access_token,
        refreshToken: tokens.refresh_token,
      });
      await fetchUserWithToken(tokens.access_token);
    },
    [fetchUserWithToken]
  );

  const register = useCallback(
    async (payload: RegisterPayload) => {
      setAuthError(null);
      await apiRequest<AuthUser>("/api/v1/auth/register", {
        method: "POST",
        body: {
          email: payload.email,
          password: payload.password,
          full_name: payload.fullName,
          phone: payload.phone || null,
        },
      });
      await login(payload.email, payload.password);
    },
    [login]
  );

  const logout = useCallback(async () => {
    try {
      if (accessToken) {
        await apiRequest<{ message: string }>("/api/v1/auth/logout", {
          method: "POST",
          token: accessToken,
        });
      }
    } catch {
      // Ignore logout transport failures and clear session anyway.
    } finally {
      clearSession();
    }
  }, [accessToken, clearSession]);

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

  const changePassword = useCallback(
    async (payload: { current_password: string; new_password: string }) => {
      if (!accessToken) {
        throw new ApiError(401, "Login required");
      }
      await apiRequest<{ message: string }>("/api/v1/users/me/change-password", {
        method: "POST",
        token: accessToken,
        body: payload,
      });
    },
    [accessToken]
  );

  const requestPasswordReset = useCallback(async (email: string) => {
    const response = await apiRequest<{ message: string }>("/api/v1/auth/forgot-password", {
      method: "POST",
      body: { email },
    });
    return response.message;
  }, []);

  const resetPassword = useCallback(
    async (payload: { token: string; newPassword: string }) => {
      const response = await apiRequest<{ message: string }>("/api/v1/auth/reset-password", {
        method: "POST",
        body: {
          token: payload.token,
          new_password: payload.newPassword,
        },
      });
      return response.message;
    },
    []
  );

  const value = useMemo<AuthContextValue>(
    () => ({
      user,
      isAuthenticated: Boolean(user && accessToken),
      loading,
      accessToken,
      authError,
      login,
      register,
      logout,
      refreshUser,
      requestPasswordReset,
      resetPassword,
      updateProfile,
      changePassword,
    }),
    [
      user,
      accessToken,
      loading,
      authError,
      login,
      register,
      logout,
      refreshUser,
      requestPasswordReset,
      resetPassword,
      updateProfile,
      changePassword,
    ]
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

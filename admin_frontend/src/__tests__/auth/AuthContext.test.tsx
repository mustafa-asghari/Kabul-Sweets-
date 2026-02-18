import { describe, it, expect, vi } from 'vitest';
import { renderHook, waitFor, act } from '@testing-library/react';
import React from 'react';
import { AuthProvider, useAuth } from '@/contexts/auth/AuthContext';

// Mock next/navigation
vi.mock('next/navigation', () => ({
  useRouter: () => ({
    push: vi.fn(),
    replace: vi.fn(),
    prefetch: vi.fn(),
  }),
  usePathname: () => '/dashboard/ecommerce',
}));

const wrapper = ({ children }: { children: React.ReactNode }) => (
  <AuthProvider>{children}</AuthProvider>
);

describe('AuthContext', () => {
  it('provides auth state', async () => {
    const { result } = renderHook(() => useAuth(), { wrapper });

    // Initially loading
    expect(result.current.isLoading).toBe(true);

    await waitFor(() => {
      expect(result.current.isLoading).toBe(false);
    });

    // After loading, should have user from /api/auth/me mock
    expect(result.current.isAuthenticated).toBe(true);
    expect(result.current.user?.email).toBe('admin@kabulsweets.com.au');
  });

  it('login succeeds with correct credentials', async () => {
    const { result } = renderHook(() => useAuth(), { wrapper });

    await waitFor(() => {
      expect(result.current.isLoading).toBe(false);
    });

    let loginResult: { success: boolean; error?: string };
    await act(async () => {
      loginResult = await result.current.login('admin@kabulsweets.com.au', 'Admin@2024!');
    });

    expect(loginResult!.success).toBe(true);
  });

  it('login fails with wrong credentials', async () => {
    const { result } = renderHook(() => useAuth(), { wrapper });

    await waitFor(() => {
      expect(result.current.isLoading).toBe(false);
    });

    let loginResult: { success: boolean; error?: string };
    await act(async () => {
      loginResult = await result.current.login('wrong@example.com', 'wrong');
    });

    expect(loginResult!.success).toBe(false);
    expect(loginResult!.error).toBeTruthy();
  });

  it('logout clears user state', async () => {
    const { result } = renderHook(() => useAuth(), { wrapper });

    await waitFor(() => {
      expect(result.current.isLoading).toBe(false);
    });

    await act(async () => {
      await result.current.logout();
    });

    expect(result.current.user).toBeNull();
    expect(result.current.isAuthenticated).toBe(false);
  });

  it('throws error when useAuth is used outside provider', () => {
    expect(() => {
      renderHook(() => useAuth());
    }).toThrow('useAuth must be used within an AuthProvider');
  });
});

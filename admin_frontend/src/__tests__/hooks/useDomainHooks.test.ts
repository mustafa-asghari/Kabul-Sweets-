import { describe, it, expect } from 'vitest';
import { renderHook, waitFor } from '@testing-library/react';
import {
  useProducts,
  useOrders,
  useUsers,
  useDashboardSummary,
  useDailyRevenue,
  useBestSellers,
  useInventoryTurnover,
  useCustomCakes,
} from '@/lib/hooks/useApi';
import {
  mockProducts,
  mockOrders,
  mockUsers,
  mockDashboardSummary,
  mockDailyRevenue,
  mockBestSellers,
  mockInventory,
  mockCustomCakes,
} from '../fixtures';

describe('useProducts', () => {
  it('fetches products list', async () => {
    const { result } = renderHook(() => useProducts());
    await waitFor(() => expect(result.current.loading).toBe(false));
    expect(result.current.data?.data).toEqual(mockProducts);
  });
});

describe('useOrders', () => {
  it('fetches orders list', async () => {
    const { result } = renderHook(() => useOrders());
    await waitFor(() => expect(result.current.loading).toBe(false));
    expect(result.current.data?.data).toEqual(mockOrders);
  });
});

describe('useUsers', () => {
  it('fetches users list', async () => {
    const { result } = renderHook(() => useUsers());
    await waitFor(() => expect(result.current.loading).toBe(false));
    expect(result.current.data?.data).toEqual(mockUsers);
  });
});

describe('useDashboardSummary', () => {
  it('fetches dashboard summary', async () => {
    const { result } = renderHook(() => useDashboardSummary());
    await waitFor(() => expect(result.current.loading).toBe(false));
    expect(result.current.data?.data).toEqual(mockDashboardSummary);
  });
});

describe('useDailyRevenue', () => {
  it('fetches daily revenue', async () => {
    const { result } = renderHook(() => useDailyRevenue());
    await waitFor(() => expect(result.current.loading).toBe(false));
    expect(result.current.data?.data).toEqual(mockDailyRevenue);
  });
});

describe('useBestSellers', () => {
  it('fetches best sellers', async () => {
    const { result } = renderHook(() => useBestSellers());
    await waitFor(() => expect(result.current.loading).toBe(false));
    expect(result.current.data?.data).toEqual(mockBestSellers);
  });
});

describe('useInventoryTurnover', () => {
  it('fetches inventory turnover', async () => {
    const { result } = renderHook(() => useInventoryTurnover());
    await waitFor(() => expect(result.current.loading).toBe(false));
    expect(result.current.data?.data).toEqual(mockInventory);
  });
});

describe('useCustomCakes', () => {
  it('fetches custom cakes', async () => {
    const { result } = renderHook(() => useCustomCakes());
    await waitFor(() => expect(result.current.loading).toBe(false));
    expect(result.current.data?.data).toEqual(mockCustomCakes);
  });
});

'use client';

import { useCallback, useEffect, useState } from 'react';
import type { IApiResponse } from '@/types/api-response';
import type { ProductListItem, Product } from '@/types/products';
import type { OrderListItem, Order } from '@/types/order';
import type { UserResponse } from '@/types/user';
import type {
  DashboardSummary,
  DailyRevenue,
  BestSeller,
  InventoryTurnover,
  VisitorAnalytics,
  PopularCakeSize,
  CartRecoveryAnalytics,
  ProductPageView,
  WeeklyOrderStatusMix,
} from '@/types/analytics';
import type { CustomCake } from '@/types/custom-cake';

export type ApiResponse<T> = IApiResponse<T>;

interface UseApiGetOptions {
  enabled?: boolean;
}

// Generic hook for GET requests with proper loading/error/refetch
export function useApiGet<T>(
  endpoint: string | null | undefined,
  options: UseApiGetOptions = {},
) {
  const { enabled = true } = options;
  const shouldFetch = Boolean(endpoint) && enabled;
  const [data, setData] = useState<ApiResponse<T> | null>(null);
  const [loading, setLoading] = useState(shouldFetch);
  const [error, setError] = useState<Error | null>(null);

  const refetch = useCallback(async () => {
    if (!shouldFetch || !endpoint) {
      setLoading(false);
      setError(null);
      setData(null);
      return;
    }

    setLoading(true);
    setError(null);
    try {
      const res = await fetch(endpoint, {
        credentials: 'include',
        cache: 'no-store',
      });
      const json = await res.json();

      if (
        res.status === 401 &&
        typeof window !== 'undefined' &&
        !window.location.pathname.startsWith('/auth/')
      ) {
        const callbackUrl = encodeURIComponent(window.location.pathname);
        window.location.href = `/auth/signin?callbackUrl=${callbackUrl}`;
        return;
      }

      setData(json);

      if (!res.ok) {
        const message =
          (json && typeof json === 'object' && 'message' in json
            ? String((json as { message?: unknown }).message)
            : '') || `Request failed with status ${res.status}`;
        setError(new Error(message));
      }
    } catch (err) {
      setError(err instanceof Error ? err : new Error('Fetch failed'));
    } finally {
      setLoading(false);
    }
  }, [endpoint, shouldFetch]);

  useEffect(() => {
    if (!shouldFetch) {
      setLoading(false);
      setError(null);
      setData(null);
      return;
    }

    refetch();
  }, [refetch, shouldFetch]);

  return { data, loading, error, refetch };
}

// Mutation helpers
export async function apiPost<T>(
  endpoint: string,
  body: unknown,
): Promise<ApiResponse<T>> {
  const res = await fetch(endpoint, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
    credentials: 'include',
  });
  return res.json();
}


export async function apiPostFormData<T>(
  endpoint: string,
  formData: FormData
): Promise<ApiResponse<T>> {
  const res = await fetch(endpoint, {
    method: 'POST',
    body: formData,
    credentials: 'include',
  });
  return res.json();
}

export async function apiPatch<T>(
  endpoint: string,
  body: unknown,
): Promise<ApiResponse<T>> {
  const res = await fetch(endpoint, {
    method: 'PATCH',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
    credentials: 'include',
  });
  return res.json();
}

export async function apiDelete<T>(endpoint: string): Promise<ApiResponse<T>> {
  const res = await fetch(endpoint, {
    method: 'DELETE',
    credentials: 'include',
  });
  return res.json();
}

export async function apiGetBlob(endpoint: string): Promise<Blob> {
  const res = await fetch(endpoint, {
    credentials: 'include',
  });
  if (!res.ok) throw new Error(`Failed to fetch blob: ${res.statusText}`);
  return res.blob();
}

// Products
export function useProducts(params?: string) {
  const query = params ? `?${params}` : '';
  return useApiGet<ProductListItem[]>(`/api/products${query}`);
}

export function useProduct(id?: string | null) {
  return useApiGet<Product>(id ? `/api/products/${id}` : null);
}

// Orders
export function useOrders(params?: string) {
  const query = params ? `?${params}` : '';
  return useApiGet<OrderListItem[]>(`/api/orders${query}`);
}

export function useOrder(id?: string | null) {
  return useApiGet<Order>(id ? `/api/orders/${id}` : null);
}

// Users
export function useUsers(params?: string) {
  const query = params ? `?${params}` : '';
  return useApiGet<UserResponse[]>(`/api/customers${query}`);
}

export function useProfile() {
  return useApiGet<UserResponse>('/api/auth/me');
}

// Analytics
export function useDashboardSummary() {
  return useApiGet<DashboardSummary>('/api/analytics/dashboard');
}

export function useDailyRevenue(params?: string) {
  const query = params ? `?${params}` : '';
  return useApiGet<DailyRevenue[]>(`/api/analytics/revenue${query}`);
}

export function useBestSellers(params?: string) {
  const query = params ? `?${params}` : '';
  return useApiGet<BestSeller[]>(`/api/analytics/best-sellers${query}`);
}

export function useWorstSellers(params?: string) {
  const query = params ? `?${params}` : '';
  return useApiGet<BestSeller[]>(`/api/analytics/worst-sellers${query}`);
}

export function usePopularCakeSizes(params?: string) {
  const query = params ? `?${params}` : '';
  return useApiGet<PopularCakeSize[]>(
    `/api/analytics/popular-cake-sizes${query}`,
  );
}

export function useInventoryTurnover(params?: string) {
  const query = params ? `?${params}` : '';
  return useApiGet<InventoryTurnover[]>(
    `/api/analytics/inventory-turnover${query}`,
  );
}

export function useVisitorAnalytics(params?: string) {
  const query = params ? `?${params}` : '';
  return useApiGet<VisitorAnalytics>(`/api/analytics/visitors${query}`);
}

export function useCartRecoveryAnalytics(params?: string) {
  const query = params ? `?${params}` : '';
  return useApiGet<CartRecoveryAnalytics>(
    `/api/analytics/cart-recovery${query}`,
  );
}

export function useProductPageViews(params?: string) {
  const query = params ? `?${params}` : '';
  return useApiGet<ProductPageView[]>(`/api/analytics/product-page-views${query}`);
}

export function useOrdersStatusMix() {
  return useApiGet<WeeklyOrderStatusMix>('/api/analytics/orders-status-mix');
}

// Custom Cakes
export function useCustomCakes(params?: string) {
  const query = params ? `?${params}` : '';
  return useApiGet<CustomCake[]>(`/api/custom-cakes${query}`);
}

export function useCustomCake(id?: string | null) {
  return useApiGet<CustomCake>(id ? `/api/custom-cakes/${id}` : null);
}

import { describe, it, expect, vi } from 'vitest';
import { renderHook, waitFor } from '@testing-library/react';
import { useApiGet, apiPost, apiPatch, apiDelete } from '@/lib/hooks/useApi';
import { mockProducts, wrapApiResponse } from '../fixtures';

describe('useApiGet', () => {
  it('fetches data and returns it', async () => {
    const { result } = renderHook(() => useApiGet('/api/products'));

    expect(result.current.loading).toBe(true);

    await waitFor(() => {
      expect(result.current.loading).toBe(false);
    });

    expect(result.current.data?.succeeded).toBe(true);
    expect(result.current.data?.data).toEqual(mockProducts);
    expect(result.current.error).toBeNull();
  });

  it('handles fetch errors', async () => {
    const { result } = renderHook(() => useApiGet('/api/nonexistent'));

    await waitFor(() => {
      expect(result.current.loading).toBe(false);
    });

    // MSW will warn about unhandled request; the hook should handle gracefully
  });

  it('supports refetch', async () => {
    const { result } = renderHook(() => useApiGet('/api/products'));

    await waitFor(() => {
      expect(result.current.loading).toBe(false);
    });

    // Trigger refetch
    result.current.refetch();

    await waitFor(() => {
      expect(result.current.data?.succeeded).toBe(true);
    });
  });
});

describe('apiPost', () => {
  it('sends POST request and returns response', async () => {
    const newProduct = { name: 'New Cake', category: 'cake', base_price: 50 };
    const result = await apiPost('/api/products', newProduct);

    expect(result.succeeded).toBe(true);
    expect(result.data).toMatchObject({ name: 'New Cake' });
  });
});

describe('apiPatch', () => {
  it('sends PATCH request', async () => {
    // Since we don't have a PATCH handler in MSW, this tests the function structure
    const mockFetch = vi.spyOn(global, 'fetch').mockResolvedValueOnce({
      json: () => Promise.resolve(wrapApiResponse({ id: 'prod-1', name: 'Updated' })),
    } as Response);

    const result = await apiPatch('/api/products/prod-1', { name: 'Updated' });
    expect(result.succeeded).toBe(true);

    mockFetch.mockRestore();
  });
});

describe('apiDelete', () => {
  it('sends DELETE request', async () => {
    const mockFetch = vi.spyOn(global, 'fetch').mockResolvedValueOnce({
      json: () => Promise.resolve(wrapApiResponse(null)),
    } as Response);

    const result = await apiDelete('/api/products/prod-1');
    expect(result.succeeded).toBe(true);

    mockFetch.mockRestore();
  });
});

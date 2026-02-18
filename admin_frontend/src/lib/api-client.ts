import { cookies } from 'next/headers';
import { IApiResponse } from '@/types/api-response';

const API_URL = process.env.API_URL || 'http://localhost:8000/api/v1';
const IS_PRODUCTION = process.env.NODE_ENV === 'production';
const ACCESS_TOKEN_MAX_AGE = 60 * 30; // 30 minutes
const REFRESH_TOKEN_MAX_AGE = 60 * 60 * 24 * 7; // 7 days

interface FetchOptions extends Omit<RequestInit, 'headers'> {
  headers?: Record<string, string>;
}

function extractDetail(detail: unknown): string {
  if (Array.isArray(detail)) {
    return detail
      .map((item) => {
        if (typeof item === 'string') return item;
        if (item && typeof item === 'object' && 'msg' in item) {
          return String((item as { msg: unknown }).msg);
        }
        return JSON.stringify(item);
      })
      .join('; ');
  }

  if (typeof detail === 'string') return detail;
  if (detail && typeof detail === 'object') return JSON.stringify(detail);
  return '';
}

async function refreshAccessToken(
  cookieStore: Awaited<ReturnType<typeof cookies>>
): Promise<string | null> {
  const refreshToken = cookieStore.get('refresh_token')?.value;

  if (!refreshToken) return null;

  try {
    const res = await fetch(`${API_URL}/auth/refresh`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ refresh_token: refreshToken }),
    });

    if (!res.ok) {
      cookieStore.delete('access_token');
      cookieStore.delete('refresh_token');
      return null;
    }

    const data = await res.json();
    if (!data?.access_token || !data?.refresh_token) return null;

    cookieStore.set('access_token', data.access_token, {
      httpOnly: true,
      secure: IS_PRODUCTION,
      sameSite: 'lax',
      path: '/',
      maxAge: ACCESS_TOKEN_MAX_AGE,
    });

    cookieStore.set('refresh_token', data.refresh_token, {
      httpOnly: true,
      secure: IS_PRODUCTION,
      sameSite: 'lax',
      path: '/',
      maxAge: REFRESH_TOKEN_MAX_AGE,
    });

    return data.access_token;
  } catch {
    return null;
  }
}

export async function apiClient<T>(
  endpoint: string,
  options: FetchOptions = {}
): Promise<IApiResponse<T>> {
  const cookieStore = await cookies();
  const accessToken = cookieStore.get('access_token')?.value;

  const headers: Record<string, string> = {
    'Content-Type': 'application/json',
    ...options.headers,
  };

  if (accessToken) {
    headers['Authorization'] = `Bearer ${accessToken}`;
  }

  const url = endpoint.startsWith('http') ? endpoint : `${API_URL}${endpoint}`;

  try {
    let res = await fetch(url, { ...options, headers });

    // If 401 and we have a refresh token, try refreshing
    if (res.status === 401) {
      const newToken = await refreshAccessToken(cookieStore);
      if (newToken) {
        headers['Authorization'] = `Bearer ${newToken}`;
        res = await fetch(url, { ...options, headers });
      }
    }

    if (!res.ok) {
      const errorBody = await res.json().catch(() => ({}));
      const detail = extractDetail(errorBody.detail ?? errorBody.message);
      return {
        succeeded: false,
        message: detail || `Request failed with status ${res.status}`,
        statusCode: res.status,
        timestamp: new Date().toISOString(),
        errors: [{ message: detail || res.statusText }],
      };
    }

    const data = await res.json();

    return {
      succeeded: true,
      message: 'Success',
      statusCode: res.status,
      timestamp: new Date().toISOString(),
      data: data as T,
    };
  } catch (error) {
    return {
      succeeded: false,
      message: error instanceof Error ? error.message : 'Network error',
      statusCode: 503,
      timestamp: new Date().toISOString(),
      errors: [{ message: error instanceof Error ? error.message : 'Network error' }],
    };
  }
}

export async function apiUpload<T>(
  endpoint: string,
  formData: FormData
): Promise<IApiResponse<T>> {
  const cookieStore = await cookies();
  const accessToken = cookieStore.get('access_token')?.value;

  const headers: Record<string, string> = {};
  if (accessToken) {
    headers['Authorization'] = `Bearer ${accessToken}`;
  }

  const url = endpoint.startsWith('http') ? endpoint : `${API_URL}${endpoint}`;

  try {
    const res = await fetch(url, {
      method: 'POST',
      headers,
      body: formData,
    });

    if (!res.ok) {
      const errorBody = await res.json().catch(() => ({}));
      const detail = extractDetail(errorBody.detail);
      return {
        succeeded: false,
        message: detail || `Upload failed with status ${res.status}`,
        statusCode: res.status,
        timestamp: new Date().toISOString(),
        errors: [{ message: detail || res.statusText }],
      };
    }

    const data = await res.json();
    return {
      succeeded: true,
      message: 'Success',
      statusCode: res.status,
      timestamp: new Date().toISOString(),
      data: data as T,
    };
  } catch (error) {
    return {
      succeeded: false,
      message: error instanceof Error ? error.message : 'Network error',
      statusCode: 503,
      timestamp: new Date().toISOString(),
      errors: [{ message: error instanceof Error ? error.message : 'Network error' }],
    };
  }
}

import { NextRequest, NextResponse } from 'next/server';

const API_URL = process.env.API_URL || 'http://localhost:8000/api/v1';
const IS_PRODUCTION = process.env.NODE_ENV === 'production';
const ACCESS_TOKEN_MAX_AGE = 60 * 30; // 30 minutes
const REFRESH_TOKEN_MAX_AGE = 60 * 60 * 24 * 7; // 7 days

type RefreshedTokens = {
  access_token: string;
  refresh_token: string;
};

async function fetchCurrentUser(accessToken: string) {
  return fetch(`${API_URL}/auth/me`, {
    headers: {
      Authorization: `Bearer ${accessToken}`,
    },
  });
}

async function patchCurrentUser(accessToken: string, updates: unknown) {
  return fetch(`${API_URL}/users/me`, {
    method: 'PATCH',
    headers: {
      Authorization: `Bearer ${accessToken}`,
      'Content-Type': 'application/json',
    },
    body: JSON.stringify(updates),
  });
}

async function refreshTokens(refreshToken: string): Promise<RefreshedTokens | null> {
  const refreshRes = await fetch(`${API_URL}/auth/refresh`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ refresh_token: refreshToken }),
  });

  if (!refreshRes.ok) return null;
  const refreshed = await refreshRes.json();
  if (!refreshed?.access_token || !refreshed?.refresh_token) return null;
  return refreshed as RefreshedTokens;
}

function applyAuthCookies(response: NextResponse, tokens: RefreshedTokens) {
  response.cookies.set('access_token', tokens.access_token, {
    httpOnly: true,
    secure: IS_PRODUCTION,
    sameSite: 'lax',
    path: '/',
    maxAge: ACCESS_TOKEN_MAX_AGE,
  });

  response.cookies.set('refresh_token', tokens.refresh_token, {
    httpOnly: true,
    secure: IS_PRODUCTION,
    sameSite: 'lax',
    path: '/',
    maxAge: REFRESH_TOKEN_MAX_AGE,
  });
}

function clearAuthCookies(response: NextResponse) {
  response.cookies.delete('access_token');
  response.cookies.delete('refresh_token');
}

export async function GET(request: NextRequest) {
  const accessToken = request.cookies.get('access_token')?.value;
  const refreshToken = request.cookies.get('refresh_token')?.value;

  try {
    let activeAccessToken = accessToken;
    let refreshedTokens: RefreshedTokens | null = null;

    if (!activeAccessToken && refreshToken) {
      refreshedTokens = await refreshTokens(refreshToken);
      activeAccessToken = refreshedTokens?.access_token;
    }

    if (!activeAccessToken) {
      const response = NextResponse.json(
        {
          succeeded: false,
          message: 'Not authenticated',
          timestamp: new Date().toISOString(),
          errors: [{ message: 'No access token' }],
        },
        { status: 401 }
      );
      clearAuthCookies(response);
      return response;
    }

    let res = await fetchCurrentUser(activeAccessToken);

    // Access token may be expired but refresh token is still valid
    if (res.status === 401 && refreshToken) {
      if (!refreshedTokens) {
        refreshedTokens = await refreshTokens(refreshToken);
      }

      if (refreshedTokens?.access_token) {
        activeAccessToken = refreshedTokens.access_token;
        res = await fetchCurrentUser(activeAccessToken);
      }
    }

    if (!res.ok) {
      const response = NextResponse.json(
        {
          succeeded: false,
          message: 'Failed to fetch user',
          timestamp: new Date().toISOString(),
          errors: [{ message: 'Authentication failed' }],
        },
        { status: res.status }
      );
      if (res.status === 401) clearAuthCookies(response);
      return response;
    }

    const user = await res.json();

    const response = NextResponse.json({
      succeeded: true,
      message: 'User retrieved',
      timestamp: new Date().toISOString(),
      data: user,
    });

    if (refreshedTokens) {
      applyAuthCookies(response, refreshedTokens);
    }

    return response;
  } catch {
    return NextResponse.json(
      {
        succeeded: false,
        message: 'Service unavailable',
        timestamp: new Date().toISOString(),
        errors: [{ message: 'Could not connect to user service' }],
      },
      { status: 503 }
    );
  }
}

export async function PATCH(request: NextRequest) {
  const accessToken = request.cookies.get('access_token')?.value;
  const refreshToken = request.cookies.get('refresh_token')?.value;

  let updates: unknown;
  try {
    updates = await request.json();
  } catch {
    return NextResponse.json(
      {
        succeeded: false,
        message: 'Invalid request payload',
        timestamp: new Date().toISOString(),
        errors: [{ message: 'Request body must be valid JSON' }],
      },
      { status: 400 }
    );
  }

  try {
    let activeAccessToken = accessToken;
    let refreshedTokens: RefreshedTokens | null = null;

    if (!activeAccessToken && refreshToken) {
      refreshedTokens = await refreshTokens(refreshToken);
      activeAccessToken = refreshedTokens?.access_token;
    }

    if (!activeAccessToken) {
      const response = NextResponse.json(
        {
          succeeded: false,
          message: 'Not authenticated',
          timestamp: new Date().toISOString(),
          errors: [{ message: 'No access token' }],
        },
        { status: 401 }
      );
      clearAuthCookies(response);
      return response;
    }

    let res = await patchCurrentUser(activeAccessToken, updates);

    if (res.status === 401 && refreshToken) {
      if (!refreshedTokens) {
        refreshedTokens = await refreshTokens(refreshToken);
      }

      if (refreshedTokens?.access_token) {
        activeAccessToken = refreshedTokens.access_token;
        res = await patchCurrentUser(activeAccessToken, updates);
      }
    }

    if (!res.ok) {
      const errorBody = await res.json().catch(() => ({}));
      const detail =
        typeof errorBody.detail === 'string'
          ? errorBody.detail
          : Array.isArray(errorBody.detail)
            ? errorBody.detail.map((item: { msg?: string }) => item.msg || JSON.stringify(item)).join('; ')
            : 'Failed to update user';

      const response = NextResponse.json(
        {
          succeeded: false,
          message: detail,
          timestamp: new Date().toISOString(),
          errors: [{ message: detail }],
        },
        { status: res.status }
      );
      if (res.status === 401) {
        clearAuthCookies(response);
      }
      return response;
    }

    const user = await res.json();
    const response = NextResponse.json({
      succeeded: true,
      message: 'Profile updated successfully',
      timestamp: new Date().toISOString(),
      data: user,
    });

    if (refreshedTokens) {
      applyAuthCookies(response, refreshedTokens);
    }

    return response;
  } catch {
    return NextResponse.json(
      {
        succeeded: false,
        message: 'Service unavailable',
        timestamp: new Date().toISOString(),
        errors: [{ message: 'Could not connect to user service' }],
      },
      { status: 503 }
    );
  }
}

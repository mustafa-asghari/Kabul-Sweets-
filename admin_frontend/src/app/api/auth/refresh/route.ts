import { NextRequest, NextResponse } from 'next/server';

const API_URL = process.env.API_URL || 'http://localhost:8000/api/v1';

export async function POST(request: NextRequest) {
  const refreshToken = request.cookies.get('refresh_token')?.value;

  if (!refreshToken) {
    return NextResponse.json(
      {
        succeeded: false,
        message: 'No refresh token',
        timestamp: new Date().toISOString(),
        errors: [{ message: 'Refresh token not found' }],
      },
      { status: 401 }
    );
  }

  try {
    const res = await fetch(`${API_URL}/auth/refresh`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ refresh_token: refreshToken }),
    });

    if (!res.ok) {
      const response = NextResponse.json(
        {
          succeeded: false,
          message: 'Token refresh failed',
          timestamp: new Date().toISOString(),
          errors: [{ message: 'Session expired, please login again' }],
        },
        { status: 401 }
      );
      response.cookies.delete('access_token');
      response.cookies.delete('refresh_token');
      return response;
    }

    const data = await res.json();

    const response = NextResponse.json({
      succeeded: true,
      message: 'Token refreshed',
      timestamp: new Date().toISOString(),
    });

    response.cookies.set('access_token', data.access_token, {
      httpOnly: true,
      secure: process.env.NODE_ENV === 'production',
      sameSite: 'lax',
      path: '/',
      maxAge: 60 * 30,
    });

    response.cookies.set('refresh_token', data.refresh_token, {
      httpOnly: true,
      secure: process.env.NODE_ENV === 'production',
      sameSite: 'lax',
      path: '/',
      maxAge: 60 * 60 * 24 * 7,
    });

    return response;
  } catch {
    return NextResponse.json(
      {
        succeeded: false,
        message: 'Refresh service unavailable',
        timestamp: new Date().toISOString(),
        errors: [{ message: 'Could not connect to authentication service' }],
      },
      { status: 503 }
    );
  }
}

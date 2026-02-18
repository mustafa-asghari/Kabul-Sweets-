import { NextRequest, NextResponse } from 'next/server';

const API_URL = process.env.API_URL || 'http://localhost:8000/api/v1';

export async function POST(request: NextRequest) {
  try {
    const body = await request.json();

    const res = await fetch(`${API_URL}/auth/login`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body),
    });

    const data = await res.json();

    if (!res.ok) {
      return NextResponse.json(
        {
          succeeded: false,
          message: data.detail || 'Invalid credentials',
          timestamp: new Date().toISOString(),
          errors: [{ message: data.detail || 'Login failed' }],
        },
        { status: res.status }
      );
    }

    const response = NextResponse.json({
      succeeded: true,
      message: 'Login successful',
      timestamp: new Date().toISOString(),
      data: { token_type: data.token_type },
    });

    // Set tokens as httpOnly cookies
    response.cookies.set('access_token', data.access_token, {
      httpOnly: true,
      secure: process.env.NODE_ENV === 'production',
      sameSite: 'lax',
      path: '/',
      maxAge: 60 * 30, // 30 minutes
    });

    response.cookies.set('refresh_token', data.refresh_token, {
      httpOnly: true,
      secure: process.env.NODE_ENV === 'production',
      sameSite: 'lax',
      path: '/',
      maxAge: 60 * 60 * 24 * 7, // 7 days
    });

    return response;
  } catch (error) {
    return NextResponse.json(
      {
        succeeded: false,
        message: 'Login service unavailable',
        timestamp: new Date().toISOString(),
        errors: [{ message: 'Could not connect to authentication service' }],
      },
      { status: 503 }
    );
  }
}

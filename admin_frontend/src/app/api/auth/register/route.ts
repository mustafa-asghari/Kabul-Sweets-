import { NextRequest, NextResponse } from 'next/server';

const API_URL = process.env.API_URL || 'http://localhost:8000/api/v1';

export async function POST(request: NextRequest) {
  try {
    const body = await request.json();

    const res = await fetch(`${API_URL}/auth/register`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body),
    });

    const data = await res.json();

    if (!res.ok) {
      const detail =
        typeof data.detail === 'string'
          ? data.detail
          : Array.isArray(data.detail)
            ? data.detail.map((d: { msg?: string }) => d.msg || JSON.stringify(d)).join('; ')
            : 'Registration failed';

      return NextResponse.json(
        {
          succeeded: false,
          message: detail,
          timestamp: new Date().toISOString(),
          errors: [{ message: detail }],
        },
        { status: res.status }
      );
    }

    return NextResponse.json({
      succeeded: true,
      message: 'Account created successfully',
      timestamp: new Date().toISOString(),
      data,
    });
  } catch {
    return NextResponse.json(
      {
        succeeded: false,
        message: 'Registration service unavailable',
        timestamp: new Date().toISOString(),
        errors: [{ message: 'Could not connect to registration service' }],
      },
      { status: 503 }
    );
  }
}

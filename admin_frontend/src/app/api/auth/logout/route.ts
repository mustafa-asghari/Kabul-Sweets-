import { NextRequest, NextResponse } from 'next/server';

const API_URL = process.env.API_URL || 'http://localhost:8000/api/v1';

export async function POST(request: NextRequest) {
  const accessToken = request.cookies.get('access_token')?.value;

  // Call backend logout to revoke refresh token
  if (accessToken) {
    try {
      await fetch(`${API_URL}/auth/logout`, {
        method: 'POST',
        headers: {
          Authorization: `Bearer ${accessToken}`,
        },
      });
    } catch {
      // Proceed with clearing cookies even if backend call fails
    }
  }

  const response = NextResponse.json({
    succeeded: true,
    message: 'Logged out successfully',
    timestamp: new Date().toISOString(),
  });

  response.cookies.delete('access_token');
  response.cookies.delete('refresh_token');

  return response;
}

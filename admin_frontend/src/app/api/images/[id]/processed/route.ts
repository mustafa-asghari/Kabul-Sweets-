import { cookies } from 'next/headers';
import { NextResponse } from 'next/server';

const API_URL = process.env.API_URL || 'http://localhost:8000/api/v1';

function buildErrorResponse(message: string, statusCode: number) {
  return NextResponse.json(
    {
      succeeded: false,
      message,
      statusCode,
      timestamp: new Date().toISOString(),
      errors: [{ message }],
    },
    { status: statusCode },
  );
}

export async function GET(
  _request: Request,
  { params }: { params: Promise<{ id: string }> },
) {
  const { id } = await params;
  const cookieStore = await cookies();
  const accessToken = cookieStore.get('access_token')?.value;

  const headers: Record<string, string> = {};
  if (accessToken) {
    headers.Authorization = `Bearer ${accessToken}`;
  }

  const response = await fetch(`${API_URL}/images/${id}/processed`, {
    headers,
    cache: 'no-store',
  });

  if (!response.ok) {
    const rawError = await response.text();
    let message = `Failed to fetch processed image (${response.status})`;

    if (rawError) {
      try {
        const parsed = JSON.parse(rawError) as { detail?: unknown };
        if (typeof parsed.detail === 'string') {
          message = parsed.detail;
        } else {
          message = rawError;
        }
      } catch {
        message = rawError;
      }
    }

    return buildErrorResponse(message, response.status);
  }

  const contentType =
    response.headers.get('content-type') || 'application/octet-stream';
  const payload = await response.arrayBuffer();

  return new NextResponse(payload, {
    status: 200,
    headers: {
      'Content-Type': contentType,
      'Cache-Control': 'no-store',
    },
  });
}

import { NextRequest, NextResponse } from 'next/server';
import { apiClient } from '@/lib/api-client';
import { normalizeCustomCake } from '../normalize';

export async function GET(
  _request: NextRequest,
  { params }: { params: Promise<{ id: string }> },
) {
  const { id } = await params;
  const result = await apiClient<unknown>(`/admin/custom-cakes/${id}`);

  const normalizedData =
    result.succeeded && result.data
      ? normalizeCustomCake(result.data as Record<string, unknown>)
      : result.data;

  return NextResponse.json(
    {
      ...result,
      data: normalizedData,
    },
    {
      status: result.succeeded ? 200 : 404,
    },
  );
}

export async function POST(
  request: NextRequest,
  { params }: { params: Promise<{ id: string }> },
) {
  const { id } = await params;
  const body = await request.json();
  const { action, ...rest } = body;

  let endpoint: string;
  if (action === 'approve') {
    endpoint = `/admin/custom-cakes/${id}/approve`;
  } else if (action === 'reject') {
    endpoint = `/admin/custom-cakes/${id}/reject`;
  } else if (action === 'production' || action === 'completed') {
    endpoint = `/admin/custom-cakes/${id}/status?action=${action}`;
  } else {
    return NextResponse.json(
      {
        succeeded: false,
        message: 'Invalid action',
        timestamp: new Date().toISOString(),
        errors: [
          {
            message: 'Action must be approve, reject, production, or completed',
          },
        ],
      },
      { status: 400 },
    );
  }

  const result = await apiClient(endpoint, {
    method: 'POST',
    body: JSON.stringify(rest),
  });

  return NextResponse.json(result, {
    status: result.succeeded ? 200 : 400,
  });
}

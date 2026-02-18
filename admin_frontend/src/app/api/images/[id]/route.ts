import { NextRequest, NextResponse } from 'next/server';
import { apiClient } from '@/lib/api-client';

export async function GET(
  request: NextRequest,
  { params }: { params: Promise<{ id: string }> }
) {
  const { id } = await params;
  const result = await apiClient(`/images/${id}`);

  return NextResponse.json(result, {
    status: result.succeeded ? 200 : 404,
  });
}

export async function POST(
  request: NextRequest,
  { params }: { params: Promise<{ id: string }> }
) {
  const { id } = await params;
  const body = await request.json();
  const { action, ...rest } = body;

  let endpoint: string;
  if (action === 'process') {
    endpoint = '/images/process';
  } else if (action === 'choose') {
    endpoint = '/images/choose';
  } else if (action === 'reject') {
    endpoint = '/images/reject';
  } else {
    return NextResponse.json(
      {
        succeeded: false,
        message: 'Invalid action',
        timestamp: new Date().toISOString(),
        errors: [{ message: 'Action must be process, choose, or reject' }],
      },
      { status: 400 }
    );
  }

  const result = await apiClient(endpoint, {
    method: 'POST',
    body: JSON.stringify({ image_id: id, ...rest }),
  });

  return NextResponse.json(result, {
    status: result.succeeded ? 200 : 400,
  });
}

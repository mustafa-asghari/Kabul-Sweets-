import { NextResponse } from 'next/server';
import { apiClient } from '@/lib/api-client';

export async function POST(
  request: Request,
  { params }: { params: Promise<{ id: string }> }
) {
  const { id } = await params;
  const url = new URL(request.url);
  let reason = url.searchParams.get('reason') ?? '';

  if (!reason) {
    const body = (await request.json().catch(() => ({}))) as { reason?: string };
    reason = (body.reason || '').trim();
  }

  if (!reason) {
    return NextResponse.json(
      {
        succeeded: false,
        message: 'Rejection reason is required',
        statusCode: 400,
        timestamp: new Date().toISOString(),
        errors: [{ message: 'Rejection reason is required' }],
      },
      { status: 400 }
    );
  }

  const result = await apiClient<{ message: string; detail?: string }>(
    `/payments/admin/orders/${id}/reject`,
    {
      method: 'POST',
      body: JSON.stringify({ reason }),
    }
  );

  return NextResponse.json(result, {
    status: result.succeeded ? 200 : result.statusCode ?? 400,
  });
}

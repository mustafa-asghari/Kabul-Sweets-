import { NextResponse } from 'next/server';
import { apiClient } from '@/lib/api-client';

export async function POST(
  request: Request,
  { params }: { params: Promise<{ id: string }> }
) {
  const { id } = await params;
  const body = (await request.json().catch(() => ({}))) as { reason?: string };
  const reason = (body.reason || '').trim();
  const payload = reason ? { reason } : {};

  const result = await apiClient<{ message: string; detail?: string }>(
    `/payments/admin/orders/${id}/approve`,
    {
      method: 'POST',
      body: JSON.stringify(payload),
    }
  );

  return NextResponse.json(result, {
    status: result.succeeded ? 200 : result.statusCode ?? 400,
  });
}

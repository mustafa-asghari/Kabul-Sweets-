import { NextResponse } from 'next/server';
import { apiClient } from '@/lib/api-client';

export async function POST(
  _request: Request,
  { params }: { params: Promise<{ id: string }> }
) {
  const { id } = await params;

  const result = await apiClient<{ message: string; detail?: string }>(
    `/payments/admin/orders/${id}/approve`,
    {
      method: 'POST',
      body: JSON.stringify({}),
    }
  );

  return NextResponse.json(result, {
    status: result.succeeded ? 200 : result.statusCode ?? 400,
  });
}

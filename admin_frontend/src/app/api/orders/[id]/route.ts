import { NextRequest, NextResponse } from 'next/server';
import { apiClient } from '@/lib/api-client';
import { Order } from '@/types/order';

export async function GET(
  request: NextRequest,
  { params }: { params: Promise<{ id: string }> }
) {
  const { id } = await params;
  const result = await apiClient<Order>(`/orders/${id}`);

  return NextResponse.json(result, {
    status: result.succeeded ? 200 : 404,
  });
}

export async function PATCH(
  request: NextRequest,
  { params }: { params: Promise<{ id: string }> }
) {
  const { id } = await params;
  const body = await request.json();

  const result = await apiClient<Order>(`/orders/${id}`, {
    method: 'PATCH',
    body: JSON.stringify(body),
  });

  return NextResponse.json(result, {
    status: result.succeeded ? 200 : 400,
  });
}

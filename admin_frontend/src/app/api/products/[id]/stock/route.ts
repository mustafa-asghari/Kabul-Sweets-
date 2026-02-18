import { NextRequest, NextResponse } from 'next/server';
import { apiClient } from '@/lib/api-client';
import { StockAdjustmentResponse } from '@/types/products';

export async function POST(
  request: NextRequest,
  { params }: { params: Promise<{ id: string }> }
) {
  const { id } = await params;
  const body = await request.json();

  const result = await apiClient<StockAdjustmentResponse>(
    `/products/${id}/stock`,
    {
      method: 'POST',
      body: JSON.stringify(body),
    }
  );

  return NextResponse.json(result, {
    status: result.succeeded ? 201 : 400,
  });
}

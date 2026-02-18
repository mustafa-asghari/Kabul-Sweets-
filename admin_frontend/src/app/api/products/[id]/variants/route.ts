import { NextRequest, NextResponse } from 'next/server';
import { apiClient } from '@/lib/api-client';
import { ProductVariant } from '@/types/products';

export async function POST(
  request: NextRequest,
  { params }: { params: Promise<{ id: string }> }
) {
  const { id } = await params;
  const body = await request.json();

  const result = await apiClient<ProductVariant>(
    `/products/${id}/variants`,
    {
      method: 'POST',
      body: JSON.stringify(body),
    }
  );

  return NextResponse.json(result, {
    status: result.succeeded ? 201 : 400,
  });
}

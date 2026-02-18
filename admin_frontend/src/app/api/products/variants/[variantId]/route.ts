import { NextRequest, NextResponse } from 'next/server';

import { apiClient } from '@/lib/api-client';
import { ProductVariant } from '@/types/products';

export async function PATCH(
  request: NextRequest,
  { params }: { params: Promise<{ variantId: string }> }
) {
  const { variantId } = await params;
  const body = await request.json();

  const result = await apiClient<ProductVariant>(`/products/variants/${variantId}`, {
    method: 'PATCH',
    body: JSON.stringify(body),
  });

  return NextResponse.json(result, {
    status: result.succeeded ? 200 : result.statusCode ?? 400,
  });
}

export async function DELETE(
  request: NextRequest,
  { params }: { params: Promise<{ variantId: string }> }
) {
  const { variantId } = await params;

  const result = await apiClient(`/products/variants/${variantId}`, {
    method: 'DELETE',
  });

  return NextResponse.json(result, {
    status: result.succeeded ? 200 : result.statusCode ?? 400,
  });
}

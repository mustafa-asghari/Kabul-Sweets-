import { NextRequest, NextResponse } from 'next/server';
import { apiClient } from '@/lib/api-client';
import { ProductListItem, Product } from '@/types/products';

export async function GET(request: NextRequest) {
  const searchParams = request.nextUrl.searchParams;
  const params = new URLSearchParams();

  for (const [key, value] of searchParams.entries()) {
    params.set(key, value);
  }

  const result = await apiClient<ProductListItem[]>(
    `/products/admin/all?${params.toString()}`
  );

  return NextResponse.json(result, {
    status: result.succeeded ? 200 : result.statusCode ?? 500,
  });
}

export async function POST(request: NextRequest) {
  const body = await request.json();

  const result = await apiClient<Product>('/products/', {
    method: 'POST',
    body: JSON.stringify(body),
  });

  return NextResponse.json(result, {
    status: result.succeeded ? 201 : 400,
  });
}

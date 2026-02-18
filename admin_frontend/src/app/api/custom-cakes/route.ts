import { NextRequest, NextResponse } from 'next/server';
import { apiClient } from '@/lib/api-client';
import { normalizeCustomCakeList } from './normalize';

export async function GET(request: NextRequest) {
  const searchParams = request.nextUrl.searchParams;
  const params = new URLSearchParams();

  for (const [key, value] of searchParams.entries()) {
    params.set(key, value);
  }

  const result = await apiClient<unknown[]>(
    `/admin/custom-cakes?${params.toString()}`,
  );

  const normalizedData = result.succeeded
    ? normalizeCustomCakeList(result.data)
    : result.data;

  return NextResponse.json(
    {
      ...result,
      data: normalizedData,
    },
    {
      status: result.succeeded ? 200 : result.statusCode ?? 500,
    },
  );
}

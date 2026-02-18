import { NextRequest, NextResponse } from 'next/server';
import { apiClient } from '@/lib/api-client';
import { DailyRevenue } from '@/types/analytics';

export async function GET(request: NextRequest) {
  const searchParams = request.nextUrl.searchParams;
  const params = new URLSearchParams();

  for (const [key, value] of searchParams.entries()) {
    params.set(key, value);
  }

  const result = await apiClient<DailyRevenue[]>(
    `/analytics/revenue/daily?${params.toString()}`
  );

  return NextResponse.json(result, {
    status: result.succeeded ? 200 : result.statusCode ?? 500,
  });
}

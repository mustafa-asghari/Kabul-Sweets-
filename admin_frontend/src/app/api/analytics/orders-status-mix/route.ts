import { NextResponse } from 'next/server';
import { apiClient } from '@/lib/api-client';
import { WeeklyOrderStatusMix } from '@/types/analytics';

export async function GET() {
  const result = await apiClient<WeeklyOrderStatusMix>('/analytics/orders-status-mix');

  return NextResponse.json(result, {
    status: result.succeeded ? 200 : result.statusCode ?? 500,
  });
}

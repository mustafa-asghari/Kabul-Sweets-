import { NextResponse } from 'next/server';
import { apiClient } from '@/lib/api-client';
import { DashboardSummary } from '@/types/analytics';

export async function GET() {
  const result = await apiClient<DashboardSummary>('/analytics/dashboard');

  return NextResponse.json(result, {
    status: result.succeeded ? 200 : result.statusCode ?? 500,
  });
}

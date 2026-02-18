import { NextRequest, NextResponse } from 'next/server';
import { apiClient } from '@/lib/api-client';

export async function GET(
  request: NextRequest,
  { params }: { params: Promise<{ id: string }> }
) {
  const { id } = await params;

  const result = await apiClient<unknown>(`/orders/${id}/risk-analysis`);

  // If backend doesn't implement this endpoint, return a safe fallback
  if (!result.succeeded && result.statusCode === 404) {
    return NextResponse.json({
      succeeded: true,
      message: 'Risk analysis not available',
      data: null,
    });
  }

  return NextResponse.json(result, {
    status: result.succeeded ? 200 : result.statusCode ?? 500,
  });
}

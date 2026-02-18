import { NextRequest, NextResponse } from 'next/server';
import { apiClient } from '@/lib/api-client';

export async function PATCH(
  request: NextRequest,
  { params }: { params: Promise<{ id: string }> }
) {
  const { id } = await params;

  const result = await apiClient<{ message: string }>(`/users/${id}/activate`, {
    method: 'PATCH',
  });

  return NextResponse.json(result, {
    status: result.succeeded ? 200 : 400,
  });
}

import { NextRequest, NextResponse } from 'next/server';
import { apiClient, apiUpload } from '@/lib/api-client';

export async function GET(request: NextRequest) {
  const searchParams = request.nextUrl.searchParams;
  const params = new URLSearchParams();

  for (const [key, value] of searchParams.entries()) {
    params.set(key, value);
  }

  const result = await apiClient(`/images/?${params.toString()}`);

  return NextResponse.json(result, {
    status: result.succeeded ? 200 : result.statusCode ?? 500,
  });
}

export async function POST(request: NextRequest) {
  const formData = await request.formData();

  const result = await apiUpload('/images/upload', formData);

  return NextResponse.json(result, {
    status: result.succeeded ? 201 : 400,
  });
}

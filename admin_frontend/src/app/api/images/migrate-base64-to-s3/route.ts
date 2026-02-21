import { NextResponse } from 'next/server';
import { apiClient } from '@/lib/api-client';

export async function POST() {
    const result = await apiClient('/images/migrate-base64-to-s3', { method: 'POST' });
    return NextResponse.json(result, {
        status: result.succeeded ? 200 : 500,
    });
}

import { NextRequest, NextResponse } from 'next/server';
import { apiClient } from '@/lib/api-client';
import { CartRecoveryAnalytics } from '@/types/analytics';

type RecoveryStatsResponse = {
  total_carts: number;
  active_carts: number;
  abandoned_carts_contacted: number;
  converted_carts: number;
  recovered_carts: number;
  conversion_rate: string;
};

type AbandonedCart = {
  cart_id: string;
  customer_id: string;
  item_count: number;
  last_activity: string;
  hours_abandoned: number;
};

export async function GET(request: NextRequest) {
  const minAgeHours =
    Number(request.nextUrl.searchParams.get('min_age_hours') || '1') || 1;

  const [statsResult, abandonedResult] = await Promise.all([
    apiClient<RecoveryStatsResponse>('/cart/recovery/stats'),
    apiClient<AbandonedCart[]>(`/cart/abandoned?min_age_hours=${minAgeHours}`),
  ]);

  if (!statsResult.succeeded) {
    return NextResponse.json(statsResult, {
      status: statsResult.statusCode ?? 500,
    });
  }

  const abandonedCarts = abandonedResult.succeeded ? abandonedResult.data || [] : [];

  const data: CartRecoveryAnalytics = {
    total_carts: statsResult.data?.total_carts ?? 0,
    active_carts: statsResult.data?.active_carts ?? 0,
    abandoned_carts_contacted: statsResult.data?.abandoned_carts_contacted ?? 0,
    converted_carts: statsResult.data?.converted_carts ?? 0,
    recovered_carts: statsResult.data?.recovered_carts ?? 0,
    conversion_rate: statsResult.data?.conversion_rate ?? '0%',
    current_abandoned_carts: abandonedCarts.length,
  };

  return NextResponse.json(
    {
      succeeded: true,
      message: 'Cart recovery analytics retrieved',
      timestamp: new Date().toISOString(),
      data,
    },
    { status: 200 }
  );
}

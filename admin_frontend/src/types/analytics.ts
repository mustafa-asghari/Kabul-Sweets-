export interface DashboardSummary {
  revenue_today: number;
  revenue_this_week: number;
  revenue_this_month: number;
  orders_today: number;
  orders_pending: number;
  orders_preparing: number;
  cake_orders_today: number;
  low_stock_count: number;
  total_customers: number;
}

export interface DailyRevenue {
  date: string;
  total_revenue: number;
  total_orders: number;
  total_items_sold: number;
  cake_orders: number;
  average_order_value: number;
  category_breakdown: Record<string, unknown> | null;
}

export interface BestSeller {
  product_id: string;
  product_name: string;
  category: string;
  total_quantity_sold: number;
  total_revenue: number;
}

export interface InventoryTurnover {
  product_id: string;
  variant_id: string;
  product_name: string;
  variant_name: string;
  current_stock: number;
  total_sold_30d: number;
  turnover_rate: number;
  days_of_stock_remaining: number | null;
}

export interface RevenueSummary {
  total_revenue: number;
  total_orders: number;
  total_items_sold: number;
  cake_orders: number;
  average_order_value: number;
  period_start: string;
  period_end: string;
}

export interface VisitorPoint {
  date: string;
  visits: number;
  unique_visitors: number;
}

export interface VisitorAnalytics {
  visits_over_time: VisitorPoint[];
  top_locations: Array<{
    location: string;
    visits: number;
  }>;
  device_breakdown: Array<{
    device: string;
    visits: number;
  }>;
}

export interface PopularCakeSize {
  variant_name: string;
  total_quantity_sold: number;
  total_revenue: number;
}

export interface CartRecoveryAnalytics {
  total_carts: number;
  active_carts: number;
  abandoned_carts_contacted: number;
  converted_carts: number;
  recovered_carts: number;
  conversion_rate: string;
  current_abandoned_carts: number;
}

export interface ProductPageView {
  product_slug: string;
  page_url: string;
  visits: number;
}

export interface WeeklyOrderStatusMix {
  week_start: string;
  week_end: string;
  passed_orders: number;
  rejected_orders: number;
  pending_orders: number;
  total_orders: number;
}

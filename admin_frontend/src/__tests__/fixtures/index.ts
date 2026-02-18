import type { ProductListItem } from '@/types/products';
import type { OrderListItem } from '@/types/order';
import type { UserResponse } from '@/types/user';
import type { DashboardSummary, DailyRevenue, BestSeller, InventoryTurnover } from '@/types/analytics';
import type { CustomCake } from '@/types/custom-cake';

export const mockProducts: ProductListItem[] = [
  {
    id: 'prod-1',
    name: 'Afghan Cake',
    slug: 'afghan-cake',
    short_description: 'Traditional Afghan cake',
    category: 'cake',
    base_price: 45.0,
    thumbnail: null,
    is_cake: true,
    is_featured: true,
    is_active: true,
    variants: [],
    created_at: '2025-01-01T00:00:00Z',
  },
  {
    id: 'prod-2',
    name: 'Baklava',
    slug: 'baklava',
    short_description: 'Classic baklava',
    category: 'pastry',
    base_price: 25.0,
    thumbnail: null,
    is_cake: false,
    is_featured: false,
    is_active: true,
    variants: [],
    created_at: '2025-01-02T00:00:00Z',
  },
];

export const mockOrders: OrderListItem[] = [
  {
    id: 'ord-1',
    order_number: 'KS-001',
    customer_name: 'John Doe',
    status: 'confirmed',
    total: 120.5,
    has_cake: true,
    pickup_date: '2025-02-01T10:00:00Z',
    created_at: '2025-01-28T12:00:00Z',
  },
  {
    id: 'ord-2',
    order_number: 'KS-002',
    customer_name: 'Jane Smith',
    status: 'pending',
    total: 45.0,
    has_cake: false,
    pickup_date: null,
    created_at: '2025-01-29T14:00:00Z',
  },
];

export const mockUsers: UserResponse[] = [
  {
    id: 'user-1',
    email: 'admin@kabulsweets.com.au',
    full_name: 'Admin User',
    phone: '+61400000000',
    role: 'admin',
    is_active: true,
    is_verified: true,
    created_at: '2024-01-01T00:00:00Z',
    last_login: '2025-01-30T08:00:00Z',
  },
  {
    id: 'user-2',
    email: 'customer@example.com',
    full_name: 'Test Customer',
    phone: null,
    role: 'customer',
    is_active: true,
    is_verified: false,
    created_at: '2025-01-15T00:00:00Z',
    last_login: null,
  },
];

export const mockDashboardSummary: DashboardSummary = {
  revenue_today: 450.0,
  revenue_this_week: 3200.0,
  revenue_this_month: 15420.5,
  orders_today: 3,
  orders_pending: 5,
  orders_preparing: 2,
  cake_orders_today: 1,
  low_stock_count: 3,
  total_customers: 42,
};

export const mockDailyRevenue: DailyRevenue[] = [
  { date: '2025-01-28', total_revenue: 450.0, total_orders: 5, total_items_sold: 12, cake_orders: 2, average_order_value: 90.0, category_breakdown: null },
  { date: '2025-01-29', total_revenue: 320.0, total_orders: 3, total_items_sold: 7, cake_orders: 1, average_order_value: 106.67, category_breakdown: null },
  { date: '2025-01-30', total_revenue: 580.0, total_orders: 7, total_items_sold: 18, cake_orders: 3, average_order_value: 82.86, category_breakdown: null },
];

export const mockBestSellers: BestSeller[] = [
  { product_id: 'prod-1', product_name: 'Afghan Cake', category: 'cake', total_quantity_sold: 45, total_revenue: 2025.0 },
  { product_id: 'prod-2', product_name: 'Baklava', category: 'pastry', total_quantity_sold: 120, total_revenue: 3000.0 },
];

export const mockInventory: InventoryTurnover[] = [
  {
    product_id: 'prod-1',
    variant_id: 'var-1',
    product_name: 'Afghan Cake',
    variant_name: 'Small',
    current_stock: 10,
    total_sold_30d: 20,
    turnover_rate: 2.0,
    days_of_stock_remaining: 15,
  },
  {
    product_id: 'prod-2',
    variant_id: 'var-2',
    product_name: 'Baklava',
    variant_name: 'Box of 12',
    current_stock: 3,
    total_sold_30d: 30,
    turnover_rate: 10.0,
    days_of_stock_remaining: 3,
  },
];

export const mockCustomCakes: CustomCake[] = [
  {
    id: 'cc-1',
    customer_id: 'user-2',
    order_id: null,
    customer_name: 'Test Customer',
    customer_email: 'customer@example.com',
    flavor: 'Chocolate',
    layers: 2,
    diameter_inches: 10,
    height_inches: 4,
    shape: 'round',
    decoration_complexity: 'moderate',
    decoration_description: 'Floral patterns',
    cake_message: 'Happy Birthday',
    event_type: 'birthday',
    is_rush_order: false,
    ingredients: null,
    allergen_notes: null,
    reference_images: null,
    predicted_price: 85.0,
    final_price: null,
    predicted_servings: 12,
    ai_description_short: null,
    ai_description_long: null,
    requested_date: null,
    time_slot: null,
    status: 'pending_review',
    admin_notes: null,
    rejection_reason: null,
    approved_at: null,
    approved_by: null,
    checkout_url: null,
    created_at: '2025-01-30T10:00:00Z',
    updated_at: '2025-01-30T10:00:00Z',
  },
];

export function wrapApiResponse<T>(data: T) {
  return {
    succeeded: true,
    message: 'Success',
    timestamp: new Date().toISOString(),
    data,
  };
}

export function wrapApiError(message: string) {
  return {
    succeeded: false,
    message,
    timestamp: new Date().toISOString(),
    errors: [{ message }],
  };
}

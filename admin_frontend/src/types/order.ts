export type OrderStatus =
  | 'draft'
  | 'pending'
  | 'pending_approval'
  | 'paid'
  | 'confirmed'
  | 'preparing'
  | 'ready'
  | 'completed'
  | 'cancelled'
  | 'refunded';

export type PaymentStatus =
  | 'pending'
  | 'succeeded'
  | 'failed'
  | 'refunded'
  | 'partially_refunded';

export interface OrderItemResponse {
  id: string;
  product_id: string | null;
  variant_id: string | null;
  product_name: string;
  variant_name: string | null;
  unit_price: number;
  quantity: number;
  line_total: number;
  cake_message: string | null;
}

export interface PaymentResponse {
  id: string;
  order_id: string;
  stripe_checkout_session_id: string | null;
  stripe_payment_intent_id: string | null;
  amount: number;
  currency: string;
  status: PaymentStatus;
  payment_method: string | null;
  refund_amount: number | null;
  failure_code: string | null;
  failure_message: string | null;
  created_at: string;
  updated_at: string;
}

export interface Order {
  id: string;
  order_number: string;
  customer_id: string | null;
  status: OrderStatus;
  customer_name: string;
  customer_email: string;
  customer_phone: string | null;
  pickup_date: string | null;
  pickup_time_slot: string | null;
  cake_message: string | null;
  has_cake: boolean;
  special_instructions: string | null;
  subtotal: number;
  tax_amount: number;
  discount_amount: number;
  total: number;
  discount_code: string | null;
  admin_notes: string | null;
  items: OrderItemResponse[];
  payment: PaymentResponse | null;
  created_at: string;
  updated_at: string;
  paid_at: string | null;
  completed_at: string | null;
}

export interface OrderListItem {
  id: string;
  order_number: string;
  customer_name: string;
  status: OrderStatus;
  has_cake: boolean;
  total: number;
  pickup_date: string | null;
  created_at: string;
}

export interface OrderItemCreate {
  product_id: string;
  variant_id?: string;
  quantity?: number;
  cake_message?: string;
}

export interface OrderCreate {
  items: OrderItemCreate[];
  customer_name: string;
  customer_email: string;
  customer_phone?: string;
  pickup_date?: string;
  pickup_time_slot?: string;
  cake_message?: string;
  special_instructions?: string;
  discount_code?: string;
}

export interface OrderUpdateAdmin {
  status?: OrderStatus;
  pickup_date?: string;
  pickup_time_slot?: string;
  admin_notes?: string;
}

export interface RefundRequest {
  amount?: number;
  reason: string;
}

// Legacy compatibility types still used by some UI components.
export type PaymentMethod = 1 | 2 | 3 | 4 | 5 | string;

export interface OrderDto {
  id: string;
  product?: string;
  date?: string;
  total: number;
  status?: OrderStatus | number;
  payment_method?: PaymentMethod;
}

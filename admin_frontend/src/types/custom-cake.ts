export type CustomCakeStatus =
  | 'pending_review'
  | 'approved_awaiting_payment'
  | 'paid'
  | 'in_production'
  | 'completed'
  | 'rejected'
  | 'cancelled';

export type DecorationComplexity = 'simple' | 'moderate' | 'complex' | 'elaborate';

export interface CustomCake {
  id: string;
  customer_id: string;
  order_id: string | null;
  status: CustomCakeStatus;
  flavor: string;
  diameter_inches: number;
  height_inches: number;
  layers: number;
  shape: string;
  decoration_complexity: DecorationComplexity;
  decoration_description: string | null;
  cake_message: string | null;
  event_type: string | null;
  is_rush_order: boolean;
  ingredients: Record<string, unknown> | null;
  allergen_notes: string | null;
  reference_images: string[] | null;
  predicted_price: number | null;
  final_price: number | null;
  predicted_servings: number | null;
  ai_description_short: string | null;
  ai_description_long: string | null;
  requested_date: string | null;
  time_slot: string | null;
  admin_notes: string | null;
  rejection_reason: string | null;
  approved_at: string | null;
  approved_by: string | null;
  checkout_url: string | null;
  created_at: string;
  updated_at: string;
  // Populated from join
  customer_name?: string;
  customer_email?: string;
}

export interface AdminApproveRequest {
  final_price: number;
  admin_notes?: string;
}

export interface AdminRejectRequest {
  rejection_reason: string;
}

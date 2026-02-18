import type {
  CustomCake,
  CustomCakeStatus,
  DecorationComplexity,
} from '@/types/custom-cake';

type RawCustomCake = Partial<CustomCake> & {
  diameter?: unknown;
  height?: unknown;
  decoration?: unknown;
  is_rush?: unknown;
};

const VALID_STATUSES: CustomCakeStatus[] = [
  'pending_review',
  'approved_awaiting_payment',
  'paid',
  'in_production',
  'completed',
  'rejected',
  'cancelled',
];

const VALID_COMPLEXITIES: DecorationComplexity[] = [
  'simple',
  'moderate',
  'complex',
  'elaborate',
];

function toNumber(value: unknown): number | null {
  if (typeof value === 'number' && Number.isFinite(value)) return value;
  if (typeof value === 'string' && value.trim().length > 0) {
    const parsed = Number(value);
    return Number.isFinite(parsed) ? parsed : null;
  }
  return null;
}

function toBoolean(value: unknown): boolean {
  if (typeof value === 'boolean') return value;
  if (typeof value === 'string') {
    return value.toLowerCase() === 'true';
  }
  return false;
}

function toStringValue(value: unknown): string | null {
  return typeof value === 'string' && value.trim().length > 0 ? value : null;
}

function toStringArray(value: unknown): string[] | null {
  if (!Array.isArray(value)) return null;

  const items = value.filter(
    (item): item is string =>
      typeof item === 'string' && item.trim().length > 0,
  );

  return items.length > 0 ? items : null;
}

function toRecord(value: unknown): Record<string, unknown> | null {
  if (!value || typeof value !== 'object' || Array.isArray(value)) return null;
  return value as Record<string, unknown>;
}

function toStatus(value: unknown): CustomCakeStatus {
  return VALID_STATUSES.includes(value as CustomCakeStatus)
    ? (value as CustomCakeStatus)
    : 'pending_review';
}

function toComplexity(value: unknown): DecorationComplexity {
  return VALID_COMPLEXITIES.includes(value as DecorationComplexity)
    ? (value as DecorationComplexity)
    : 'moderate';
}

export function normalizeCustomCake(rawCake: RawCustomCake): CustomCake {
  const createdAt =
    toStringValue(rawCake.created_at) ?? new Date().toISOString();
  const diameter = toNumber(rawCake.diameter_inches ?? rawCake.diameter) ?? 0;
  const height = toNumber(rawCake.height_inches ?? rawCake.height) ?? 4;
  const layers = Math.max(1, Math.round(toNumber(rawCake.layers) ?? 1));
  const servings = toNumber(rawCake.predicted_servings);

  return {
    id: toStringValue(rawCake.id) ?? '',
    customer_id: toStringValue(rawCake.customer_id) ?? '',
    order_id: toStringValue(rawCake.order_id),
    status: toStatus(rawCake.status),
    flavor: toStringValue(rawCake.flavor) ?? 'Unknown',
    diameter_inches: diameter,
    height_inches: height,
    layers,
    shape: toStringValue(rawCake.shape) ?? 'round',
    decoration_complexity: toComplexity(
      rawCake.decoration_complexity ?? rawCake.decoration,
    ),
    decoration_description: toStringValue(rawCake.decoration_description),
    cake_message: toStringValue(rawCake.cake_message),
    event_type: toStringValue(rawCake.event_type),
    is_rush_order: toBoolean(rawCake.is_rush_order ?? rawCake.is_rush),
    ingredients: toRecord(rawCake.ingredients),
    allergen_notes: toStringValue(rawCake.allergen_notes),
    reference_images: toStringArray(rawCake.reference_images),
    predicted_price: toNumber(rawCake.predicted_price),
    final_price: toNumber(rawCake.final_price),
    predicted_servings: servings == null ? null : Math.round(servings),
    ai_description_short: toStringValue(rawCake.ai_description_short),
    ai_description_long: toStringValue(rawCake.ai_description_long),
    requested_date: toStringValue(rawCake.requested_date),
    time_slot: toStringValue(rawCake.time_slot),
    admin_notes: toStringValue(rawCake.admin_notes),
    rejection_reason: toStringValue(rawCake.rejection_reason),
    approved_at: toStringValue(rawCake.approved_at),
    approved_by: toStringValue(rawCake.approved_by),
    checkout_url: toStringValue(rawCake.checkout_url),
    created_at: createdAt,
    updated_at: toStringValue(rawCake.updated_at) ?? createdAt,
    customer_name: toStringValue(rawCake.customer_name) ?? undefined,
    customer_email: toStringValue(rawCake.customer_email) ?? undefined,
  };
}

export function normalizeCustomCakeList(rawData: unknown): CustomCake[] {
  if (!Array.isArray(rawData)) return [];

  return rawData.map((item) =>
    normalizeCustomCake((item as RawCustomCake) || {}),
  );
}

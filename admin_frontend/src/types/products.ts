export type ProductCategory =
  | 'cake'
  | 'pastry'
  | 'cookie'
  | 'bread'
  | 'sweet'
  | 'drink'
  | 'other';

export interface ProductVariant {
  id: string;
  product_id: string;
  name: string;
  sku: string | null;
  price: number;
  stock_quantity: number;
  low_stock_threshold: number;
  serves: number | null;
  dimensions: Record<string, unknown> | null;
  is_active: boolean;
  is_in_stock: boolean;
  sort_order: number;
  created_at: string;
  updated_at: string;
}

export interface Product {
  id: string;
  name: string;
  slug: string;
  description: string | null;
  short_description: string | null;
  category: ProductCategory;
  base_price: number;
  images: string[] | null;
  thumbnail: string | null;
  tags: string[] | null;
  is_active: boolean;
  is_featured: boolean;
  is_cake: boolean;
  max_per_order: number | null;
  sort_order: number;
  variants: ProductVariant[];
  created_at: string;
  updated_at: string;
}

export interface ProductListItem {
  id: string;
  name: string;
  slug: string;
  short_description: string | null;
  category: ProductCategory;
  base_price: number;
  thumbnail: string | null;
  is_active: boolean;
  is_featured: boolean;
  is_cake: boolean;
  variants: ProductVariant[];
  created_at: string;
}

export interface ProductCreate {
  name: string;
  slug?: string;
  description?: string;
  short_description?: string;
  images?: string[];
  thumbnail?: string | null;
  category: ProductCategory;
  base_price: number;
  tags?: string[];
  is_active?: boolean;
  is_featured?: boolean;
  is_cake?: boolean;
  max_per_order?: number;
  sort_order?: number;
  variants?: VariantCreate[];
}

export interface ProductUpdate {
  name?: string;
  slug?: string;
  description?: string;
  short_description?: string;
  category?: ProductCategory;
  base_price?: number;
  tags?: string[];
  is_active?: boolean;
  is_featured?: boolean;
  is_cake?: boolean;
  max_per_order?: number;
  sort_order?: number;
}

export interface VariantCreate {
  name: string;
  sku?: string;
  price: number;
  stock_quantity?: number;
  low_stock_threshold?: number;
  serves?: number;
  dimensions?: Record<string, unknown>;
  is_active?: boolean;
  sort_order?: number;
}

export interface VariantUpdate {
  name?: string;
  price?: number;
  stock_quantity?: number;
  low_stock_threshold?: number;
  serves?: number;
  dimensions?: Record<string, unknown>;
  is_active?: boolean;
  sort_order?: number;
}

export interface StockAdjustmentRequest {
  variant_id: string;
  quantity_change: number;
  reason: string;
  notes?: string;
}

export interface StockAdjustmentResponse {
  id: string;
  product_id: string;
  variant_id: string | null;
  quantity_change: number;
  previous_quantity: number;
  new_quantity: number;
  reason: string;
  notes: string | null;
  created_at: string;
}

// Legacy compatibility interfaces still used by older product/category UI cards.
export interface IProductCategory {
  id: string;
  title: string;
  description?: string;
  productCount?: number;
}

export interface IProduct {
  id: string;
  title: string;
  description?: string;
  price: number;
  quantityInStock: number;
  isActive: boolean;
  sku?: string;
  categoryName?: string;
  category?: IProductCategory | null;
}

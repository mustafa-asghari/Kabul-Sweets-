export interface StorefrontVariant {
  id: string;
  name: string;
  price: number;
  stockQuantity: number;
  isInStock: boolean;
}

export interface StorefrontProduct {
  id: string;
  slug: string;
  title: string;
  category: string;
  categoryKey: string;
  price: number;
  shortDescription: string;
  description: string;
  options: string[];
  imageSrc: string;
  thumbnails: string[];
  tags: string[];
  isFeatured: boolean;
  isCake: boolean;
  maxPerOrder: number | null;
  variants: StorefrontVariant[];
}

export interface StorefrontCollection {
  title: string;
  description: string;
  imageSrc: string;
  imageAlt: string;
  categoryKey: string;
  count: number;
}

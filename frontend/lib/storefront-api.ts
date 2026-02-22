import "server-only";

import type {
  StorefrontCollection,
  StorefrontProduct,
} from "@/lib/storefront-types";

interface ApiVariant {
  id: string;
  name: string;
  price: string | number;
  stock_quantity: number;
  is_in_stock: boolean;
}

interface ApiProductList {
  id: string;
  name: string;
  slug: string;
  short_description: string | null;
  category: string;
  base_price: string | number;
  thumbnail: string | null;
  is_featured: boolean;
  is_cake: boolean;
  max_per_order?: number | null;
  variants: ApiVariant[];
  description?: string | null;
  images?: string[] | null;
  tags?: string[] | null;
}

const INTERNAL_API_BASE_URL = (() => {
  const fallback = "http://localhost:8000";
  const fromEnv =
    process.env.INTERNAL_API_BASE_URL ||
    process.env.NEXT_PUBLIC_API_BASE_URL ||
    process.env.API_BASE_URL;
  return (fromEnv || fallback).replace(/\/+$/, "");
})();

const PUBLIC_API_BASE_URL = (() => {
  const fallback = "http://localhost:8000";
  const fromEnv =
    process.env.NEXT_PUBLIC_API_BASE_URL ||
    process.env.INTERNAL_API_BASE_URL ||
    process.env.API_BASE_URL;
  return (fromEnv || fallback).replace(/\/+$/, "");
})();

const CATEGORY_LABELS: Record<string, string> = {
  cake: "Cakes",
  pastry: "Pastries",
  sweet: "Sweets",
  cookie: "Cookies",
  bread: "Bread",
  drink: "Drinks",
  other: "Other",
};

const CATEGORY_DESCRIPTIONS: Record<string, string> = {
  cake: "Custom and celebration cakes prepared fresh for every occasion.",
  pastry: "Small cakes and pastry bites for everyday pickup.",
  sweet: "Traditional Afghan sweets and baklava made fresh each day.",
  cookie: "Fresh cookie assortments for tea-time, gifting, and events.",
  bread: "Freshly baked Afghan breads and savory bakery staples.",
  drink: "Hot and cold beverages crafted to pair with your order.",
  other: "Browse all specialty bakery products in this collection.",
};

const CATEGORY_ORDER = ["cake", "pastry", "sweet", "cookie", "bread", "drink", "other"];

const CATEGORY_FALLBACK_IMAGES: Record<string, string> = {
  cake: "/products/cake-main.png",
  pastry: "/products/pastry-main.png",
  sweet: "/products/sweets-main.png",
  cookie: "/products/cookies-main.png",
  bread: "/products/pastry-alt.png",
  drink: "/products/pastry-alt.png",
  other: "/products/pastry-main.png",
};

function getInternalApiBaseUrl() {
  return INTERNAL_API_BASE_URL;
}

function getPublicApiBaseUrl() {
  return PUBLIC_API_BASE_URL;
}

function getStoreApiBaseCandidates() {
  const seen = new Set<string>();
  const candidates = [
    getInternalApiBaseUrl(),
    "http://api:8000",
    "http://localhost:8000",
  ];

  return candidates.filter((value) => {
    const normalized = value.replace(/\/+$/, "");
    if (!normalized || seen.has(normalized)) {
      return false;
    }
    seen.add(normalized);
    return true;
  });
}

function toNumber(value: string | number | null | undefined) {
  if (typeof value === "number") {
    return Number.isFinite(value) ? value : 0;
  }
  if (typeof value === "string") {
    const parsed = Number(value);
    return Number.isFinite(parsed) ? parsed : 0;
  }
  return 0;
}

function normalizeCategoryKey(value: string | null | undefined) {
  return (value || "other").toLowerCase().trim();
}

/** Rewrite /original → /serve so public pages don't hit the admin-only endpoint. */
function rewriteImagePath(pathname: string): string {
  return pathname.replace(/\/original([?#].*)?$/, "/serve$1");
}

function normalizeImageSrc(value: string, categoryKey: string) {
  const trimmed = value.trim();
  if (trimmed.startsWith("http://") || trimmed.startsWith("https://")) {
    try {
      const source = new URL(trimmed);
      const pathname = source.pathname;
      // Rewrite /original → /serve for ANY URL that looks like our image API,
      // regardless of host (covers mismatched INTERNAL_API_BASE_URL in prod).
      if (/\/api\/v1\/images\/[^/?#]+\/original([?#]|$)/.test(pathname)) {
        return rewriteImagePath(pathname + source.search + source.hash);
      }
      // For other internal URLs: strip the host if origins match.
      try {
        const internal = new URL(getInternalApiBaseUrl());
        if (source.origin === internal.origin) {
          return rewriteImagePath(`${pathname}${source.search}${source.hash}`);
        }
      } catch { /* ignore */ }
    } catch {
      // Keep original URL when parsing fails.
    }
    return trimmed;
  }
  if (trimmed.startsWith("/")) {
    return rewriteImagePath(trimmed);
  }
  if (trimmed.length === 0) {
    return CATEGORY_FALLBACK_IMAGES[categoryKey] || CATEGORY_FALLBACK_IMAGES.other;
  }
  return `/${trimmed}`;
}

function unique(values: string[]) {
  return [...new Set(values)];
}

export function getCategoryLabel(categoryKey: string) {
  const normalized = normalizeCategoryKey(categoryKey);
  return CATEGORY_LABELS[normalized] || CATEGORY_LABELS.other;
}

export function categoryLabelToKey(categoryLabel: string) {
  const normalized = categoryLabel.toLowerCase().trim();
  if (CATEGORY_LABELS[normalized]) {
    return normalized;
  }
  for (const [key, label] of Object.entries(CATEGORY_LABELS)) {
    if (label.toLowerCase() === normalized) {
      return key;
    }
  }
  return undefined;
}

function mapProduct(product: ApiProductList): StorefrontProduct {
  const categoryKey = normalizeCategoryKey(product.category);
  const fallbackImage = CATEGORY_FALLBACK_IMAGES[categoryKey] || CATEGORY_FALLBACK_IMAGES.other;
  const inputImages = Array.isArray(product.images) ? product.images : [];
  const thumbnails = unique(
    [product.thumbnail || "", ...inputImages]
      .filter((image): image is string => typeof image === "string" && image.trim().length > 0)
      .map((image) => normalizeImageSrc(image, categoryKey))
  );
  const variants = (product.variants || []).map((variant) => ({
    id: variant.id,
    name: variant.name,
    price: toNumber(variant.price),
    stockQuantity: variant.stock_quantity ?? 0,
    isInStock: Boolean(variant.is_in_stock),
  }));
  const minVariantPrice =
    variants.length > 0 ? Math.min(...variants.map((variant) => variant.price)) : undefined;

  return {
    id: product.id,
    slug: product.slug,
    title: product.name,
    category: getCategoryLabel(categoryKey),
    categoryKey,
    price: minVariantPrice ?? toNumber(product.base_price),
    shortDescription:
      product.short_description || product.description || "Freshly prepared at Kabul Sweets.",
    description:
      product.description || product.short_description || "Freshly prepared at Kabul Sweets.",
    options: variants.map((variant) => variant.name),
    imageSrc: thumbnails[0] || fallbackImage,
    thumbnails: thumbnails.length > 0 ? thumbnails : [fallbackImage],
    tags: Array.isArray(product.tags) ? product.tags : [],
    isFeatured: Boolean(product.is_featured),
    isCake: Boolean(product.is_cake),
    maxPerOrder:
      typeof product.max_per_order === "number" ? product.max_per_order : null,
    variants,
  };
}

function createProductsUrl(params?: {
  category?: string;
  isFeatured?: boolean;
  isCake?: boolean;
  search?: string;
  skip?: number;
  limit?: number;
}) {
  const query = new URLSearchParams();
  if (params?.category) {
    query.set("category", params.category);
  }
  if (typeof params?.isFeatured === "boolean") {
    query.set("is_featured", String(params.isFeatured));
  }
  if (typeof params?.isCake === "boolean") {
    query.set("is_cake", String(params.isCake));
  }
  if (params?.search?.trim()) {
    query.set("search", params.search.trim());
  }
  if (typeof params?.skip === "number") {
    query.set("skip", String(params.skip));
  }
  query.set("limit", String(params?.limit ?? 100));
  const serialized = query.toString();
  return serialized ? `/api/v1/products/?${serialized}` : "/api/v1/products/";
}

async function fetchJson<T>(path: string): Promise<T | null> {
  const baseCandidates = getStoreApiBaseCandidates();

  for (const baseUrl of baseCandidates) {
    const targetUrl = `${baseUrl}${path}`;
    try {
      const response = await fetch(targetUrl, {
        method: "GET",
        headers: {
          Accept: "application/json",
        },
        next: { revalidate: 86400, tags: ["products"] },
      });
      if (!response.ok) {
        continue;
      }
      return (await response.json()) as T;
    } catch {
      continue;
    }
  }

  return null;
}

export async function fetchStoreProducts(params?: {
  categoryLabel?: string;
  isFeatured?: boolean;
  isCake?: boolean;
  search?: string;
  skip?: number;
  limit?: number;
}) {
  const categoryKey = params?.categoryLabel
    ? categoryLabelToKey(params.categoryLabel)
    : undefined;
  const data = await fetchJson<ApiProductList[]>(
    createProductsUrl({
      category: categoryKey,
      isFeatured: params?.isFeatured,
      isCake: params?.isCake,
      search: params?.search,
      skip: params?.skip,
      limit: params?.limit ?? 100,
    })
  );
  if (!data) {
    return [] as StorefrontProduct[];
  }
  return data.map(mapProduct);
}

export async function fetchStoreProductBySlug(slug: string) {
  const data = await fetchJson<ApiProductList>(
    `/api/v1/products/slug/${encodeURIComponent(slug)}`
  );
  if (!data) {
    return null;
  }
  return mapProduct(data);
}

export async function fetchRelatedStoreProducts(
  product: StorefrontProduct,
  limit = 3
) {
  const sameCategory = await fetchStoreProducts({
    categoryLabel: product.category,
    limit: limit + 8,
  });

  const filteredSameCategory = sameCategory.filter((item) => item.slug !== product.slug);
  if (filteredSameCategory.length >= limit) {
    return filteredSameCategory.slice(0, limit);
  }

  // Fallback: fetch a small cross-category set (cached, so no extra cost)
  const fallback = await fetchStoreProducts({ limit: 20 });
  return fallback.filter((item) => item.slug !== product.slug).slice(0, limit);
}

export function getProductCategoriesFromProducts(products: StorefrontProduct[]) {
  const keys = [...new Set(products.map((product) => product.categoryKey))];
  keys.sort((a, b) => {
    const left = CATEGORY_ORDER.indexOf(a);
    const right = CATEGORY_ORDER.indexOf(b);
    if (left === -1 && right === -1) {
      return a.localeCompare(b);
    }
    if (left === -1) {
      return 1;
    }
    if (right === -1) {
      return -1;
    }
    return left - right;
  });
  return ["All", ...keys.map((key) => getCategoryLabel(key))];
}

export function getCollectionsFromProducts(products: StorefrontProduct[]) {
  const grouped = new Map<
    string,
    {
      categoryKey: string;
      title: string;
      count: number;
      imageSrc: string;
    }
  >();

  products.forEach((product) => {
    const key = product.categoryKey;
    const existing = grouped.get(key);
    if (existing) {
      existing.count += 1;
      if (!existing.imageSrc && product.imageSrc) {
        existing.imageSrc = product.imageSrc;
      }
      return;
    }
    grouped.set(key, {
      categoryKey: key,
      title: getCategoryLabel(key),
      count: 1,
      imageSrc: product.imageSrc,
    });
  });

  const collections: StorefrontCollection[] = Array.from(grouped.values()).map((entry) => ({
    categoryKey: entry.categoryKey,
    title: entry.title,
    count: entry.count,
    imageSrc:
      entry.imageSrc ||
      CATEGORY_FALLBACK_IMAGES[entry.categoryKey] ||
      CATEGORY_FALLBACK_IMAGES.other,
    imageAlt: `${entry.title} collection`,
    description:
      CATEGORY_DESCRIPTIONS[entry.categoryKey] || CATEGORY_DESCRIPTIONS.other,
  }));

  collections.sort((a, b) => {
    const left = CATEGORY_ORDER.indexOf(a.categoryKey);
    const right = CATEGORY_ORDER.indexOf(b.categoryKey);
    if (left === -1 && right === -1) {
      return b.count - a.count;
    }
    if (left === -1) {
      return 1;
    }
    if (right === -1) {
      return -1;
    }
    return left - right;
  });

  return collections;
}

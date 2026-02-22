"use client";

import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useRef,
  useState,
} from "react";
import { ApiError, apiRequest } from "@/lib/api-client";
import { useAuth } from "@/context/AuthContext";

interface ServerCartItem {
  id: string;
  product_id: string;
  variant_id: string | null;
  quantity: number;
}

interface ServerCartResponse {
  id: string;
  customer_id: string;
  status: string;
  items: ServerCartItem[];
  item_count: number;
  last_activity: string;
}

interface ServerProductVariant {
  id: string;
  name: string;
  price: string | number;
}

interface ServerProduct {
  id: string;
  slug: string;
  name: string;
  thumbnail: string | null;
  images: string[] | null;
  base_price: string | number;
  variants: ServerProductVariant[];
}

export interface CartLine {
  id: string;
  productId: string;
  variantId: string | null;
  slug: string;
  title: string;
  imageSrc: string;
  price: number;
  quantity: number;
  optionLabel: string | null;
}

interface CheckoutPayload {
  customerPhone?: string;
  pickupDate?: string;
  pickupTimeSlot?: string;
  cakeMessage?: string;
  specialInstructions?: string;
}

interface CheckoutResult {
  checkoutUrl: string;
  orderId: string;
  orderNumber: string;
}

interface CartContextValue {
  lines: CartLine[];
  rawItems: ServerCartItem[];
  cartCount: number;
  subtotal: number;
  loading: boolean;
  checkoutLoading: boolean;
  cartError: string | null;
  refreshCart: () => Promise<void>;
  addItem: (payload: { productId: string; variantId?: string | null; quantity?: number }) => Promise<void>;
  updateQuantity: (itemId: string, quantity: number) => Promise<void>;
  removeItem: (itemId: string) => Promise<void>;
  clearAll: () => Promise<void>;
  checkout: (payload: CheckoutPayload) => Promise<CheckoutResult>;
}

const CartContext = createContext<CartContextValue | undefined>(undefined);

function asPrice(value: string | number | null | undefined) {
  if (typeof value === "number") {
    return Number.isFinite(value) ? value : 0;
  }
  if (typeof value === "string") {
    const parsed = Number(value);
    return Number.isFinite(parsed) ? parsed : 0;
  }
  return 0;
}

function rewriteImageUrl(url: string): string {
  const trimmed = url.trim();
  // Absolute URL: strip host if it points to the backend API proxy path
  if (trimmed.startsWith("http://") || trimmed.startsWith("https://")) {
    try {
      const parsed = new URL(trimmed);
      // Treat any absolute URL whose path starts with /api/v1/images/ as internal
      if (/^\/api\/v1\/images\//.test(parsed.pathname)) {
        return parsed.pathname.replace(/\/original([?#].*)?$/, "/serve$1") + parsed.search + parsed.hash;
      }
    } catch {
      // fall through to relative handling
    }
  }
  // Relative path: rewrite /original → /serve
  if (/^\/api\/v1\/images\/[^/?#]+\/original([?#].*)?$/.test(trimmed)) {
    return trimmed.replace(/\/original([?#].*)?$/, "/serve$1");
  }
  return trimmed;
}

function resolveProductImage(product: ServerProduct) {
  if (product.thumbnail && product.thumbnail.trim().length > 0) {
    return rewriteImageUrl(product.thumbnail);
  }
  if (Array.isArray(product.images) && product.images[0]) {
    return rewriteImageUrl(product.images[0]);
  }
  return "/products/pastry-main.png";
}

function mapCartLines(items: ServerCartItem[], products: Map<string, ServerProduct>): CartLine[] {
  return items.map((item) => {
    const product = products.get(item.product_id);
    if (!product) {
      return {
        id: item.id,
        productId: item.product_id,
        variantId: item.variant_id,
        slug: "shop",
        title: "Product unavailable",
        imageSrc: "/products/pastry-main.png",
        price: 0,
        quantity: item.quantity,
        optionLabel: null,
      };
    }

    const variant = item.variant_id
      ? product.variants.find((candidate) => candidate.id === item.variant_id) || null
      : null;
    const unitPrice = variant ? asPrice(variant.price) : asPrice(product.base_price);

    return {
      id: item.id,
      productId: item.product_id,
      variantId: item.variant_id,
      slug: product.slug,
      title: product.name,
      imageSrc: resolveProductImage(product),
      price: unitPrice,
      quantity: item.quantity,
      optionLabel: variant?.name || null,
    };
  });
}

const PRODUCT_CACHE_TTL_MS = 5 * 60 * 1000;

interface ProductCacheEntry {
  product: ServerProduct;
  cachedAt: number;
}

const productCache = new Map<string, ProductCacheEntry>();

function getCachedProduct(productId: string): ServerProduct | null {
  const entry = productCache.get(productId);
  if (!entry) {
    return null;
  }
  if (Date.now() - entry.cachedAt > PRODUCT_CACHE_TTL_MS) {
    productCache.delete(productId);
    return null;
  }
  return entry.product;
}

function setCachedProduct(productId: string, product: ServerProduct): void {
  productCache.set(productId, { product, cachedAt: Date.now() });
}

function evictProduct(productId: string): void {
  productCache.delete(productId);
}
export function CartProvider({ children }: { children: React.ReactNode }) {
  const { accessToken, isAuthenticated, user, loading: authLoading } = useAuth();
  const [rawItems, setRawItems] = useState<ServerCartItem[]>([]);
  const [lines, setLines] = useState<CartLine[]>([]);
  const [loading, setLoading] = useState(true);
  const [checkoutLoading, setCheckoutLoading] = useState(false);
  const [cartError, setCartError] = useState<string | null>(null);
  // Tracks whether we've completed at least one successful load.
  // Subsequent refreshes run silently in the background without showing a spinner.
  const hasLoadedRef = useRef(false);

  const refreshCart = useCallback(async () => {
    if (!accessToken || !isAuthenticated) {
      setRawItems([]);
      setLines([]);
      setCartError(null);
      setLoading(false);
      hasLoadedRef.current = false;
      return;
    }

    // First load: show spinner. Subsequent refreshes run silently in the background
    // so the cart drawer shows the previous state instantly while fresh data loads.
    if (!hasLoadedRef.current) {
      setLoading(true);
    }
    setCartError(null);

    try {
      const cart = await apiRequest<ServerCartResponse>(`/api/v1/cart?_t=${Date.now()}`, {
        token: accessToken,
      });
      setRawItems(cart.items);

      const uniqueProductIds = [...new Set(cart.items.map((item) => item.product_id))];
      const uncachedIds = uniqueProductIds.filter((id) => !getCachedProduct(id));
      await Promise.all(
        uncachedIds.map(async (productId) => {
          try {
            const product = await apiRequest<ServerProduct>(`/api/v1/products/${productId}`);
            setCachedProduct(productId, product);
          } catch {
            evictProduct(productId);
          }
        })
      );

      const productMap = new Map(
        uniqueProductIds
          .map((id) => [id, getCachedProduct(id)] as const)
          .filter((entry): entry is readonly [string, ServerProduct] => entry[1] !== null)
      );

      // Auto-remove cart items whose products no longer exist (deleted from admin).
      const deletedItemIds = cart.items
        .filter((item) => !productMap.has(item.product_id))
        .map((item) => item.id);

      if (deletedItemIds.length > 0) {
        await Promise.allSettled(
          deletedItemIds.map((itemId) =>
            apiRequest(`/api/v1/cart/items/${itemId}`, {
              method: "DELETE",
              token: accessToken,
            })
          )
        );
        // Re-fetch the cleaned cart
        const cleanCart = await apiRequest<ServerCartResponse>(`/api/v1/cart?_t=${Date.now()}`, { token: accessToken });
        setRawItems(cleanCart.items);
        setLines(mapCartLines(cleanCart.items, productMap));
      } else {
        setLines(mapCartLines(cart.items, productMap));
      }

      hasLoadedRef.current = true;
    } catch (error) {
      if (error instanceof ApiError) {
        setCartError(error.detail);
      } else {
        setCartError("Unable to load cart.");
      }
      setRawItems([]);
      setLines([]);
    } finally {
      setLoading(false);
    }
  }, [accessToken, isAuthenticated]);

  useEffect(() => {
    if (authLoading) {
      return;
    }
    refreshCart();
  }, [authLoading, refreshCart]);

  const addItem = useCallback(
    async ({
      productId,
      variantId = null,
      quantity = 1,
    }: {
      productId: string;
      variantId?: string | null;
      quantity?: number;
    }) => {
      if (!accessToken) {
        throw new ApiError(401, "Please log in before adding items to cart.");
      }

      const updatedCart = await apiRequest<ServerCartResponse>("/api/v1/cart/items", {
        method: "POST",
        token: accessToken,
        body: {
          product_id: productId,
          variant_id: variantId,
          quantity,
        },
      });

      // Fast UI response: update item counts immediately from POST response.
      setRawItems(updatedCart.items);

      // If all products are already cached, update lines immediately too.
      const uniqueProductIds = [...new Set(updatedCart.items.map((item) => item.product_id))];
      const allProductsCached = uniqueProductIds.every((id) => getCachedProduct(id) !== null);
      if (allProductsCached) {
        const productMap = new Map(
          uniqueProductIds
            .map((id) => [id, getCachedProduct(id)] as const)
            .filter((entry): entry is readonly [string, ServerProduct] => entry[1] !== null)
        );
        setLines(mapCartLines(updatedCart.items, productMap));
      }

      // Run full sync in background (non-blocking) to avoid slow add-to-cart UX.
      void refreshCart();
    },
    [accessToken, refreshCart]
  );

  const updateQuantity = useCallback(
    async (itemId: string, quantity: number) => {
      if (!accessToken) {
        throw new ApiError(401, "Please log in first.");
      }
      await apiRequest<ServerCartResponse>(`/api/v1/cart/items/${itemId}`, {
        method: "PUT",
        token: accessToken,
        body: { quantity },
      });
      await refreshCart();
    },
    [accessToken, refreshCart]
  );

  const removeItem = useCallback(
    async (itemId: string) => {
      if (!accessToken) {
        throw new ApiError(401, "Please log in first.");
      }
      try {
        await apiRequest<{ message: string }>(`/api/v1/cart/items/${itemId}`, {
          method: "DELETE",
          token: accessToken,
        });
      } catch (err) {
        // 404 = item already gone from backend (e.g. stale cached cart ID).
        // Still refresh so the UI syncs with the real cart state.
        if (err instanceof ApiError && err.status === 404) {
          await refreshCart();
          return;
        }
        throw err;
      }
      await refreshCart();
    },
    [accessToken, refreshCart]
  );

  const clearAll = useCallback(async () => {
    if (!accessToken) {
      return;
    }
    await apiRequest<{ message: string }>("/api/v1/cart", {
      method: "DELETE",
      token: accessToken,
    });
    await refreshCart();
  }, [accessToken, refreshCart]);

  const checkout = useCallback(
    async (payload: CheckoutPayload) => {
      if (!accessToken || !user) {
        throw new ApiError(401, "Please log in to checkout.");
      }
      if (rawItems.length === 0) {
        throw new ApiError(400, "Your cart is empty.");
      }
      if (!payload.pickupDate) {
        throw new ApiError(400, "Pickup date is required.");
      }
      if (!payload.pickupTimeSlot) {
        throw new ApiError(400, "Pickup time slot is required.");
      }

      setCheckoutLoading(true);
      setCartError(null);
      try {
        const order = await apiRequest<{
          id: string;
          order_number: string;
        }>("/api/v1/orders", {
          method: "POST",
          token: accessToken,
          body: {
            items: rawItems.map((item) => ({
              product_id: item.product_id,
              variant_id: item.variant_id,
              quantity: item.quantity,
            })),
            customer_name: user.full_name,
            customer_email: user.email,
            customer_phone: payload.customerPhone || user.phone || null,
            pickup_date: `${payload.pickupDate}T12:00:00`,
            pickup_time_slot: payload.pickupTimeSlot,
            cake_message: payload.cakeMessage || null,
            special_instructions: payload.specialInstructions || null,
          },
        });

        await clearAll();

        return {
          checkoutUrl: `/orders?submitted=1&order=${encodeURIComponent(order.order_number)}`,
          orderId: order.id,
          orderNumber: order.order_number,
        };
      } finally {
        setCheckoutLoading(false);
      }
    },
    [accessToken, clearAll, rawItems, user]
  );

  const cartCount = useMemo(
    () => rawItems.reduce((sum, item) => sum + item.quantity, 0),
    [rawItems]
  );
  const subtotal = useMemo(
    () => lines.reduce((sum, line) => sum + line.price * line.quantity, 0),
    [lines]
  );

  const value = useMemo<CartContextValue>(
    () => ({
      lines,
      rawItems,
      cartCount,
      subtotal,
      loading,
      checkoutLoading,
      cartError,
      refreshCart,
      addItem,
      updateQuantity,
      removeItem,
      clearAll,
      checkout,
    }),
    [
      lines,
      rawItems,
      cartCount,
      subtotal,
      loading,
      checkoutLoading,
      cartError,
      refreshCart,
      addItem,
      updateQuantity,
      removeItem,
      clearAll,
      checkout,
    ]
  );

  return <CartContext.Provider value={value}>{children}</CartContext.Provider>;
}

export function useCart() {
  const context = useContext(CartContext);
  if (!context) {
    throw new Error("useCart must be used within CartProvider");
  }
  return context;
}

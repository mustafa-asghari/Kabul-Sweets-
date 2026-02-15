export interface CartItem {
  slug: string;
  title: string;
  price: number;
  imageSrc: string;
  quantity: number;
  selectedColor?: string;
}

const CART_STORAGE_KEY = "kabul_sweets_cart";

function isBrowser() {
  return typeof window !== "undefined";
}

function normalizeCart(value: unknown): CartItem[] {
  if (!Array.isArray(value)) {
    return [];
  }

  return value
    .map((item) => {
      if (!item || typeof item !== "object") {
        return null;
      }

      const typedItem = item as Partial<CartItem>;
      if (
        !typedItem.slug ||
        !typedItem.title ||
        typeof typedItem.price !== "number" ||
        !typedItem.imageSrc
      ) {
        return null;
      }

      return {
        slug: typedItem.slug,
        title: typedItem.title,
        price: typedItem.price,
        imageSrc: typedItem.imageSrc,
        quantity:
          typeof typedItem.quantity === "number" && typedItem.quantity > 0
            ? Math.floor(typedItem.quantity)
            : 1,
        selectedColor: typedItem.selectedColor,
      } satisfies CartItem;
    })
    .filter((item): item is CartItem => item !== null);
}

function emitCartUpdated() {
  if (!isBrowser()) {
    return;
  }
  window.dispatchEvent(new Event("cart-updated"));
}

export function readCart(): CartItem[] {
  if (!isBrowser()) {
    return [];
  }

  try {
    const raw = window.localStorage.getItem(CART_STORAGE_KEY);
    if (!raw) {
      return [];
    }

    return normalizeCart(JSON.parse(raw));
  } catch {
    return [];
  }
}

export function writeCart(items: CartItem[]) {
  if (!isBrowser()) {
    return;
  }

  window.localStorage.setItem(CART_STORAGE_KEY, JSON.stringify(items));
  emitCartUpdated();
}

export function getCartCount(items = readCart()) {
  return items.reduce((sum, item) => sum + item.quantity, 0);
}

export function addToCart(item: Omit<CartItem, "quantity">, quantity = 1) {
  const nextQuantity = Math.max(1, Math.floor(quantity));
  const cart = readCart();
  const existing = cart.find(
    (entry) =>
      entry.slug === item.slug && (entry.selectedColor ?? "") === (item.selectedColor ?? "")
  );

  if (existing) {
    existing.quantity += nextQuantity;
  } else {
    cart.push({ ...item, quantity: nextQuantity });
  }

  writeCart(cart);
  return cart;
}

export function updateCartItemQuantity(slug: string, selectedColor: string | undefined, quantity: number) {
  const cart = readCart();
  const nextQuantity = Math.max(1, Math.floor(quantity));
  const item = cart.find(
    (entry) => entry.slug === slug && (entry.selectedColor ?? "") === (selectedColor ?? "")
  );

  if (!item) {
    return cart;
  }

  item.quantity = nextQuantity;
  writeCart(cart);
  return cart;
}

export function removeCartItem(slug: string, selectedColor: string | undefined) {
  const cart = readCart().filter(
    (entry) => !(entry.slug === slug && (entry.selectedColor ?? "") === (selectedColor ?? ""))
  );
  writeCart(cart);
  return cart;
}

export function clearCart() {
  writeCart([]);
}

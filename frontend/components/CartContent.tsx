"use client";

import Image from "next/image";
import Link from "next/link";
import { useEffect, useMemo, useState } from "react";
import {
  clearCart,
  readCart,
  removeCartItem,
  type CartItem,
  updateCartItemQuantity,
} from "@/lib/cart";
import { formatPrice } from "@/data/storefront";

export default function CartContent() {
  const [items, setItems] = useState<CartItem[]>([]);
  const [loaded, setLoaded] = useState(false);

  useEffect(() => {
    const syncCart = () => {
      setItems(readCart());
      setLoaded(true);
    };

    syncCart();
    window.addEventListener("cart-updated", syncCart);
    window.addEventListener("storage", syncCart);

    return () => {
      window.removeEventListener("cart-updated", syncCart);
      window.removeEventListener("storage", syncCart);
    };
  }, []);

  const subtotal = useMemo(
    () => items.reduce((sum, item) => sum + item.price * item.quantity, 0),
    [items]
  );

  if (!loaded) {
    return (
      <section className="max-w-[1200px] mx-auto px-6 pb-20">
        <div className="rounded-[1.5rem] bg-cream-dark/60 p-8 text-sm text-gray-500">Loading cart...</div>
      </section>
    );
  }

  if (items.length === 0) {
    return (
      <section className="max-w-[1200px] mx-auto px-6 pb-20">
        <div className="rounded-[1.5rem] bg-cream-dark/60 p-8">
          <h2 className="text-2xl font-extrabold tracking-tight text-black">Your cart is empty</h2>
          <p className="mt-2 text-sm text-gray-600">Add products from the shop to start an order.</p>
          <Link
            href="/shop"
            className="mt-5 inline-flex items-center gap-2 text-sm font-semibold text-black hover:text-accent transition"
          >
            Continue Shopping
            <span className="material-symbols-outlined text-[16px]">arrow_forward</span>
          </Link>
        </div>
      </section>
    );
  }

  return (
    <section className="max-w-[1200px] mx-auto px-6 pb-20">
      <div className="grid grid-cols-1 lg:grid-cols-[1fr_320px] gap-6">
        <div className="space-y-4">
          {items.map((item) => (
            <article
              key={`${item.slug}-${item.selectedColor ?? "default"}`}
              className="rounded-[1.5rem] bg-white p-4 md:p-5 flex items-center gap-4 border border-[#efe5d6]"
            >
              <Link href={`/products/${item.slug}`} className="shrink-0">
                <Image
                  src={item.imageSrc}
                  alt={item.title}
                  width={90}
                  height={90}
                  sizes="90px"
                  className="h-[90px] w-[90px] rounded-xl object-cover"
                />
              </Link>
              <div className="min-w-0 flex-1">
                <Link href={`/products/${item.slug}`} className="font-bold text-black hover:text-accent transition">
                  {item.title}
                </Link>
                {item.selectedColor ? (
                  <p className="text-xs text-gray-500 mt-1">Option: {item.selectedColor}</p>
                ) : null}
                <p className="text-sm font-semibold text-black mt-2">{formatPrice(item.price)}</p>
              </div>
              <div className="flex items-center gap-2">
                <button
                  type="button"
                  onClick={() =>
                    setItems(updateCartItemQuantity(item.slug, item.selectedColor, item.quantity - 1))
                  }
                  className="h-8 w-8 rounded-full bg-cream-dark text-black hover:bg-[#eadbc4] transition"
                  aria-label="Decrease quantity"
                >
                  -
                </button>
                <span className="w-8 text-center text-sm font-semibold text-black">{item.quantity}</span>
                <button
                  type="button"
                  onClick={() =>
                    setItems(updateCartItemQuantity(item.slug, item.selectedColor, item.quantity + 1))
                  }
                  className="h-8 w-8 rounded-full bg-cream-dark text-black hover:bg-[#eadbc4] transition"
                  aria-label="Increase quantity"
                >
                  +
                </button>
              </div>
              <button
                type="button"
                onClick={() => setItems(removeCartItem(item.slug, item.selectedColor))}
                className="text-gray-500 hover:text-black transition"
                aria-label="Remove item"
              >
                <span className="material-symbols-outlined text-[20px]">delete</span>
              </button>
            </article>
          ))}
        </div>

        <aside className="rounded-[1.5rem] bg-cream-dark/70 p-6 h-fit lg:sticky lg:top-24">
          <h2 className="text-2xl font-extrabold tracking-tight text-black">Order Summary</h2>
          <div className="mt-4 flex items-center justify-between text-sm text-gray-600">
            <span>Subtotal</span>
            <span className="font-semibold text-black">{formatPrice(subtotal)}</span>
          </div>
          <p className="mt-1 text-xs text-gray-500">Pickup and tax calculated at checkout.</p>
          <button
            type="button"
            className="mt-5 w-full rounded-full bg-black py-3 text-sm font-semibold text-white hover:bg-[#222] transition"
          >
            Proceed to Checkout
          </button>
          <button
            type="button"
            onClick={() => {
              clearCart();
              setItems([]);
            }}
            className="mt-3 w-full rounded-full bg-white py-3 text-sm font-semibold text-black hover:bg-[#f4f4f4] transition"
          >
            Clear Cart
          </button>
        </aside>
      </div>
    </section>
  );
}

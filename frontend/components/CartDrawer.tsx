"use client";

import { AnimatePresence, motion } from "framer-motion";
import Image from "next/image";
import Link from "next/link";
import { useEffect, useMemo, useState } from "react";
import { formatPrice } from "@/data/storefront";
import {
  clearCart,
  readCart,
  removeCartItem,
  type CartItem,
  updateCartItemQuantity,
} from "@/lib/cart";

interface CartDrawerProps {
  open: boolean;
  onClose: () => void;
}

export default function CartDrawer({ open, onClose }: CartDrawerProps) {
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

  return (
    <AnimatePresence>
      {open ? (
        <motion.div
          className="fixed inset-0 z-[95] bg-black/35 backdrop-blur-[1px]"
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          exit={{ opacity: 0 }}
          onClick={onClose}
        >
          <motion.aside
            initial={{ x: 460 }}
            animate={{ x: 0 }}
            exit={{ x: 460 }}
            transition={{ type: "spring", stiffness: 320, damping: 34 }}
            className="ml-auto h-full w-full max-w-[430px] bg-[#f6f1e8] border-l border-[#e6d9c5] shadow-[-12px_0_36px_rgba(0,0,0,0.18)]"
            onClick={(event) => event.stopPropagation()}
          >
            <div className="h-full flex flex-col">
              <div className="flex items-center justify-between px-5 py-4 border-b border-[#e6d9c5]">
                <h2 className="text-xl font-extrabold tracking-tight text-black">Cart</h2>
                <button
                  type="button"
                  onClick={onClose}
                  className="text-gray-500 hover:text-black transition"
                  aria-label="Close cart"
                >
                  <span className="material-symbols-outlined text-[22px]">close</span>
                </button>
              </div>

              <div className="flex-1 overflow-y-auto px-4 py-4">
                {!loaded ? (
                  <p className="text-sm text-gray-500">Loading cart...</p>
                ) : items.length === 0 ? (
                  <div className="rounded-2xl bg-white px-4 py-5 border border-[#ece0cf]">
                    <p className="text-base font-semibold text-black">Your cart is empty</p>
                    <p className="mt-1 text-sm text-gray-600">Add products to start your order.</p>
                    <Link
                      href="/shop"
                      onClick={onClose}
                      className="mt-4 inline-flex items-center text-sm font-semibold text-black hover:text-accent transition"
                    >
                      Continue shopping
                    </Link>
                  </div>
                ) : (
                  <div className="space-y-3">
                    {items.map((item) => (
                      <article
                        key={`${item.slug}-${item.selectedColor ?? "default"}`}
                        className="rounded-2xl border border-[#ece0cf] bg-white p-3"
                      >
                        <div className="flex gap-3">
                          <Link href={`/products/${item.slug}`} onClick={onClose} className="shrink-0">
                            <Image
                              src={item.imageSrc}
                              alt={item.title}
                              width={72}
                              height={72}
                              className="h-[72px] w-[72px] rounded-xl object-cover"
                            />
                          </Link>
                          <div className="min-w-0 flex-1">
                            <Link
                              href={`/products/${item.slug}`}
                              onClick={onClose}
                              className="text-sm font-bold text-black hover:text-accent transition line-clamp-2"
                            >
                              {item.title}
                            </Link>
                            {item.selectedColor ? (
                              <p className="text-xs text-gray-500 mt-1">Option: {item.selectedColor}</p>
                            ) : null}
                            <p className="mt-1 text-sm font-semibold text-black">
                              {formatPrice(item.price)}
                            </p>
                          </div>
                          <button
                            type="button"
                            onClick={() => setItems(removeCartItem(item.slug, item.selectedColor))}
                            className="text-gray-400 hover:text-black transition"
                            aria-label="Remove item"
                          >
                            <span className="material-symbols-outlined text-[19px]">delete</span>
                          </button>
                        </div>

                        <div className="mt-3 flex items-center gap-2">
                          <button
                            type="button"
                            onClick={() =>
                              setItems(
                                updateCartItemQuantity(item.slug, item.selectedColor, item.quantity - 1)
                              )
                            }
                            className="h-7 w-7 rounded-full bg-cream-dark text-black hover:bg-[#eadbc4] transition"
                            aria-label="Decrease quantity"
                          >
                            -
                          </button>
                          <span className="w-7 text-center text-sm font-semibold text-black">
                            {item.quantity}
                          </span>
                          <button
                            type="button"
                            onClick={() =>
                              setItems(
                                updateCartItemQuantity(item.slug, item.selectedColor, item.quantity + 1)
                              )
                            }
                            className="h-7 w-7 rounded-full bg-cream-dark text-black hover:bg-[#eadbc4] transition"
                            aria-label="Increase quantity"
                          >
                            +
                          </button>
                        </div>
                      </article>
                    ))}
                  </div>
                )}
              </div>

              <div className="border-t border-[#e6d9c5] px-5 py-4">
                <div className="flex items-center justify-between text-sm">
                  <span className="text-gray-600">Subtotal</span>
                  <span className="font-semibold text-black">{formatPrice(subtotal)}</span>
                </div>
                <button
                  type="button"
                  className="mt-3 w-full rounded-full bg-black py-3 text-sm font-semibold text-white hover:bg-[#222] transition"
                >
                  Checkout
                </button>
                <button
                  type="button"
                  onClick={() => {
                    clearCart();
                    setItems([]);
                  }}
                  className="mt-2 w-full rounded-full bg-white py-3 text-sm font-semibold text-black hover:bg-[#f6f6f6] transition"
                >
                  Clear Cart
                </button>
              </div>
            </div>
          </motion.aside>
        </motion.div>
      ) : null}
    </AnimatePresence>
  );
}

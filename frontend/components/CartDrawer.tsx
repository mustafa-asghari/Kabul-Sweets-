"use client";

import { AnimatePresence, motion } from "framer-motion";
import Image from "next/image";
import Link from "next/link";
import { useEffect, useState } from "react";
import { formatPrice } from "@/data/storefront";
import { ApiError, apiRequest } from "@/lib/api-client";
import { useAuth } from "@/context/AuthContext";
import { useCart } from "@/context/CartContext";

interface CartDrawerProps {
  open: boolean;
  onClose: () => void;
}

interface CustomCakeCartSummary {
  id: string;
  flavor: string;
  status: string;
  diameter_inches: number;
  predicted_price: string | null;
  final_price: string | null;
  checkout_url: string | null;
  created_at: string;
}

function cakeStatusLabel(status: string) {
  switch (status) {
    case "pending_review":
      return "Pending Review";
    case "approved_awaiting_payment":
      return "Approved - Awaiting Payment";
    case "paid":
      return "Paid";
    case "in_production":
      return "In Production";
    case "completed":
      return "Completed";
    case "rejected":
      return "Rejected";
    case "cancelled":
      return "Cancelled";
    default:
      return status.replace(/_/g, " ");
  }
}

function toNumber(value: string | number | null | undefined) {
  if (typeof value === "number") {
    return value;
  }
  const parsed = Number(value);
  return Number.isFinite(parsed) ? parsed : 0;
}

export default function CartDrawer({ open, onClose }: CartDrawerProps) {
  const { accessToken, isAuthenticated, user } = useAuth();
  const {
    lines,
    subtotal,
    loading,
    checkoutLoading,
    cartError,
    removeItem,
    updateQuantity,
    clearAll,
    checkout,
  } = useCart();

  const [customerPhone, setCustomerPhone] = useState(user?.phone || "");
  const [pickupDate, setPickupDate] = useState("");
  const [pickupTimeSlot, setPickupTimeSlot] = useState("");
  const [specialInstructions, setSpecialInstructions] = useState("");
  const [checkoutError, setCheckoutError] = useState<string | null>(null);
  const [customCakes, setCustomCakes] = useState<CustomCakeCartSummary[]>([]);
  const [loadingCustomCakes, setLoadingCustomCakes] = useState(false);

  const openAuthPrompt = () => {
    window.dispatchEvent(new Event("open-auth-modal"));
  };

  useEffect(() => {
    setCustomerPhone(user?.phone || "");
  }, [user?.phone]);

  useEffect(() => {
    if (!open || !isAuthenticated || !accessToken) {
      if (!isAuthenticated) {
        setCustomCakes([]);
      }
      return;
    }

    let cancelled = false;
    setLoadingCustomCakes(true);

    apiRequest<CustomCakeCartSummary[]>("/api/v1/custom-cakes/my-cakes", {
      token: accessToken,
    })
      .then((data) => {
        if (!cancelled) {
          setCustomCakes(data);
        }
      })
      .catch(() => {
        if (!cancelled) {
          setCustomCakes([]);
        }
      })
      .finally(() => {
        if (!cancelled) {
          setLoadingCustomCakes(false);
        }
      });

    return () => {
      cancelled = true;
    };
  }, [open, isAuthenticated, accessToken]);

  const handleCheckout = async () => {
    setCheckoutError(null);
    try {
      const result = await checkout({
        customerPhone,
        pickupDate,
        pickupTimeSlot,
        specialInstructions,
      });
      onClose();
      window.location.href = result.checkoutUrl;
    } catch (error) {
      if (error instanceof ApiError) {
        setCheckoutError(error.detail);
      } else {
        setCheckoutError("Checkout failed. Please try again.");
      }
    }
  };

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

              <div className="flex-1 overflow-y-auto px-4 py-4 space-y-4">
                {!isAuthenticated ? (
                  <div className="rounded-2xl bg-white px-4 py-5 border border-[#ece0cf]">
                    <p className="text-base font-semibold text-black">Login required</p>
                    <p className="mt-1 text-sm text-gray-600">
                      Please login to use your server cart and place orders.
                    </p>
                    <button
                      type="button"
                      onClick={() => {
                        onClose();
                        openAuthPrompt();
                      }}
                      className="mt-4 inline-flex items-center rounded-full bg-black px-4 py-2 text-sm font-semibold text-white"
                    >
                      Login / Register
                    </button>
                  </div>
                ) : loading ? (
                  <p className="text-sm text-gray-500">Loading cart...</p>
                ) : lines.length === 0 ? (
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
                  <>
                    <div className="space-y-3">
                      {lines.map((item) => (
                        <article
                          key={item.id}
                          className="rounded-2xl border border-[#ece0cf] bg-white p-3"
                        >
                          <div className="flex gap-3">
                            <Link href={`/products/${item.slug}`} onClick={onClose} className="shrink-0">
                              <Image
                                src={item.imageSrc}
                                alt={item.title}
                                width={72}
                                height={72}
                                sizes="72px"
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
                              {item.optionLabel ? (
                                <p className="text-xs text-gray-500 mt-1">Option: {item.optionLabel}</p>
                              ) : null}
                              <p className="mt-1 text-sm font-semibold text-black">{formatPrice(item.price)}</p>
                            </div>
                            <button
                              type="button"
                              onClick={() => removeItem(item.id)}
                              className="text-gray-400 hover:text-black transition"
                              aria-label="Remove item"
                            >
                              <span className="material-symbols-outlined text-[19px]">delete</span>
                            </button>
                          </div>

                          <div className="mt-3 flex items-center gap-2">
                            <button
                              type="button"
                              onClick={() => updateQuantity(item.id, Math.max(0, item.quantity - 1))}
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
                              onClick={() => updateQuantity(item.id, item.quantity + 1)}
                              className="h-7 w-7 rounded-full bg-cream-dark text-black hover:bg-[#eadbc4] transition"
                              aria-label="Increase quantity"
                            >
                              +
                            </button>
                          </div>
                        </article>
                      ))}
                    </div>

                    <div className="rounded-2xl border border-[#ece0cf] bg-white p-4 space-y-3">
                      <h3 className="text-sm font-bold text-black">Checkout details</h3>
                      <label className="block text-xs text-gray-600">
                        Phone
                        <input
                          type="text"
                          value={customerPhone}
                          onChange={(event) => setCustomerPhone(event.target.value)}
                          className="mt-1 w-full rounded-lg border border-[#e8dcc9] px-3 py-2 text-sm"
                        />
                      </label>
                      <label className="block text-xs text-gray-600">
                        Pickup Date (optional)
                        <input
                          type="date"
                          value={pickupDate}
                          onChange={(event) => setPickupDate(event.target.value)}
                          className="mt-1 w-full rounded-lg border border-[#e8dcc9] px-3 py-2 text-sm"
                        />
                      </label>
                      <label className="block text-xs text-gray-600">
                        Pickup Time Slot (optional)
                        <input
                          type="text"
                          value={pickupTimeSlot}
                          onChange={(event) => setPickupTimeSlot(event.target.value)}
                          placeholder="e.g. 3:00 PM - 4:00 PM"
                          className="mt-1 w-full rounded-lg border border-[#e8dcc9] px-3 py-2 text-sm"
                        />
                      </label>
                      <label className="block text-xs text-gray-600">
                        Special Instructions
                        <textarea
                          value={specialInstructions}
                          onChange={(event) => setSpecialInstructions(event.target.value)}
                          rows={3}
                          className="mt-1 w-full rounded-lg border border-[#e8dcc9] px-3 py-2 text-sm"
                        />
                      </label>
                      <p className="text-[11px] text-gray-500 leading-relaxed">
                        Your payment is authorized first and marked as awaiting confirmation.
                        The card is charged only after admin approval.
                      </p>
                    </div>
                  </>
                )}

                {isAuthenticated ? (
                  <div className="rounded-2xl border border-[#ece0cf] bg-white p-4 space-y-3">
                    <div className="flex items-center justify-between gap-3">
                      <h3 className="text-sm font-bold text-black">Custom cake requests</h3>
                      <Link
                        href="/custom-cakes"
                        onClick={onClose}
                        className="text-xs font-semibold text-black hover:text-accent transition"
                      >
                        Open
                      </Link>
                    </div>

                    {loadingCustomCakes ? (
                      <p className="text-xs text-gray-500">Loading custom cakes...</p>
                    ) : customCakes.length === 0 ? (
                      <p className="text-xs text-gray-500">No custom cake requests yet.</p>
                    ) : (
                      <div className="space-y-2">
                        {customCakes.slice(0, 3).map((cake) => {
                          const price = cake.final_price ?? cake.predicted_price;
                          const payable = cake.status === "approved_awaiting_payment" && Boolean(cake.checkout_url);

                          return (
                            <article key={cake.id} className="rounded-xl border border-[#ece0cf] p-3">
                              <p className="text-xs font-semibold text-black">
                                {cake.flavor} ({cake.diameter_inches} inch)
                              </p>
                              <p className="mt-1 text-[11px] text-gray-600">
                                {cakeStatusLabel(cake.status)} - {formatPrice(toNumber(price))}
                              </p>
                              {payable ? (
                                <a
                                  href={cake.checkout_url || "#"}
                                  className="mt-2 inline-flex rounded-full bg-black px-3 py-1.5 text-[11px] font-semibold text-white hover:bg-[#222] transition"
                                >
                                  Pay custom cake
                                </a>
                              ) : null}
                            </article>
                          );
                        })}
                      </div>
                    )}
                  </div>
                ) : null}

                {cartError ? <p className="text-xs text-red-600">{cartError}</p> : null}
                {checkoutError ? <p className="text-xs text-red-600">{checkoutError}</p> : null}
              </div>

              <div className="border-t border-[#e6d9c5] px-5 py-4">
                <div className="flex items-center justify-between text-sm">
                  <span className="text-gray-600">Subtotal</span>
                  <span className="font-semibold text-black">{formatPrice(subtotal)}</span>
                </div>
                <button
                  type="button"
                  onClick={handleCheckout}
                  disabled={!isAuthenticated || lines.length === 0 || checkoutLoading}
                  className="mt-3 w-full rounded-full bg-black py-3 text-sm font-semibold text-white hover:bg-[#222] transition disabled:opacity-60"
                >
                  {checkoutLoading ? "Please wait..." : "Authorize Payment"}
                </button>
                <button
                  type="button"
                  onClick={() => clearAll()}
                  disabled={!isAuthenticated || lines.length === 0}
                  className="mt-2 w-full rounded-full bg-white py-3 text-sm font-semibold text-black hover:bg-[#f6f6f6] transition disabled:opacity-60"
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

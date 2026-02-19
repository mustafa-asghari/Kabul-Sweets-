"use client";

import { Suspense, useCallback, useEffect, useState } from "react";
import Link from "next/link";
import { useSearchParams } from "next/navigation";
import Navbar from "@/components/Navbar";
import Footer from "@/components/Footer";
import { ApiError, apiRequest } from "@/lib/api-client";
import { useAuth } from "@/context/AuthContext";
import { formatPrice } from "@/data/storefront";

interface OrderSummary {
  id: string;
  order_number: string;
  customer_name: string;
  status: string;
  has_cake: boolean;
  total: string | number;
  pickup_date: string | null;
  pickup_time_slot: string | null;
  created_at: string;
  items?: OrderItemSummary[];
}

interface OrderItemSummary {
  product_id: string | null;
  product_name: string;
  variant_name: string | null;
  quantity: number;
  unit_price?: string | number;
  line_total?: string | number;
}

interface CustomCakeSummary {
  id: string;
  flavor: string;
  status: string;
  diameter_inches: number;
  predicted_price: string | null;
  final_price: string | null;
  predicted_servings: number | null;
  requested_date: string | null;
  time_slot: string | null;
  checkout_url: string | null;
  created_at: string;
}

interface OrderDetailResponse {
  id: string;
  items: OrderItemSummary[];
}

interface ProductLookupResponse {
  slug: string;
}

function statusLabel(status: string | null | undefined) {
  switch (status) {
    case "pending_approval":
      return "Approved - Awaiting Payment";
    case "pending":
      return "Under Review";
    case "confirmed":
      return "Confirmed";
    case "paid":
      return "Paid";
    case "cancelled":
      return "Rejected / Cancelled";
    case "completed":
      return "Completed";
    default:
      return (status ?? "unknown").replace(/_/g, " ");
  }
}

function cakeStatusLabel(status: string | null | undefined) {
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
      return (status ?? "unknown").replace(/_/g, " ");
  }
}

function toNumber(value: string | number | null | undefined) {
  if (typeof value === "number") {
    return value;
  }
  const parsed = Number(value);
  return Number.isFinite(parsed) ? parsed : 0;
}

function toReadablePickup(dateValue: string | null, timeSlot: string | null) {
  if (!dateValue) {
    return "Not set";
  }
  const parsed = new Date(dateValue);
  if (Number.isNaN(parsed.getTime())) {
    return "Not set";
  }

  const dateLabel = parsed.toLocaleDateString("en-AU", {
    day: "2-digit",
    month: "short",
    year: "numeric",
  });
  if (!timeSlot) {
    return dateLabel;
  }
  return `${dateLabel} (${timeSlot})`;
}

function OrdersPageContent() {
  const searchParams = useSearchParams();
  const { accessToken, isAuthenticated, loading: authLoading } = useAuth();
  const [orders, setOrders] = useState<OrderSummary[]>([]);
  const [customCakes, setCustomCakes] = useState<CustomCakeSummary[]>([]);
  const [productSlugById, setProductSlugById] = useState<Record<string, string>>({});
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [payingOrderId, setPayingOrderId] = useState<string | null>(null);
  const [deletingOrderId, setDeletingOrderId] = useState<string | null>(null);
  const [orderActionErrors, setOrderActionErrors] = useState<Record<string, string>>({});
  const [payingCakeId, setPayingCakeId] = useState<string | null>(null);
  const [deletingCakeId, setDeletingCakeId] = useState<string | null>(null);
  const [cakeActionErrors, setCakeActionErrors] = useState<Record<string, string>>({});
  const submittedOrderNumber = searchParams.get("order");
  const showSubmittedBanner = searchParams.get("submitted") === "1";

  const fetchOrders = useCallback(async (background = false) => {
    if (!accessToken || !isAuthenticated) {
      setOrders([]);
      setCustomCakes([]);
      setProductSlugById({});
      setLoading(false);
      return;
    }

    if (!background) {
      setLoading(true);
      setError(null);
    }
    try {
      const [ordersResult, cakesResult] = await Promise.allSettled([
        apiRequest<OrderSummary[]>("/api/v1/orders/my-orders", {
          token: accessToken,
        }),
        apiRequest<CustomCakeSummary[]>("/api/v1/custom-cakes/my-cakes", {
          token: accessToken,
        }),
      ]);

      // Surface any fetch errors so they're visible (don't silently show empty)
      if (!background) {
        const errors: string[] = [];
        if (ordersResult.status === "rejected") {
          const reason = ordersResult.reason;
          errors.push(`Orders: ${reason instanceof ApiError ? reason.detail : reason instanceof Error ? reason.message : "failed"}`);
        }
        if (cakesResult.status === "rejected") {
          const reason = cakesResult.reason;
          errors.push(`Custom cakes: ${reason instanceof ApiError ? reason.detail : reason instanceof Error ? reason.message : "failed"}`);
        }
        if (errors.length > 0) {
          setError(errors.join(" | "));
        }
      }

      const rawOrders = ordersResult.status === "fulfilled" ? ordersResult.value : [];
      const rawCakes = cakesResult.status === "fulfilled" ? cakesResult.value : [];
      const ordersData = Array.isArray(rawOrders) ? rawOrders : [];
      const cakesData = Array.isArray(rawCakes) ? rawCakes : [];
      const visibleCakes = cakesData.filter((cake) => cake.status !== "cancelled");

      const detailPairs = await Promise.all(
        ordersData.map(async (order) => {
          try {
            const detail = await apiRequest<OrderDetailResponse>(
              `/api/v1/orders/my-orders/${order.id}`,
              {
                token: accessToken,
              }
            );
            return [order.id, detail.items || []] as const;
          } catch {
            return [order.id, [] as OrderItemSummary[]] as const;
          }
        })
      );

      const orderItemsByOrderId = new Map<string, OrderItemSummary[]>(detailPairs);
      const ordersWithItems = ordersData.map((order) => ({
        ...order,
        items: orderItemsByOrderId.get(order.id) || [],
      }));

      const uniqueProductIds = [
        ...new Set(
          ordersWithItems.flatMap((order) =>
            (order.items || [])
              .map((item) => item.product_id)
              .filter((value): value is string => Boolean(value))
          )
        ),
      ];

      const productSlugPairs = await Promise.all(
        uniqueProductIds.map(async (productId) => {
          try {
            const product = await apiRequest<ProductLookupResponse>(`/api/v1/products/${productId}`);
            return [productId, product.slug] as const;
          } catch {
            return [productId, ""] as const;
          }
        })
      );

      const nextProductSlugById: Record<string, string> = {};
      for (const [productId, slug] of productSlugPairs) {
        if (slug) {
          nextProductSlugById[productId] = slug;
        }
      }

      setOrders(ordersWithItems);
      setCustomCakes(visibleCakes);
      setProductSlugById(nextProductSlugById);
    } catch (fetchError) {
      if (!background) {
        if (fetchError instanceof ApiError) {
          setError(fetchError.detail);
        } else if (fetchError instanceof Error) {
          setError(fetchError.message);
        } else {
          setError("Unable to load orders. Please refresh the page.");
        }
        setOrders([]);
        setCustomCakes([]);
        setProductSlugById({});
      }
    } finally {
      if (!background) {
        setLoading(false);
      }
    }
  }, [accessToken, isAuthenticated]);

  useEffect(() => {
    if (authLoading) {
      return;
    }
    fetchOrders(false);
  }, [authLoading, fetchOrders]);

  useEffect(() => {
    if (authLoading || !isAuthenticated || !accessToken) {
      return;
    }

    const interval = window.setInterval(() => {
      if (document.visibilityState === "visible") {
        fetchOrders(true);
      }
    }, 8000);

    return () => window.clearInterval(interval);
  }, [authLoading, isAuthenticated, accessToken, fetchOrders]);

  const handleOrderPayNow = useCallback(
    async (orderId: string) => {
      if (!accessToken) {
        return;
      }

      setPayingOrderId(orderId);
      setOrderActionErrors((prev) => ({ ...prev, [orderId]: "" }));

      try {
        const result = await apiRequest<{ checkout_url: string }>(
          `/api/v1/payments/${orderId}/checkout`,
          {
            method: "POST",
            token: accessToken,
          }
        );

        if (!result.checkout_url) {
          throw new ApiError(400, "No checkout URL returned for this order.");
        }
        window.location.href = result.checkout_url;
      } catch (actionError) {
        const detail =
          actionError instanceof ApiError ? actionError.detail : "Unable to open checkout.";
        setOrderActionErrors((prev) => ({ ...prev, [orderId]: detail }));
      } finally {
        setPayingOrderId(null);
      }
    },
    [accessToken]
  );

  const handleDeleteOrder = useCallback(
    async (orderId: string, orderNumber: string) => {
      if (!accessToken) {
        return;
      }

      const ok = window.confirm(
        `Delete order ${orderNumber}? This is permanent and cannot be undone.`
      );
      if (!ok) {
        return;
      }

      setDeletingOrderId(orderId);
      setOrderActionErrors((prev) => ({ ...prev, [orderId]: "" }));

      try {
        await apiRequest<{ message: string }>(`/api/v1/orders/my-orders/${orderId}`, {
          method: "DELETE",
          token: accessToken,
        });
        setOrders((prev) => prev.filter((order) => order.id !== orderId));
      } catch (actionError) {
        const detail =
          actionError instanceof ApiError ? actionError.detail : "Unable to delete this order.";
        setOrderActionErrors((prev) => ({ ...prev, [orderId]: detail }));
      } finally {
        setDeletingOrderId(null);
      }
    },
    [accessToken]
  );

  const handlePayNow = useCallback(async (cakeId: string) => {
    if (!accessToken) {
      return;
    }

    setPayingCakeId(cakeId);
    setCakeActionErrors((prev) => ({ ...prev, [cakeId]: "" }));

    try {
      const result = await apiRequest<{ checkout_url: string }>(
        `/api/v1/custom-cakes/${cakeId}/checkout`,
        {
          method: "POST",
          token: accessToken,
        }
      );

      if (!result.checkout_url) {
        throw new ApiError(400, "No checkout URL returned for this request.");
      }
      window.location.href = result.checkout_url;
    } catch (actionError) {
      const detail = actionError instanceof ApiError ? actionError.detail : "Unable to open checkout.";
      setCakeActionErrors((prev) => ({ ...prev, [cakeId]: detail }));
    } finally {
      setPayingCakeId(null);
    }
  }, [accessToken]);

  const handleDeleteCake = useCallback(
    async (cakeId: string, flavor: string) => {
      if (!accessToken) {
        return;
      }

      const ok = window.confirm(
        `Delete this custom cake request for ${flavor}? This cannot be undone.`
      );
      if (!ok) {
        return;
      }

      setDeletingCakeId(cakeId);
      setCakeActionErrors((prev) => ({ ...prev, [cakeId]: "" }));

      try {
        await apiRequest<{ message: string }>(`/api/v1/custom-cakes/${cakeId}/cancel`, {
          method: "POST",
          token: accessToken,
          body: {
            reason: "Customer deleted request from orders page.",
          },
        });
        setCustomCakes((prev) => prev.filter((cake) => cake.id !== cakeId));
        await fetchOrders(true);
      } catch (actionError) {
        const detail =
          actionError instanceof ApiError ? actionError.detail : "Unable to delete this request.";
        setCakeActionErrors((prev) => ({ ...prev, [cakeId]: detail }));
      } finally {
        setDeletingCakeId(null);
      }
    },
    [accessToken, fetchOrders]
  );

  return (
    <>
      <Navbar />
      <main className="flex-1 pb-20">
        <section className="max-w-[980px] mx-auto px-6 pt-8">
          <div className="rounded-[2rem] bg-cream-dark px-6 py-12">
            <h1 className="text-4xl font-extrabold tracking-tight text-black">My Orders</h1>
            <p className="mt-2 text-sm text-gray-600">
              Track your regular orders and custom cake requests.
            </p>
          </div>
        </section>

        <section className="max-w-[980px] mx-auto px-6 pt-8 space-y-6">
          {showSubmittedBanner ? (
            <div className="rounded-[1.5rem] border border-[#e6d6bf] bg-[#fff7ea] p-4 text-sm text-[#7a5a1f]">
              Order request submitted{submittedOrderNumber ? ` (${submittedOrderNumber})` : ""}. We will review it first. Once approved, you can pay from this page.
            </div>
          ) : null}
          {!authLoading && !isAuthenticated ? (
            <div className="rounded-[1.5rem] bg-white border border-[#eadcc8] p-6">
              <p className="text-black font-semibold">Please login to view your orders.</p>
              <button
                type="button"
                onClick={() => window.dispatchEvent(new Event("open-auth-modal"))}
                className="mt-4 rounded-full bg-black px-5 py-2 text-sm font-semibold text-white"
              >
                Login / Register
              </button>
            </div>
          ) : loading ? (
            <p className="text-sm text-gray-500">Loading orders...</p>
          ) : (
            <>
              {error ? (
                <div className="rounded-[1.5rem] border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">
                  {error}
                </div>
              ) : null}
              <section className="space-y-4">
                <h2 className="text-xl font-extrabold tracking-tight text-black">Product Orders</h2>
                {orders.length === 0 ? (
                  <div className="rounded-[1.5rem] bg-white border border-[#eadcc8] p-6">
                    <p className="text-black font-semibold">No product orders yet.</p>
                  </div>
                ) : (
                  orders.map((order) => {
                    const payable = order.status === "pending_approval";
                    const deletable = order.status === "pending";

                    return (
                    <article key={order.id} className="rounded-[1.5rem] bg-white border border-[#eadcc8] p-5">
                      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-2">
                        <div>
                          <h3 className="text-lg font-bold text-black">{order.order_number}</h3>
                          <p className="text-sm text-gray-500">{new Date(order.created_at).toLocaleString()}</p>
                        </div>
                        <span className="inline-flex rounded-full bg-cream-dark px-3 py-1 text-xs font-semibold text-black capitalize">
                          {statusLabel(order.status)}
                        </span>
                      </div>
                      <div className="mt-4 grid grid-cols-1 sm:grid-cols-3 gap-3 text-sm text-gray-600">
                        <p>
                          <span className="font-semibold text-black">Total:</span>{" "}
                          {formatPrice(toNumber(order.total))}
                        </p>
                        <p>
                          <span className="font-semibold text-black">Cake Order:</span>{" "}
                          {order.has_cake ? "Yes" : "No"}
                        </p>
                        <p>
                          <span className="font-semibold text-black">Pickup:</span>{" "}
                          {toReadablePickup(order.pickup_date, order.pickup_time_slot)}
                        </p>
                      </div>
                      <div className="mt-4">
                        <p className="text-xs font-semibold uppercase tracking-wide text-gray-500">Ordered items</p>
                        {!order.items || order.items.length === 0 ? (
                          <p className="mt-2 text-sm text-gray-500">No item references available.</p>
                        ) : (
                          <ul className="mt-2 space-y-2">
                            {order.items.map((item, index) => {
                              const slug = item.product_id ? productSlugById[item.product_id] : "";
                              return (
                                <li
                                  key={`${order.id}-${item.product_id || item.product_name}-${index}`}
                                  className="rounded-xl border border-[#efe4d3] bg-[#fdfaf5] p-3 text-sm"
                                >
                                  <div className="flex flex-wrap items-center justify-between gap-2">
                                    {slug ? (
                                      <Link
                                        href={`/products/${slug}`}
                                        className="font-semibold text-black underline decoration-[#d7b883] underline-offset-4 hover:text-accent transition"
                                      >
                                        {item.product_name}
                                      </Link>
                                    ) : (
                                      <span className="font-semibold text-black">{item.product_name}</span>
                                    )}
                                    <span className="text-xs text-gray-600">
                                      Qty: <span className="font-semibold text-black">{item.quantity}</span>
                                    </span>
                                  </div>
                                  <div className="mt-1 flex flex-wrap items-center gap-x-4 gap-y-1 text-xs text-gray-600">
                                    <span>
                                      Variant:{" "}
                                      <span className="font-medium text-black">{item.variant_name || "Default"}</span>
                                    </span>
                                    <span>
                                      Unit:{" "}
                                      <span className="font-medium text-black">
                                        {formatPrice(toNumber(item.unit_price))}
                                      </span>
                                    </span>
                                    <span>
                                      Line total:{" "}
                                      <span className="font-semibold text-black">
                                        {formatPrice(toNumber(item.line_total))}
                                      </span>
                                    </span>
                                  </div>
                                </li>
                              );
                            })}
                          </ul>
                        )}
                      </div>
                      {payable || deletable ? (
                        <div className="mt-4 flex items-center gap-2">
                          {payable ? (
                            <button
                              type="button"
                              disabled={payingOrderId === order.id || deletingOrderId === order.id}
                              onClick={() => handleOrderPayNow(order.id)}
                              className="inline-flex rounded-full bg-black px-4 py-2 text-xs font-semibold text-white hover:bg-[#222] transition disabled:opacity-60 disabled:cursor-not-allowed"
                            >
                              {payingOrderId === order.id ? "Opening checkout..." : "Pay Now"}
                            </button>
                          ) : null}
                          {deletable ? (
                            <button
                              type="button"
                              disabled={deletingOrderId === order.id || payingOrderId === order.id}
                              onClick={() => handleDeleteOrder(order.id, order.order_number)}
                              className="inline-flex rounded-full border border-red-300 bg-red-50 px-4 py-2 text-xs font-semibold text-red-700 hover:bg-red-100 transition disabled:opacity-60 disabled:cursor-not-allowed"
                            >
                              {deletingOrderId === order.id ? "Deleting..." : "Delete Order"}
                            </button>
                          ) : null}
                        </div>
                      ) : null}
                      {orderActionErrors[order.id] ? (
                        <p className="mt-3 text-xs font-medium text-red-600">{orderActionErrors[order.id]}</p>
                      ) : null}
                    </article>
                    );
                  })
                )}
              </section>

              <section className="space-y-4">
                <h2 className="text-xl font-extrabold tracking-tight text-black">Custom Cake Requests</h2>
                {customCakes.length === 0 ? (
                  <div className="rounded-[1.5rem] bg-white border border-[#eadcc8] p-6">
                    <p className="text-black font-semibold">No custom cake requests yet.</p>
                  </div>
                ) : (
                  customCakes.map((cake) => {
                    const payable = cake.status === "approved_awaiting_payment";
                    const deletable = ["pending_review", "rejected"].includes(
                      cake.status
                    );
                    const displayPrice = cake.final_price ?? cake.predicted_price;

                    return (
                      <article key={cake.id} className="rounded-[1.5rem] bg-white border border-[#eadcc8] p-5">
                        <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-2">
                          <div>
                            <h3 className="text-lg font-bold text-black">{cake.flavor}</h3>
                            <p className="text-sm text-gray-500">{new Date(cake.created_at).toLocaleString()}</p>
                          </div>
                          <span className="inline-flex rounded-full bg-cream-dark px-3 py-1 text-xs font-semibold text-black capitalize">
                            {cakeStatusLabel(cake.status)}
                          </span>
                        </div>
                        <div className="mt-4 grid grid-cols-1 sm:grid-cols-2 gap-3 text-sm text-gray-600">
                          <p>
                            <span className="font-semibold text-black">Size:</span>{" "}
                            {cake.diameter_inches} inch
                          </p>
                          <p>
                            <span className="font-semibold text-black">Servings:</span>{" "}
                            {cake.predicted_servings ?? "N/A"}
                          </p>
                          <p>
                            <span className="font-semibold text-black">Price:</span>{" "}
                            {formatPrice(toNumber(displayPrice))}
                          </p>
                          <p>
                            <span className="font-semibold text-black">Pickup:</span>{" "}
                            {toReadablePickup(cake.requested_date, cake.time_slot)}
                          </p>
                          <p>
                            <span className="font-semibold text-black">Reference:</span>{" "}
                            <Link
                              href={`/custom-cakes?request=${encodeURIComponent(
                                cake.id
                              )}#request-${cake.id}`}
                              className="font-semibold text-black underline decoration-[#d7b883] underline-offset-4 hover:text-accent transition"
                            >
                              Open custom cake request
                            </Link>
                          </p>
                        </div>

                        {payable || deletable ? (
                          <div className="mt-4 flex flex-wrap items-center gap-2">
                            {payable ? (
                              <button
                                type="button"
                                disabled={payingCakeId === cake.id || deletingCakeId === cake.id}
                                onClick={() => handlePayNow(cake.id)}
                                className="inline-flex rounded-full bg-black px-4 py-2 text-xs font-semibold text-white hover:bg-[#222] transition disabled:opacity-60 disabled:cursor-not-allowed"
                              >
                                {payingCakeId === cake.id ? "Opening checkout..." : "Pay Now"}
                              </button>
                            ) : null}
                            {deletable ? (
                              <button
                                type="button"
                                disabled={deletingCakeId === cake.id || payingCakeId === cake.id}
                                onClick={() => handleDeleteCake(cake.id, cake.flavor)}
                                className="inline-flex rounded-full border border-red-300 bg-red-50 px-4 py-2 text-xs font-semibold text-red-700 hover:bg-red-100 transition disabled:opacity-60 disabled:cursor-not-allowed"
                              >
                                {deletingCakeId === cake.id ? "Deleting..." : "Delete Request"}
                              </button>
                            ) : null}
                          </div>
                        ) : null}
                        {cakeActionErrors[cake.id] ? (
                          <p className="mt-3 text-xs font-medium text-red-600">{cakeActionErrors[cake.id]}</p>
                        ) : null}
                      </article>
                    );
                  })
                )}
              </section>
            </>
          )}
        </section>
      </main>
      <Footer />
    </>
  );
}

function OrdersPageFallback() {
  return (
    <>
      <Navbar />
      <main className="flex-1 pb-20">
        <section className="max-w-[980px] mx-auto px-6 pt-8">
          <div className="rounded-[2rem] bg-cream-dark px-6 py-12">
            <h1 className="text-4xl font-extrabold tracking-tight text-black">My Orders</h1>
            <p className="mt-2 text-sm text-gray-600">Loading orders...</p>
          </div>
        </section>
      </main>
      <Footer />
    </>
  );
}

export default function OrdersPage() {
  return (
    <Suspense fallback={<OrdersPageFallback />}>
      <OrdersPageContent />
    </Suspense>
  );
}

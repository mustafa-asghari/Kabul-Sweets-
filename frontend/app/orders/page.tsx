"use client";

import { useCallback, useEffect, useState } from "react";
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
  created_at: string;
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

function statusLabel(status: string) {
  switch (status) {
    case "pending_approval":
      return "Awaiting Admin Confirmation";
    case "pending":
      return "Pending Payment";
    case "confirmed":
      return "Confirmed";
    case "paid":
      return "Paid";
    case "cancelled":
      return "Rejected / Cancelled";
    case "completed":
      return "Completed";
    default:
      return status.replace(/_/g, " ");
  }
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

function toReadableDate(value: string | null) {
  if (!value) {
    return "Not set";
  }
  const parsed = new Date(value);
  if (Number.isNaN(parsed.getTime())) {
    return "Not set";
  }
  return parsed.toLocaleDateString();
}

export default function OrdersPage() {
  const { accessToken, isAuthenticated, loading: authLoading } = useAuth();
  const [orders, setOrders] = useState<OrderSummary[]>([]);
  const [customCakes, setCustomCakes] = useState<CustomCakeSummary[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchOrders = useCallback(async () => {
    if (!accessToken || !isAuthenticated) {
      setOrders([]);
      setCustomCakes([]);
      setLoading(false);
      return;
    }

    setLoading(true);
    setError(null);
    try {
      const [ordersData, cakesData] = await Promise.all([
        apiRequest<OrderSummary[]>("/api/v1/orders/my-orders", {
          token: accessToken,
        }),
        apiRequest<CustomCakeSummary[]>("/api/v1/custom-cakes/my-cakes", {
          token: accessToken,
        }),
      ]);

      setOrders(ordersData);
      setCustomCakes(cakesData);
    } catch (fetchError) {
      if (fetchError instanceof ApiError) {
        setError(fetchError.detail);
      } else {
        setError("Unable to load orders.");
      }
      setOrders([]);
      setCustomCakes([]);
    } finally {
      setLoading(false);
    }
  }, [accessToken, isAuthenticated]);

  useEffect(() => {
    if (authLoading) {
      return;
    }
    fetchOrders();
  }, [authLoading, fetchOrders]);

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
          ) : error ? (
            <p className="text-sm text-red-600">{error}</p>
          ) : (
            <>
              <section className="space-y-4">
                <h2 className="text-xl font-extrabold tracking-tight text-black">Product Orders</h2>
                {orders.length === 0 ? (
                  <div className="rounded-[1.5rem] bg-white border border-[#eadcc8] p-6">
                    <p className="text-black font-semibold">No product orders yet.</p>
                  </div>
                ) : (
                  orders.map((order) => (
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
                          {toReadableDate(order.pickup_date)}
                        </p>
                      </div>
                    </article>
                  ))
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
                    const payable = cake.status === "approved_awaiting_payment" && Boolean(cake.checkout_url);
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
                            {toReadableDate(cake.requested_date)}
                            {cake.time_slot ? ` (${cake.time_slot})` : ""}
                          </p>
                        </div>

                        {payable ? (
                          <div className="mt-4">
                            <a
                              href={cake.checkout_url || "#"}
                              className="inline-flex rounded-full bg-black px-4 py-2 text-xs font-semibold text-white hover:bg-[#222] transition"
                            >
                              Pay Now
                            </a>
                          </div>
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

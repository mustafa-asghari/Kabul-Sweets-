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

function toNumber(value: string | number) {
  if (typeof value === "number") {
    return value;
  }
  const parsed = Number(value);
  return Number.isFinite(parsed) ? parsed : 0;
}

export default function OrdersPage() {
  const { accessToken, isAuthenticated, loading: authLoading } = useAuth();
  const [orders, setOrders] = useState<OrderSummary[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchOrders = useCallback(async () => {
    if (!accessToken || !isAuthenticated) {
      setOrders([]);
      setLoading(false);
      return;
    }
    setLoading(true);
    setError(null);
    try {
      const data = await apiRequest<OrderSummary[]>("/api/v1/orders/my-orders", {
        token: accessToken,
      });
      setOrders(data);
    } catch (fetchError) {
      if (fetchError instanceof ApiError) {
        setError(fetchError.detail);
      } else {
        setError("Unable to load orders.");
      }
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
              Track your orders and approval status.
            </p>
          </div>
        </section>

        <section className="max-w-[980px] mx-auto px-6 pt-8">
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
          ) : orders.length === 0 ? (
            <div className="rounded-[1.5rem] bg-white border border-[#eadcc8] p-6">
              <p className="text-black font-semibold">No orders yet.</p>
            </div>
          ) : (
            <div className="space-y-4">
              {orders.map((order) => (
                <article key={order.id} className="rounded-[1.5rem] bg-white border border-[#eadcc8] p-5">
                  <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-2">
                    <div>
                      <h2 className="text-lg font-bold text-black">{order.order_number}</h2>
                      <p className="text-sm text-gray-500">
                        {new Date(order.created_at).toLocaleString()}
                      </p>
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
                      {order.pickup_date ? new Date(order.pickup_date).toLocaleDateString() : "Not set"}
                    </p>
                  </div>
                </article>
              ))}
            </div>
          )}
        </section>
      </main>
      <Footer />
    </>
  );
}

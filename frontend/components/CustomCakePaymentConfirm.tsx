"use client";

import { useEffect, useState } from "react";

import { ApiError, apiRequest } from "@/lib/api-client";

interface CustomCakePaymentConfirmProps {
  customCakeId?: string;
  sessionId?: string;
}

type SyncState = "idle" | "syncing" | "ok" | "error";

export default function CustomCakePaymentConfirm({
  customCakeId,
  sessionId,
}: CustomCakePaymentConfirmProps) {
  const [state, setState] = useState<SyncState>("idle");
  const [message, setMessage] = useState<string>("");

  useEffect(() => {
    if (!customCakeId || !sessionId) {
      return;
    }

    let active = true;
    setState("syncing");
    setMessage("Finalizing payment status...");

    void apiRequest<{ status: string }>("/api/v1/payments/custom-cakes/confirm", {
      method: "POST",
      body: {
        custom_cake_id: customCakeId,
        session_id: sessionId,
      },
    })
      .then((result) => {
        if (!active) {
          return;
        }

        if (result.status === "paid" || result.status === "in_production" || result.status === "completed") {
          setState("ok");
          setMessage("Payment confirmed. Your custom cake is now marked paid.");
          return;
        }

        setState("idle");
        setMessage("");
      })
      .catch((error: unknown) => {
        if (!active) {
          return;
        }

        const detail =
          error instanceof ApiError ? error.detail : "Payment succeeded, but status sync is delayed.";
        setState("error");
        setMessage(`${detail} Please refresh your Orders page in a moment.`);
      });

    return () => {
      active = false;
    };
  }, [customCakeId, sessionId]);

  if (!message) {
    return null;
  }

  const toneClass =
    state === "ok"
      ? "text-green-700 bg-green-50 border-green-200"
      : state === "error"
        ? "text-amber-700 bg-amber-50 border-amber-200"
        : "text-gray-700 bg-white border-[#e8dcc9]";

  return <p className={`mt-4 rounded-xl border px-4 py-2 text-sm ${toneClass}`}>{message}</p>;
}

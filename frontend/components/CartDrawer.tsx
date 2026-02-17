"use client";

import { AnimatePresence, motion } from "framer-motion";
import Image from "next/image";
import Link from "next/link";
import { useEffect, useMemo, useRef, useState } from "react";
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

const WEEKDAY_LABELS = ["M", "T", "W", "T", "F", "S", "S"] as const;
const BUSINESS_HOURS_BY_WEEKDAY: Record<number, { openHour: number; closeHour: number }> = {
  0: { openHour: 9, closeHour: 18 }, // Sunday
  1: { openHour: 9, closeHour: 18 }, // Monday
  2: { openHour: 9, closeHour: 18 }, // Tuesday
  3: { openHour: 9, closeHour: 18 }, // Wednesday
  4: { openHour: 9, closeHour: 18 }, // Thursday
  5: { openHour: 9, closeHour: 19 }, // Friday
  6: { openHour: 9, closeHour: 19 }, // Saturday
};
const PICKUP_BUFFER_HOURS = 1;

interface SelectOption {
  value: string;
  label: string;
}

interface ThemedSelectProps {
  value: string;
  onChange: (next: string) => void;
  options: SelectOption[];
  className?: string;
  placeholder?: string;
}

interface ThemedDatePickerProps {
  value: string;
  onChange: (next: string) => void;
  className?: string;
  minDateValue?: string;
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

function toDateInputValue(date: Date) {
  const year = date.getFullYear();
  const month = `${date.getMonth() + 1}`.padStart(2, "0");
  const day = `${date.getDate()}`.padStart(2, "0");
  return `${year}-${month}-${day}`;
}

function parseDateInputValue(value: string) {
  if (!value) {
    return null;
  }

  const date = new Date(`${value}T00:00:00`);
  if (Number.isNaN(date.getTime())) {
    return null;
  }
  return date;
}

function isSameDate(a: Date, b: Date) {
  return (
    a.getFullYear() === b.getFullYear() &&
    a.getMonth() === b.getMonth() &&
    a.getDate() === b.getDate()
  );
}

function formatDateLabel(value: string) {
  const parsed = parseDateInputValue(value);
  if (!parsed) {
    return "Select date";
  }

  return new Intl.DateTimeFormat("en-AU", {
    day: "numeric",
    month: "long",
    year: "numeric",
  }).format(parsed);
}

function formatTimeLabel(hour: number, minute = 0) {
  const date = new Date();
  date.setHours(hour, minute, 0, 0);
  return new Intl.DateTimeFormat("en-AU", {
    hour: "numeric",
    minute: "2-digit",
    hour12: true,
  }).format(date);
}

function getBusinessHoursForDate(date: Date) {
  return BUSINESS_HOURS_BY_WEEKDAY[date.getDay()] ?? BUSINESS_HOURS_BY_WEEKDAY[1];
}

function getPickupHoursForDate(date: Date, now = new Date()) {
  const { openHour, closeHour } = getBusinessHoursForDate(date);
  let startHour = Math.min(closeHour - 1, openHour + PICKUP_BUFFER_HOURS);

  if (isSameDate(date, now)) {
    const nextWholeHour =
      now.getMinutes() > 0 || now.getSeconds() > 0 || now.getMilliseconds() > 0
        ? now.getHours() + 1
        : now.getHours();
    startHour = Math.max(startHour, nextWholeHour);
  }

  return { startHour, closeHour };
}

function buildTimeSlotOptionsForDate(date: Date): SelectOption[] {
  const { startHour, closeHour } = getPickupHoursForDate(date);
  const options: SelectOption[] = [];
  for (let hour = startHour; hour < closeHour; hour += 1) {
    const fromValue = `${String(hour).padStart(2, "0")}:00`;
    const toValue = `${String(hour + 1).padStart(2, "0")}:00`;
    options.push({
      value: `${fromValue}-${toValue}`,
      label: `${formatTimeLabel(hour)} - ${formatTimeLabel(hour + 1)}`,
    });
  }
  return options;
}

function formatBusinessHoursText(date: Date) {
  const { openHour, closeHour } = getBusinessHoursForDate(date);
  return `${formatTimeLabel(openHour)} - ${formatTimeLabel(closeHour)}`;
}

function ThemedSelect({
  value,
  onChange,
  options,
  className,
  placeholder = "Select option",
}: ThemedSelectProps) {
  const rootRef = useRef<HTMLDivElement | null>(null);
  const [open, setOpen] = useState(false);

  const selected = options.find((option) => option.value === value);

  useEffect(() => {
    const onPointerDown = (event: MouseEvent) => {
      if (!rootRef.current) return;
      if (event.target instanceof Node && !rootRef.current.contains(event.target)) {
        setOpen(false);
      }
    };

    document.addEventListener("mousedown", onPointerDown);
    return () => {
      document.removeEventListener("mousedown", onPointerDown);
    };
  }, []);

  return (
    <div ref={rootRef} className={`relative ${className || ""}`}>
      <button
        type="button"
        aria-haspopup="listbox"
        aria-expanded={open}
        onClick={() => setOpen((current) => !current)}
        className="w-full rounded-lg border border-[#e8dcc9] bg-white px-3 py-2 text-left text-sm text-gray-700 outline-none transition hover:border-[#d8c6ad] focus:ring-2 focus:ring-accent/25"
      >
        <span>{selected?.label || placeholder}</span>
        <span className="pointer-events-none absolute right-3 top-1/2 -translate-y-1/2 text-gray-500 material-symbols-outlined text-[18px]">
          {open ? "expand_less" : "expand_more"}
        </span>
      </button>

      {open ? (
        <div className="absolute z-40 mt-2 max-h-64 w-full overflow-auto rounded-2xl border border-[#e5d5bf] bg-[#fbf7f0] p-1 shadow-[0_16px_40px_rgba(0,0,0,0.12)]">
          <button
            type="button"
            role="option"
            aria-selected={value === ""}
            onClick={() => {
              onChange("");
              setOpen(false);
            }}
            className={`flex w-full items-center justify-between rounded-xl px-3 py-2 text-sm transition ${
              value === "" ? "bg-[#f4e7d2] text-black font-semibold" : "text-gray-700 hover:bg-[#f1e4d0]"
            }`}
          >
            <span>No preference</span>
          </button>
          {options.map((option) => {
            const isSelected = option.value === value;
            return (
              <button
                key={option.value}
                type="button"
                role="option"
                aria-selected={isSelected}
                onClick={() => {
                  onChange(option.value);
                  setOpen(false);
                }}
                className={`flex w-full items-center justify-between rounded-xl px-3 py-2 text-sm transition ${
                  isSelected ? "bg-[#f4e7d2] text-black font-semibold" : "text-gray-700 hover:bg-[#f1e4d0]"
                }`}
              >
                <span>{option.label}</span>
                {isSelected ? (
                  <span className="material-symbols-outlined text-[17px] text-[#ad751c]">check</span>
                ) : null}
              </button>
            );
          })}
        </div>
      ) : null}
    </div>
  );
}

function ThemedDatePicker({ value, onChange, className, minDateValue }: ThemedDatePickerProps) {
  const rootRef = useRef<HTMLDivElement | null>(null);
  const [open, setOpen] = useState(false);

  const selectedDate = useMemo(() => parseDateInputValue(value), [value]);
  const minimumDate = useMemo(() => {
    if (!minDateValue) return null;
    return parseDateInputValue(minDateValue);
  }, [minDateValue]);
  const [viewMonth, setViewMonth] = useState(() => {
    const initial = parseDateInputValue(value) || new Date();
    return new Date(initial.getFullYear(), initial.getMonth(), 1);
  });

  useEffect(() => {
    const onPointerDown = (event: MouseEvent) => {
      if (!rootRef.current) return;
      if (event.target instanceof Node && !rootRef.current.contains(event.target)) {
        setOpen(false);
      }
    };

    document.addEventListener("mousedown", onPointerDown);
    return () => {
      document.removeEventListener("mousedown", onPointerDown);
    };
  }, []);

  useEffect(() => {
    if (!selectedDate) return;
    setViewMonth(new Date(selectedDate.getFullYear(), selectedDate.getMonth(), 1));
  }, [selectedDate]);

  const calendarDays = useMemo(() => {
    const firstOfMonth = new Date(viewMonth.getFullYear(), viewMonth.getMonth(), 1);
    const firstWeekdayMonday = (firstOfMonth.getDay() + 6) % 7;
    const gridStart = new Date(firstOfMonth);
    gridStart.setDate(firstOfMonth.getDate() - firstWeekdayMonday);

    return Array.from({ length: 42 }, (_, index) => {
      const day = new Date(gridStart);
      day.setDate(gridStart.getDate() + index);
      return {
        date: day,
        isCurrentMonth: day.getMonth() === viewMonth.getMonth(),
      };
    });
  }, [viewMonth]);

  const monthLabel = useMemo(
    () =>
      new Intl.DateTimeFormat("en-AU", {
        month: "long",
        year: "numeric",
      }).format(viewMonth),
    [viewMonth]
  );

  return (
    <div ref={rootRef} className={`relative ${className || ""}`}>
      <button
        type="button"
        onClick={() => setOpen((current) => !current)}
        className="w-full rounded-lg border border-[#e8dcc9] bg-white px-3 py-2 text-left text-sm text-gray-700 outline-none transition hover:border-[#d8c6ad] focus:ring-2 focus:ring-accent/25"
      >
        <span>{formatDateLabel(value)}</span>
        <span className="pointer-events-none absolute right-3 top-1/2 -translate-y-1/2 text-gray-500 material-symbols-outlined text-[18px]">
          calendar_month
        </span>
      </button>

      {open ? (
        <div className="absolute z-40 mt-2 w-[310px] rounded-2xl border border-[#e5d5bf] bg-[#fbf7f0] p-4 shadow-[0_16px_40px_rgba(0,0,0,0.12)]">
          <div className="mb-3 flex items-center justify-between">
            <button
              type="button"
              onClick={() =>
                setViewMonth((current) => new Date(current.getFullYear(), current.getMonth() - 1, 1))
              }
              className="inline-flex h-9 w-9 items-center justify-center rounded-full bg-white text-gray-700 transition hover:bg-[#f4e7d2]"
              aria-label="Previous month"
            >
              <span className="material-symbols-outlined text-[18px]">chevron_left</span>
            </button>

            <p className="text-sm font-bold text-black">{monthLabel}</p>

            <button
              type="button"
              onClick={() =>
                setViewMonth((current) => new Date(current.getFullYear(), current.getMonth() + 1, 1))
              }
              className="inline-flex h-9 w-9 items-center justify-center rounded-full bg-white text-gray-700 transition hover:bg-[#f4e7d2]"
              aria-label="Next month"
            >
              <span className="material-symbols-outlined text-[18px]">chevron_right</span>
            </button>
          </div>

          <div className="grid grid-cols-7 gap-1 text-center text-[11px] font-semibold text-gray-500">
            {WEEKDAY_LABELS.map((day, index) => (
              <span key={`${day}-${index}`}>{day}</span>
            ))}
          </div>

          <div className="mt-2 grid grid-cols-7 gap-1">
            {calendarDays.map((entry) => {
              const entryValue = toDateInputValue(entry.date);
              const isSelected = value === entryValue;
              const isDisabled = minimumDate ? entry.date < minimumDate : false;
              return (
                <button
                  key={entryValue}
                  type="button"
                  disabled={isDisabled}
                  onClick={() => {
                    if (isDisabled) return;
                    onChange(entryValue);
                    setOpen(false);
                  }}
                  className={`h-9 rounded-lg text-sm transition ${
                    isSelected
                      ? "bg-[#ad751c] font-semibold text-white"
                      : isDisabled
                        ? "cursor-not-allowed text-gray-300"
                        : entry.isCurrentMonth
                          ? "text-gray-800 hover:bg-[#f4e7d2]"
                          : "text-gray-400 hover:bg-[#f4e7d2]"
                  }`}
                >
                  {entry.date.getDate()}
                </button>
              );
            })}
          </div>

          <div className="mt-3 flex items-center justify-between">
            <button
              type="button"
              onClick={() => onChange("")}
              className="text-xs font-semibold text-gray-600 transition hover:text-black"
            >
              Clear
            </button>
            <button
              type="button"
              onClick={() => {
                const today = new Date();
                today.setHours(0, 0, 0, 0);
                onChange(toDateInputValue(today));
                setOpen(false);
              }}
              className="text-xs font-semibold text-[#ad751c] transition hover:text-[#8f5f13]"
            >
              Today
            </button>
          </div>
        </div>
      ) : null}
    </div>
  );
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
  const minimumPickupDate = useMemo(() => {
    const today = new Date();
    today.setHours(0, 0, 0, 0);
    return toDateInputValue(today);
  }, []);
  const selectedPickupDate = useMemo(() => parseDateInputValue(pickupDate), [pickupDate]);
  const pickupTimeSlotOptions = useMemo(
    () => (selectedPickupDate ? buildTimeSlotOptionsForDate(selectedPickupDate) : []),
    [selectedPickupDate]
  );
  const pickupHoursHint = useMemo(() => {
    if (!selectedPickupDate) {
      return "Select a date to see available pickup hours.";
    }
    if (pickupTimeSlotOptions.length === 0) {
      return "No pickup slots left for this date. Please choose another day.";
    }
    return `Available pickup hours: ${formatBusinessHoursText(selectedPickupDate)}`;
  }, [pickupTimeSlotOptions.length, selectedPickupDate]);

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

  useEffect(() => {
    if (!pickupTimeSlot) {
      return;
    }
    const stillValid = pickupTimeSlotOptions.some((option) => option.value === pickupTimeSlot);
    if (!stillValid) {
      setPickupTimeSlot("");
    }
  }, [pickupTimeSlot, pickupTimeSlotOptions]);

  const handleCheckout = async () => {
    setCheckoutError(null);
    const selectedDate = parseDateInputValue(pickupDate);
    const today = new Date();
    today.setHours(0, 0, 0, 0);

    if (selectedDate && selectedDate < today) {
      setCheckoutError("Pickup date cannot be in the past.");
      return;
    }

    if (pickupTimeSlot && !selectedDate) {
      setCheckoutError("Please select a pickup date before choosing a pickup time slot.");
      return;
    }

    if (selectedDate) {
      const validSlots = buildTimeSlotOptionsForDate(selectedDate);
      if (validSlots.length === 0 && pickupTimeSlot) {
        setCheckoutError("No pickup slots left for the selected date. Please choose another date.");
        return;
      }
      if (pickupTimeSlot && !validSlots.some((slot) => slot.value === pickupTimeSlot)) {
        setCheckoutError("The selected pickup time is no longer available. Please choose a new slot.");
        return;
      }
    }

    const selectedTimeSlotLabel =
      pickupTimeSlotOptions.find((option) => option.value === pickupTimeSlot)?.label || pickupTimeSlot;

    try {
      const result = await checkout({
        customerPhone,
        pickupDate,
        pickupTimeSlot: selectedTimeSlotLabel,
        specialInstructions,
      });
      onClose();
      window.location.href = result.checkoutUrl;
    } catch (error) {
      if (error instanceof ApiError) {
        setCheckoutError(error.detail);
      } else {
        setCheckoutError("Order submission failed. Please try again.");
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
                        <ThemedDatePicker
                          className="mt-1"
                          value={pickupDate}
                          onChange={(next) => setPickupDate(next)}
                          minDateValue={minimumPickupDate}
                        />
                      </label>
                      <label className="block text-xs text-gray-600">
                        Pickup Time Slot (optional)
                        <ThemedSelect
                          className="mt-1"
                          value={pickupTimeSlot}
                          onChange={(next) => setPickupTimeSlot(next)}
                          options={pickupTimeSlotOptions}
                          placeholder={selectedPickupDate ? "Select pickup time" : "Select date first"}
                        />
                        <span className="mt-1 block text-[11px] text-gray-500">{pickupHoursHint}</span>
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
                        Your order is submitted for admin review first.
                        After approval, you can pay from the Orders page.
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
                  {checkoutLoading ? "Please wait..." : "Submit Order"}
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

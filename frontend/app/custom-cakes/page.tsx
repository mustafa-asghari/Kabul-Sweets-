"use client";

import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import Link from "next/link";
import Footer from "@/components/Footer";
import Navbar from "@/components/Navbar";
import ScrollReveal from "@/components/ScrollReveal";
import { ApiError, apiRequest } from "@/lib/api-client";
import { useAuth } from "@/context/AuthContext";

const MAX_REFERENCE_IMAGE_BYTES = 4 * 1024 * 1024;
const ALLOWED_REFERENCE_TYPES = ["image/jpeg", "image/png", "image/webp"];
const AVAILABLE_SIZES_INCHES = [10, 12, 14, 16] as const;
const AVAILABLE_FLAVORS = ["Spong + Vanila"] as const;
const DEFAULT_HEIGHT_INCHES = 4;
const DEFAULT_LAYERS = 1;
const DEFAULT_SHAPE = "round";
const WEEKDAY_LABELS = ["M", "T", "W", "T", "F", "S", "S"] as const;
const WEEKDAY_NAMES = [
  "Sunday",
  "Monday",
  "Tuesday",
  "Wednesday",
  "Thursday",
  "Friday",
  "Saturday",
] as const;

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

type AllowedFlavor = (typeof AVAILABLE_FLAVORS)[number];

interface ServingEstimateResponse {
  predicted_servings: number;
  suggestion: string;
}

interface SizeRecommendation {
  recommended_size_inches: number;
  predicted_servings: number;
  suggestion: string;
}

interface AiDescriptions {
  short?: string;
  long?: string;
  seo?: string;
}

interface PriceBreakdown {
  actual_margin_pct?: number;
  base_cost?: number | string;
  decoration_multiplier?: number;
  ingredients_cost?: number | string;
  labor_cost?: number | string;
  rush_surcharge_applied?: boolean;
  target_margin_pct?: number;
  volume_cubic_inches?: number;
}

interface CustomCakeSubmissionResponse {
  custom_cake_id: string;
  status: string;
  predicted_price: string | number;
  predicted_servings: number;
  predicted_size_inches?: number;
  price_breakdown?: PriceBreakdown;
  ai_descriptions?: AiDescriptions;
}

interface MyCakeSummary {
  id: string;
  flavor: string;
  status: string;
  predicted_price: string | null;
  final_price: string | null;
  predicted_servings: number | null;
  requested_date: string | null;
  created_at: string;
}

interface CakeFormState {
  flavor: AllowedFlavor;
  diameter_inches: number;
  desired_servings: number;
  decoration_description: string;
  cake_message: string;
  requested_date: string;
  time_slot: string;
}

const defaultFormState: CakeFormState = {
  flavor: "Spong + Vanila",
  diameter_inches: 12,
  desired_servings: 25,
  decoration_description: "",
  cake_message: "",
  requested_date: "",
  time_slot: "",
};

function asCurrency(value: string | number | null | undefined) {
  if (value === null || value === undefined) {
    return "AUD 0.00";
  }
  const parsed = typeof value === "number" ? value : Number(value);
  if (!Number.isFinite(parsed)) {
    return "AUD 0.00";
  }
  return new Intl.NumberFormat("en-AU", {
    style: "currency",
    currency: "AUD",
  }).format(parsed);
}

function validateReferenceFile(file: File) {
  if (!ALLOWED_REFERENCE_TYPES.includes(file.type)) {
    return "Only JPG, PNG, or WEBP images are allowed.";
  }
  if (file.size > MAX_REFERENCE_IMAGE_BYTES) {
    return "Image is too large. Please upload an image under 4MB.";
  }
  return null;
}

function fileToDataUrl(file: File) {
  return new Promise<string>((resolve, reject) => {
    const reader = new FileReader();
    reader.onload = () => {
      if (typeof reader.result !== "string") {
        reject(new Error("Unable to read image."));
        return;
      }
      resolve(reader.result);
    };
    reader.onerror = () => reject(new Error("Unable to read image."));
    reader.readAsDataURL(file);
  });
}

function statusBadge(status: string) {
  const normalized = status.toLowerCase();
  if (normalized === "pending_review") return "bg-[#f6e5b9] text-[#7a5608]";
  if (normalized === "approved_awaiting_payment") return "bg-[#d8e8ff] text-[#17529e]";
  if (normalized === "paid") return "bg-[#d8f3dc] text-[#17613d]";
  if (normalized === "in_production") return "bg-[#fce9cf] text-[#a56417]";
  if (normalized === "completed") return "bg-[#d9f8e3] text-[#0f7a3a]";
  if (normalized === "rejected") return "bg-[#ffe0e0] text-[#a32e2e]";
  return "bg-[#ece8de] text-[#4a4640]";
}

function statusLabel(status: string) {
  return status.replace(/_/g, " ");
}

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

function getPickupHoursForDate(date: Date) {
  const { openHour, closeHour } = getBusinessHoursForDate(date);
  const pickupStartHour = Math.min(closeHour - 1, openHour + PICKUP_BUFFER_HOURS);
  return {
    startHour: pickupStartHour,
    closeHour,
  };
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
  const { startHour, closeHour } = getPickupHoursForDate(date);
  const dayName = WEEKDAY_NAMES[date.getDay()];
  return `${dayName}: ${formatTimeLabel(startHour)} - ${formatTimeLabel(closeHour)}`;
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
      if (!rootRef.current) {
        return;
      }

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
        className="w-full rounded-xl border border-[#e8dccb] bg-white px-4 py-3 text-left text-sm text-gray-700 outline-none transition hover:border-[#d8c6ad] focus:ring-2 focus:ring-accent/25"
      >
        <span>{selected?.label || placeholder}</span>
        <span className="pointer-events-none absolute right-3 top-1/2 -translate-y-1/2 text-gray-500 material-symbols-outlined text-[20px]">
          {open ? "expand_less" : "expand_more"}
        </span>
      </button>

      {open ? (
        <div className="absolute z-40 mt-2 max-h-64 w-full overflow-auto rounded-2xl border border-[#e5d5bf] bg-[#fbf7f0] p-1 shadow-[0_16px_40px_rgba(0,0,0,0.12)]">
          {options.map((option) => {
            const isSelected = option.value === value;
            return (
              <button
                key={option.value || option.label}
                type="button"
                role="option"
                aria-selected={isSelected}
                onClick={() => {
                  onChange(option.value);
                  setOpen(false);
                }}
                className={`flex w-full items-center justify-between rounded-xl px-3 py-2 text-sm transition ${
                  isSelected
                    ? "bg-[#f4e7d2] text-black font-semibold"
                    : "text-gray-700 hover:bg-[#f1e4d0]"
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

interface ThemedDatePickerProps {
  value: string;
  onChange: (next: string) => void;
  className?: string;
  minDateValue?: string;
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
      if (!rootRef.current) {
        return;
      }

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
    if (!selectedDate) {
      return;
    }

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
        className="w-full rounded-xl border border-[#e8dccb] bg-white px-4 py-3 text-left text-sm text-gray-700 outline-none transition hover:border-[#d8c6ad] focus:ring-2 focus:ring-accent/25"
      >
        <span>{formatDateLabel(value)}</span>
        <span className="pointer-events-none absolute right-3 top-1/2 -translate-y-1/2 text-gray-500 material-symbols-outlined text-[19px]">
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
                const tomorrow = new Date();
                tomorrow.setHours(0, 0, 0, 0);
                tomorrow.setDate(tomorrow.getDate() + 1);
                onChange(toDateInputValue(tomorrow));
                setOpen(false);
              }}
              className="text-xs font-semibold text-[#ad751c] transition hover:text-[#8f5f13]"
            >
              Tomorrow
            </button>
          </div>
        </div>
      ) : null}
    </div>
  );
}

export default function CustomCakesPage() {
  const { user, accessToken, loading: authLoading, isAuthenticated } = useAuth();

  const [form, setForm] = useState<CakeFormState>(defaultFormState);
  const [referenceCakeFile, setReferenceCakeFile] = useState<File | null>(null);
  const [imageOnCakeFile, setImageOnCakeFile] = useState<File | null>(null);

  const [sizeRecommendation, setSizeRecommendation] = useState<SizeRecommendation | null>(null);
  const [estimatingSize, setEstimatingSize] = useState(false);
  const [estimateError, setEstimateError] = useState<string | null>(null);

  const [submitting, setSubmitting] = useState(false);
  const [submitError, setSubmitError] = useState<string | null>(null);
  const [submitResult, setSubmitResult] = useState<CustomCakeSubmissionResponse | null>(null);

  const [myRequests, setMyRequests] = useState<MyCakeSummary[]>([]);
  const [loadingRequests, setLoadingRequests] = useState(false);

  const minimumRequestedDate = useMemo(() => {
    const tomorrow = new Date();
    tomorrow.setHours(0, 0, 0, 0);
    tomorrow.setDate(tomorrow.getDate() + 1);
    return toDateInputValue(tomorrow);
  }, []);

  const hasAnyContact = Boolean(user?.email || user?.phone);
  const activeScheduleDate = useMemo(() => parseDateInputValue(form.requested_date) || new Date(), [form.requested_date]);
  const timeSlotOptions = useMemo(() => buildTimeSlotOptionsForDate(activeScheduleDate), [activeScheduleDate]);
  const businessHoursText = useMemo(() => formatBusinessHoursText(activeScheduleDate), [activeScheduleDate]);

  const updateForm = useCallback(<K extends keyof CakeFormState>(field: K, value: CakeFormState[K]) => {
    setForm((current) => ({ ...current, [field]: value }));
  }, []);

  useEffect(() => {
    setForm((current) => {
      let next = current;
      let changed = false;

      const hasSlot = timeSlotOptions.some((option) => option.value === current.time_slot);
      if (!hasSlot) {
        const fallbackSlot = timeSlotOptions[0]?.value || "";
        if (current.time_slot !== fallbackSlot) {
          next = { ...next, time_slot: fallbackSlot };
          changed = true;
        }
      }

      return changed ? next : current;
    });
  }, [timeSlotOptions]);

  const loadMyRequests = useCallback(async () => {
    if (!accessToken || !isAuthenticated) {
      setMyRequests([]);
      return;
    }

    setLoadingRequests(true);
    try {
      const data = await apiRequest<MyCakeSummary[]>("/api/v1/custom-cakes/my-cakes", {
        token: accessToken,
      });
      setMyRequests(data);
    } catch {
      setMyRequests([]);
    } finally {
      setLoadingRequests(false);
    }
  }, [accessToken, isAuthenticated]);

  useEffect(() => {
    if (authLoading) {
      return;
    }
    loadMyRequests();
  }, [authLoading, loadMyRequests]);

  useEffect(() => {
    if (!Number.isFinite(form.desired_servings) || form.desired_servings < 1) {
      setSizeRecommendation(null);
      setEstimateError("Please enter a valid number of servings.");
      return;
    }

    const timeoutId = window.setTimeout(async () => {
      setEstimatingSize(true);
      setEstimateError(null);
      try {
        const results = await Promise.all(
          AVAILABLE_SIZES_INCHES.map(async (size) => {
            const estimate = await apiRequest<ServingEstimateResponse>("/api/v1/ml/estimate-servings", {
              method: "POST",
              body: {
                diameter_inches: size,
                height_inches: DEFAULT_HEIGHT_INCHES,
                layers: DEFAULT_LAYERS,
                shape: DEFAULT_SHAPE,
                serving_style: "party",
              },
            });

            return {
              size,
              predicted_servings: estimate.predicted_servings,
              suggestion: estimate.suggestion,
            };
          })
        );

        const recommended =
          results.find((row) => row.predicted_servings >= form.desired_servings) ||
          results[results.length - 1];

        setSizeRecommendation({
          recommended_size_inches: recommended.size,
          predicted_servings: recommended.predicted_servings,
          suggestion: recommended.suggestion,
        });

        setForm((current) => {
          if (current.diameter_inches === recommended.size) {
            return current;
          }
          return { ...current, diameter_inches: recommended.size };
        });
      } catch {
        setEstimateError("Could not calculate the best size right now.");
        setSizeRecommendation(null);
      } finally {
        setEstimatingSize(false);
      }
    }, 350);

    return () => {
      window.clearTimeout(timeoutId);
    };
  }, [form.desired_servings]);

  const resetFormAfterSuccess = () => {
    setForm(defaultFormState);
    setReferenceCakeFile(null);
    setImageOnCakeFile(null);
    setSizeRecommendation(null);
    setEstimateError(null);
  };

  const onSubmit = async (event: React.FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    setSubmitError(null);
    setSubmitResult(null);

    if (!isAuthenticated || !accessToken || !user) {
      setSubmitError("Please sign in to submit a custom cake request.");
      return;
    }

    if (!hasAnyContact) {
      setSubmitError("We need at least one contact method (email or phone) on your account.");
      return;
    }

    if (!Number.isFinite(form.desired_servings) || form.desired_servings < 1) {
      setSubmitError("Please enter how many people the cake should serve.");
      return;
    }

    if (form.requested_date && form.requested_date < minimumRequestedDate) {
      setSubmitError("Please select tomorrow or a future date for pickup.");
      return;
    }

    if (!form.time_slot) {
      setSubmitError("Please select a pickup time slot.");
      return;
    }

    if (!referenceCakeFile) {
      setSubmitError("Please upload one reference cake image.");
      return;
    }

    const imageValidationError = validateReferenceFile(referenceCakeFile);
    if (imageValidationError) {
      setSubmitError(imageValidationError);
      return;
    }

    if (imageOnCakeFile) {
      const imageOnCakeValidationError = validateReferenceFile(imageOnCakeFile);
      if (imageOnCakeValidationError) {
        setSubmitError(imageOnCakeValidationError);
        return;
      }
    }

    setSubmitting(true);
    try {
      const referenceImages = [await fileToDataUrl(referenceCakeFile)];
      if (imageOnCakeFile) {
        referenceImages.push(await fileToDataUrl(imageOnCakeFile));
      }
      const selectedTimeSlot = timeSlotOptions.find((option) => option.value === form.time_slot);
      const formattedTimeSlot = selectedTimeSlot?.label || form.time_slot;

      const submission = await apiRequest<CustomCakeSubmissionResponse>("/api/v1/custom-cakes", {
        method: "POST",
        token: accessToken,
        body: {
          flavor: form.flavor,
          diameter_inches: form.diameter_inches,
          decoration_description: form.decoration_description.trim() || null,
          cake_message: form.cake_message.trim() || null,
          ingredients: {
            desired_servings: form.desired_servings,
            selected_size_inches: form.diameter_inches,
            allowed_sizes_inches: AVAILABLE_SIZES_INCHES,
            image_on_cake_requested: Boolean(imageOnCakeFile),
          },
          reference_images: referenceImages,
          requested_date: form.requested_date ? `${form.requested_date}T00:00:00` : null,
          time_slot: formattedTimeSlot || null,
        },
      });

      setSubmitResult(submission);
      resetFormAfterSuccess();
      await loadMyRequests();
    } catch (error) {
      if (error instanceof ApiError) {
        setSubmitError(error.detail);
      } else {
        setSubmitError("Could not submit your request. Please try again.");
      }
    } finally {
      setSubmitting(false);
    }
  };

  const sizeDetails = useMemo(() => {
    const selected = form.diameter_inches;
    return `${selected}-inch round custom cake`;
  }, [form.diameter_inches]);

  return (
    <>
      <Navbar />
      <main className="flex-1 pb-20">
        <section className="max-w-[1200px] mx-auto px-6 pt-8">
          <ScrollReveal>
            <div className="rounded-[2rem] bg-cream-dark px-6 py-12 md:px-10 md:py-14">
              <span className="inline-flex items-center rounded-full bg-white px-4 py-1.5 text-xs font-semibold text-gray-600 shadow-sm">
                Custom Cake Studio
              </span>
              <h1 className="mt-5 text-4xl md:text-6xl font-extrabold tracking-tight text-black leading-[1.06]">
                Tell us servings, style image, and timing. We predict size and price.
              </h1>
              <p className="mt-4 max-w-3xl text-sm md:text-base text-gray-600 leading-relaxed">
                We currently offer only <strong>Spong + Vanila</strong> flavor, in
                10, 12, 14, and 16 inch sizes. Share your reference cake image and how many people
                the cake should serve, then our ML pricing system returns the suggested size and estimate.
              </p>
            </div>
          </ScrollReveal>
        </section>

        <section className="max-w-[1200px] mx-auto px-6 pt-8 grid grid-cols-1 xl:grid-cols-[minmax(0,2.2fr)_minmax(0,1fr)] gap-6">
          <ScrollReveal className="rounded-[1.75rem] bg-white border border-[#eadcc8] p-6 md:p-8">
            {!authLoading && !isAuthenticated ? (
              <div className="rounded-2xl bg-cream-dark p-6">
                <h2 className="text-2xl font-extrabold tracking-tight text-black">Sign in to request a custom cake</h2>
                <p className="mt-2 text-sm text-gray-600">
                  We need your customer account so your request can be reviewed and approved safely.
                </p>
                <button
                  type="button"
                  onClick={() => window.dispatchEvent(new Event("open-auth-modal"))}
                  className="mt-5 inline-flex rounded-full bg-black px-5 py-2.5 text-sm font-semibold text-white hover:bg-[#222] transition"
                >
                  Login / Register
                </button>
              </div>
            ) : (
              <form onSubmit={onSubmit} className="space-y-8">
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  <label className="text-sm font-semibold text-black">
                    Customer name
                    <input
                      type="text"
                      value={user?.full_name || ""}
                      readOnly
                      className="mt-2 w-full rounded-xl border border-[#e8dccb] bg-[#f9f5ee] px-4 py-3 text-sm text-gray-700 outline-none"
                    />
                  </label>
                  <label className="text-sm font-semibold text-black">
                    Contact
                    <input
                      type="text"
                      value={user?.phone || user?.email || ""}
                      readOnly
                      className="mt-2 w-full rounded-xl border border-[#e8dccb] bg-[#f9f5ee] px-4 py-3 text-sm text-gray-700 outline-none"
                    />
                  </label>
                </div>

                {!hasAnyContact ? (
                  <p className="text-sm text-red-600">
                    Please update your profile with at least email or phone before submitting.
                  </p>
                ) : null}

                <div className="grid grid-cols-1 gap-4">
                  <label className="text-sm font-semibold text-black">
                    Flavor
                    <ThemedSelect
                      className="mt-2"
                      value={form.flavor}
                      onChange={(next) => updateForm("flavor", next as AllowedFlavor)}
                      options={AVAILABLE_FLAVORS.map((flavor) => ({
                        value: flavor,
                        label: flavor,
                      }))}
                    />
                    <span className="mt-1 block text-xs text-gray-500">Only Spong + Vanila is available.</span>
                  </label>
                </div>

                <div>
                  <h3 className="text-xl font-extrabold tracking-tight text-black">Size Planning</h3>
                  <div className="mt-4 grid grid-cols-1 md:grid-cols-2 gap-4">
                    <label className="text-sm font-semibold text-black">
                      How many people should this cake serve?
                      <input
                        type="number"
                        min={1}
                        max={500}
                        value={Number.isFinite(form.desired_servings) ? form.desired_servings : ""}
                        onChange={(event) => {
                          const rawValue = event.target.value;
                          if (rawValue === "") {
                            updateForm("desired_servings", Number.NaN);
                            return;
                          }

                          const parsedValue = Number(rawValue);
                          if (!Number.isFinite(parsedValue)) {
                            return;
                          }

                          updateForm("desired_servings", parsedValue);
                        }}
                        className="mt-2 w-full rounded-xl border border-[#e8dccb] bg-white px-4 py-3 text-sm text-gray-700 outline-none focus:ring-2 focus:ring-accent/25"
                      />
                    </label>
                    <label className="text-sm font-semibold text-black">
                      Cake size (inches)
                      <ThemedSelect
                        className="mt-2"
                        value={String(form.diameter_inches)}
                        onChange={(next) => updateForm("diameter_inches", Number(next))}
                        options={AVAILABLE_SIZES_INCHES.map((size) => ({
                          value: String(size),
                          label: `${size} inch`,
                        }))}
                      />
                      <span className="mt-1 block text-xs text-gray-500">Available sizes: 10, 12, 14, 16 inch.</span>
                    </label>
                  </div>

                  <div className="mt-4 rounded-2xl bg-cream-dark/80 p-4">
                    <p className="text-sm font-semibold text-black">
                      {estimatingSize
                        ? "Calculating best size..."
                        : sizeRecommendation
                          ? `Recommended size: ${sizeRecommendation.recommended_size_inches} inch (about ${sizeRecommendation.predicted_servings} servings)`
                          : "Size recommendation unavailable"}
                    </p>
                    <p className="mt-1 text-xs text-gray-600">
                      {estimateError || sizeRecommendation?.suggestion || "Recommendation updates when servings change."}
                    </p>
                    <p className="mt-2 text-xs text-gray-500">Current selection: {sizeDetails}</p>
                  </div>
                </div>

                <div>
                  <h3 className="text-xl font-extrabold tracking-tight text-black">Design Reference</h3>
                  <div className="mt-4 space-y-4">
                    <label className="text-sm font-semibold text-black block">
                      Decoration description
                      <textarea
                        rows={4}
                        value={form.decoration_description}
                        onChange={(event) => updateForm("decoration_description", event.target.value)}
                        placeholder="Design ideas, piping style, flowers, theme..."
                        className="mt-2 w-full rounded-xl border border-[#e8dccb] bg-white px-4 py-3 text-sm text-gray-700 outline-none resize-none focus:ring-2 focus:ring-accent/25"
                      />
                    </label>

                    <label className="text-sm font-semibold text-black block">
                      Reference cake image
                      <input
                        required
                        type="file"
                        accept=".jpg,.jpeg,.png,.webp,image/jpeg,image/png,image/webp"
                        onChange={(event) => {
                          const selected = event.target.files?.[0] || null;
                          setReferenceCakeFile(selected);
                        }}
                        className="mt-2 block w-full text-sm text-gray-600 file:mr-4 file:rounded-full file:border-0 file:bg-black file:px-4 file:py-2 file:text-sm file:font-semibold file:text-white"
                      />
                      <span className="mt-1 block text-xs text-gray-500">Upload one clear image (JPG/PNG/WEBP, max 4MB).</span>
                    </label>

                    <label className="text-sm font-semibold text-black block">
                      Image to print on cake (optional)
                      <input
                        type="file"
                        accept=".jpg,.jpeg,.png,.webp,image/jpeg,image/png,image/webp"
                        onChange={(event) => {
                          const selected = event.target.files?.[0] || null;
                          setImageOnCakeFile(selected);
                        }}
                        className="mt-2 block w-full text-sm text-gray-600 file:mr-4 file:rounded-full file:border-0 file:bg-accent file:px-4 file:py-2 file:text-sm file:font-semibold file:text-white"
                      />
                      <span className="mt-1 block text-xs text-gray-500">
                        Upload an image only if you want it printed on the cake.
                      </span>
                    </label>
                  </div>
                </div>

                <div>
                  <h3 className="text-xl font-extrabold tracking-tight text-black">Message, Timing & Extras</h3>
                  <div className="mt-4 grid grid-cols-1 md:grid-cols-2 gap-4">
                    <label className="text-sm font-semibold text-black">
                      Message on cake
                      <input
                        type="text"
                        maxLength={200}
                        value={form.cake_message}
                        onChange={(event) => updateForm("cake_message", event.target.value)}
                        placeholder="Happy Birthday Mustafa"
                        className="mt-2 w-full rounded-xl border border-[#e8dccb] bg-white px-4 py-3 text-sm text-gray-700 outline-none focus:ring-2 focus:ring-accent/25"
                      />
                    </label>
                    <label className="text-sm font-semibold text-black">
                      Requested date
                      <ThemedDatePicker
                        className="mt-2"
                        value={form.requested_date}
                        onChange={(next) => updateForm("requested_date", next)}
                        minDateValue={minimumRequestedDate}
                      />
                    </label>
                    <label className="text-sm font-semibold text-black">
                      Pickup time
                      <ThemedSelect
                        className="mt-2"
                        value={form.time_slot}
                        onChange={(next) => updateForm("time_slot", next)}
                        options={timeSlotOptions}
                      />
                      <span className="mt-1 block text-xs text-gray-500">
                        Available pickup hours for selected day: {businessHoursText}
                      </span>
                    </label>
                  </div>
                </div>

                {submitError ? <p className="text-sm text-red-600">{submitError}</p> : null}

                <button
                  type="submit"
                  disabled={submitting || !hasAnyContact}
                  className="inline-flex items-center justify-center rounded-full bg-black px-6 py-3 text-sm font-semibold text-white hover:bg-[#222] transition disabled:opacity-50"
                >
                  {submitting ? "Submitting request..." : "Submit custom cake request"}
                </button>
              </form>
            )}
          </ScrollReveal>

          <div className="space-y-6">
            <ScrollReveal className="rounded-[1.5rem] bg-white border border-[#eadcc8] p-5">
              <h3 className="text-xl font-extrabold tracking-tight text-black">How this works</h3>
              <ol className="mt-4 space-y-2 text-sm text-gray-600 list-decimal list-inside">
                <li>Choose flavor, tell us servings, and upload your reference image.</li>
                <li>ML selects from available sizes and predicts your cake price.</li>
                <li>Admin reviews and confirms the final quote.</li>
                <li>You receive payment approval details before final charge.</li>
              </ol>
            </ScrollReveal>

            <ScrollReveal className="rounded-[1.5rem] bg-white border border-[#eadcc8] p-5">
              <h3 className="text-xl font-extrabold tracking-tight text-black">Latest prediction</h3>
              {submitResult ? (
                <div className="mt-4 space-y-2 text-sm text-gray-700">
                  <p>
                    <span className="font-semibold text-black">Request ID:</span> {submitResult.custom_cake_id}
                  </p>
                  <p>
                    <span className="font-semibold text-black">Status:</span> {statusLabel(submitResult.status)}
                  </p>
                  <p>
                    <span className="font-semibold text-black">Predicted size:</span>{" "}
                    {submitResult.predicted_size_inches ? `${submitResult.predicted_size_inches} inch` : "N/A"}
                  </p>
                  <p>
                    <span className="font-semibold text-black">Predicted price:</span>{" "}
                    {asCurrency(submitResult.predicted_price)}
                  </p>
                  <p>
                    <span className="font-semibold text-black">Estimated servings:</span>{" "}
                    {submitResult.predicted_servings}
                  </p>
                  {submitResult.ai_descriptions?.short ? (
                    <p className="pt-2 text-gray-600">{submitResult.ai_descriptions.short}</p>
                  ) : null}
                </div>
              ) : (
                <p className="mt-4 text-sm text-gray-500">
                  Submit a request to see ML prediction and generated description here.
                </p>
              )}
            </ScrollReveal>

            <ScrollReveal className="rounded-[1.5rem] bg-white border border-[#eadcc8] p-5">
              <div className="flex items-center justify-between gap-3">
                <h3 className="text-xl font-extrabold tracking-tight text-black">My custom cake requests</h3>
                <button
                  type="button"
                  onClick={loadMyRequests}
                  className="rounded-full border border-[#eadcc8] px-3 py-1 text-xs font-semibold text-gray-700 hover:bg-cream-dark transition"
                >
                  Refresh
                </button>
              </div>
              {loadingRequests ? (
                <p className="mt-4 text-sm text-gray-500">Loading requests...</p>
              ) : myRequests.length === 0 ? (
                <p className="mt-4 text-sm text-gray-500">No custom cake requests yet.</p>
              ) : (
                <div className="mt-4 space-y-3">
                  {myRequests.slice(0, 6).map((request) => (
                    <article key={request.id} className="rounded-xl border border-[#eadcc8] bg-cream-dark/50 p-3">
                      <div className="flex items-start justify-between gap-3">
                        <div>
                          <p className="text-sm font-semibold text-black">{request.flavor}</p>
                          <p className="text-xs text-gray-500">{new Date(request.created_at).toLocaleString()}</p>
                        </div>
                        <span className={`rounded-full px-2.5 py-1 text-[11px] font-semibold capitalize ${statusBadge(request.status)}`}>
                          {statusLabel(request.status)}
                        </span>
                      </div>
                      <div className="mt-2 text-xs text-gray-700">
                        Predicted: {request.predicted_price ? asCurrency(request.predicted_price) : "N/A"} | Final:{" "}
                        {request.final_price ? asCurrency(request.final_price) : "Pending admin"}
                      </div>
                    </article>
                  ))}
                </div>
              )}
              {!isAuthenticated ? (
                <p className="mt-4 text-sm text-gray-600">Please login to see your request history.</p>
              ) : null}
            </ScrollReveal>
          </div>
        </section>

        <section className="max-w-[1200px] mx-auto px-6 pt-8">
          <ScrollReveal className="rounded-[1.5rem] bg-cream-dark px-6 py-6">
            <p className="text-sm text-gray-700">
              Need account details updated before ordering? Visit{" "}
              <Link href="/account" className="font-semibold text-black underline decoration-accent/70 underline-offset-4">
                Account settings
              </Link>
              .
            </p>
          </ScrollReveal>
        </section>
      </main>
      <Footer />
    </>
  );
}

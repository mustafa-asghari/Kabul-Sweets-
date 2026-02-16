"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import Link from "next/link";
import Footer from "@/components/Footer";
import Navbar from "@/components/Navbar";
import ScrollReveal from "@/components/ScrollReveal";
import { ApiError, apiRequest } from "@/lib/api-client";
import { useAuth } from "@/context/AuthContext";

const MAX_REFERENCE_IMAGE_BYTES = 4 * 1024 * 1024;
const ALLOWED_REFERENCE_TYPES = ["image/jpeg", "image/png", "image/webp"];
const IMAGE_ON_CAKE_SURCHARGE = 25;

type DecorationComplexity = "simple" | "moderate" | "complex" | "elaborate";
type CakeShape = "round" | "square" | "rectangle" | "heart" | "hexagon" | "tiered";

interface ServingEstimateResponse {
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
  flavor: string;
  diameter_inches: number;
  height_inches: number;
  layers: number;
  shape: CakeShape;
  decoration_complexity: DecorationComplexity;
  decoration_description: string;
  cake_message: string;
  event_type: string;
  allergen_notes: string;
  requested_date: string;
  time_slot: string;
  is_rush_order: boolean;
  wants_image_on_cake: boolean;
  approved_image_fee: boolean;
}

const defaultFormState: CakeFormState = {
  flavor: "",
  diameter_inches: 8,
  height_inches: 4,
  layers: 1,
  shape: "round",
  decoration_complexity: "moderate",
  decoration_description: "",
  cake_message: "",
  event_type: "",
  allergen_notes: "",
  requested_date: "",
  time_slot: "Morning",
  is_rush_order: false,
  wants_image_on_cake: false,
  approved_image_fee: false,
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

function toHex(value: number) {
  return value.toString(16).padStart(2, "0");
}

function rgbToHex(r: number, g: number, b: number) {
  return `#${toHex(r)}${toHex(g)}${toHex(b)}`;
}

function hexToRgb(hex: string) {
  const normalized = hex.replace("#", "").trim();
  if (!/^[0-9a-fA-F]{6}$/.test(normalized)) {
    return null;
  }

  return {
    r: Number.parseInt(normalized.slice(0, 2), 16),
    g: Number.parseInt(normalized.slice(2, 4), 16),
    b: Number.parseInt(normalized.slice(4, 6), 16),
  };
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

export default function CustomCakesPage() {
  const { user, accessToken, loading: authLoading, isAuthenticated } = useAuth();

  const [form, setForm] = useState<CakeFormState>(defaultFormState);
  const [rgb, setRgb] = useState({ r: 173, g: 117, b: 28 });
  const [imageOnCakeFile, setImageOnCakeFile] = useState<File | null>(null);
  const [colorReferenceFile, setColorReferenceFile] = useState<File | null>(null);

  const [servingEstimate, setServingEstimate] = useState<ServingEstimateResponse | null>(null);
  const [estimatingServings, setEstimatingServings] = useState(false);
  const [estimateError, setEstimateError] = useState<string | null>(null);

  const [submitting, setSubmitting] = useState(false);
  const [submitError, setSubmitError] = useState<string | null>(null);
  const [submitResult, setSubmitResult] = useState<CustomCakeSubmissionResponse | null>(null);

  const [myRequests, setMyRequests] = useState<MyCakeSummary[]>([]);
  const [loadingRequests, setLoadingRequests] = useState(false);

  const colorHex = useMemo(() => rgbToHex(rgb.r, rgb.g, rgb.b), [rgb.b, rgb.g, rgb.r]);
  const hasAnyContact = Boolean(user?.email || user?.phone);

  const updateForm = useCallback(<K extends keyof CakeFormState>(field: K, value: CakeFormState[K]) => {
    setForm((current) => ({ ...current, [field]: value }));
  }, []);

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
    const timeoutId = window.setTimeout(async () => {
      setEstimatingServings(true);
      setEstimateError(null);
      try {
        const estimate = await apiRequest<ServingEstimateResponse>("/api/v1/ml/estimate-servings", {
          method: "POST",
          body: {
            diameter_inches: form.diameter_inches,
            height_inches: form.height_inches,
            layers: form.layers,
            shape: form.shape,
            serving_style: "party",
          },
        });
        setServingEstimate(estimate);
      } catch {
        setEstimateError("Could not estimate servings right now.");
        setServingEstimate(null);
      } finally {
        setEstimatingServings(false);
      }
    }, 350);

    return () => {
      window.clearTimeout(timeoutId);
    };
  }, [form.diameter_inches, form.height_inches, form.layers, form.shape]);

  const resetFormAfterSuccess = () => {
    setForm(defaultFormState);
    setImageOnCakeFile(null);
    setColorReferenceFile(null);
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

    if (!form.flavor.trim()) {
      setSubmitError("Please enter the cake flavor.");
      return;
    }

    if (form.wants_image_on_cake && !form.approved_image_fee) {
      setSubmitError("Please confirm the $25 image-on-cake fee to continue.");
      return;
    }

    if (form.wants_image_on_cake && form.approved_image_fee && !imageOnCakeFile) {
      setSubmitError("Please upload one image for the cake print.");
      return;
    }

    if (imageOnCakeFile) {
      const imageValidationError = validateReferenceFile(imageOnCakeFile);
      if (imageValidationError) {
        setSubmitError(imageValidationError);
        return;
      }
    }

    if (colorReferenceFile) {
      const colorValidationError = validateReferenceFile(colorReferenceFile);
      if (colorValidationError) {
        setSubmitError(colorValidationError);
        return;
      }
    }

    setSubmitting(true);
    try {
      const referenceImages: string[] = [];
      if (colorReferenceFile) {
        referenceImages.push(await fileToDataUrl(colorReferenceFile));
      }
      if (form.wants_image_on_cake && imageOnCakeFile) {
        referenceImages.push(await fileToDataUrl(imageOnCakeFile));
      }

      const colorText = `Preferred colour: ${colorHex} (rgb(${rgb.r}, ${rgb.g}, ${rgb.b}))`;
      const imageRequestText = form.wants_image_on_cake
        ? `Image on cake requested (+$${IMAGE_ON_CAKE_SURCHARGE}): yes`
        : "Image on cake requested: no";
      const decorationDescription = [form.decoration_description.trim(), colorText, imageRequestText]
        .filter(Boolean)
        .join("\n");

      const submission = await apiRequest<CustomCakeSubmissionResponse>("/api/v1/custom-cakes", {
        method: "POST",
        token: accessToken,
        body: {
          flavor: form.flavor.trim(),
          diameter_inches: form.diameter_inches,
          height_inches: form.height_inches,
          layers: form.layers,
          shape: form.shape,
          decoration_complexity: form.decoration_complexity,
          decoration_description: decorationDescription,
          cake_message: form.cake_message.trim() || null,
          event_type: form.event_type.trim() || null,
          is_rush_order: form.is_rush_order,
          ingredients: {
            preferred_colour_hex: colorHex,
            preferred_colour_rgb: { r: rgb.r, g: rgb.g, b: rgb.b },
            image_on_cake_requested: form.wants_image_on_cake,
            image_on_cake_fee_approved: form.wants_image_on_cake ? form.approved_image_fee : false,
            image_on_cake_fee_amount_aud: form.wants_image_on_cake ? IMAGE_ON_CAKE_SURCHARGE : 0,
            color_reference_attached: Boolean(colorReferenceFile),
          },
          allergen_notes: form.allergen_notes.trim() || null,
          reference_images: referenceImages.length > 0 ? referenceImages : null,
          requested_date: form.requested_date ? `${form.requested_date}T00:00:00` : null,
          time_slot: form.time_slot || null,
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
                Build your cake request with exact size, colour, and style.
              </h1>
              <p className="mt-4 max-w-3xl text-sm md:text-base text-gray-600 leading-relaxed">
                Submit everything in one go: flavor, servings, preferred RGB colour, cake text, and
                optional image printing. Our ML engine estimates price from your size/spec, then admin reviews and confirms.
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
                  We need your customer account so your order goes to admin review and payment approval safely.
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
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  <label className="text-sm font-semibold text-black">
                    Flavor
                    <input
                      required
                      type="text"
                      value={form.flavor}
                      onChange={(event) => updateForm("flavor", event.target.value)}
                      placeholder="e.g. Chocolate Hazelnut"
                      className="mt-2 w-full rounded-xl border border-[#e8dccb] bg-white px-4 py-3 text-sm text-gray-700 outline-none focus:ring-2 focus:ring-accent/25"
                    />
                  </label>
                  <label className="text-sm font-semibold text-black">
                    Event type
                    <input
                      type="text"
                      value={form.event_type}
                      onChange={(event) => updateForm("event_type", event.target.value)}
                      placeholder="Birthday, wedding, engagement..."
                      className="mt-2 w-full rounded-xl border border-[#e8dccb] bg-white px-4 py-3 text-sm text-gray-700 outline-none focus:ring-2 focus:ring-accent/25"
                    />
                  </label>
                </div>

                <div>
                  <h3 className="text-xl font-extrabold tracking-tight text-black">Size & Structure</h3>
                  <div className="mt-4 grid grid-cols-2 md:grid-cols-4 gap-4">
                    <label className="text-sm font-semibold text-black">
                      Diameter (in)
                      <input
                        type="number"
                        min={5}
                        max={24}
                        step={1}
                        value={form.diameter_inches}
                        onChange={(event) => updateForm("diameter_inches", Number(event.target.value))}
                        className="mt-2 w-full rounded-xl border border-[#e8dccb] bg-white px-3 py-3 text-sm text-gray-700 outline-none focus:ring-2 focus:ring-accent/25"
                      />
                    </label>
                    <label className="text-sm font-semibold text-black">
                      Height (in)
                      <input
                        type="number"
                        min={2}
                        max={12}
                        step={0.5}
                        value={form.height_inches}
                        onChange={(event) => updateForm("height_inches", Number(event.target.value))}
                        className="mt-2 w-full rounded-xl border border-[#e8dccb] bg-white px-3 py-3 text-sm text-gray-700 outline-none focus:ring-2 focus:ring-accent/25"
                      />
                    </label>
                    <label className="text-sm font-semibold text-black">
                      Layers
                      <input
                        type="number"
                        min={1}
                        max={5}
                        value={form.layers}
                        onChange={(event) => updateForm("layers", Number(event.target.value))}
                        className="mt-2 w-full rounded-xl border border-[#e8dccb] bg-white px-3 py-3 text-sm text-gray-700 outline-none focus:ring-2 focus:ring-accent/25"
                      />
                    </label>
                    <label className="text-sm font-semibold text-black">
                      Shape
                      <select
                        value={form.shape}
                        onChange={(event) => updateForm("shape", event.target.value as CakeShape)}
                        className="mt-2 w-full rounded-xl border border-[#e8dccb] bg-white px-3 py-3 text-sm text-gray-700 outline-none focus:ring-2 focus:ring-accent/25"
                      >
                        <option value="round">Round</option>
                        <option value="square">Square</option>
                        <option value="rectangle">Rectangle</option>
                        <option value="heart">Heart</option>
                        <option value="hexagon">Hexagon</option>
                        <option value="tiered">Tiered</option>
                      </select>
                    </label>
                  </div>
                  <div className="mt-4 rounded-2xl bg-cream-dark/80 p-4">
                    <p className="text-sm font-semibold text-black">
                      {estimatingServings
                        ? "Estimating servings..."
                        : servingEstimate
                          ? `Estimated servings: ${servingEstimate.predicted_servings} people`
                          : "Serving estimate unavailable"}
                    </p>
                    <p className="mt-1 text-xs text-gray-600">
                      {estimateError || servingEstimate?.suggestion || "Serving estimate updates with size changes."}
                    </p>
                  </div>
                </div>

                <div>
                  <h3 className="text-xl font-extrabold tracking-tight text-black">Decoration & Colour</h3>
                  <div className="mt-4 grid grid-cols-1 md:grid-cols-[minmax(0,1.8fr)_minmax(0,1fr)] gap-5">
                    <div className="space-y-4">
                      <label className="text-sm font-semibold text-black block">
                        Decoration complexity
                        <select
                          value={form.decoration_complexity}
                          onChange={(event) => updateForm("decoration_complexity", event.target.value as DecorationComplexity)}
                          className="mt-2 w-full rounded-xl border border-[#e8dccb] bg-white px-4 py-3 text-sm text-gray-700 outline-none focus:ring-2 focus:ring-accent/25"
                        >
                          <option value="simple">Simple</option>
                          <option value="moderate">Moderate</option>
                          <option value="complex">Complex</option>
                          <option value="elaborate">Elaborate</option>
                        </select>
                      </label>
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
                    </div>
                    <div className="rounded-2xl border border-[#eadcc8] bg-[#f8f2e8] p-4">
                      <div className="flex items-center gap-4">
                        <div className="h-20 w-20 rounded-full bg-white p-1 ring-1 ring-black/10">
                          <span
                            className="block h-full w-full rounded-full"
                            style={{ backgroundColor: colorHex }}
                          />
                        </div>
                        <div className="text-sm">
                          <p className="font-semibold text-black">Pick colour with RGB</p>
                          <p className="mt-1 text-xs leading-relaxed text-gray-600">
                            Choose a base shade with Quick pick, then fine-tune it using the RGB sliders.
                            The HEX code updates automatically for your final color choice.
                          </p>
                          <p className="mt-1 font-extrabold tracking-wide text-black">{colorHex.toUpperCase()}</p>
                        </div>
                      </div>

                      <label className="mt-4 flex items-center justify-between rounded-xl border border-[#eadcc8] bg-white px-3 py-2 text-xs text-gray-600">
                        Quick pick
                        <input
                          type="color"
                          value={colorHex}
                          onChange={(event) => {
                            const parsed = hexToRgb(event.target.value);
                            if (parsed) {
                              setRgb(parsed);
                            }
                          }}
                          className="h-9 w-9 cursor-pointer rounded-full border-0 bg-transparent p-0"
                        />
                      </label>

                      <div className="mt-4 space-y-3">
                        <label className="text-xs text-gray-600 block">
                          Red channel
                          <input
                            type="range"
                            min={0}
                            max={255}
                            value={rgb.r}
                            onChange={(event) => setRgb((current) => ({ ...current, r: Number(event.target.value) }))}
                            className="mt-1 w-full accent-red-500"
                          />
                        </label>
                        <label className="text-xs text-gray-600 block">
                          Green channel
                          <input
                            type="range"
                            min={0}
                            max={255}
                            value={rgb.g}
                            onChange={(event) => setRgb((current) => ({ ...current, g: Number(event.target.value) }))}
                            className="mt-1 w-full accent-green-500"
                          />
                        </label>
                        <label className="text-xs text-gray-600 block">
                          Blue channel
                          <input
                            type="range"
                            min={0}
                            max={255}
                            value={rgb.b}
                            onChange={(event) => setRgb((current) => ({ ...current, b: Number(event.target.value) }))}
                            className="mt-1 w-full accent-blue-500"
                          />
                        </label>
                      </div>
                    </div>
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
                      Allergen notes
                      <input
                        type="text"
                        value={form.allergen_notes}
                        onChange={(event) => updateForm("allergen_notes", event.target.value)}
                        placeholder="Nut free, egg free, etc."
                        className="mt-2 w-full rounded-xl border border-[#e8dccb] bg-white px-4 py-3 text-sm text-gray-700 outline-none focus:ring-2 focus:ring-accent/25"
                      />
                    </label>
                    <label className="text-sm font-semibold text-black">
                      Requested date
                      <input
                        type="date"
                        value={form.requested_date}
                        onChange={(event) => updateForm("requested_date", event.target.value)}
                        className="mt-2 w-full rounded-xl border border-[#e8dccb] bg-white px-4 py-3 text-sm text-gray-700 outline-none focus:ring-2 focus:ring-accent/25"
                      />
                    </label>
                    <label className="text-sm font-semibold text-black">
                      Preferred time slot
                      <select
                        value={form.time_slot}
                        onChange={(event) => updateForm("time_slot", event.target.value)}
                        className="mt-2 w-full rounded-xl border border-[#e8dccb] bg-white px-4 py-3 text-sm text-gray-700 outline-none focus:ring-2 focus:ring-accent/25"
                      >
                        <option value="Morning">Morning</option>
                        <option value="Afternoon">Afternoon</option>
                        <option value="Evening">Evening</option>
                      </select>
                    </label>
                  </div>
                  <label className="mt-4 inline-flex items-center gap-2 text-sm font-semibold text-black">
                    <input
                      type="checkbox"
                      checked={form.is_rush_order}
                      onChange={(event) => updateForm("is_rush_order", event.target.checked)}
                    />
                    Rush order needed
                  </label>
                </div>

                <div className="rounded-2xl border border-[#e8dccb] bg-[#fbf7f0] p-5">
                  <h3 className="text-lg font-extrabold tracking-tight text-black">Image options</h3>
                  <label className="mt-3 inline-flex items-center gap-2 text-sm font-semibold text-black">
                    <input
                      type="checkbox"
                      checked={form.wants_image_on_cake}
                      onChange={(event) => {
                        const nextValue = event.target.checked;
                        updateForm("wants_image_on_cake", nextValue);
                        if (!nextValue) {
                          updateForm("approved_image_fee", false);
                          setImageOnCakeFile(null);
                        }
                      }}
                    />
                    I want an image printed on the cake
                  </label>
                  {form.wants_image_on_cake ? (
                    <div className="mt-3 space-y-3 rounded-xl bg-white p-4 border border-[#eadcc8]">
                      <p className="text-sm text-black font-semibold">
                        Image printing adds {asCurrency(IMAGE_ON_CAKE_SURCHARGE)}.
                      </p>
                      <label className="inline-flex items-center gap-2 text-sm text-gray-700">
                        <input
                          type="checkbox"
                          checked={form.approved_image_fee}
                          onChange={(event) => updateForm("approved_image_fee", event.target.checked)}
                        />
                        I approve the extra image charge
                      </label>
                      <label className="block text-sm font-semibold text-black">
                        Upload one image for the cake
                        <input
                          disabled={!form.approved_image_fee}
                          type="file"
                          accept=".jpg,.jpeg,.png,.webp,image/jpeg,image/png,image/webp"
                          onChange={(event) => {
                            const selected = event.target.files?.[0] || null;
                            setImageOnCakeFile(selected);
                          }}
                          className="mt-2 block w-full text-sm text-gray-600 file:mr-4 file:rounded-full file:border-0 file:bg-accent file:px-4 file:py-2 file:text-sm file:font-semibold file:text-white disabled:opacity-40"
                        />
                      </label>
                    </div>
                  ) : null}

                  <label className="mt-4 block text-sm font-semibold text-black">
                    Optional colour reference image
                    <input
                      type="file"
                      accept=".jpg,.jpeg,.png,.webp,image/jpeg,image/png,image/webp"
                      onChange={(event) => {
                        const selected = event.target.files?.[0] || null;
                        setColorReferenceFile(selected);
                      }}
                      className="mt-2 block w-full text-sm text-gray-600 file:mr-4 file:rounded-full file:border-0 file:bg-black file:px-4 file:py-2 file:text-sm file:font-semibold file:text-white"
                    />
                  </label>
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
                <li>Submit your cake details and preferences.</li>
                <li>ML estimates servings and predicts a price from size/spec.</li>
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
                    <span className="font-semibold text-black">Status:</span>{" "}
                    {statusLabel(submitResult.status)}
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
                <p className="mt-4 text-sm text-gray-600">
                  Please login to see your request history.
                </p>
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

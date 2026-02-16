"use client";

import { AnimatePresence, motion, useInView } from "framer-motion";
import { useEffect, useMemo, useRef, useState } from "react";
import Image from "next/image";

interface Review {
  authorName: string;
  avatarUrl: string | null;
  rating: number;
  text: string;
  relativeTime: string;
  time: number;
}

interface ReviewsApiResponse {
  source?: "google" | "fallback";
  placeName?: string;
  reviews?: Review[];
}

const ROTATE_MS = 6500;
const FEATURED_REVIEWS: Review[] = [
  {
    authorName: "Sarah A.",
    avatarUrl: null,
    rating: 5,
    text: "The most authentic Afghan sweets I've tasted outside of Kabul. The custom cake was a masterpiece!",
    relativeTime: "recent",
    time: 1,
  },
  {
    authorName: "Hamid R.",
    avatarUrl: null,
    rating: 5,
    text: "Excellent service and fresh desserts every time. Our family now orders all birthday cakes from Kabul Sweets.",
    relativeTime: "recent",
    time: 2,
  },
  {
    authorName: "Nadia M.",
    avatarUrl: null,
    rating: 5,
    text: "Beautiful presentation, rich flavor, and very friendly staff. Pickup was quick and easy.",
    relativeTime: "recent",
    time: 3,
  },
];

function getInitials(name: string) {
  return name
    .split(" ")
    .filter(Boolean)
    .slice(0, 2)
    .map((part) => part[0]?.toUpperCase() ?? "")
    .join("");
}

function isReview(value: unknown): value is Review {
  if (!value || typeof value !== "object") {
    return false;
  }

  const candidate = value as Partial<Review>;
  return (
    typeof candidate.authorName === "string" &&
    typeof candidate.text === "string" &&
    typeof candidate.rating === "number" &&
    typeof candidate.relativeTime === "string" &&
    typeof candidate.time === "number"
  );
}

export default function TestimonialSection() {
  const ref = useRef(null);
  const isInView = useInView(ref, { once: true, margin: "0px 0px -50px 0px" });
  const [reviews, setReviews] = useState<Review[]>(FEATURED_REVIEWS);
  const [source, setSource] = useState<"google" | "fallback">("fallback");
  const [placeName, setPlaceName] = useState("Kabul Sweets Bakery");
  const [activeIndex, setActiveIndex] = useState(0);

  useEffect(() => {
    let cancelled = false;

    const loadReviews = async () => {
      try {
        const response = await fetch("/api/google-reviews", { cache: "no-store" });
        if (!response.ok) {
          return;
        }

        const payload = (await response.json()) as ReviewsApiResponse;
        const loadedReviews = Array.isArray(payload.reviews)
          ? payload.reviews.filter(isReview)
          : [];

        if (cancelled || loadedReviews.length === 0) {
          return;
        }

        setReviews(loadedReviews);
        setSource(payload.source === "google" ? "google" : "fallback");
        if (typeof payload.placeName === "string" && payload.placeName.trim().length > 0) {
          setPlaceName(payload.placeName.trim());
        }
      } catch {
        // Keep local fallback reviews when API fetch fails.
      }
    };

    void loadReviews();

    return () => {
      cancelled = true;
    };
  }, []);

  useEffect(() => {
    if (reviews.length < 2) {
      return;
    }

    const intervalId = window.setInterval(() => {
      setActiveIndex((prev) => (prev + 1) % reviews.length);
    }, ROTATE_MS);

    return () => {
      window.clearInterval(intervalId);
    };
  }, [reviews.length]);

  useEffect(() => {
    if (activeIndex >= reviews.length) {
      setActiveIndex(0);
    }
  }, [activeIndex, reviews.length]);

  const currentReview = useMemo(() => reviews[activeIndex] ?? null, [reviews, activeIndex]);
  const averageRating = useMemo(() => {
    if (reviews.length === 0) {
      return null;
    }
    const total = reviews.reduce((sum, review) => sum + review.rating, 0);
    return total / reviews.length;
  }, [reviews]);

  const onPrev = () => {
    if (reviews.length < 2) {
      return;
    }
    setActiveIndex((prev) => (prev - 1 + reviews.length) % reviews.length);
  };

  const onNext = () => {
    if (reviews.length < 2) {
      return;
    }
    setActiveIndex((prev) => (prev + 1) % reviews.length);
  };

  return (
    <section className="max-w-[1200px] mx-auto px-6 pb-20">
      <motion.div
        ref={ref}
        initial={{ opacity: 0, y: 40, scale: 0.98 }}
        animate={
          isInView
            ? { opacity: 1, y: 0, scale: 1 }
            : { opacity: 0, y: 40, scale: 0.98 }
        }
        transition={{ type: "spring", stiffness: 100, damping: 30 }}
        className="bg-cream-dark rounded-[2rem] py-16 px-8 md:px-16 text-center relative overflow-hidden"
      >
        <div className="absolute top-8 right-8 flex gap-2">
          <button
            type="button"
            onClick={onPrev}
            disabled={reviews.length < 2}
            className="flex h-10 w-10 items-center justify-center text-gray-500 transition hover:text-black disabled:opacity-40 disabled:cursor-not-allowed"
            aria-label="Previous review"
          >
            <span className="material-symbols-outlined text-[18px]">
              arrow_back
            </span>
          </button>
          <button
            type="button"
            onClick={onNext}
            disabled={reviews.length < 2}
            className="flex h-10 w-10 items-center justify-center text-gray-500 transition hover:text-black disabled:opacity-40 disabled:cursor-not-allowed"
            aria-label="Next review"
          >
            <span className="material-symbols-outlined text-[18px]">
              arrow_forward
            </span>
          </button>
        </div>

        <AnimatePresence mode="wait">
          {currentReview ? (
            <motion.div
              key={`${currentReview.authorName}-${currentReview.time}-${activeIndex}`}
              initial={{ opacity: 0, y: 16 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -16 }}
              transition={{ duration: 0.45, ease: "easeInOut" }}
            >
              <div className="w-16 h-16 rounded-full overflow-hidden mx-auto mb-8 shadow-md bg-white flex items-center justify-center">
                {currentReview.avatarUrl ? (
                  <Image
                    src={currentReview.avatarUrl}
                    alt={currentReview.authorName}
                    width={64}
                    height={64}
                    sizes="64px"
                    className="w-full h-full object-cover"
                  />
                ) : (
                  <span className="text-sm font-semibold text-gray-600">
                    {getInitials(currentReview.authorName)}
                  </span>
                )}
              </div>

              <h2 className="text-2xl md:text-[2rem] font-extrabold tracking-tight text-black leading-snug max-w-2xl mx-auto mb-8">
                &ldquo;{currentReview.text}&rdquo;
              </h2>

              <div className="flex gap-0.5 justify-center mb-2">
                {Array.from({ length: 5 }, (_, i) => (
                  <span
                    key={i}
                    className={`material-symbols-outlined text-lg ${
                      i < currentReview.rating ? "text-black" : "text-gray-300"
                    }`}
                    style={{ fontVariationSettings: "'FILL' 1" }}
                  >
                    star
                  </span>
                ))}
              </div>

              <p className="text-sm text-gray-600 font-medium">
                {currentReview.authorName}
                <span className="ml-2 text-gray-400">· {currentReview.relativeTime}</span>
              </p>
            </motion.div>
          ) : (
            <motion.p
              key="loading"
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              className="text-sm text-gray-500"
            >
              Loading reviews...
            </motion.p>
          )}
        </AnimatePresence>

        <p className="text-xs text-gray-400 mt-8 mb-4">
          {source === "google"
            ? `Top customer reviews from ${placeName} on Google.`
            : "Featured customer reviews from Kabul Sweets Bakery."}
        </p>
        <div className="flex items-center justify-center gap-2 text-sm text-gray-600">
          <span className="material-symbols-outlined text-[17px] text-black">star</span>
          <span className="font-semibold">{averageRating?.toFixed(1) ?? "5.0"}</span>
          <span>Customer rating</span>
          <span>({reviews.length} reviews)</span>
        </div>
      </motion.div>
    </section>
  );
}

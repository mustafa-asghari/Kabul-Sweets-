import { NextResponse } from "next/server";

interface GoogleReviewPayload {
  author_name?: string;
  profile_photo_url?: string;
  rating?: number;
  text?: string;
  relative_time_description?: string;
  time?: number;
}

interface GoogleFindPlaceResponse {
  candidates?: Array<{
    place_id?: string;
  }>;
}

interface GooglePlaceDetailsResponse {
  result?: {
    name?: string;
    reviews?: GoogleReviewPayload[];
  };
}

interface PublicReview {
  authorName: string;
  avatarUrl: string | null;
  rating: number;
  text: string;
  relativeTime: string;
  time: number;
}

const DEFAULT_PLACE_NAME = "Kabul Sweets Bakery";
const DEFAULT_PLACE_QUERY = "Kabul Sweets Bakery Acacia Ridge QLD";
const REVIEWS_LIMIT = 6;
const RESPONSE_HEADERS = {
  "Cache-Control": "public, s-maxage=1800, stale-while-revalidate=86400",
};

const FALLBACK_REVIEWS: PublicReview[] = [
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

function clampRating(value: number): number {
  if (value < 0) {
    return 0;
  }

  if (value > 5) {
    return 5;
  }

  return Math.round(value);
}

function mapGoogleReview(review: GoogleReviewPayload): PublicReview | null {
  if (typeof review.author_name !== "string" || review.author_name.trim().length === 0) {
    return null;
  }

  if (typeof review.text !== "string" || review.text.trim().length === 0) {
    return null;
  }

  const rawRating = typeof review.rating === "number" ? review.rating : 5;
  const rawTime = typeof review.time === "number" ? review.time : 0;

  return {
    authorName: review.author_name.trim(),
    avatarUrl:
      typeof review.profile_photo_url === "string" && review.profile_photo_url.trim().length > 0
        ? review.profile_photo_url
        : null,
    rating: clampRating(rawRating),
    text: review.text.trim(),
    relativeTime:
      typeof review.relative_time_description === "string" &&
      review.relative_time_description.trim().length > 0
        ? review.relative_time_description.trim()
        : "recent",
    time: rawTime,
  };
}

function pickBestReviews(reviews: PublicReview[]): PublicReview[] {
  return [...reviews]
    .sort((a, b) => {
      if (b.rating !== a.rating) {
        return b.rating - a.rating;
      }

      if (b.time !== a.time) {
        return b.time - a.time;
      }

      return b.text.length - a.text.length;
    })
    .slice(0, REVIEWS_LIMIT);
}

async function findPlaceId(apiKey: string): Promise<string | null> {
  if (typeof process.env.GOOGLE_PLACE_ID === "string" && process.env.GOOGLE_PLACE_ID.trim()) {
    return process.env.GOOGLE_PLACE_ID.trim();
  }

  const query =
    typeof process.env.GOOGLE_PLACE_QUERY === "string" && process.env.GOOGLE_PLACE_QUERY.trim()
      ? process.env.GOOGLE_PLACE_QUERY.trim()
      : DEFAULT_PLACE_QUERY;

  const url = new URL("https://maps.googleapis.com/maps/api/place/findplacefromtext/json");
  url.searchParams.set("input", query);
  url.searchParams.set("inputtype", "textquery");
  url.searchParams.set("fields", "place_id");
  url.searchParams.set("key", apiKey);

  const response = await fetch(url.toString(), {
    next: { revalidate: 60 * 60 * 12 },
  });

  if (!response.ok) {
    return null;
  }

  const payload = (await response.json()) as GoogleFindPlaceResponse;
  const placeId = payload.candidates?.[0]?.place_id;

  if (typeof placeId !== "string" || placeId.trim().length === 0) {
    return null;
  }

  return placeId;
}

async function fetchGoogleReviews(apiKey: string, placeId: string): Promise<{
  placeName: string;
  reviews: PublicReview[];
} | null> {
  const url = new URL("https://maps.googleapis.com/maps/api/place/details/json");
  url.searchParams.set("place_id", placeId);
  url.searchParams.set("fields", "name,reviews");
  url.searchParams.set("reviews_sort", "newest");
  url.searchParams.set("key", apiKey);

  const response = await fetch(url.toString(), {
    next: { revalidate: 60 * 30 },
  });

  if (!response.ok) {
    return null;
  }

  const payload = (await response.json()) as GooglePlaceDetailsResponse;
  const mappedReviews = (payload.result?.reviews ?? [])
    .map(mapGoogleReview)
    .filter((review): review is PublicReview => review !== null);

  if (mappedReviews.length === 0) {
    return null;
  }

  return {
    placeName: payload.result?.name?.trim() || DEFAULT_PLACE_NAME,
    reviews: pickBestReviews(mappedReviews),
  };
}

function fallbackResponse(error?: string) {
  return NextResponse.json(
    {
      source: "fallback",
      placeName: DEFAULT_PLACE_NAME,
      reviews: FALLBACK_REVIEWS,
      ...(typeof error === "string" ? { error } : {}),
    },
    { headers: RESPONSE_HEADERS }
  );
}

export async function GET() {
  try {
    const apiKey =
      process.env.GOOGLE_MAPS_API_KEY || process.env.GOOGLE_PLACES_API_KEY || "";

    if (!apiKey) {
      return fallbackResponse("Missing Google Places API key.");
    }

    const placeId = await findPlaceId(apiKey);
    if (!placeId) {
      return fallbackResponse("Unable to resolve Google Place ID.");
    }

    const googleData = await fetchGoogleReviews(apiKey, placeId);
    if (!googleData) {
      return fallbackResponse("No Google reviews found.");
    }

    return NextResponse.json(
      {
        source: "google",
        placeName: googleData.placeName,
        reviews: googleData.reviews,
      },
      { headers: RESPONSE_HEADERS }
    );
  } catch {
    return fallbackResponse("Failed to fetch Google reviews.");
  }
}

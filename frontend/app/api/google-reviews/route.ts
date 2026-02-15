import { NextResponse } from "next/server";

interface LegacyReview {
  author_name?: string;
  profile_photo_url?: string;
  rating?: number;
  relative_time_description?: string;
  text?: string;
  time?: number;
}

interface LegacyPlaceDetailsResponse {
  status?: string;
  error_message?: string;
  result?: {
    name?: string;
    rating?: number;
    user_ratings_total?: number;
    reviews?: LegacyReview[];
  };
}

interface LegacyFindPlaceResponse {
  status?: string;
  error_message?: string;
  candidates?: Array<{
    place_id?: string;
  }>;
}

interface PublicReview {
  authorName: string;
  avatarUrl: string | null;
  rating: number;
  text: string;
  relativeTime: string;
  time: number;
}

const DEFAULT_QUERY = "Kabul Sweets Bakery Acacia Ridge";
const CACHE_CONTROL = "public, s-maxage=1800, stale-while-revalidate=86400";

const fallbackReviews: PublicReview[] = [
  {
    authorName: "Sarah A.",
    avatarUrl: null,
    rating: 5,
    text: "The most authentic Afghan sweets I've tasted outside of Kabul. The custom cake was a masterpiece!",
    relativeTime: "recent",
    time: 0,
  },
  {
    authorName: "Ahmed R.",
    avatarUrl: null,
    rating: 5,
    text: "Fresh, rich flavor and excellent service. Perfect pickup option for family gatherings.",
    relativeTime: "recent",
    time: 0,
  },
  {
    authorName: "Nadia K.",
    avatarUrl: null,
    rating: 5,
    text: "Baklava quality is outstanding and the staff are always friendly and helpful.",
    relativeTime: "recent",
    time: 0,
  },
];

function normalizeReviews(reviews: LegacyReview[] | undefined): PublicReview[] {
  if (!reviews?.length) {
    return [];
  }

  return reviews
    .map((review) => ({
      authorName: review.author_name?.trim() || "Google customer",
      avatarUrl: review.profile_photo_url?.trim() || null,
      rating: Math.min(5, Math.max(1, Math.round(review.rating ?? 5))),
      text: review.text?.trim() || "",
      relativeTime: review.relative_time_description?.trim() || "recent",
      time: review.time ?? 0,
    }))
    .filter((review) => review.text.length > 0)
    .sort((a, b) => b.rating - a.rating || b.time - a.time)
    .slice(0, 5);
}

async function resolvePlaceId(apiKey: string): Promise<string | null> {
  const configuredPlaceId = process.env.GOOGLE_PLACES_PLACE_ID?.trim();
  if (configuredPlaceId) {
    return configuredPlaceId;
  }

  const searchQuery = process.env.GOOGLE_PLACES_QUERY?.trim() || DEFAULT_QUERY;
  const searchParams = new URLSearchParams({
    input: searchQuery,
    inputtype: "textquery",
    fields: "place_id",
    key: apiKey,
  });

  const response = await fetch(
    `https://maps.googleapis.com/maps/api/place/findplacefromtext/json?${searchParams.toString()}`,
    { next: { revalidate: 1800 } }
  );

  if (!response.ok) {
    return null;
  }

  const payload = (await response.json()) as LegacyFindPlaceResponse;
  if (payload.status !== "OK") {
    return null;
  }

  return payload.candidates?.[0]?.place_id ?? null;
}

export async function GET() {
  const apiKey = process.env.GOOGLE_PLACES_API_KEY?.trim();

  if (!apiKey) {
    return NextResponse.json(
      {
        placeName: "Kabul Sweets Bakery",
        placeRating: 4.5,
        totalRatings: null,
        source: "fallback",
        reviews: fallbackReviews,
      },
      {
        headers: {
          "Cache-Control": CACHE_CONTROL,
        },
      }
    );
  }

  try {
    const placeId = await resolvePlaceId(apiKey);
    if (!placeId) {
      return NextResponse.json(
        {
          placeName: "Kabul Sweets Bakery",
          placeRating: 4.5,
          totalRatings: null,
          source: "fallback",
          reviews: fallbackReviews,
        },
        {
          headers: {
            "Cache-Control": CACHE_CONTROL,
          },
        }
      );
    }

    const detailsParams = new URLSearchParams({
      place_id: placeId,
      fields: "name,rating,user_ratings_total,reviews",
      language: process.env.GOOGLE_PLACES_LANGUAGE?.trim() || "en",
      reviews_sort: "most_relevant",
      key: apiKey,
    });

    const detailsResponse = await fetch(
      `https://maps.googleapis.com/maps/api/place/details/json?${detailsParams.toString()}`,
      { next: { revalidate: 1800 } }
    );

    if (!detailsResponse.ok) {
      throw new Error(`Google Place Details failed with ${detailsResponse.status}`);
    }

    const detailsPayload = (await detailsResponse.json()) as LegacyPlaceDetailsResponse;
    if (detailsPayload.status !== "OK" || !detailsPayload.result) {
      throw new Error(detailsPayload.error_message || "Unable to fetch Google place details.");
    }

    const reviews = normalizeReviews(detailsPayload.result.reviews);

    return NextResponse.json(
      {
        placeName: detailsPayload.result.name || "Kabul Sweets Bakery",
        placeRating: detailsPayload.result.rating ?? 4.5,
        totalRatings: detailsPayload.result.user_ratings_total ?? null,
        source: reviews.length ? "google" : "fallback",
        reviews: reviews.length ? reviews : fallbackReviews,
      },
      {
        headers: {
          "Cache-Control": CACHE_CONTROL,
        },
      }
    );
  } catch {
    return NextResponse.json(
      {
        placeName: "Kabul Sweets Bakery",
        placeRating: 4.5,
        totalRatings: null,
        source: "fallback",
        reviews: fallbackReviews,
      },
      {
        headers: {
          "Cache-Control": CACHE_CONTROL,
        },
      }
    );
  }
}

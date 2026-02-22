import { NextRequest, NextResponse } from "next/server";

export const dynamic = "force-dynamic";

/** Same candidate list as storefront-api.ts — try each until one works. */
function getBackendCandidates(): string[] {
  const seen = new Set<string>();
  const candidates = [
    process.env.INTERNAL_API_BASE_URL || "",
    process.env.NEXT_PUBLIC_API_BASE_URL || "",
    process.env.API_BASE_URL || "",
    "http://api:8000",
    "http://localhost:8000",
  ];
  return candidates
    .map((u) => u.replace(/\/+$/, ""))
    .filter((u) => {
      if (!u || seen.has(u)) return false;
      seen.add(u);
      return true;
    });
}

function copyRequestHeaders(source: Headers) {
  const headers = new Headers();
  source.forEach((value, key) => {
    const normalized = key.toLowerCase();
    if (
      normalized === "host" ||
      normalized === "connection" ||
      normalized === "content-length"
    ) {
      return;
    }
    headers.set(key, value);
  });
  return headers;
}

function copyResponseHeaders(source: Headers) {
  const headers = new Headers();
  source.forEach((value, key) => {
    const normalized = key.toLowerCase();
    if (normalized === "content-encoding" || normalized === "transfer-encoding") {
      return;
    }
    headers.set(key, value);
  });
  return headers;
}

async function proxy(
  request: NextRequest,
  { params }: { params: Promise<{ path: string[] }> }
) {
  const { path } = await params;
  const apiPath = path.map(encodeURIComponent).join("/");
  const query = request.nextUrl.search;
  const method = request.method.toUpperCase();

  // Only read body if the request actually has content.
  // Sending an empty body on DELETE can confuse FastAPI.
  const hasBody =
    method !== "GET" &&
    method !== "HEAD" &&
    (Number(request.headers.get("content-length") ?? 0) > 0 ||
      !!request.headers.get("transfer-encoding"));
  const body = hasBody ? await request.blob() : undefined;

  const reqHeaders = copyRequestHeaders(request.headers);
  const candidates = getBackendCandidates();

  for (const base of candidates) {
    const targetUrl = `${base}/api/v1/${apiPath}${query}`;
    try {
      const upstream = await fetch(targetUrl, {
        method,
        headers: reqHeaders,
        body,
        redirect: "follow",
        cache: "no-store",
      });
      const responseBody = await upstream.arrayBuffer();
      const responseHeaders = copyResponseHeaders(upstream.headers);
      responseHeaders.set(
        "Cache-Control",
        "private, no-store, no-cache, must-revalidate"
      );
      responseHeaders.set("Pragma", "no-cache");
      // Vary by Authorization so Railway's Varnish/Fastly CDN never shares
      // one user's API response (e.g. cart) with another user.
      responseHeaders.set("Vary", "Authorization, Cookie");
      return new NextResponse(responseBody, {
        status: upstream.status,
        headers: responseHeaders,
      });

    } catch {
      // Try next candidate
      continue;
    }
  }

  return NextResponse.json(
    { detail: "Backend service is unavailable. Please try again shortly." },
    { status: 503 }
  );
}

export async function GET(
  request: NextRequest,
  context: { params: Promise<{ path: string[] }> }
) {
  return proxy(request, context);
}

export async function POST(
  request: NextRequest,
  context: { params: Promise<{ path: string[] }> }
) {
  return proxy(request, context);
}

export async function PUT(
  request: NextRequest,
  context: { params: Promise<{ path: string[] }> }
) {
  return proxy(request, context);
}

export async function PATCH(
  request: NextRequest,
  context: { params: Promise<{ path: string[] }> }
) {
  return proxy(request, context);
}

export async function DELETE(
  request: NextRequest,
  context: { params: Promise<{ path: string[] }> }
) {
  return proxy(request, context);
}

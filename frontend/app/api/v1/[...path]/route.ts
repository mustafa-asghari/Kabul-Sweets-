import { NextRequest, NextResponse } from "next/server";

export const dynamic = "force-dynamic";

const backendBaseUrl = (() => {
  const url =
    process.env.INTERNAL_API_BASE_URL ||
    process.env.NEXT_PUBLIC_API_BASE_URL ||
    process.env.API_BASE_URL;
  if (!url && process.env.NODE_ENV === "production") {
    throw new Error(
      "Missing API base URL. Set INTERNAL_API_BASE_URL or NEXT_PUBLIC_API_BASE_URL."
    );
  }
  return (url || "http://localhost:8000").replace(/\/+$/, "");
})();

function buildTargetUrl(pathSegments: string[], query: string) {
  const apiPath = pathSegments.map(encodeURIComponent).join("/");
  return `${backendBaseUrl}/api/v1/${apiPath}${query}`;
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
  try {
    const { path } = await params;
    const targetUrl = buildTargetUrl(path, request.nextUrl.search);
    const method = request.method.toUpperCase();
    // Blob remains replayable across 307/308 redirects in Node/Undici.
    const body =
      method === "GET" || method === "HEAD" ? undefined : await request.blob();

    const upstream = await fetch(targetUrl, {
      method,
      headers: copyRequestHeaders(request.headers),
      body,
      // Follow backend slash-normalization redirects on the server side.
      redirect: "follow",
      cache: "no-store",
    });

    const responseBody = await upstream.arrayBuffer();
    return new NextResponse(responseBody, {
      status: upstream.status,
      headers: copyResponseHeaders(upstream.headers),
    });
  } catch {
    return NextResponse.json(
      { detail: "Backend service is unavailable. Please try again shortly." },
      { status: 503 }
    );
  }
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

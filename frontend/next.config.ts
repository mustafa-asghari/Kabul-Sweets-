import type { NextConfig } from "next";

const isProduction = process.env.NODE_ENV === "production";

const nextConfig: NextConfig = {
  // Keep standalone output for Docker production builds only.
  // In dev mode this can break route manifests during hot-restarts.
  output: isProduction ? "standalone" : undefined,
  async headers() {
    return [
      {
        // Never cache HTML pages — prevents stale Server Action ID errors
        source: "/((?!_next/static|_next/image|favicon.ico).*)",
        headers: [
          {
            key: "Cache-Control",
            value: "no-store, must-revalidate",
          },
        ],
      },
    ];
  },
  images: {
    formats: ["image/avif", "image/webp"],
    minimumCacheTTL: 60 * 60 * 24 * 14,
    remotePatterns: [
      // Google profile pictures
      {
        protocol: "https",
        hostname: "lh3.googleusercontent.com",
      },
      // AWS S3 — standard hosted buckets (e.g. kabul-sweets-media.s3.ap-southeast-2.amazonaws.com)
      {
        protocol: "https",
        hostname: "**.amazonaws.com",
      },
      // AWS S3 — path-style URLs (s3.ap-southeast-2.amazonaws.com/kabul-sweets-media/...)
      {
        protocol: "https",
        hostname: "s3.*.amazonaws.com",
      },
      // MinIO / LocalStack for local dev
      {
        protocol: "http",
        hostname: "localhost",
        port: "9000",
      },
      {
        protocol: "http",
        hostname: "minio",
        port: "9000",
      },
    ],
    // Images served via the backend proxy (/api/v1/images/.../serve) redirect to
    // S3 pre-signed URLs that include query-string signatures. Allow those through
    // without attempting further optimisation so the 307 redirect is preserved.
    dangerouslyAllowSVG: false,
  },
};

export default nextConfig;

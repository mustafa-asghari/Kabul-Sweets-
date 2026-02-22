import { clerkMiddleware } from "@clerk/nextjs/server";

export default clerkMiddleware();

export const config = {
  matcher: [
    // Limit Clerk middleware to Clerk-hosted auth routes.
    // Running this globally (especially for /api/*) adds avoidable latency.
    "/sign-in(.*)",
    "/sign-up(.*)",
  ],
};

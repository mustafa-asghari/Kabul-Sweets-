import { revalidateTag } from "next/cache";
import { NextRequest, NextResponse } from "next/server";

/**
 * POST /api/revalidate
 *
 * On-demand cache invalidation webhook.
 * Called by the admin backend after any product/image create, update, or delete.
 *
 * Protected by a shared secret: REVALIDATION_SECRET env var.
 * Example call from backend:
 *   POST https://kabulsweets.com.au/api/revalidate
 *   Authorization: Bearer <REVALIDATION_SECRET>
 *   Body: { "tags": ["products"] }   ← optional, defaults to ["products"]
 */
export async function POST(request: NextRequest) {
    const secret = process.env.REVALIDATION_SECRET;

    // If a secret is configured, enforce it.
    if (secret) {
        const auth = request.headers.get("authorization") ?? "";
        const token = auth.startsWith("Bearer ") ? auth.slice(7) : auth;
        if (token !== secret) {
            return NextResponse.json({ error: "Unauthorized" }, { status: 401 });
        }
    }

    let tags: string[] = ["products"];
    try {
        const body = await request.json();
        if (Array.isArray(body?.tags) && body.tags.length > 0) {
            tags = body.tags;
        }
    } catch {
        // No body / not JSON — use default tags
    }

    for (const tag of tags) {
        revalidateTag(tag);
    }

    return NextResponse.json({
        revalidated: true,
        tags,
        timestamp: new Date().toISOString(),
    });
}

import { revalidateTag } from "next/cache";
import { NextRequest, NextResponse } from "next/server";

/**
 * POST /api/revalidate
 *
 * On-demand cache invalidation — called by the backend after any product
 * create, update, or delete.  Instantly busts the "products" Next.js cache
 * tag so the next visitor gets fresh, re-rendered HTML.
 *
 * Protected by REVALIDATION_SECRET env var (optional but recommended).
 */
export async function POST(request: NextRequest) {
    const secret = process.env.REVALIDATION_SECRET;

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
        // no body / not JSON — use default tags
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

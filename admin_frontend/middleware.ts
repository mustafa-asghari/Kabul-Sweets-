import { NextResponse } from 'next/server';
import type { NextRequest } from 'next/server';

const publicPaths = ['/auth/signin', '/auth/signup', '/auth/password-reset'];

export default function middleware(req: NextRequest) {
  const { pathname } = req.nextUrl;

  // Allow API routes, public paths, and static assets
  if (
    pathname.startsWith('/api/') ||
    publicPaths.some((path) => pathname.startsWith(path))
  ) {
    return NextResponse.next();
  }

  const accessToken = req.cookies.get('access_token')?.value;
  const refreshToken = req.cookies.get('refresh_token')?.value;

  // No auth cookies at all: redirect to sign-in
  if (!accessToken && !refreshToken) {
    const signinUrl = new URL('/auth/signin', req.url);
    signinUrl.searchParams.set('callbackUrl', pathname);
    return NextResponse.redirect(signinUrl);
  }

  // Stale partial session: clear and force re-auth
  if (accessToken && !refreshToken) {
    const signinUrl = new URL('/auth/signin', req.url);
    signinUrl.searchParams.set('callbackUrl', pathname);
    const response = NextResponse.redirect(signinUrl);
    response.cookies.delete('access_token');
    return response;
  }

  return NextResponse.next();
}

export const config = {
  matcher: [
    '/((?!_next|[^?]*\\.(?:html?|css|js(?!on)|jpe?g|webp|png|gif|svg|ttf|woff2?|ico|csv|docx?|xlsx?|zip|webmanifest)).*)',
    '/(api|trpc)(.*)',
  ],
};

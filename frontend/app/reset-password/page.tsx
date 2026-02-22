"use client";

import Link from "next/link";
import Navbar from "@/components/Navbar";
import Footer from "@/components/Footer";

export default function ResetPasswordPage() {
  return (
    <>
      <Navbar />
      <main className="flex-1 pb-20">
        <section className="max-w-[720px] mx-auto px-6 pt-8">
          <div className="rounded-[2rem] bg-cream-dark px-6 py-12">
            <h1 className="text-4xl font-extrabold tracking-tight text-black">
              Reset Password
            </h1>
            <p className="mt-2 text-sm text-gray-600">
              Password management is now handled through our sign-in system.
            </p>
          </div>
        </section>

        <section className="max-w-[720px] mx-auto px-6 pt-8">
          <div className="rounded-[1.5rem] bg-white border border-[#eadcc8] p-6">
            <p className="text-sm text-gray-700">
              We have upgraded to a more secure sign-in system. Password resets
              are now handled directly through the sign-in flow — click
              &ldquo;Forgot password?&rdquo; on the sign-in screen to reset yours.
            </p>
            <div className="mt-5 flex flex-wrap gap-3">
              <button
                type="button"
                onClick={() => window.dispatchEvent(new Event("open-auth-modal"))}
                className="rounded-full bg-black px-5 py-2.5 text-sm font-semibold text-white hover:bg-[#222] transition"
              >
                Sign in
              </button>
              <Link
                href="/"
                className="rounded-full border border-[#e7d8c2] px-5 py-2.5 text-sm font-semibold text-black hover:bg-[#f5f2eb] transition"
              >
                Back to home
              </Link>
            </div>
          </div>
        </section>
      </main>
      <Footer />
    </>
  );
}

import Link from "next/link";
import Navbar from "@/components/Navbar";

export default function NotFound() {
  return (
    <>
      <Navbar />
      <main className="flex-1">
        <section className="max-w-[1200px] mx-auto px-6 py-8">
          <div className="min-h-[70vh] rounded-[2rem] bg-cream-dark flex items-center justify-center px-6 py-14 text-center">
            <div>
              <span className="inline-flex items-center rounded-full bg-white px-4 py-1.5 text-xs font-semibold text-gray-600 shadow-sm">
                Page Not Found
              </span>
              <h1 className="mt-6 text-5xl md:text-7xl font-extrabold tracking-tight leading-[1.04] text-black">
                You look a little lost?
              </h1>
              <p className="mt-4 text-base md:text-lg text-gray-500">
                Don&apos;t worry, let&apos;s go home.
              </p>
              <Link
                href="/"
                className="mt-8 inline-flex items-center gap-2 rounded-full bg-white px-6 py-3 text-sm font-semibold text-black shadow-sm hover:shadow-md transition"
              >
                Go Home
                <span className="material-symbols-outlined text-[18px]">north_east</span>
              </Link>
            </div>
          </div>
        </section>
      </main>
    </>
  );
}

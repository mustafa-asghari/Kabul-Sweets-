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
              <h1 className="text-5xl md:text-7xl font-extrabold tracking-tight leading-[1.04] text-black">
                You look a little lost?
              </h1>
              <p className="mt-4 text-base md:text-lg text-gray-500">
                Don&apos;t worry, let&apos;s go home.
              </p>
              <Link
                href="/"
                className="mt-8 inline-flex text-sm font-semibold text-black hover:text-accent transition"
              >
                Go Home
              </Link>
            </div>
          </div>
        </section>
      </main>
    </>
  );
}

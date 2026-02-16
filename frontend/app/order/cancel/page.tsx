import Link from "next/link";
import Navbar from "@/components/Navbar";
import Footer from "@/components/Footer";

export default function OrderCancelPage() {
  return (
    <>
      <Navbar />
      <main className="flex-1 pb-20">
        <section className="max-w-[820px] mx-auto px-6 pt-12">
          <div className="rounded-[2rem] bg-cream-dark px-6 py-12 text-center">
            <h1 className="text-4xl font-extrabold tracking-tight text-black">
              Checkout Cancelled
            </h1>
            <p className="mt-3 text-sm text-gray-600">
              Your payment was not authorized. You can return to your cart and try again.
            </p>
            <div className="mt-6 flex items-center justify-center gap-3">
              <Link
                href="/shop"
                className="rounded-full bg-black px-5 py-2 text-sm font-semibold text-white"
              >
                Back to Shop
              </Link>
              <Link
                href="/orders"
                className="rounded-full bg-white px-5 py-2 text-sm font-semibold text-black border border-[#e8dcc9]"
              >
                View Orders
              </Link>
            </div>
          </div>
        </section>
      </main>
      <Footer />
    </>
  );
}

import Link from "next/link";
import Navbar from "@/components/Navbar";
import Footer from "@/components/Footer";
import CustomCakePaymentConfirm from "@/components/CustomCakePaymentConfirm";

interface OrderSuccessPageProps {
  searchParams: Promise<{
    payment_type?: string;
    session_id?: string;
    custom_cake_id?: string;
  }>;
}

export default async function OrderSuccessPage({ searchParams }: OrderSuccessPageProps) {
  const params = await searchParams;
  const paymentType = (params.payment_type || "").toLowerCase();
  const isCustomCakePayment = paymentType === "custom_cake";
  const sessionId = params.session_id;
  const customCakeId = params.custom_cake_id;

  const title = isCustomCakePayment ? "Payment Received" : "Payment Authorized";
  const description = isCustomCakePayment
    ? "Your custom cake payment was successful. Your request is marked paid and moved forward for preparation."
    : "Your order is now awaiting admin confirmation. Your card is only charged after approval.";

  return (
    <>
      <Navbar />
      <main className="flex-1 pb-20">
        <section className="max-w-[820px] mx-auto px-6 pt-12">
          <div className="rounded-[2rem] bg-cream-dark px-6 py-12 text-center">
            <h1 className="text-4xl font-extrabold tracking-tight text-black">
              {title}
            </h1>
            <p className="mt-3 text-sm text-gray-600">
              {description}
            </p>
            {isCustomCakePayment ? (
              <CustomCakePaymentConfirm customCakeId={customCakeId} sessionId={sessionId} />
            ) : null}
            <div className="mt-6 flex items-center justify-center gap-3">
              <Link
                href="/orders"
                className="rounded-full bg-black px-5 py-2 text-sm font-semibold text-white"
              >
                View Orders
              </Link>
              <Link
                href="/shop"
                className="rounded-full bg-white px-5 py-2 text-sm font-semibold text-black border border-[#e8dcc9]"
              >
                Continue Shopping
              </Link>
            </div>
          </div>
        </section>
      </main>
      <Footer />
    </>
  );
}

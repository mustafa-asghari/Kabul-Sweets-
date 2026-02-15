import Footer from "@/components/Footer";
import Navbar from "@/components/Navbar";
import PageHero from "@/components/PageHero";
import ScrollReveal from "@/components/ScrollReveal";

const privacyParagraphs = [
  "Kabul Sweets values your privacy. This policy explains how we collect, use, and protect your personal information when you browse or place an order.",
  "We collect only the details needed to complete your order and provide support, including contact information, pickup details, and order preferences.",
  "Payment details are processed through secure third-party payment providers. Kabul Sweets does not store full card information on its own servers.",
  "We may use analytics and cookies to understand how visitors use the site and to improve performance, content, and checkout flow.",
  "Your information is never sold. We only share necessary data with payment processors or service providers needed to fulfill pickup and takeaway orders.",
  "You may request access, updates, or deletion of your personal information by contacting our support team.",
];

export default function PrivacyPolicyPage() {
  return (
    <>
      <Navbar />
      <main className="flex-1 pb-20">
        <PageHero
          badge="Legal"
          title="Privacy Policy"
          description="Last updated: February 2026"
        />

        <section className="max-w-[900px] mx-auto px-6 pb-8">
          <ScrollReveal className="rounded-[1.8rem] bg-white p-8 md:p-12 shadow-sm">
            <div className="space-y-6">
              {privacyParagraphs.map((paragraph) => (
                <p key={paragraph} className="text-base text-gray-700 leading-relaxed">
                  {paragraph}
                </p>
              ))}
            </div>
          </ScrollReveal>
        </section>
      </main>
      <Footer />
    </>
  );
}

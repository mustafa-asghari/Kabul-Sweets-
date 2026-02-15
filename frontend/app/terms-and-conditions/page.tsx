import Footer from "@/components/Footer";
import Navbar from "@/components/Navbar";
import PageHero from "@/components/PageHero";
import ScrollReveal from "@/components/ScrollReveal";

const termsParagraphs = [
  "Welcome to Kabul Sweets. By using our website and services, you agree to comply with and be bound by these terms and conditions.",
  "By accessing our website, you confirm that you are at least 18 years old or have the legal authority to agree to these terms. You agree to use the site only for lawful purposes and in compliance with all applicable laws.",
  "All text, images, logos, and product descriptions on this website are the property of Kabul Sweets or its licensors. You may not copy, reproduce, or distribute website content without written consent.",
  "If you submit reviews, photos, or feedback, you grant Kabul Sweets a non-exclusive, royalty-free license to use that content for promotional or operational purposes.",
  "Our services are provided as-is. While we aim to keep information accurate and current, we do not guarantee uninterrupted availability or complete accuracy at all times.",
  "Kabul Sweets is not liable for indirect or consequential damages arising from website use, order delays caused by external carriers, or events outside our control.",
  "These terms may be updated periodically to reflect legal or operational changes. Continued use of the website after updates constitutes acceptance of the revised terms.",
];

export default function TermsAndConditionsPage() {
  return (
    <>
      <Navbar />
      <main className="flex-1 pb-20">
        <PageHero
          badge="Legal"
          title="Terms & Conditions"
          description="Last updated: February 2026"
        />

        <section className="max-w-[900px] mx-auto px-6 pb-8">
          <ScrollReveal className="rounded-[1.8rem] bg-white p-8 md:p-12 shadow-sm">
            <div className="space-y-6">
              {termsParagraphs.map((paragraph) => (
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

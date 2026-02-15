import Footer from "@/components/Footer";
import Navbar from "@/components/Navbar";
import PageHero from "@/components/PageHero";
import FaqAccordion from "@/components/FaqAccordion";
import ScrollReveal from "@/components/ScrollReveal";
import { supportBenefits, supportFaqs } from "@/data/storefront";

export default function SupportPage() {
  return (
    <>
      <Navbar />
      <main className="flex-1 pb-20">
        <PageHero
          badge="Support"
          title="Help your customers quickly and clearly."
          description="Use this page to answer common questions, guide customers, and keep support requests organized."
        />

        <section className="max-w-[860px] mx-auto px-6 pb-16">
          <ScrollReveal className="text-center mb-8">
            <h2 className="text-4xl font-extrabold tracking-tight text-black">Frequently asked questions</h2>
            <p className="mt-3 text-sm text-gray-500">
              Give customers quick answers to the questions they ask most.
            </p>
          </ScrollReveal>

          <ScrollReveal>
            <FaqAccordion items={supportFaqs} />
          </ScrollReveal>
        </section>

        <section className="max-w-[860px] mx-auto px-6 pb-16">
          <ScrollReveal className="text-center mb-8">
            <h2 className="text-4xl font-extrabold tracking-tight text-black">Still got questions?</h2>
            <p className="mt-3 text-sm text-gray-500">
              Send us a message and we will get back to you within one business day.
            </p>
          </ScrollReveal>

          <ScrollReveal>
            <form
              className="rounded-[2rem] bg-cream-dark/60 p-6 md:p-8"
              onSubmit={(event) => event.preventDefault()}
            >
              <div className="grid grid-cols-1 gap-5">
                <label className="text-sm font-semibold text-black">
                  Name
                  <input
                    type="text"
                    placeholder="Joe Gomez"
                    className="mt-2 w-full rounded-xl border border-transparent bg-white px-4 py-3 text-sm text-gray-700 outline-none focus:ring-2 focus:ring-accent/30"
                  />
                </label>
                <label className="text-sm font-semibold text-black">
                  Email
                  <input
                    type="email"
                    placeholder="joe@gomez.com"
                    className="mt-2 w-full rounded-xl border border-transparent bg-white px-4 py-3 text-sm text-gray-700 outline-none focus:ring-2 focus:ring-accent/30"
                  />
                </label>
                <label className="text-sm font-semibold text-black">
                  Message
                  <textarea
                    rows={4}
                    placeholder="Hey, I need help with..."
                    className="mt-2 w-full rounded-xl border border-transparent bg-white px-4 py-3 text-sm text-gray-700 outline-none resize-none focus:ring-2 focus:ring-accent/30"
                  />
                </label>
                <button
                  type="submit"
                  className="w-full rounded-full bg-accent py-3 text-sm font-semibold text-white hover:bg-accent-light transition"
                >
                  Submit
                </button>
              </div>
            </form>
          </ScrollReveal>
        </section>

        <section className="max-w-[1200px] mx-auto px-6 pb-6">
          <ScrollReveal
            staggerChildren={0.08}
            className="grid grid-cols-1 sm:grid-cols-2 xl:grid-cols-4 gap-6"
          >
            {supportBenefits.map((benefit) => (
              <article key={benefit.title} className="bg-cream-dark rounded-[1.5rem] p-6">
                <div className="w-10 h-10 rounded-full bg-white flex items-center justify-center mb-4">
                  <span className="material-symbols-outlined text-accent text-[20px]">
                    {benefit.icon}
                  </span>
                </div>
                <h3 className="text-2xl font-bold tracking-tight text-black">{benefit.title}</h3>
                <p className="mt-2 text-sm text-gray-500 leading-relaxed">{benefit.description}</p>
              </article>
            ))}
          </ScrollReveal>
        </section>
      </main>
      <Footer />
    </>
  );
}

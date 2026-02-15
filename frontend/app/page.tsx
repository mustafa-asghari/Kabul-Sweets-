import Navbar from "@/components/Navbar";
import HeroSection from "@/components/HeroSection";
import ProductCard from "@/components/ProductCard";
import TestimonialSection from "@/components/TestimonialSection";
import CollectionCard from "@/components/CollectionCard";
import ActionBanner from "@/components/ActionBanner";
import FeatureCard from "@/components/FeatureCard";
import Footer from "@/components/Footer";
import ScrollReveal from "@/components/ScrollReveal";

const products = [
  {
    title: "Celebration Cakes",
    category: "Cakes",
    price: "From $45",
    imageSrc:
      "https://lh3.googleusercontent.com/aida-public/AB6AXuDq89SDCLSN76kunOlhOstWiLYy_EeKgfBrsy6JZz0jpshRTC5CihmDbiihKD5znmF1qTa8n9HUjyYRQUtb3CC56I5AgfAWbENpaxpv1KCiW_H8R9o4YhRNGErDGMrNhP8iYQ0iawo7QghrlZvf8kpWnMlHIu-Gzgre5OAYuR3DZYP_N8DnY6bkbpZd3TKkzKZx6XhoL2hWzO0FWacx2PSfE-Uw_6QfzhhRXSpffNHqrVnQSyIPwq6ha430fe3jmJL4Xv45KFNk83g",
    imageAlt: "Cakes",
  },
  {
    title: "Traditional Cookies",
    category: "Cookies",
    price: "From $12",
    imageSrc:
      "https://lh3.googleusercontent.com/aida-public/AB6AXuAmNszbrm5j1meuumPGKDE44YrXMEXbDqMCtVelbJ3rqmX2HTN1soWGITmlVS5_igaZorkr-J750uVaLXsDIzUIJ-P9XHIbFow4tCrjTkG0MLacpug5Gvbt3l4w2RQx4Y1lhUb_l5DDrxiYjnDT6hxu4SHja7QVSLwqdk2CJwqNvOUFDGS_-_AENosF3_itewm-6_hxFqhZf3Hwutqt9WoQwAt6gF5YamYYW85QRRmn_uMjtGtqKJmw8wTF4X46bqXr2wU1cAwwq-0",
    imageAlt: "Cookies",
  },
  {
    title: "Custom Desserts",
    category: "Custom",
    price: "Get a Quote",
    imageSrc:
      "https://lh3.googleusercontent.com/aida-public/AB6AXuCRwMWm2SS6iyVE6wOWLPYDtztsggz0K3W3udSsDaxpmV8Wt1pP5Tih-0ZmOOvdCJY0a6Us9whZg6EjdfYQQS_OttCQi2itTCd3PGQJGYOEhFPvSThq3v8eSREXXLkmZP4pu2Ek96v3wq6DvK8w1rzT4cVtsakLB7u02N2rN8quIf9QmPNt6DO_RBqBtpcJnmYSt9zqAlyHZ0d6OwAwJjLDxYRzTjmEaUJf4BX6s9BKjfi5jAF00hEUM-v12G5FMjH8KT_eCWa3P-Q",
    imageAlt: "Custom",
  },
];

const collections = [
  {
    title: "Cakes",
    imageSrc:
      "https://lh3.googleusercontent.com/aida-public/AB6AXuCES2iOrCShE2dEwcyQDRg8ucodp66z8YYUrcjcCCUlmC_sfkQ-sXaRzKGFSg2sSz2ysGvsP5502plUf9n_ubXb1LhlnKES14MsXQ8yQBZW2fpRZEv5gV6M1pboGxGY_CQ0rk3nTNdR2NdwzQEHpFcDeVBNz0XvhMDDeiNjBcEoGceGCMRqzTztTuz9soQ-ts9f_pEf5FwdVXoG2NuSVdumVY4N2GjLBwqtbasRvJEbYKf2phSVJpYPaMLlz3P_19A-odFA4W3DUFk",
    imageAlt: "Cakes collection",
  },
  {
    title: "Sweets",
    imageSrc:
      "https://lh3.googleusercontent.com/aida-public/AB6AXuAmNszbrm5j1meuumPGKDE44YrXMEXbDqMCtVelbJ3rqmX2HTN1soWGITmlVS5_igaZorkr-J750uVaLXsDIzUIJ-P9XHIbFow4tCrjTkG0MLacpug5Gvbt3l4w2RQx4Y1lhUb_l5DDrxiYjnDT6hxu4SHja7QVSLwqdk2CJwqNvOUFDGS_-_AENosF3_itewm-6_hxFqhZf3Hwutqt9WoQwAt6gF5YamYYW85QRRmn_uMjtGtqKJmw8wTF4X46bqXr2wU1cAwwq-0",
    imageAlt: "Sweets collection",
  },
  {
    title: "Baklava",
    imageSrc:
      "https://lh3.googleusercontent.com/aida-public/AB6AXuB6tLZJ1uVLF31wVgDU2cOO-RvXdoqiX4F8mHhoDsArffu9w20bplOd6O0ag8LfJ1RCKfE2wZaNtMaty8Fja0ymXQtQhiPzbX4KeMjbBUzeS7FT1rvxLBciQo_PFLaSZOox2IItWRcR_bRw2Llcl6oFCBvyf3acMyyF_pXCe1xf8mz5MHuWeAQ0KT4QsbCvFWYS4lsZitsJbYJgdd5Za6JBivEWfyQubhKbZ4VI5Dt7EQMAgvjGFEFDHjWwpgRR5Rafp9j8x3cVsiQ",
    imageAlt: "Baklava collection",
  },
];

const features = [
  {
    icon: "verified",
    title: "Halal Certified",
    description:
      "All our products are 100% Halal certified, ensuring the highest standards.",
  },
  {
    icon: "local_shipping",
    title: "QLD Delivery",
    description:
      "Fast and reliable delivery across Queensland for all your events.",
  },
  {
    icon: "oven_gen",
    title: "Baked Fresh Daily",
    description:
      "Our ovens run every morning to bring you the freshest taste.",
  },
];

export default function Home() {
  return (
    <>
      <Navbar />
      <main className="flex-1">
        <HeroSection />

        {/* Most Popular */}
        <section className="max-w-[1200px] mx-auto px-6 pb-20">
          <ScrollReveal>
            <div className="flex flex-col md:flex-row justify-between items-start md:items-end mb-2 gap-2">
              <div>
                <h2 className="text-2xl font-extrabold tracking-tight text-black">
                  Most Popular
                </h2>
                <p className="text-sm text-gray-500 mt-1">
                  Showcase our most popular products, front and center.
                </p>
              </div>
              <a
                href="#"
                className="inline-flex items-center gap-1.5 rounded-full border border-black/10 bg-white px-4 py-2 text-xs font-semibold text-black shadow-sm transition-all hover:-translate-y-0.5 hover:border-accent hover:text-accent hover:shadow-md"
              >
                View All{" "}
                <span className="material-symbols-outlined text-[16px]">
                  arrow_forward
                </span>
              </a>
            </div>
          </ScrollReveal>
          <hr className="border-gray-200 mb-10" />
          <ScrollReveal staggerChildren={0.1} className="grid grid-cols-1 md:grid-cols-3 gap-6">
            {products.map((product) => (
              <ProductCard key={product.title} {...product} />
            ))}
          </ScrollReveal>
        </section>

        <TestimonialSection />

        {/* Our Collections */}
        <section className="max-w-[1200px] mx-auto px-6 pb-20">
          <ScrollReveal>
            <div className="flex flex-col md:flex-row justify-between items-start md:items-end mb-2 gap-2">
              <div>
                <h2 className="text-2xl font-extrabold tracking-tight text-black">
                  Our Collections
                </h2>
                <p className="text-sm text-gray-500 mt-1">
                  Showcase all the different collections you have to offer.
                </p>
              </div>
              <a
                href="#"
                className="inline-flex items-center gap-1.5 rounded-full border border-black/10 bg-white px-4 py-2 text-xs font-semibold text-black shadow-sm transition-all hover:-translate-y-0.5 hover:border-accent hover:text-accent hover:shadow-md"
              >
                View All{" "}
                <span className="material-symbols-outlined text-[16px]">
                  arrow_forward
                </span>
              </a>
            </div>
          </ScrollReveal>
          <hr className="border-gray-200 mb-10" />
          <ScrollReveal staggerChildren={0.1} className="grid grid-cols-1 md:grid-cols-3 gap-6">
            {collections.map((collection) => (
              <CollectionCard key={collection.title} {...collection} />
            ))}
          </ScrollReveal>
        </section>

        <ActionBanner />

        {/* Features */}
        <section className="max-w-[1200px] mx-auto px-6 pb-20">
          <ScrollReveal className="text-center mb-12">
            <h2 className="text-2xl font-extrabold tracking-tight text-black mb-2">
              Highlight what makes you stand out
            </h2>
            <p className="text-sm text-gray-500">
              Use this section to show off the key features like these.
            </p>
          </ScrollReveal>
          <ScrollReveal staggerChildren={0.1} className="grid grid-cols-1 md:grid-cols-3 gap-6">
            {features.map((feature) => (
              <FeatureCard key={feature.title} {...feature} />
            ))}
          </ScrollReveal>
        </section>
      </main>
      <Footer />
    </>
  );
}

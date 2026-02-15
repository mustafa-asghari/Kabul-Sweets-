import Link from "next/link";
import Navbar from "@/components/Navbar";
import HeroSection from "@/components/HeroSection";
import ProductCard from "@/components/ProductCard";
import TestimonialSection from "@/components/TestimonialSection";
import CollectionCard from "@/components/CollectionCard";
import ActionBanner from "@/components/ActionBanner";
import FeatureCard from "@/components/FeatureCard";
import Footer from "@/components/Footer";
import ScrollReveal from "@/components/ScrollReveal";
import { collections, formatPrice, storeProducts } from "@/data/storefront";

const featuredProducts = storeProducts.slice(0, 3);
const featuredCollections = collections;
const businessHighlights = [
  {
    icon: "location_on",
    title: "Store Location",
    description: "1102 Beaudesert Rd, Acacia Ridge QLD 4110.",
  },
  {
    icon: "star",
    title: "Google Rating 4.5",
    description:
      "Google users rate Kabul Sweets Bakery 4.5 out of 5.",
  },
  {
    icon: "storefront",
    title: "Pickup & Takeaway",
    description:
      "No delivery service. Orders are for in-store pickup and takeaway.",
  },
];

export default function Home() {
  return (
    <>
      <Navbar />
      <main className="flex-1">
        <HeroSection />

        <section className="max-w-[1200px] mx-auto px-6 pb-20">
          <ScrollReveal>
            <div className="flex flex-col md:flex-row justify-between items-start md:items-end mb-2 gap-2">
              <div>
                <h2 className="text-2xl font-extrabold tracking-tight text-black">
                  Most Popular
                </h2>
                <p className="text-sm text-gray-500 mt-1">
                  Fresh picks your customers usually add first.
                </p>
              </div>
              <Link
                href="/shop"
                className="text-sm font-semibold text-black hover:text-accent transition flex items-center gap-1"
              >
                View All
                <span className="material-symbols-outlined text-[16px]">
                  arrow_forward
                </span>
              </Link>
            </div>
          </ScrollReveal>
          <hr className="border-gray-200 mb-10" />
          <ScrollReveal
            staggerChildren={0.1}
            className="grid grid-cols-1 md:grid-cols-3 gap-6"
          >
            {featuredProducts.map((product) => (
              <ProductCard
                key={product.slug}
                slug={product.slug}
                title={product.title}
                category={product.category}
                price={formatPrice(product.price)}
                imageSrc={product.imageSrc}
                imageAlt={product.title}
              />
            ))}
          </ScrollReveal>
        </section>

        <section className="max-w-[1200px] mx-auto px-6 pb-20">
          <ScrollReveal
            staggerChildren={0.1}
            className="grid grid-cols-1 md:grid-cols-3 gap-6"
          >
            {businessHighlights.map((item) => (
              <FeatureCard key={item.title} {...item} />
            ))}
          </ScrollReveal>
        </section>

        <section className="max-w-[1200px] mx-auto px-6 pb-20">
          <ScrollReveal>
            <div className="flex flex-col md:flex-row justify-between items-start md:items-end mb-2 gap-2">
              <div>
                <h2 className="text-2xl font-extrabold tracking-tight text-black">
                  Our Collections
                </h2>
                <p className="text-sm text-gray-500 mt-1">
                  Browse grouped products for faster shopping.
                </p>
              </div>
              <Link
                href="/collections"
                className="text-sm font-semibold text-black hover:text-accent transition flex items-center gap-1"
              >
                View All
                <span className="material-symbols-outlined text-[16px]">
                  arrow_forward
                </span>
              </Link>
            </div>
          </ScrollReveal>
          <hr className="border-gray-200 mb-10" />
          <ScrollReveal
            staggerChildren={0.1}
            className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-6"
          >
            {featuredCollections.map((collection) => (
              <CollectionCard
                key={collection.title}
                title={collection.title}
                description={collection.description}
                imageSrc={collection.imageSrc}
                imageAlt={collection.imageAlt}
                href={`/shop?category=${encodeURIComponent(collection.title)}`}
              />
            ))}
          </ScrollReveal>
        </section>

        <ActionBanner />

        <TestimonialSection />
      </main>
      <Footer />
    </>
  );
}

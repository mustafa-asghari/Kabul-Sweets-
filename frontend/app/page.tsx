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
import { formatPrice, supportBenefits } from "@/data/storefront";
import { fetchStoreProducts, getCollectionsFromProducts } from "@/lib/storefront-api";

// Always render fresh — products change in real-time via the admin panel.
export const dynamic = "force-dynamic";

export default async function Home() {
  const allProducts = await fetchStoreProducts({ limit: 30 });
  const featuredProducts = (allProducts.filter((product) => product.isFeatured).length > 0
    ? allProducts.filter((product) => product.isFeatured)
    : allProducts
  ).slice(0, 3);
  const featuredCollections = getCollectionsFromProducts(allProducts).slice(0, 3);
  const businessHighlights = supportBenefits.slice(0, 3);

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
            {featuredProducts.length > 0 ? (
              featuredProducts.map((product) => (
                <ProductCard
                  key={product.slug}
                  slug={product.slug}
                  title={product.title}
                  category={product.category}
                  price={formatPrice(product.price)}
                  imageSrc={product.imageSrc}
                  imageAlt={product.title}
                />
              ))
            ) : (
              <article className="md:col-span-3 rounded-[1.5rem] bg-cream-dark/60 p-8">
                <h3 className="text-2xl font-extrabold tracking-tight text-black">No featured products yet</h3>
                <p className="mt-2 text-sm text-gray-600">
                  Add products in the backend to populate this section.
                </p>
              </article>
            )}
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
            {featuredCollections.length > 0 ? (
              featuredCollections.map((collection) => (
                <CollectionCard
                  key={collection.title}
                  title={collection.title}
                  description={collection.description}
                  imageSrc={collection.imageSrc}
                  imageAlt={collection.imageAlt}
                  href={`/shop?category=${encodeURIComponent(collection.title)}`}
                />
              ))
            ) : (
              <article className="md:col-span-2 xl:col-span-3 rounded-[1.5rem] bg-cream-dark/60 p-8">
                <h3 className="text-2xl font-extrabold tracking-tight text-black">No collections available</h3>
                <p className="mt-2 text-sm text-gray-600">
                  Collections are generated from product categories in the backend.
                </p>
              </article>
            )}
          </ScrollReveal>
        </section>

        <ActionBanner zoomOut />

        <TestimonialSection />
      </main>
      <Footer />
    </>
  );
}

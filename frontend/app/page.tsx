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
import {
  blogPosts,
  collections,
  formatPrice,
  storeProducts,
  supportBenefits,
} from "@/data/storefront";

const featuredProducts = storeProducts.slice(0, 3);
const featuredCollections = collections.slice(0, 3);
const homeFeatures = supportBenefits.slice(0, 3);
const [featuredPost, ...secondaryPosts] = blogPosts;

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
                className="inline-flex items-center gap-1.5 rounded-full border border-black/10 bg-white px-4 py-2 text-xs font-semibold text-black shadow-sm transition-all hover:-translate-y-0.5 hover:border-accent hover:text-accent hover:shadow-md"
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

        <TestimonialSection />

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
                className="inline-flex items-center gap-1.5 rounded-full border border-black/10 bg-white px-4 py-2 text-xs font-semibold text-black shadow-sm transition-all hover:-translate-y-0.5 hover:border-accent hover:text-accent hover:shadow-md"
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
            {featuredCollections.map((collection) => (
              <CollectionCard
                key={collection.title}
                title={collection.title}
                imageSrc={collection.imageSrc}
                imageAlt={collection.imageAlt}
                href={`/shop?category=${encodeURIComponent(collection.title)}`}
              />
            ))}
          </ScrollReveal>
        </section>

        <ActionBanner />

        <section className="max-w-[1200px] mx-auto px-6 pb-20">
          <ScrollReveal className="text-center mb-12">
            <h2 className="text-2xl font-extrabold tracking-tight text-black mb-2">
              Highlight what makes you stand out
            </h2>
            <p className="text-sm text-gray-500">
              Build trust quickly with clear service promises.
            </p>
          </ScrollReveal>
          <ScrollReveal
            staggerChildren={0.1}
            className="grid grid-cols-1 md:grid-cols-3 gap-6"
          >
            {homeFeatures.map((feature) => (
              <FeatureCard key={feature.title} {...feature} />
            ))}
          </ScrollReveal>
        </section>

        <section className="max-w-[1200px] mx-auto px-6 pb-20">
          <ScrollReveal>
            <div className="flex items-end justify-between mb-8">
              <div>
                <h2 className="text-2xl font-extrabold tracking-tight text-black">
                  Explore the blog
                </h2>
                <p className="mt-1 text-sm text-gray-500">
                  Share stories, product ideas, and catering tips.
                </p>
              </div>
              <Link
                href="/blog"
                className="inline-flex items-center gap-1.5 rounded-full border border-black/10 bg-white px-4 py-2 text-xs font-semibold text-black shadow-sm transition-all hover:-translate-y-0.5 hover:border-accent hover:text-accent hover:shadow-md"
              >
                View Posts
                <span className="material-symbols-outlined text-[16px]">
                  arrow_forward
                </span>
              </Link>
            </div>
          </ScrollReveal>

          <ScrollReveal className="rounded-[2rem] overflow-hidden bg-cream-dark grid grid-cols-1 md:grid-cols-2 mb-6">
            <div className="relative min-h-[280px] md:min-h-full bg-[radial-gradient(circle_at_20%_20%,#fff2c8_0%,#f2d59d_26%,#e4be76_52%,#f5ebda_82%)]" />
            <div className="p-8 md:p-10 flex flex-col justify-between">
              <div>
                <span className="inline-flex rounded-full bg-white px-3 py-1 text-xs font-semibold text-gray-600">
                  {featuredPost.tag}
                </span>
                <h3 className="mt-4 text-3xl font-extrabold tracking-tight leading-tight text-black">
                  {featuredPost.title}
                </h3>
                <p className="mt-4 text-sm text-gray-600 leading-relaxed">
                  {featuredPost.excerpt}
                </p>
              </div>
              <p className="mt-6 text-xs text-gray-500">
                Written by {featuredPost.author}
                <span className="block">{featuredPost.role}</span>
              </p>
            </div>
          </ScrollReveal>

          <ScrollReveal
            staggerChildren={0.08}
            className="grid grid-cols-1 md:grid-cols-3 gap-6"
          >
            {secondaryPosts.map((post) => (
              <article
                key={post.slug}
                className="rounded-[1.5rem] overflow-hidden bg-white hover:shadow-md transition-shadow"
              >
                <div className="h-44 bg-cream-dark" />
                <div className="p-5">
                  <span className="inline-flex rounded-full bg-cream-dark px-3 py-1 text-xs font-semibold text-gray-600">
                    {post.tag}
                  </span>
                  <h3 className="mt-3 font-bold text-lg leading-snug text-black">{post.title}</h3>
                </div>
              </article>
            ))}
          </ScrollReveal>
        </section>
      </main>
      <Footer />
    </>
  );
}

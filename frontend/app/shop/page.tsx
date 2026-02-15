import Link from "next/link";
import Footer from "@/components/Footer";
import Navbar from "@/components/Navbar";
import PageHero from "@/components/PageHero";
import ProductCard from "@/components/ProductCard";
import ScrollReveal from "@/components/ScrollReveal";
import {
  formatPrice,
  productCategories,
  storeProducts,
} from "@/data/storefront";

interface ShopPageProps {
  searchParams: Promise<{
    category?: string;
  }>;
}

export default async function ShopPage({ searchParams }: ShopPageProps) {
  const params = await searchParams;
  const selectedCategory = params.category ?? "All";

  const products =
    selectedCategory === "All"
      ? storeProducts
      : storeProducts.filter((product) => product.category === selectedCategory);

  return (
    <>
      <Navbar />
      <main className="flex-1 pb-20">
        <PageHero
          badge="Shop"
          title="Showcase all your products in one place."
          description="Use this page to display your full catalog so customers can discover products quickly."
        />

        <section className="max-w-[1200px] mx-auto px-6">
          <div className="grid grid-cols-1 lg:grid-cols-[220px_1fr] gap-8 lg:gap-12">
            <ScrollReveal className="lg:sticky lg:top-24 lg:h-fit">
              <div className="rounded-[1.5rem] bg-cream-dark/60 p-5">
                <h2 className="text-2xl font-extrabold tracking-tight text-black">Shop</h2>
                <p className="mt-2 text-sm text-gray-500 leading-relaxed">
                  Split products into categories so visitors can browse faster.
                </p>
                <ul className="mt-5 divide-y divide-cream">
                  {productCategories.map((category) => {
                    const isActive = category === selectedCategory;
                    const href =
                      category === "All"
                        ? "/shop"
                        : `/shop?category=${encodeURIComponent(category)}`;

                    return (
                      <li key={category}>
                        <Link
                          href={href}
                          className={`flex items-center gap-2 py-3 text-sm transition ${
                            isActive ? "text-black font-semibold" : "text-gray-500 hover:text-black"
                          }`}
                        >
                          <span
                            className={`w-2 h-2 rounded-full ${
                              isActive ? "bg-black" : "bg-transparent border border-gray-300"
                            }`}
                          />
                          {category}
                        </Link>
                      </li>
                    );
                  })}
                </ul>
              </div>
            </ScrollReveal>

            <ScrollReveal
              staggerChildren={0.08}
              className="grid grid-cols-1 sm:grid-cols-2 xl:grid-cols-3 gap-6"
            >
              {products.map((product) => (
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
          </div>
        </section>
      </main>
      <Footer />
    </>
  );
}

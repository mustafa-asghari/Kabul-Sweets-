import Link from "next/link";
import Footer from "@/components/Footer";
import Navbar from "@/components/Navbar";
import PageHero from "@/components/PageHero";
import ProductCard from "@/components/ProductCard";
import ScrollReveal from "@/components/ScrollReveal";
import {
  formatPrice,
} from "@/data/storefront";
import {
  fetchStoreProducts,
  getProductCategoriesFromProducts,
} from "@/lib/storefront-api";

interface ShopPageProps {
  searchParams: Promise<{
    category?: string;
    q?: string;
  }>;
}

export default async function ShopPage({ searchParams }: ShopPageProps) {
  const params = await searchParams;
  const allProducts = await fetchStoreProducts({ limit: 100 });
  const productCategories = getProductCategoriesFromProducts(allProducts);
  const selectedCategory = params.category ?? "All";
  const safeCategory = productCategories.includes(selectedCategory) ? selectedCategory : "All";
  const searchQuery = params.q?.trim() ?? "";
  const normalizedQuery = searchQuery.toLowerCase();

  const productsByCategory =
    safeCategory === "All"
      ? allProducts
      : allProducts.filter((product) => product.category === safeCategory);
  const products =
    normalizedQuery.length === 0
      ? productsByCategory
      : productsByCategory.filter((product) =>
          [product.title, product.category, product.shortDescription, product.description]
            .join(" ")
            .toLowerCase()
            .includes(normalizedQuery)
        );

  const clearSearchHref =
    safeCategory === "All"
      ? "/shop"
      : `/shop?category=${encodeURIComponent(safeCategory)}`;

  return (
    <>
      <Navbar />
      <main className="flex-1 pb-20">
        <PageHero
          badge="Shop"
          title="Shop Fresh Cakes, Sweets, Pastries, and Cookies."
          description="Browse our full menu and place your order for in-store pickup in Acacia Ridge."
        />

        <section className="max-w-[1200px] mx-auto px-6">
          <div className="grid grid-cols-1 lg:grid-cols-[220px_1fr] gap-8 lg:gap-12">
            <ScrollReveal className="lg:sticky lg:top-24 lg:h-fit">
              <div className="rounded-[1.5rem] bg-cream-dark/60 p-5">
                <h2 className="text-2xl font-extrabold tracking-tight text-black">Shop</h2>
                <p className="mt-2 text-sm text-gray-500 leading-relaxed">
                  Split products into categories so visitors can browse faster.
                </p>
                <form action="/shop" method="get" className="mt-5" id="catalog-search">
                  {safeCategory !== "All" ? (
                    <input type="hidden" name="category" value={safeCategory} />
                  ) : null}
                  <label htmlFor="product-search" className="sr-only">
                    Search products
                  </label>
                  <div className="flex items-center gap-2 rounded-xl border border-[#e8dcc9] bg-white px-3 py-2">
                    <span className="material-symbols-outlined text-[18px] text-gray-400">
                      search
                    </span>
                    <input
                      id="product-search"
                      type="text"
                      name="q"
                      defaultValue={searchQuery}
                      placeholder="Search products"
                      className="w-full bg-transparent text-sm text-black placeholder:text-gray-400 focus:outline-none"
                    />
                  </div>
                </form>
                {searchQuery ? (
                  <div className="mt-3 flex items-center justify-between">
                    <p className="text-xs text-gray-500">
                      Showing results for <span className="font-semibold text-black">{searchQuery}</span>
                    </p>
                    <Link href={clearSearchHref} className="text-xs font-semibold text-black hover:text-accent transition">
                      Clear
                    </Link>
                  </div>
                ) : null}
                <ul className="mt-5 divide-y divide-cream">
                  {productCategories.map((category) => {
                    const isActive = category === safeCategory;
                    const hrefParams = new URLSearchParams();
                    if (category !== "All") {
                      hrefParams.set("category", category);
                    }
                    if (searchQuery) {
                      hrefParams.set("q", searchQuery);
                    }
                    const href = hrefParams.toString() ? `/shop?${hrefParams.toString()}` : "/shop";

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
              {products.length > 0 ? (
                products.map((product) => (
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
                <article className="sm:col-span-2 xl:col-span-3 rounded-[1.5rem] bg-cream-dark/60 p-8">
                  <h2 className="text-2xl font-extrabold tracking-tight text-black">No products found</h2>
                  <p className="mt-2 text-sm text-gray-600">
                    Try a different keyword or clear the search to see all products.
                  </p>
                </article>
              )}
            </ScrollReveal>
          </div>
        </section>
      </main>
      <Footer />
    </>
  );
}

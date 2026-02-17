import Footer from "@/components/Footer";
import Navbar from "@/components/Navbar";
import PageHero from "@/components/PageHero";
import CollectionCard from "@/components/CollectionCard";
import ActionBanner from "@/components/ActionBanner";
import ScrollReveal from "@/components/ScrollReveal";
import { fetchStoreProducts, getCollectionsFromProducts } from "@/lib/storefront-api";

export const dynamic = "force-dynamic";

export default async function CollectionsPage() {
  const products = await fetchStoreProducts({ limit: 120 });
  const collections = getCollectionsFromProducts(products);

  return (
    <>
      <Navbar />
      <main className="flex-1 pb-20">
        <PageHero
          badge="Collections"
          title="Explore Our Product Collections."
          description="Browse curated categories to quickly find the sweets, pastries, and cookies you need."
        />

        <section className="max-w-[1200px] mx-auto px-6">
          <ScrollReveal
            staggerChildren={0.1}
            className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-6"
          >
            {collections.length > 0 ? (
              collections.map((collection) => (
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
                <h2 className="text-2xl font-extrabold tracking-tight text-black">No collections available</h2>
                <p className="mt-2 text-sm text-gray-600">
                  Add products in backend categories to populate this page.
                </p>
              </article>
            )}
          </ScrollReveal>
        </section>

        <ActionBanner zoomOut />
      </main>
      <Footer />
    </>
  );
}

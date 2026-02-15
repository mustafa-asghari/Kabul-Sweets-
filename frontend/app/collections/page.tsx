import Footer from "@/components/Footer";
import Navbar from "@/components/Navbar";
import PageHero from "@/components/PageHero";
import CollectionCard from "@/components/CollectionCard";
import ScrollReveal from "@/components/ScrollReveal";
import { collections } from "@/data/storefront";

export default function CollectionsPage() {
  return (
    <>
      <Navbar />
      <main className="flex-1 pb-20">
        <PageHero
          badge="Collections"
          title="Curate your products into simple collections."
          description="Use collections to group products clearly so customers can explore and order faster."
        />

        <section className="max-w-[1200px] mx-auto px-6">
          <ScrollReveal
            staggerChildren={0.1}
            className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-4 gap-6"
          >
            {collections.map((collection) => (
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
      </main>
      <Footer />
    </>
  );
}

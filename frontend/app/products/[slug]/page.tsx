import type { Metadata } from "next";
import { notFound } from "next/navigation";
import Footer from "@/components/Footer";
import Navbar from "@/components/Navbar";
import ProductDetailView from "@/components/ProductDetailView";
import {
  fetchRelatedStoreProducts,
  fetchStoreProductBySlug,
} from "@/lib/storefront-api";

interface ProductPageProps {
  params: Promise<{
    slug: string;
  }>;
}

export async function generateMetadata({ params }: ProductPageProps): Promise<Metadata> {
  const { slug } = await params;
  const product = await fetchStoreProductBySlug(slug);

  if (!product) {
    return {
      title: "Product Not Found | Kabul Sweets",
    };
  }

  return {
    title: `${product.title} | Kabul Sweets`,
    description: product.shortDescription,
  };
}

export default async function ProductPage({ params }: ProductPageProps) {
  const { slug } = await params;
  const product = await fetchStoreProductBySlug(slug);

  if (!product) {
    notFound();
  }

  const relatedProducts = await fetchRelatedStoreProducts(product, 3);

  return (
    <>
      <Navbar />
      <main className="flex-1">
        <ProductDetailView product={product} relatedProducts={relatedProducts} />
      </main>
      <Footer />
    </>
  );
}

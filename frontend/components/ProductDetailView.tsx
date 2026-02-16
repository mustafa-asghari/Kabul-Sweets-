"use client";

import Image from "next/image";
import Link from "next/link";
import { useState } from "react";
import ProductCard from "@/components/ProductCard";
import ScrollReveal from "@/components/ScrollReveal";
import { ApiError } from "@/lib/api-client";
import {
  formatPrice,
  supportBenefits,
} from "@/data/storefront";
import { useAuth } from "@/context/AuthContext";
import { useCart } from "@/context/CartContext";
import type { StorefrontProduct } from "@/lib/storefront-types";

interface ProductDetailViewProps {
  product: StorefrontProduct;
  relatedProducts: StorefrontProduct[];
}

const accordionItems = [
  {
    title: "Warranty",
    body: "Every order is backed by our freshness promise. If your product arrives with any issue, our team will arrange a quick replacement.",
  },
  {
    title: "Pickup Information",
    body: "Orders are prepared for in-store pickup and takeaway only. You can choose a pickup time at checkout.",
  },
  {
    title: "Support",
    body: "Need help with custom notes, event timing, or allergen details? Our support team is available seven days a week.",
  },
];

export default function ProductDetailView({
  product,
  relatedProducts,
}: ProductDetailViewProps) {
  const [activeImage, setActiveImage] = useState(0);
  const [activeVariantId, setActiveVariantId] = useState(
    product.variants[0]?.id ?? null
  );
  const [activeAccordion, setActiveAccordion] = useState(0);
  const [cartMessage, setCartMessage] = useState<string | null>(null);
  const activeVariant =
    (activeVariantId && product.variants.find((variant) => variant.id === activeVariantId)) ||
    product.variants[0];
  const displayPrice = activeVariant?.price ?? product.price;
  const { isAuthenticated } = useAuth();
  const { addItem } = useCart();

  const handleAddToCart = async () => {
    setCartMessage(null);
    if (!isAuthenticated) {
      window.dispatchEvent(new Event("open-auth-modal"));
      setCartMessage("Please login first to add items.");
      return;
    }

    try {
      await addItem({
        productId: product.id,
        variantId: activeVariant?.id || null,
        quantity: 1,
      });
      setCartMessage("Added to cart");
      window.setTimeout(() => setCartMessage(null), 1400);
    } catch (error) {
      if (error instanceof ApiError) {
        setCartMessage(error.detail);
      } else {
        setCartMessage("Unable to add item to cart.");
      }
    }
  };

  return (
    <>
      <section className="max-w-[1200px] mx-auto px-6 pt-8 pb-14">
        <div className="grid grid-cols-1 lg:grid-cols-[1.3fr_1fr] gap-10 lg:gap-12">
          <ScrollReveal className="grid grid-cols-[68px_1fr] gap-4 md:gap-6 items-start">
            <div className="space-y-3">
              {product.thumbnails.map((thumbnail, index) => {
                const isActive = index === activeImage;

                return (
                  <button
                    key={`${thumbnail}-${index}`}
                    type="button"
                    aria-label={`Thumbnail ${index + 1}`}
                    onClick={() => setActiveImage(index)}
                    className={`relative h-[68px] w-[68px] rounded-xl overflow-hidden border-2 transition ${
                      isActive ? "border-accent" : "border-transparent"
                    }`}
                  >
                    <Image
                      src={thumbnail}
                      alt={product.title}
                      fill
                      sizes="68px"
                      className="object-cover"
                    />
                  </button>
                );
              })}
            </div>

            <div className="relative rounded-[2rem] bg-cream-dark p-8 min-h-[560px] flex items-center justify-center overflow-hidden">
              <div className="absolute top-4 right-4 rounded-2xl bg-white px-3 py-2 text-xs font-semibold text-gray-600 shadow-sm">
                Hover to zoom
              </div>
              <Image
                src={product.thumbnails[activeImage] ?? product.imageSrc}
                alt={product.title}
                width={600}
                height={600}
                sizes="(max-width: 1024px) 86vw, 700px"
                className="w-[80%] h-auto object-contain"
                priority
              />
            </div>
          </ScrollReveal>

          <ScrollReveal className="lg:sticky lg:top-24 lg:h-fit">
            <p className="text-sm text-gray-400">
              <Link href="/shop" className="hover:text-black transition">
                Shop
              </Link>
              <span className="mx-1">•</span>
              {product.category}
            </p>

            <h1 className="mt-2 text-5xl font-extrabold tracking-tight text-black leading-[1.04]">
              {product.title}
            </h1>

            <p className="mt-4 text-4xl font-extrabold tracking-tight text-black">
              {formatPrice(displayPrice)}
            </p>

            <p className="mt-7 text-xl text-gray-600 leading-relaxed">{product.description}</p>

            {product.variants.length > 0 ? (
              <div className="mt-8">
                <h2 className="text-2xl font-bold tracking-tight text-black">Options</h2>
                <div className="mt-4 flex flex-wrap gap-3">
                  {product.variants.map((variant) => {
                    const isActive = variant.id === activeVariant?.id;

                    return (
                      <button
                        key={variant.id}
                        type="button"
                        onClick={() => setActiveVariantId(variant.id)}
                        className={`px-5 py-2.5 rounded-xl text-sm font-semibold transition ${
                          isActive
                            ? "bg-black text-white"
                            : "bg-cream-dark text-black hover:bg-[#eadbc4]"
                        }`}
                      >
                        {variant.name}
                      </button>
                    );
                  })}
                </div>
              </div>
            ) : null}

            <div className="mt-8 space-y-3">
              <button
                type="button"
                onClick={handleAddToCart}
                className="w-full rounded-full bg-black py-4 text-base font-semibold text-white hover:bg-[#222] transition"
              >
                Add to Cart
              </button>
              <button
                type="button"
                onClick={handleAddToCart}
                className="w-full rounded-full bg-cream-dark py-4 text-base font-semibold text-black hover:bg-[#eadbc4] transition"
              >
                Add & Checkout
              </button>
              {cartMessage ? <p className="text-sm text-gray-600">{cartMessage}</p> : null}
            </div>

            <div className="mt-8 divide-y divide-gray-200 border-y border-gray-200">
              {accordionItems.map((item, index) => {
                const isOpen = index === activeAccordion;

                return (
                  <div key={item.title}>
                    <button
                      type="button"
                      onClick={() => setActiveAccordion(isOpen ? -1 : index)}
                      className="w-full flex items-center justify-between gap-4 py-5 text-left"
                    >
                      <span className="text-3xl font-bold tracking-tight text-black">
                        {item.title}
                      </span>
                      <span className="material-symbols-outlined text-2xl text-gray-500">
                        {isOpen ? "expand_less" : "expand_more"}
                      </span>
                    </button>
                    {isOpen ? (
                      <p className="pb-5 text-lg text-gray-500 leading-relaxed">{item.body}</p>
                    ) : null}
                  </div>
                );
              })}
            </div>
          </ScrollReveal>
        </div>
      </section>

      <section className="max-w-[1200px] mx-auto px-6 pb-16">
        <ScrollReveal
          staggerChildren={0.08}
          className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-4 gap-6"
        >
          {supportBenefits.map((benefit) => (
            <article key={benefit.title} className="bg-cream-dark rounded-[1.5rem] p-6">
              <div className="w-11 h-11 rounded-full bg-white flex items-center justify-center mb-5">
                <span className="material-symbols-outlined text-accent text-[21px]">
                  {benefit.icon}
                </span>
              </div>
              <h2 className="text-3xl font-extrabold tracking-tight text-black">{benefit.title}</h2>
              <p className="mt-2 text-base text-gray-500 leading-relaxed">{benefit.description}</p>
            </article>
          ))}
        </ScrollReveal>
      </section>

      <section className="max-w-[1200px] mx-auto px-6 pb-20">
        <ScrollReveal>
          <div className="flex flex-col md:flex-row justify-between items-start md:items-end mb-2 gap-2">
            <div>
              <h2 className="text-4xl font-extrabold tracking-tight text-black">You may also like</h2>
              <p className="text-base text-gray-500 mt-1">Suggested picks from the same collection.</p>
            </div>
            <Link
              href="/shop"
              className="text-base font-semibold text-black hover:text-accent transition flex items-center gap-1"
            >
              View all
              <span className="material-symbols-outlined text-[18px]">arrow_forward</span>
            </Link>
          </div>
        </ScrollReveal>
        <hr className="border-gray-200 mb-10" />
        <ScrollReveal
          staggerChildren={0.08}
          className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-6"
        >
          {relatedProducts.map((related) => (
            <ProductCard
              key={related.slug}
              slug={related.slug}
              title={related.title}
              category={related.category}
              price={formatPrice(related.price)}
              imageSrc={related.imageSrc}
              imageAlt={related.title}
            />
          ))}
        </ScrollReveal>
      </section>
    </>
  );
}

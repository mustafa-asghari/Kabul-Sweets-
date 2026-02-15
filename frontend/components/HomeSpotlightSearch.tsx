"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useMemo, useState } from "react";

interface SpotlightProduct {
  slug: string;
  title: string;
}

interface HomeSpotlightSearchProps {
  categories: string[];
  collections: string[];
  products: SpotlightProduct[];
}

function uniqueTerms(terms: string[]) {
  const seen = new Set<string>();
  return terms.filter((term) => {
    const key = term.toLowerCase();
    if (seen.has(key)) {
      return false;
    }
    seen.add(key);
    return true;
  });
}

export default function HomeSpotlightSearch({
  categories,
  collections,
  products,
}: HomeSpotlightSearchProps) {
  const router = useRouter();
  const [query, setQuery] = useState("");

  const trimmedQuery = query.trim();
  const searchableTerms = useMemo(
    () =>
      uniqueTerms([
        ...categories,
        ...collections,
        "Collections",
        "Cake",
        "Sweets",
        "Cookies",
        "Pastries",
      ]),
    [categories, collections]
  );

  const matchingTerms = useMemo(() => {
    if (!trimmedQuery) {
      return searchableTerms.slice(0, 8);
    }

    const lowerQuery = trimmedQuery.toLowerCase();
    return searchableTerms
      .filter((term) => term.toLowerCase().includes(lowerQuery))
      .slice(0, 8);
  }, [searchableTerms, trimmedQuery]);

  const matchingProducts = useMemo(() => {
    if (!trimmedQuery) {
      return products.slice(0, 4);
    }

    const lowerQuery = trimmedQuery.toLowerCase();
    return products
      .filter((product) => product.title.toLowerCase().includes(lowerQuery))
      .slice(0, 4);
  }, [products, trimmedQuery]);

  const runSearch = (value: string) => {
    const nextQuery = value.trim();
    if (!nextQuery) {
      router.push("/shop");
      return;
    }

    const lowerQuery = nextQuery.toLowerCase();

    if (lowerQuery.includes("collection")) {
      router.push("/collections");
      return;
    }

    const matchedCategory = categories.find(
      (category) => category.toLowerCase() === lowerQuery
    );

    if (matchedCategory) {
      router.push(`/shop?category=${encodeURIComponent(matchedCategory)}`);
      return;
    }

    router.push(`/shop?q=${encodeURIComponent(nextQuery)}`);
  };

  return (
    <section id="spotlight-search" className="max-w-[1200px] mx-auto px-6 pb-20">
      <div className="relative overflow-hidden rounded-[2rem] border border-[#eadbc4] bg-cream-dark/75 p-6 md:p-8">
        <div className="pointer-events-none absolute inset-0 bg-[radial-gradient(circle_at_16%_20%,rgba(255,242,200,0.85)_0%,rgba(240,216,162,0.46)_32%,rgba(245,235,218,0)_68%)]" />
        <div className="relative">
          <p className="text-xs font-semibold uppercase tracking-[0.18em] text-gray-500">
            Spotlight Search
          </p>
          <h2 className="mt-3 text-2xl md:text-3xl font-extrabold tracking-tight text-black">
            Search cakes, sweets, cookies, pastries, and collections.
          </h2>

          <form
            className="mt-5"
            onSubmit={(event) => {
              event.preventDefault();
              runSearch(query);
            }}
          >
            <label htmlFor="home-spotlight-search" className="sr-only">
              Search products and collections
            </label>
            <div className="flex flex-col sm:flex-row gap-3">
              <input
                id="home-spotlight-search"
                type="text"
                value={query}
                onChange={(event) => setQuery(event.target.value)}
                placeholder="Try: cake, sweets, pastries, cookies, collections"
                className="h-12 w-full rounded-xl border border-[#e8dcc9] bg-white px-4 text-sm text-black placeholder:text-gray-400 focus:outline-none focus:ring-2 focus:ring-[#d7bc8a]"
              />
              <button
                type="submit"
                className="h-12 px-6 rounded-xl bg-black text-sm font-semibold text-white hover:bg-[#222] transition"
              >
                Search
              </button>
            </div>
          </form>

          <div className="mt-4 flex flex-wrap gap-2">
            {matchingTerms.map((term) => (
              <button
                key={term}
                type="button"
                onClick={() => runSearch(term)}
                className="px-3 py-1.5 rounded-full bg-white/80 text-xs font-semibold text-gray-700 hover:text-black hover:bg-white transition"
              >
                {term}
              </button>
            ))}
          </div>

          <div className="mt-5 grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-2">
            {matchingProducts.map((product) => (
              <Link
                key={product.slug}
                href={`/products/${product.slug}`}
                className="rounded-xl bg-white/80 px-3 py-2 text-sm font-medium text-gray-700 hover:text-black hover:bg-white transition truncate"
                title={product.title}
              >
                {product.title}
              </Link>
            ))}
          </div>
        </div>
      </div>
    </section>
  );
}

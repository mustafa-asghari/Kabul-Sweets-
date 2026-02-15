"use client";

import { AnimatePresence, motion, useScroll, useMotionValueEvent } from "framer-motion";
import { useEffect, useMemo, useRef, useState } from "react";
import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { collections, productCategories, storeProducts } from "@/data/storefront";
import { getCartCount, readCart } from "@/lib/cart";

const navLinks = [
  { href: "/shop", label: "Shop" },
  { href: "/collections", label: "Collections" },
  { href: "/support", label: "Support" },
];

interface SpotlightItem {
  id: string;
  title: string;
  subtitle: string;
  href: string;
  icon: string;
  keywords: string;
}

const spotlightCatalog: SpotlightItem[] = [
  {
    id: "all-products",
    title: "All Products",
    subtitle: "Browse the full product catalog",
    href: "/shop",
    icon: "storefront",
    keywords: "all products catalog shop",
  },
  ...productCategories
    .filter((category) => category !== "All")
    .map((category) => ({
      id: `category-${category.toLowerCase()}`,
      title: category,
      subtitle: "Category",
      href: `/shop?category=${encodeURIComponent(category)}`,
      icon: "category",
      keywords: `${category} category`,
    })),
  ...collections.map((collection) => ({
    id: `collection-${collection.title.toLowerCase()}`,
    title: collection.title,
    subtitle: "Collection",
    href: `/shop?category=${encodeURIComponent(collection.title)}`,
    icon: "layers",
    keywords: `${collection.title} collection`,
  })),
  ...storeProducts.map((product) => ({
    id: `product-${product.slug}`,
    title: product.title,
    subtitle: product.category,
    href: `/products/${product.slug}`,
    icon: "bakery_dining",
    keywords: `${product.title} ${product.category} ${product.shortDescription}`,
  })),
];

export default function Navbar() {
  const [shrink, setShrink] = useState(false);
  const [cartCount, setCartCount] = useState(0);
  const [searchOpen, setSearchOpen] = useState(false);
  const [searchQuery, setSearchQuery] = useState("");
  const searchInputRef = useRef<HTMLInputElement>(null);
  const { scrollY } = useScroll();
  const pathname = usePathname();
  const router = useRouter();

  useMotionValueEvent(scrollY, "change", (latest) => {
    setShrink(latest > 50);
  });

  useEffect(() => {
    const syncCartCount = () => {
      setCartCount(getCartCount(readCart()));
    };

    syncCartCount();
    window.addEventListener("cart-updated", syncCartCount);
    window.addEventListener("storage", syncCartCount);

    return () => {
      window.removeEventListener("cart-updated", syncCartCount);
      window.removeEventListener("storage", syncCartCount);
    };
  }, []);

  useEffect(() => {
    const onKeyDown = (event: KeyboardEvent) => {
      if ((event.metaKey || event.ctrlKey) && event.key.toLowerCase() === "k") {
        event.preventDefault();
        setSearchOpen((current) => !current);
      }

      if (event.key === "Escape") {
        setSearchOpen(false);
      }
    };

    window.addEventListener("keydown", onKeyDown);
    return () => {
      window.removeEventListener("keydown", onKeyDown);
    };
  }, []);

  useEffect(() => {
    if (!searchOpen) {
      return;
    }

    const previousOverflow = document.body.style.overflow;
    document.body.style.overflow = "hidden";
    const timeoutId = window.setTimeout(() => {
      searchInputRef.current?.focus();
    }, 20);

    return () => {
      document.body.style.overflow = previousOverflow;
      window.clearTimeout(timeoutId);
    };
  }, [searchOpen]);

  const spotlightItems = useMemo(() => {
    const query = searchQuery.trim().toLowerCase();

    if (!query) {
      return spotlightCatalog
        .filter((item) => !item.id.startsWith("product-"))
        .slice(0, 8);
    }

    const combined = [
      {
        id: `query-${query}`,
        title: `Search “${searchQuery.trim()}”`,
        subtitle: "Find matching products and descriptions",
        href: `/shop?q=${encodeURIComponent(searchQuery.trim())}`,
        icon: "search",
        keywords: query,
      },
      ...spotlightCatalog.filter((item) => item.keywords.toLowerCase().includes(query)),
    ];

    const seen = new Set<string>();
    return combined
      .filter((item) => {
        if (seen.has(item.id)) {
          return false;
        }
        seen.add(item.id);
        return true;
      })
      .slice(0, 10);
  }, [searchQuery]);

  const closeSearch = () => {
    setSearchOpen(false);
    setSearchQuery("");
  };

  const openSearch = () => {
    setSearchOpen(true);
  };

  const navigateFromSearch = (href: string) => {
    closeSearch();
    router.push(href);
  };

  return (
    <>
      <motion.nav
        initial={{ opacity: 0, y: -20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.5, ease: "easeOut" }}
        className="sticky top-0 z-50 bg-cream/80 backdrop-blur-lg"
      >
        <div
          className={`max-w-[1200px] mx-auto px-6 flex items-center justify-between transition-all duration-300 ${
            shrink ? "py-2.5" : "py-4"
          }`}
        >
          <Link href="/" className="text-lg font-extrabold tracking-tight text-black">
            Kabul <span className="text-accent">Sweets</span>_
          </Link>
          <div className="hidden md:flex items-center gap-8 text-sm font-medium text-gray-600">
            {navLinks.map((link) => {
              const isActive = pathname === link.href;

              return (
                <Link
                  key={link.href}
                  href={link.href}
                  className={`text-sm transition ${
                    isActive ? "text-black font-semibold" : "text-gray-600 hover:text-black"
                  }`}
                >
                  {link.label}
                </Link>
              );
            })}
          </div>
          <div className="flex items-center gap-4">
            <button
              type="button"
              onClick={openSearch}
              className="text-gray-500 hover:text-black transition"
              aria-label="Open search"
            >
              <span className="material-symbols-outlined text-[22px]">search</span>
            </button>
            <Link
              href="/cart"
              className="relative text-gray-500 hover:text-black transition"
              aria-label="Open cart"
            >
              <span className="material-symbols-outlined text-[22px]">
                shopping_bag
              </span>
              <span className="absolute -top-1.5 -right-2 inline-flex h-[18px] min-w-[18px] items-center justify-center rounded-full bg-black px-1 text-[10px] font-bold text-white">
                {cartCount}
              </span>
            </Link>
          </div>
        </div>
      </motion.nav>

      <AnimatePresence>
        {searchOpen ? (
          <motion.div
            className="fixed inset-0 z-[90] bg-black/40 backdrop-blur-sm px-4 py-20"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            onClick={closeSearch}
          >
            <motion.div
              initial={{ opacity: 0, y: -20, scale: 0.98 }}
              animate={{ opacity: 1, y: 0, scale: 1 }}
              exit={{ opacity: 0, y: -20, scale: 0.98 }}
              transition={{ duration: 0.18, ease: "easeOut" }}
              onClick={(event) => event.stopPropagation()}
              className="mx-auto w-full max-w-[720px] rounded-[1.5rem] border border-white/60 bg-[#f5f2eb]/95 shadow-[0_28px_90px_rgba(0,0,0,0.28)] overflow-hidden"
            >
              <div className="flex items-center gap-3 border-b border-[#e7dcc7] px-4 py-3.5">
                <span className="material-symbols-outlined text-[20px] text-gray-400">
                  search
                </span>
                <input
                  ref={searchInputRef}
                  type="text"
                  value={searchQuery}
                  onChange={(event) => setSearchQuery(event.target.value)}
                  onKeyDown={(event) => {
                    if (event.key === "Enter" && spotlightItems.length > 0) {
                      event.preventDefault();
                      navigateFromSearch(spotlightItems[0].href);
                    }
                  }}
                  placeholder="Search cakes, sweets, cookies, pastries, collections..."
                  className="w-full bg-transparent text-[15px] text-black placeholder:text-gray-400 focus:outline-none"
                />
                <kbd className="hidden sm:inline-flex h-7 items-center rounded-md border border-[#ddd0bb] px-2 text-[11px] font-medium text-gray-500">
                  Cmd/Ctrl+K
                </kbd>
              </div>

              <div className="max-h-[430px] overflow-y-auto p-2">
                {spotlightItems.length > 0 ? (
                  spotlightItems.map((item) => (
                    <button
                      key={item.id}
                      type="button"
                      onClick={() => navigateFromSearch(item.href)}
                      className="w-full rounded-xl px-3 py-3 text-left hover:bg-white/80 transition flex items-start gap-3"
                    >
                      <span className="mt-0.5 inline-flex h-8 w-8 shrink-0 items-center justify-center rounded-lg bg-white text-gray-600">
                        <span className="material-symbols-outlined text-[18px]">
                          {item.icon}
                        </span>
                      </span>
                      <span className="min-w-0 flex-1">
                        <span className="block text-sm font-semibold text-black truncate">
                          {item.title}
                        </span>
                        <span className="block text-xs text-gray-500 truncate">
                          {item.subtitle}
                        </span>
                      </span>
                      <span className="material-symbols-outlined text-[16px] text-gray-400">
                        arrow_outward
                      </span>
                    </button>
                  ))
                ) : (
                  <div className="rounded-xl px-4 py-8 text-center">
                    <p className="text-sm font-semibold text-black">No matches found</p>
                    <p className="mt-1 text-xs text-gray-500">
                      Try searching for cakes, sweets, pastries, cookies, or a product name.
                    </p>
                  </div>
                )}
              </div>
            </motion.div>
          </motion.div>
        ) : null}
      </AnimatePresence>
    </>
  );
}

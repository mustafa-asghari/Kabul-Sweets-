"use client";

import { AnimatePresence, motion, useScroll, useMotionValueEvent } from "framer-motion";
import { useEffect, useRef, useState } from "react";
import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { collections, productCategories } from "@/data/storefront";
import { getCartCount, readCart } from "@/lib/cart";

const navLinks = [
  { href: "/shop", label: "Shop" },
  { href: "/collections", label: "Collections" },
  { href: "/support", label: "Support" },
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

  const runSpotlightSearch = () => {
    const query = searchQuery.trim();
    if (!query) {
      navigateFromSearch("/shop");
      return;
    }

    const normalizedQuery = query.toLowerCase();
    if (normalizedQuery.includes("collection")) {
      navigateFromSearch("/collections");
      return;
    }

    const matchedCategory = productCategories
      .filter((category) => category !== "All")
      .find((category) => category.toLowerCase() === normalizedQuery);

    if (matchedCategory) {
      navigateFromSearch(`/shop?category=${encodeURIComponent(matchedCategory)}`);
      return;
    }

    const matchedCollection = collections.find(
      (collection) => collection.title.toLowerCase() === normalizedQuery
    );

    if (matchedCollection) {
      navigateFromSearch(`/shop?category=${encodeURIComponent(matchedCollection.title)}`);
      return;
    }

    navigateFromSearch(`/shop?q=${encodeURIComponent(query)}`);
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
              className="mx-auto w-full max-w-[720px] rounded-[1.5rem] border border-white/60 bg-[#f5f2eb]/95 shadow-[0_28px_90px_rgba(0,0,0,0.28)]"
            >
              <div className="px-4 py-3.5">
                <input
                  ref={searchInputRef}
                  type="text"
                  value={searchQuery}
                  onChange={(event) => setSearchQuery(event.target.value)}
                  onKeyDown={(event) => {
                    if (event.key === "Enter") {
                      event.preventDefault();
                      runSpotlightSearch();
                    }
                  }}
                  placeholder="Search cakes, sweets, cookies, pastries, collections..."
                  className="w-full bg-transparent text-[15px] text-black placeholder:text-gray-400 focus:outline-none"
                />
              </div>
            </motion.div>
          </motion.div>
        ) : null}
      </AnimatePresence>
    </>
  );
}

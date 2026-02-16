"use client";

import { useEffect, useRef, useState } from "react";
import Link from "next/link";
import dynamic from "next/dynamic";
import { usePathname, useRouter } from "next/navigation";
import { useAuth } from "@/context/AuthContext";
import { useCart } from "@/context/CartContext";
import AuthModal from "@/components/AuthModal";

const CartDrawer = dynamic(() => import("@/components/CartDrawer"), {
  ssr: false,
});

const navLinks = [
  { href: "/shop", label: "Shop" },
  { href: "/collections", label: "Collections" },
  { href: "/custom-cakes", label: "Custom Cakes" },
  { href: "/support", label: "Support" },
];

export default function Navbar() {
  const [shrink, setShrink] = useState(false);
  const [cartOpen, setCartOpen] = useState(false);
  const [searchOpen, setSearchOpen] = useState(false);
  const [searchQuery, setSearchQuery] = useState("");
  const [authOpen, setAuthOpen] = useState(false);
  const [profileOpen, setProfileOpen] = useState(false);
  const searchInputRef = useRef<HTMLInputElement>(null);
  const pathname = usePathname();
  const router = useRouter();

  const { user, isAuthenticated, logout, loading } = useAuth();
  const { cartCount } = useCart();

  useEffect(() => {
    const onScroll = () => {
      setShrink(window.scrollY > 50);
    };

    onScroll();
    window.addEventListener("scroll", onScroll, { passive: true });
    return () => {
      window.removeEventListener("scroll", onScroll);
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
        setCartOpen(false);
        setAuthOpen(false);
        setProfileOpen(false);
      }
    };

    window.addEventListener("keydown", onKeyDown);
    return () => {
      window.removeEventListener("keydown", onKeyDown);
    };
  }, []);

  useEffect(() => {
    const openAuth = () => setAuthOpen(true);
    window.addEventListener("open-auth-modal", openAuth);
    return () => {
      window.removeEventListener("open-auth-modal", openAuth);
    };
  }, []);

  useEffect(() => {
    if (!searchOpen && !cartOpen && !authOpen) {
      return;
    }
    const previousOverflow = document.body.style.overflow;
    document.body.style.overflow = "hidden";
    const timeoutId = searchOpen
      ? window.setTimeout(() => {
          searchInputRef.current?.focus();
        }, 20)
      : null;

    return () => {
      document.body.style.overflow = previousOverflow;
      if (timeoutId) {
        window.clearTimeout(timeoutId);
      }
    };
  }, [searchOpen, cartOpen, authOpen]);

  const closeSearch = () => {
    setSearchOpen(false);
    setSearchQuery("");
  };

  const openSearch = () => {
    setCartOpen(false);
    setSearchOpen(true);
  };

  const openCart = () => {
    closeSearch();
    setCartOpen(true);
  };

  const closeCart = () => {
    setCartOpen(false);
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

    navigateFromSearch(`/shop?q=${encodeURIComponent(query)}`);
  };

  const handleAuthClick = () => {
    if (!isAuthenticated) {
      setAuthOpen(true);
      return;
    }
    setProfileOpen((current) => !current);
  };

  return (
    <>
      <nav className="sticky top-0 z-50 bg-cream/80 backdrop-blur-lg">
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
            {isAuthenticated ? (
              <Link
                href="/orders"
                className={`text-sm transition ${
                  pathname === "/orders" ? "text-black font-semibold" : "text-gray-600 hover:text-black"
                }`}
              >
                Orders
              </Link>
            ) : null}
          </div>
          <div className="flex items-center gap-4 relative">
            <button
              type="button"
              onClick={openSearch}
              className="text-gray-500 hover:text-black transition"
              aria-label="Open search"
            >
              <span className="material-symbols-outlined text-[22px]">search</span>
            </button>

            <button
              type="button"
              onClick={handleAuthClick}
              className="text-gray-500 hover:text-black transition"
              aria-label={isAuthenticated ? "Account menu" : "Login"}
            >
              <span className="material-symbols-outlined text-[22px]">account_circle</span>
            </button>

            <button
              type="button"
              onClick={openCart}
              className="relative text-gray-500 hover:text-black transition"
              aria-label="Open cart"
            >
              <span className="material-symbols-outlined text-[22px]">shopping_bag</span>
              <span className="absolute -top-1.5 -right-2 inline-flex h-[18px] min-w-[18px] items-center justify-center rounded-full bg-black px-1 text-[10px] font-bold text-white">
                {cartCount}
              </span>
            </button>

            {profileOpen && isAuthenticated && user ? (
              <div className="absolute top-11 right-0 z-[80] w-[220px] rounded-2xl border border-[#e6d9c5] bg-white p-3 shadow-lg">
                <p className="text-sm font-semibold text-black truncate">{user.full_name}</p>
                <p className="mt-0.5 text-xs text-gray-500 truncate">{user.email}</p>
                <div className="mt-3 space-y-1">
                  <Link
                    href="/account"
                    onClick={() => setProfileOpen(false)}
                    className="block rounded-lg px-2.5 py-2 text-sm text-gray-700 hover:bg-[#f5f2eb]"
                  >
                    Account
                  </Link>
                  <Link
                    href="/orders"
                    onClick={() => setProfileOpen(false)}
                    className="block rounded-lg px-2.5 py-2 text-sm text-gray-700 hover:bg-[#f5f2eb]"
                  >
                    My Orders
                  </Link>
                  <button
                    type="button"
                    onClick={async () => {
                      setProfileOpen(false);
                      await logout();
                    }}
                    className="w-full text-left rounded-lg px-2.5 py-2 text-sm text-red-600 hover:bg-red-50"
                  >
                    Logout
                  </button>
                </div>
              </div>
            ) : null}

            {!loading && !isAuthenticated ? (
              <button
                type="button"
                onClick={() => setAuthOpen(true)}
                className="hidden md:inline-flex rounded-full bg-black px-3.5 py-1.5 text-xs font-semibold text-white hover:bg-[#222] transition"
              >
                Login
              </button>
            ) : null}
          </div>
        </div>
      </nav>

      {searchOpen ? (
        <div
          className="fixed inset-0 z-[90] bg-black/40 backdrop-blur-sm px-4 py-20"
          onClick={closeSearch}
        >
          <div
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
          </div>
        </div>
      ) : null}

      <AuthModal open={authOpen} onClose={() => setAuthOpen(false)} />
      <CartDrawer open={cartOpen} onClose={closeCart} />
    </>
  );
}

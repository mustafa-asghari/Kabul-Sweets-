"use client";

import { motion, useScroll, useMotionValueEvent } from "framer-motion";
import { useState } from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";

const navLinks = [
  { href: "/shop", label: "Shop" },
  { href: "/collections", label: "Collections" },
  { href: "/blog", label: "Blog" },
  { href: "/support", label: "Support" },
];

export default function Navbar() {
  const [shrink, setShrink] = useState(false);
  const { scrollY } = useScroll();
  const pathname = usePathname();

  useMotionValueEvent(scrollY, "change", (latest) => {
    setShrink(latest > 50);
  });

  return (
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
          Kabul Sweets_
        </Link>
        <div className="hidden md:flex items-center gap-8 text-sm font-medium text-gray-600">
          {navLinks.map((link) => {
            const isActive = pathname === link.href;

            return (
              <Link
                key={link.href}
                href={link.href}
                className={`inline-flex items-center rounded-full border px-3.5 py-1.5 text-sm transition-all ${
                  isActive
                    ? "border-black bg-black text-white shadow-sm"
                    : "border-black/10 bg-white/85 text-gray-700 shadow-sm hover:-translate-y-0.5 hover:border-black/30 hover:text-black"
                }`}
              >
                {link.label}
              </Link>
            );
          })}
        </div>
        <div className="flex items-center gap-4">
          <Link
            href="/shop"
            className="inline-flex h-10 w-10 items-center justify-center rounded-full border border-black/10 bg-white text-gray-600 shadow-sm transition-all hover:-translate-y-0.5 hover:border-black/30 hover:text-black"
          >
            <span className="material-symbols-outlined text-[22px]">
              search
            </span>
          </Link>
          <Link
            href="/shop"
            className="relative inline-flex h-10 w-10 items-center justify-center rounded-full border border-black/10 bg-white text-gray-600 shadow-sm transition-all hover:-translate-y-0.5 hover:border-black/30 hover:text-black"
          >
            <span className="material-symbols-outlined text-[22px]">
              shopping_bag
            </span>
            <span className="absolute -top-1.5 -right-2 inline-flex h-4.5 min-w-4.5 items-center justify-center rounded-full bg-black px-1 text-[10px] font-bold text-white">
              0
            </span>
          </Link>
        </div>
      </div>
    </motion.nav>
  );
}

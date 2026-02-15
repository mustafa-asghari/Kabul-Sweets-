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
          <Link
            href="/shop"
            className="text-gray-500 hover:text-black transition"
          >
            <span className="material-symbols-outlined text-[22px]">
              search
            </span>
          </Link>
          <Link
            href="/shop"
            className="relative text-gray-500 hover:text-black transition"
          >
            <span className="material-symbols-outlined text-[22px]">
              shopping_bag
            </span>
            <span className="absolute -top-1.5 -right-2 inline-flex h-[18px] min-w-[18px] items-center justify-center rounded-full bg-black px-1 text-[10px] font-bold text-white">
              0
            </span>
          </Link>
        </div>
      </div>
    </motion.nav>
  );
}

"use client";

import { motion, useScroll, useMotionValueEvent } from "framer-motion";
import { useState } from "react";

export default function Navbar() {
  const [shrink, setShrink] = useState(false);
  const { scrollY } = useScroll();

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
        <span className="text-lg font-extrabold tracking-tight text-black">
          Kabul Sweets_
        </span>
        <div className="hidden md:flex items-center gap-8 text-sm font-medium text-gray-600">
          <a href="#" className="hover:text-black transition">
            Shop
          </a>
          <a href="#" className="hover:text-black transition">
            Collections
          </a>
          <a href="#" className="hover:text-black transition">
            Blog
          </a>
          <a href="#" className="hover:text-black transition">
            Support
          </a>
        </div>
        <div className="flex items-center gap-4">
          <button className="text-gray-500 hover:text-black transition">
            <span className="material-symbols-outlined text-[22px]">
              search
            </span>
          </button>
          <button className="relative text-gray-500 hover:text-black transition">
            <span className="material-symbols-outlined text-[22px]">
              shopping_bag
            </span>
            <span className="absolute -top-1.5 -right-2 text-[10px] font-bold text-black">
              0
            </span>
          </button>
        </div>
      </div>
    </motion.nav>
  );
}

"use client";

import { motion } from "framer-motion";
import Link from "next/link";

const fadeUp = {
  hidden: { opacity: 0, y: 30 },
  visible: (i: number) => ({
    opacity: 1,
    y: 0,
    transition: { duration: 0.7, ease: "easeOut", delay: 0.2 + i * 0.15 },
  }),
};

export default function HeroSection() {
  return (
    <section className="max-w-[1200px] mx-auto px-6 pt-6 pb-16">
      <div className="relative rounded-[2rem] overflow-hidden min-h-[520px] md:min-h-[560px] bg-cream-dark">
        <div className="absolute inset-0 bg-[radial-gradient(circle_at_14%_20%,#fff3cc_0%,#f0d8a2_30%,#e1be75_54%,rgba(245,235,218,0.86)_72%,rgba(245,235,218,0)_100%)]" />

        <div className="relative z-10 min-h-[520px] md:min-h-[560px] flex items-center justify-end px-8 md:px-16 py-12 md:py-16">
          <div className="max-w-xl w-full">
            <motion.h1
              custom={0}
              initial="hidden"
              animate="visible"
              variants={fadeUp}
              className="text-4xl md:text-[3.2rem] font-extrabold tracking-tight text-black leading-[1.1] mb-5"
            >
              The <span className="text-accent">sweetest</span> way to celebrate
              any occasion.
            </motion.h1>

            <motion.p
              custom={1}
              initial="hidden"
              animate="visible"
              variants={fadeUp}
              className="text-[15px] text-gray-700 leading-relaxed mb-8 max-w-md"
            >
              Handmade Afghan sweets and custom cakes crafted with tradition.
              Fresh baked daily for pickup and takeaway in Acacia Ridge.
            </motion.p>

            <motion.div
              custom={2}
              initial="hidden"
              animate="visible"
              variants={fadeUp}
              whileHover={{ scale: 1.03 }}
              whileTap={{ scale: 0.95 }}
            >
              <Link
                href="/shop"
                className="inline-flex items-center gap-2 text-sm font-semibold text-black hover:text-accent transition"
              >
                Shop Products
                <span className="material-symbols-outlined text-[18px]">
                  north_east
                </span>
              </Link>
            </motion.div>
          </div>
        </div>
      </div>
    </section>
  );
}

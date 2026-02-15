"use client";

import { motion } from "framer-motion";
import Image from "next/image";
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
      <div className="relative rounded-[2rem] overflow-hidden min-h-[520px] md:min-h-[560px] flex items-center bg-cream-dark p-8 md:p-16">
        <div className="absolute inset-y-0 left-0 hidden md:block w-[46%] bg-[radial-gradient(circle_at_28%_16%,#fff3cc_0%,#f2d59d_28%,#e4be76_56%,#f5ebda_86%)]" />

        <div className="relative z-10 max-w-lg">
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

        {/* Hero image */}
        <motion.div
          initial={{ opacity: 0, y: 30 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.8, ease: "easeOut", delay: 0.4 }}
          className="hidden md:block absolute right-8 lg:right-16 bottom-0 w-[380px] lg:w-[420px]"
        >
          <motion.div
            animate={{ y: [0, -12, 0] }}
            transition={{ duration: 5, ease: "easeInOut", repeat: Infinity }}
          >
            <Image
              src="https://lh3.googleusercontent.com/aida-public/AB6AXuDq89SDCLSN76kunOlhOstWiLYy_EeKgfBrsy6JZz0jpshRTC5CihmDbiihKD5znmF1qTa8n9HUjyYRQUtb3CC56I5AgfAWbENpaxpv1KCiW_H8R9o4YhRNGErDGMrNhP8iYQ0iawo7QghrlZvf8kpWnMlHIu-Gzgre5OAYuR3DZYP_N8DnY6bkbpZd3TKkzKZx6XhoL2hWzO0FWacx2PSfE-Uw_6QfzhhRXSpffNHqrVnQSyIPwq6ha430fe3jmJL4Xv45KFNk83g"
              alt="Celebration Cake"
              width={420}
              height={420}
              className="w-full h-auto drop-shadow-2xl"
              priority
            />
          </motion.div>
        </motion.div>
      </div>
    </section>
  );
}

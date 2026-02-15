"use client";

import { motion } from "framer-motion";
import Image from "next/image";

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
      <div
        className="relative rounded-[2rem] overflow-hidden min-h-[520px] md:min-h-[560px] flex items-center p-8 md:p-16"
        style={{
          background:
            "linear-gradient(135deg, #FDF6EC 0%, #f0d9a8 20%, #c9922e 50%, #d4a84b 70%, #e8c882 90%, #FDF6EC 100%)",
        }}
      >
        {/* Decorative wave SVG overlay */}
        <svg
          className="absolute inset-0 w-full h-full opacity-30 pointer-events-none"
          viewBox="0 0 1200 600"
          preserveAspectRatio="none"
          xmlns="http://www.w3.org/2000/svg"
        >
          <defs>
            <linearGradient id="wg" x1="0%" y1="0%" x2="100%" y2="100%">
              <stop
                offset="0%"
                style={{ stopColor: "#ad751c", stopOpacity: 0.4 }}
              />
              <stop
                offset="50%"
                style={{ stopColor: "#d4a84b", stopOpacity: 0.6 }}
              />
              <stop
                offset="100%"
                style={{ stopColor: "#ffffff", stopOpacity: 0.2 }}
              />
            </linearGradient>
          </defs>
          <path
            d="M0,200 C200,100 400,350 600,200 C800,50 1000,300 1200,150 L1200,600 L0,600 Z"
            fill="url(#wg)"
          />
          <path
            d="M0,350 C150,250 350,450 550,300 C750,150 950,400 1200,280 L1200,600 L0,600 Z"
            fill="rgba(255,255,255,.15)"
          />
        </svg>

        <div className="relative z-10 max-w-lg">
          <motion.div
            custom={0}
            initial="hidden"
            animate="visible"
            variants={fadeUp}
            className="inline-flex items-center gap-2 px-4 py-1.5 rounded-full bg-white/80 backdrop-blur-sm mb-6 text-xs font-semibold text-gray-700 shadow-sm"
          >
            <span className="material-symbols-outlined text-[14px]">
              storefront
            </span>
            Powered by Tradition
          </motion.div>

          <motion.h1
            custom={1}
            initial="hidden"
            animate="visible"
            variants={fadeUp}
            className="text-4xl md:text-[3.2rem] font-extrabold tracking-tight text-black leading-[1.1] mb-5"
          >
            The <span className="text-accent">sweetest</span> way to celebrate
            any occasion.
          </motion.h1>

          <motion.p
            custom={2}
            initial="hidden"
            animate="visible"
            variants={fadeUp}
            className="text-[15px] text-gray-700 leading-relaxed mb-8 max-w-md"
          >
            Handmade Afghan sweets and custom cakes crafted with tradition.
            Fresh baked daily and delivered across Queensland.
          </motion.p>

          <motion.a
            custom={3}
            initial="hidden"
            animate="visible"
            variants={fadeUp}
            href="#"
            whileHover={{ scale: 1.03 }}
            whileTap={{ scale: 0.95 }}
            className="inline-flex items-center gap-2 px-6 py-3 bg-white text-black text-sm font-semibold rounded-full shadow-md hover:shadow-lg transition-shadow"
          >
            Shop Products
            <span className="material-symbols-outlined text-[18px]">
              north_east
            </span>
          </motion.a>
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

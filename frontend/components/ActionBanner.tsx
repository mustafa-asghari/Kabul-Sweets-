"use client";

import { motion, useScroll, useTransform } from "framer-motion";
import { useRef } from "react";
import Image from "next/image";

const cakeBannerImage =
  "https://lh3.googleusercontent.com/aida-public/AB6AXuDq89SDCLSN76kunOlhOstWiLYy_EeKgfBrsy6JZz0jpshRTC5CihmDbiihKD5znmF1qTa8n9HUjyYRQUtb3CC56I5AgfAWbENpaxpv1KCiW_H8R9o4YhRNGErDGMrNhP8iYQ0iawo7QghrlZvf8kpWnMlHIu-Gzgre5OAYuR3DZYP_N8DnY6bkbpZd3TKkzKZx6XhoL2hWzO0FWacx2PSfE-Uw_6QfzhhRXSpffNHqrVnQSyIPwq6ha430fe3jmJL4Xv45KFNk83g";

export default function ActionBanner() {
  const ref = useRef(null);
  const { scrollYProgress } = useScroll({
    target: ref,
    offset: ["start end", "end start"],
  });

  const imageY = useTransform(scrollYProgress, [0, 1], ["-10%", "10%"]);

  return (
    <section className="max-w-[1200px] mx-auto px-6 pb-20">
      <div
        ref={ref}
        className="relative rounded-[2rem] overflow-hidden h-[300px] md:h-[360px] flex items-center justify-center"
      >
        <motion.div className="absolute inset-0" style={{ y: imageY }}>
          <Image
            src={cakeBannerImage}
            alt="Cake collection showcase"
            fill
            className="object-cover"
          />
        </motion.div>
        <div className="absolute inset-0 bg-black/50" />
        <h2 className="relative z-10 text-white text-2xl md:text-4xl font-extrabold tracking-tight text-center leading-snug max-w-xl px-4">
          Showcase your cake collection and highlight your signature flavors.
        </h2>
      </div>
    </section>
  );
}

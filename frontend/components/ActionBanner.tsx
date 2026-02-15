"use client";

import { motion, useScroll, useTransform } from "framer-motion";
import { useRef } from "react";
import Image from "next/image";

const cakeBannerImage =
  "/products/cake-alt.png";

interface ActionBannerProps {
  zoomOut?: boolean;
}

export default function ActionBanner({ zoomOut = false }: ActionBannerProps) {
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
            sizes="(max-width: 768px) 100vw, 1200px"
            className={
              zoomOut
                ? "object-contain scale-[0.9] md:scale-[0.86]"
                : "object-cover"
            }
          />
        </motion.div>
        <div className="absolute inset-0 bg-black/50" />
        <h2 className="relative z-10 text-white text-2xl md:text-4xl font-extrabold tracking-tight text-center leading-snug max-w-xl px-4">
          Cake Collection
        </h2>
      </div>
    </section>
  );
}

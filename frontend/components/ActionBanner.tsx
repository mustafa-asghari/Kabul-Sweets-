"use client";

import { motion, useScroll, useTransform } from "framer-motion";
import { useRef } from "react";
import Image from "next/image";

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
            src="https://lh3.googleusercontent.com/aida-public/AB6AXuA3sPImiQPkuGjSGPZxYDuO9EIzchNoS_7P5PauNwuH4Wut-wzcnw6otL03T9xZTHMQjA13sjflbr02ARE_AML8jjg7lUPCazioX6R_gIQVxJtdFPeF3sIBg57ykE18cyIkOgkcPxmi2cT84L9iH51pypSvQZGY8m86Pn8uDQH87e5UBYRw5G-jeS8LafPOFTkQkZmywcfXhubvZiE9fy74dZNCTS2E_DZHR1uGTcKxTwCLh2lbXm4-tY4JokMke7JPVooBg_SSPd0"
            alt="Bakery in action"
            fill
            className="object-cover"
          />
        </motion.div>
        <div className="absolute inset-0 bg-black/50" />
        <h2 className="relative z-10 text-white text-2xl md:text-4xl font-extrabold tracking-tight text-center leading-snug max-w-xl px-4">
          Showcase your products in action and outline their benefits.
        </h2>
      </div>
    </section>
  );
}

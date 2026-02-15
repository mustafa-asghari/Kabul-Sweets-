"use client";

import { motion, useInView } from "framer-motion";
import { useRef } from "react";
import Image from "next/image";

export default function TestimonialSection() {
  const ref = useRef(null);
  const isInView = useInView(ref, { once: true, margin: "0px 0px -50px 0px" });

  return (
    <section className="max-w-[1200px] mx-auto px-6 pb-20">
      <motion.div
        ref={ref}
        initial={{ opacity: 0, y: 40, scale: 0.98 }}
        animate={
          isInView
            ? { opacity: 1, y: 0, scale: 1 }
            : { opacity: 0, y: 40, scale: 0.98 }
        }
        transition={{ type: "spring", stiffness: 100, damping: 30 }}
        className="bg-cream-dark rounded-[2rem] py-16 px-8 md:px-16 text-center relative overflow-hidden"
      >
        {/* Nav arrows */}
        <div className="absolute top-8 right-8 flex gap-2">
          <button className="w-9 h-9 rounded-full border border-gray-300 flex items-center justify-center text-gray-400 hover:border-black hover:text-black transition">
            <span className="material-symbols-outlined text-[18px]">
              arrow_back
            </span>
          </button>
          <button className="w-9 h-9 rounded-full border border-gray-300 flex items-center justify-center text-gray-400 hover:border-black hover:text-black transition">
            <span className="material-symbols-outlined text-[18px]">
              arrow_forward
            </span>
          </button>
        </div>

        <div className="w-16 h-16 rounded-full overflow-hidden mx-auto mb-8 shadow-md">
          <Image
            src="https://lh3.googleusercontent.com/aida-public/AB6AXuAR7FDE8B7bHgv_3Bvz8mnSE6XDv_tMPgkI6K9mspZA4fxPPqKJTs99BzlcyJ-ynGQlwzvC-7oFf1PRBbbVnB-8_1BgZhlAfLWEpLdxLdWCirRd9SvLmmwwTdVoXoD4eE2CGhDEOLCTCG-REbYjRTzEqSu_bX8OaVIQlMc4KJ4tALMm3LZM6AQ9lWBTrG_ee9QLOe3IKnB_9JFEPmxmd7fcL73ncqLC-h-enpNC0LQBhi6-M6U97xcHMDl8eFmN-2sMsMzRVgUjWas"
            alt="Customer"
            width={64}
            height={64}
            className="w-full h-full object-cover"
          />
        </div>

        <h2 className="text-2xl md:text-[2rem] font-extrabold tracking-tight text-black leading-snug max-w-2xl mx-auto mb-8">
          &ldquo;The most authentic Afghan sweets I&apos;ve tasted outside of
          Kabul. The custom cake was a masterpiece!&rdquo;
        </h2>

        <div className="flex gap-0.5 justify-center mb-2">
          {[...Array(5)].map((_, i) => (
            <span
              key={i}
              className="material-symbols-outlined text-lg text-black"
              style={{ fontVariationSettings: "'FILL' 1" }}
            >
              star
            </span>
          ))}
        </div>

        <p className="text-sm text-gray-500 font-medium">Sarah A.</p>

        <p className="text-xs text-gray-400 mt-8 mb-4">
          Featured on platforms that trust quality and tradition:
        </p>
        <div className="flex items-center justify-center gap-8 opacity-30 text-black">
          <span className="text-lg font-extrabold tracking-tight">
            Uber Eats
          </span>
          <span className="text-lg font-extrabold tracking-tight">
            DoorDash
          </span>
          <span className="text-lg font-extrabold tracking-tight">Google</span>
          <span className="text-lg font-extrabold tracking-tight hidden sm:block">
            Facebook
          </span>
          <span className="text-lg font-extrabold tracking-tight hidden sm:block">
            Instagram
          </span>
        </div>
      </motion.div>
    </section>
  );
}

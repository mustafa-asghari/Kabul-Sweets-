"use client";

import { motion } from "framer-motion";
import Image from "next/image";
import { revealChild } from "./ScrollReveal";
import Link from "next/link";

interface CollectionCardProps {
  title: string;
  description?: string;
  imageSrc: string;
  imageAlt: string;
  href?: string;
}

export default function CollectionCard({
  title,
  description,
  imageSrc,
  imageAlt,
  href = "/collections",
}: CollectionCardProps) {
  return (
    <motion.div
      variants={revealChild}
      whileHover={{ y: -4 }}
      transition={{ type: "spring", stiffness: 300, damping: 20 }}
      className="group relative bg-white rounded-[1.5rem] p-6 md:p-7 min-h-[320px] flex flex-col overflow-hidden hover:shadow-lg transition-shadow duration-300 cursor-pointer"
    >
      <Link href={href} className="absolute inset-0 z-10" aria-label={title} />
      <div className="relative z-20 flex items-start justify-between gap-4 mb-4">
        <div>
          <h3 className="text-3xl md:text-4xl font-extrabold tracking-tight text-black leading-none">
            {title}
          </h3>
          {description ? (
            <p className="mt-2 text-sm text-gray-600">{description}</p>
          ) : null}
        </div>
        <span className="material-symbols-outlined text-[18px] text-gray-600 transition-all group-hover:text-black group-hover:-translate-y-0.5">
          north_east
        </span>
      </div>
      <div className="relative mt-auto rounded-2xl bg-cream-dark/70 p-3">
        <Image
          src={imageSrc}
          alt={imageAlt}
          width={500}
          height={360}
          sizes="(max-width: 768px) 88vw, (max-width: 1280px) 42vw, 360px"
          className="w-full h-48 md:h-52 object-cover rounded-xl group-hover:scale-[1.02] transition-transform duration-500"
        />
      </div>
    </motion.div>
  );
}

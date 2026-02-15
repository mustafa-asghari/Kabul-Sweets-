"use client";

import { motion } from "framer-motion";
import Image from "next/image";
import { revealChild } from "./ScrollReveal";
import Link from "next/link";

interface ProductCardProps {
  slug?: string;
  title: string;
  category: string;
  price: string;
  imageSrc: string;
  imageAlt: string;
}

export default function ProductCard({
  slug,
  title,
  category,
  price,
  imageSrc,
  imageAlt,
}: ProductCardProps) {
  const href = slug ? `/products/${slug}` : "/shop";

  return (
    <motion.div variants={revealChild} className="group">
      <motion.div
        whileHover={{ y: -4 }}
        transition={{ type: "spring", stiffness: 300, damping: 20 }}
        className="relative bg-white rounded-[1.5rem] p-6 aspect-square flex items-center justify-center overflow-hidden hover:shadow-lg transition-shadow duration-300"
      >
        <Link href={href} className="absolute inset-0 z-10" aria-label={title} />
        <Image
          src={imageSrc}
          alt={imageAlt}
          width={400}
          height={400}
          className="w-[80%] h-auto object-contain group-hover:scale-105 transition-transform duration-500"
        />
        <Link
          href={href}
          aria-label={`Open ${title}`}
          className="absolute bottom-5 right-5 w-10 h-10 bg-white rounded-full shadow-md flex items-center justify-center text-gray-600 hover:bg-black hover:text-white transition-all opacity-0 group-hover:opacity-100 translate-y-2 group-hover:translate-y-0 z-20"
        >
          <span className="material-symbols-outlined text-[18px]">
            north_east
          </span>
        </Link>
      </motion.div>
      <div className="mt-4 px-1">
        <h3 className="font-bold text-[15px] text-black">{title}</h3>
        <p className="text-xs text-gray-400 mt-0.5">{category}</p>
        <p className="text-sm text-gray-600 mt-1">
          {price.startsWith("From") ? (
            <>
              From{" "}
              <span className="font-semibold">{price.replace("From ", "")}</span>
            </>
          ) : (
            <span className="font-semibold">{price}</span>
          )}
        </p>
      </div>
    </motion.div>
  );
}

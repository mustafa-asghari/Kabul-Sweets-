"use client";

import { motion } from "framer-motion";
import Image from "next/image";
import { revealChild } from "./ScrollReveal";
import Link from "next/link";

interface CollectionCardProps {
  title: string;
  imageSrc: string;
  imageAlt: string;
  href?: string;
}

export default function CollectionCard({
  title,
  imageSrc,
  imageAlt,
  href = "/collections",
}: CollectionCardProps) {
  return (
    <motion.div
      variants={revealChild}
      whileHover={{ y: -4 }}
      transition={{ type: "spring", stiffness: 300, damping: 20 }}
      className="group relative bg-white rounded-[1.5rem] p-8 min-h-[320px] flex flex-col justify-between overflow-hidden hover:shadow-lg transition-shadow duration-300 cursor-pointer"
    >
      <Link href={href} className="absolute inset-0 z-10" aria-label={title} />
      <h3 className="text-[2.5rem] font-extrabold tracking-tight text-black leading-none z-10">
        {title}
      </h3>
      <Image
        src={imageSrc}
        alt={imageAlt}
        width={300}
        height={300}
        className="absolute bottom-4 right-4 w-[55%] h-auto object-contain opacity-80 group-hover:scale-105 transition-transform duration-500"
      />
      <Link
        href={href}
        aria-label={`Open ${title}`}
        className="absolute bottom-5 right-5 z-20 flex h-10 w-10 items-center justify-center rounded-md border border-black/10 bg-white text-gray-600 shadow-md transition-all hover:border-black hover:bg-black hover:text-white"
      >
        <span className="material-symbols-outlined text-[18px]">
          north_east
        </span>
      </Link>
    </motion.div>
  );
}

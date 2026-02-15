"use client";

import { motion } from "framer-motion";
import { revealChild } from "./ScrollReveal";

interface FeatureCardProps {
  icon: string;
  title: string;
  description: string;
}

export default function FeatureCard({
  icon,
  title,
  description,
}: FeatureCardProps) {
  return (
    <motion.div
      variants={revealChild}
      whileHover={{ y: -4 }}
      transition={{ type: "spring", stiffness: 300, damping: 20 }}
      className="bg-cream-dark rounded-[1.5rem] p-8"
    >
      <div className="w-12 h-12 rounded-xl bg-white flex items-center justify-center mb-5 shadow-sm">
        <span className="material-symbols-outlined text-accent text-[24px]">
          {icon}
        </span>
      </div>
      <h3 className="font-bold text-black mb-2">{title}</h3>
      <p className="text-sm text-gray-500 leading-relaxed">{description}</p>
    </motion.div>
  );
}

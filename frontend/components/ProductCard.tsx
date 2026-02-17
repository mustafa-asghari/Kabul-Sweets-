"use client";

import { motion } from "framer-motion";
import Image from "next/image";
import { revealChild } from "./ScrollReveal";
import Link from "next/link";
import { useCallback, useState } from "react";

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
  const [autoScale, setAutoScale] = useState(1);

  const handleImageLoad = useCallback((img: HTMLImageElement) => {
    if (typeof document === "undefined" || !img.naturalWidth || !img.naturalHeight) {
      return;
    }

    const sampleMax = 320;
    const sampleWidth = Math.max(
      24,
      Math.round((img.naturalWidth / Math.max(img.naturalWidth, img.naturalHeight)) * sampleMax)
    );
    const sampleHeight = Math.max(
      24,
      Math.round((img.naturalHeight / Math.max(img.naturalWidth, img.naturalHeight)) * sampleMax)
    );

    const canvas = document.createElement("canvas");
    canvas.width = sampleWidth;
    canvas.height = sampleHeight;

    const ctx = canvas.getContext("2d", { willReadFrequently: true });
    if (!ctx) {
      return;
    }

    try {
      ctx.drawImage(img, 0, 0, sampleWidth, sampleHeight);
      const pixelData = ctx.getImageData(0, 0, sampleWidth, sampleHeight).data;

      const nearWhite = 246;
      const neutralLightMin = 226;
      const neutralLightMaxChroma = 14;
      const nearTransparent = 16;
      const detectOccupancy = (ignoreNeutralLight: boolean) => {
        let minX = sampleWidth;
        let minY = sampleHeight;
        let maxX = -1;
        let maxY = -1;

        for (let y = 0; y < sampleHeight; y += 1) {
          for (let x = 0; x < sampleWidth; x += 1) {
            const idx = (y * sampleWidth + x) * 4;
            const r = pixelData[idx];
            const g = pixelData[idx + 1];
            const b = pixelData[idx + 2];
            const a = pixelData[idx + 3];
            const value = Math.max(r, g, b);
            const chroma = Math.max(r, g, b) - Math.min(r, g, b);
            const isNeutralLightBackground =
              ignoreNeutralLight &&
              value >= neutralLightMin &&
              chroma <= neutralLightMaxChroma;
            const isBackground =
              a <= nearTransparent ||
              (r >= nearWhite && g >= nearWhite && b >= nearWhite) ||
              isNeutralLightBackground;

            if (isBackground) {
              continue;
            }

            if (x < minX) minX = x;
            if (y < minY) minY = y;
            if (x > maxX) maxX = x;
            if (y > maxY) maxY = y;
          }
        }

        if (maxX <= minX || maxY <= minY) {
          return 0;
        }

        const subjectWidthRatio = (maxX - minX + 1) / sampleWidth;
        const subjectHeightRatio = (maxY - minY + 1) / sampleHeight;
        return Math.max(subjectWidthRatio, subjectHeightRatio);
      };

      let occupancy = detectOccupancy(true);
      if (!Number.isFinite(occupancy) || occupancy <= 0) {
        return;
      }
      if (occupancy < 0.48) {
        const relaxed = detectOccupancy(false);
        if (Number.isFinite(relaxed) && relaxed > occupancy) {
          occupancy = relaxed;
        }
      }
      if (!Number.isFinite(occupancy) || occupancy <= 0) {
        return;
      }

      const targetOccupancy = 0.88;
      const scale = Math.min(1.4, Math.max(1, targetOccupancy / occupancy));
      setAutoScale(scale);
    } catch {
      // Canvas reads can fail for some remote assets. Keep default framing.
    }
  }, []);

  return (
    <motion.div variants={revealChild} className="group">
      <motion.div
        whileHover={{ y: -4 }}
        transition={{ type: "spring", stiffness: 300, damping: 20 }}
        className="relative bg-white rounded-[1.5rem] p-6 aspect-square flex items-center justify-center overflow-hidden hover:shadow-lg transition-shadow duration-300"
      >
        <Link href={href} className="absolute inset-0 z-10" aria-label={title} />
        <div className="relative h-full w-full overflow-hidden rounded-[1.1rem]">
          <div className="relative h-full w-full transition-transform duration-500 group-hover:scale-105">
            <Image
              src={imageSrc}
              alt={imageAlt}
              fill
              sizes="(max-width: 640px) 88vw, (max-width: 1280px) 42vw, 320px"
              className="object-cover object-center transition-transform duration-300"
              style={{
                transform: `scale(${autoScale})`,
                transformOrigin: "center",
              }}
              onLoad={(event) => handleImageLoad(event.currentTarget)}
            />
          </div>
        </div>
        <Link
          href={href}
          aria-label={`Open ${title}`}
          className="absolute bottom-5 right-5 z-20 flex h-10 w-10 items-center justify-center text-gray-600 transition-all opacity-0 translate-y-2 group-hover:translate-y-0 group-hover:opacity-100 hover:text-black"
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

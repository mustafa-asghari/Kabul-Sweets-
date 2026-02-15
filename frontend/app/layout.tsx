import type { Metadata } from "next";
import { Inter } from "next/font/google";
import "./globals.css";

const inter = Inter({
  subsets: ["latin"],
  weight: ["400", "500", "600", "700", "800"],
});

export const metadata: Metadata = {
  title: "Kabul Sweets | Premium Afghan Sweets & Cakes",
  description:
    "Handmade Afghan sweets and custom cakes crafted with tradition. Fresh baked daily for pickup and takeaway in Acacia Ridge.",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en">
      <body className={`${inter.className} min-h-screen flex flex-col bg-cream text-[#111]`}>
        {children}
      </body>
    </html>
  );
}

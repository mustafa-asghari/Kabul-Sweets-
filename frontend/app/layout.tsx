import type { Metadata } from "next";
import { Inter } from "next/font/google";
import AppProviders from "@/components/AppProviders";
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
      <head>
        <link rel="preconnect" href="https://lh3.googleusercontent.com" />
      </head>
      <body className={`${inter.className} min-h-screen flex flex-col bg-cream text-[#111]`}>
        <AppProviders>{children}</AppProviders>
      </body>
    </html>
  );
}

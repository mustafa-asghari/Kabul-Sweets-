"use client";

import { motion } from "framer-motion";

export default function Footer() {
  return (
    <footer className="bg-cream">
      <div className="max-w-[1200px] mx-auto px-6 pt-12 pb-8">
        <span className="text-lg font-extrabold tracking-tight text-black mb-6 block">
          Kabul Sweets_
        </span>
        <div className="bg-cream-dark rounded-[1.5rem] p-8 md:p-12 flex flex-col md:flex-row justify-between gap-10">
          {/* Newsletter */}
          <div className="max-w-sm">
            <h3 className="text-xl md:text-2xl font-extrabold tracking-tight text-black leading-snug mb-6">
              Join our newsletter and get 20% off your first purchase with us.
            </h3>
            <form className="flex gap-2" onSubmit={(e) => e.preventDefault()}>
              <input
                type="email"
                placeholder="Your Email Address"
                className="flex-1 px-5 py-3 rounded-full bg-white border-none text-sm text-gray-800 placeholder-gray-400 outline-none focus:ring-2 focus:ring-accent/30 shadow-sm"
              />
              <motion.button
                type="submit"
                whileHover={{ scale: 1.03 }}
                whileTap={{ scale: 0.97 }}
                className="px-6 py-3 bg-accent text-white text-sm font-semibold rounded-full shadow-sm"
              >
                Join
              </motion.button>
            </form>
          </div>
          {/* Links */}
          <div className="flex gap-16">
            <div>
              <h4 className="text-xs font-bold text-black mb-4 uppercase tracking-wider">
                Pages
              </h4>
              <ul className="space-y-2.5 text-sm text-gray-500">
                <li>
                  <a href="#" className="hover:text-black transition">
                    Home
                  </a>
                </li>
                <li>
                  <a href="#" className="hover:text-black transition">
                    Shop
                  </a>
                </li>
                <li>
                  <a href="#" className="hover:text-black transition">
                    Collections
                  </a>
                </li>
                <li>
                  <a href="#" className="hover:text-black transition">
                    Blog
                  </a>
                </li>
              </ul>
            </div>
            <div>
              <h4 className="text-xs font-bold text-black mb-4 uppercase tracking-wider">
                Information
              </h4>
              <ul className="space-y-2.5 text-sm text-gray-500">
                <li>
                  <a href="#" className="hover:text-black transition">
                    Terms & Conditions
                  </a>
                </li>
                <li>
                  <a href="#" className="hover:text-black transition">
                    Privacy policy
                  </a>
                </li>
                <li>
                  <a href="#" className="hover:text-black transition">
                    Support
                  </a>
                </li>
                <li>
                  <a href="#" className="hover:text-black transition">
                    404
                  </a>
                </li>
              </ul>
            </div>
          </div>
        </div>
        <p className="text-xs text-gray-400 mt-6">
          Created by{" "}
          <span className="font-semibold text-gray-500">Kabul Sweets</span>{" "}
          &copy; 2025
        </p>
      </div>
    </footer>
  );
}

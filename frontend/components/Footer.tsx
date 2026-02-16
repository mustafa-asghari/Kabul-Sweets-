import Link from "next/link";

export default function Footer() {
  return (
    <footer className="bg-cream">
      <div className="max-w-[1200px] mx-auto px-6 pt-12 pb-8">
        <span className="text-lg font-extrabold tracking-tight text-black mb-6 block">
          Kabul <span className="text-accent">Sweets</span>_
        </span>
        <div className="bg-cream-dark rounded-[1.5rem] p-8 md:p-12 flex flex-col md:flex-row justify-between gap-10">
          {/* Newsletter */}
          <div className="max-w-sm">
            <h3 className="text-xl md:text-2xl font-extrabold tracking-tight text-black leading-snug mb-6">
              Join our newsletter and get 20% off your first purchase with us.
            </h3>
            <form action="#" className="flex gap-2">
              <input
                type="email"
                placeholder="Your Email Address"
                className="flex-1 px-5 py-3 rounded-full bg-white border-none text-sm text-gray-800 placeholder-gray-400 outline-none focus:ring-2 focus:ring-accent/30 shadow-sm"
              />
              <button
                type="submit"
                className="px-6 py-3 bg-accent text-white text-sm font-semibold rounded-full shadow-sm transition-all hover:shadow-md hover:brightness-105 active:scale-[0.98]"
              >
                Join
              </button>
            </form>
          </div>
          {/* Links */}
          <div className="flex flex-wrap gap-16">
            <div>
              <h4 className="text-xs font-bold text-black mb-4 uppercase tracking-wider">
                Pages
              </h4>
              <ul className="space-y-2.5 text-sm text-gray-500">
                <li>
                  <Link
                    href="/"
                    className="hover:text-black transition"
                  >
                    Home
                  </Link>
                </li>
                <li>
                  <Link
                    href="/shop"
                    className="hover:text-black transition"
                  >
                    Shop
                  </Link>
                </li>
                <li>
                  <Link
                    href="/collections"
                    className="hover:text-black transition"
                  >
                    Collections
                  </Link>
                </li>
              </ul>
            </div>
            <div>
              <h4 className="text-xs font-bold text-black mb-4 uppercase tracking-wider">
                Information
              </h4>
              <ul className="space-y-2.5 text-sm text-gray-500">
                <li>
                  <Link
                    href="/terms-and-conditions"
                    className="hover:text-black transition"
                  >
                    Terms & Conditions
                  </Link>
                </li>
                <li>
                  <Link
                    href="/privacy-policy"
                    className="hover:text-black transition"
                  >
                    Privacy policy
                  </Link>
                </li>
                <li>
                  <Link
                    href="/support"
                    className="hover:text-black transition"
                  >
                    Support
                  </Link>
                </li>
              </ul>
            </div>
            <div>
              <h4 className="text-xs font-bold text-black mb-4 uppercase tracking-wider">
                Visit & Contact
              </h4>
              <ul className="space-y-2.5 text-sm text-gray-500">
                <li>Kabul Sweets, Kabul, Afghanistan</li>
                <li>
                  <a
                    href="tel:+93700000000"
                    className="hover:text-black transition"
                  >
                    +93 700 000 000
                  </a>
                </li>
                <li>
                  <a
                    href="mailto:hello@kabulsweets.com"
                    className="hover:text-black transition"
                  >
                    hello@kabulsweets.com
                  </a>
                </li>
              </ul>
            </div>
          </div>
        </div>
        <p className="text-xs text-gray-400 mt-6">
          Created by{" "}
          <span className="font-semibold text-gray-500">
            Kabul <span className="text-accent">Sweets</span>
          </span>{" "}
          &copy; 2025
        </p>
      </div>
    </footer>
  );
}

import Footer from "@/components/Footer";
import Navbar from "@/components/Navbar";

const STORE_ADDRESS = "Shahr-e-Naw, Kabul, Afghanistan";
const GOOGLE_MAPS_DIRECTIONS_URL =
  "https://www.google.com/maps/dir/?api=1&destination=Shahr-e-Naw%2C+Kabul%2C+Afghanistan";
const GOOGLE_MAPS_EMBED_URL =
  "https://maps.google.com/maps?q=Shahr-e-Naw%2C%20Kabul%2C%20Afghanistan&t=&z=15&ie=UTF8&iwloc=&output=embed";

export default function ContactPage() {
  return (
    <>
      <Navbar />
      <main className="flex-1 pb-20">
        <section className="max-w-[1200px] mx-auto px-6 pt-6 pb-12">
          <div className="rounded-[2rem] bg-cream-dark px-6 py-14 md:px-12 md:py-20">
            <div className="text-center">
              <span className="inline-flex items-center rounded-full bg-white px-4 py-1.5 text-xs font-semibold text-gray-600 shadow-sm">
                Contact
              </span>
              <h1 className="mt-6 text-4xl md:text-6xl font-extrabold tracking-tight text-black leading-[1.08]">
                Visit & Contact Kabul Sweets
              </h1>
              <p className="mt-4 text-sm md:text-base text-gray-500 max-w-2xl mx-auto leading-relaxed">
                Find our location, get directions, and reach us directly from one
                page.
              </p>
            </div>
          </div>
        </section>

        <section className="max-w-[1200px] mx-auto px-6 pb-16">
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
            <a
              id="map"
              href={GOOGLE_MAPS_DIRECTIONS_URL}
              target="_blank"
              rel="noopener noreferrer"
              className="group rounded-[1.5rem] bg-cream-dark p-5 block"
            >
              <p className="text-xs font-bold text-black uppercase tracking-wider mb-3">
                Location Map
              </p>
              <div className="relative overflow-hidden rounded-xl border border-white/70 shadow-sm">
                <iframe
                  src={GOOGLE_MAPS_EMBED_URL}
                  className="h-[320px] w-full pointer-events-none"
                  loading="lazy"
                  allowFullScreen
                  referrerPolicy="no-referrer-when-downgrade"
                  title="Kabul Sweets location map"
                />
                <div className="absolute inset-x-0 bottom-0 bg-black/60 px-4 py-3 text-sm font-semibold text-white">
                  Click to open Google Maps directions
                </div>
              </div>
            </a>

            <div
              id="contact-info"
              className="rounded-[1.5rem] bg-cream-dark p-8 flex flex-col justify-center"
            >
              <p className="text-xs font-bold text-black uppercase tracking-wider mb-6">
                Contact Details
              </p>
              <ul className="space-y-4 text-gray-600">
                <li>
                  <p className="text-xs uppercase tracking-wider text-gray-500 mb-1">
                    Address
                  </p>
                  <p className="text-black font-semibold">{STORE_ADDRESS}</p>
                </li>
                <li>
                  <p className="text-xs uppercase tracking-wider text-gray-500 mb-1">
                    Phone
                  </p>
                  <a
                    href="tel:+93700000000"
                    className="text-black font-semibold hover:text-accent transition"
                  >
                    +93 700 000 000
                  </a>
                </li>
                <li>
                  <p className="text-xs uppercase tracking-wider text-gray-500 mb-1">
                    Email
                  </p>
                  <a
                    href="mailto:hello@kabulsweets.com"
                    className="text-black font-semibold hover:text-accent transition"
                  >
                    hello@kabulsweets.com
                  </a>
                </li>
                <li>
                  <p className="text-xs uppercase tracking-wider text-gray-500 mb-1">
                    Hours
                  </p>
                  <p className="text-black font-semibold">
                    Open daily, 8:00 AM - 9:00 PM
                  </p>
                </li>
              </ul>
            </div>
          </div>
        </section>
      </main>
      <Footer />
    </>
  );
}

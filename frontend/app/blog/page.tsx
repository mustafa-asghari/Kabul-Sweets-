import Image from "next/image";
import Footer from "@/components/Footer";
import Navbar from "@/components/Navbar";
import ActionBanner from "@/components/ActionBanner";
import FeatureCard from "@/components/FeatureCard";
import ScrollReveal from "@/components/ScrollReveal";
import { blogPosts } from "@/data/storefront";

const [featuredPost, ...morePosts] = blogPosts;
const blogHighlights = [
  {
    icon: "bolt",
    title: "Instant Digital Downloads",
    description: "Access your design assets immediately after checkout.",
  },
  {
    icon: "diamond",
    title: "Premium Quality Materials",
    description: "Carefully produced content and resources built for long-term use.",
  },
  {
    icon: "local_shipping",
    title: "Fast & Secure Shipping",
    description: "Reliable fulfillment with full tracking on every physical product.",
  },
];

export default function BlogPage() {
  return (
    <>
      <Navbar />
      <main className="flex-1 pb-20">
        <ActionBanner />

        <section className="max-w-[1200px] mx-auto px-6 pb-20">
          <ScrollReveal className="text-center mb-12">
            <h2 className="text-2xl font-extrabold tracking-tight text-black mb-2">
              Highlight what makes you stand out
            </h2>
            <p className="text-sm text-gray-500">
              Use this section to show off key benefits for your customers.
            </p>
          </ScrollReveal>
          <ScrollReveal
            staggerChildren={0.1}
            className="grid grid-cols-1 md:grid-cols-3 gap-6"
          >
            {blogHighlights.map((item) => (
              <FeatureCard key={item.title} {...item} />
            ))}
          </ScrollReveal>
        </section>

        <section className="max-w-[1200px] mx-auto px-6 pb-14">
          <ScrollReveal>
            <div className="flex flex-col md:flex-row justify-between items-start md:items-end mb-8 gap-2">
              <div>
                <h2 className="text-2xl font-extrabold tracking-tight text-black">
                  Explore the blog
                </h2>
                <p className="mt-1 text-sm text-gray-500">
                  Share insights, boost SEO, and build trust with your audience.
                </p>
              </div>
              <a
                href="#more-posts"
                className="text-sm font-semibold text-black hover:text-accent transition flex items-center gap-1"
              >
                View Posts
                <span className="material-symbols-outlined text-[16px]">
                  arrow_forward
                </span>
              </a>
            </div>
          </ScrollReveal>

          <ScrollReveal className="rounded-[2rem] overflow-hidden bg-cream-dark grid grid-cols-1 lg:grid-cols-[1.1fr_1fr]">
            <div className="relative min-h-[320px] lg:min-h-[420px]">
              <Image
                src={featuredPost.imageSrc}
                alt={featuredPost.title}
                fill
                className="object-cover"
              />
            </div>
            <div className="p-8 md:p-10 flex flex-col justify-between">
              <div>
                <span className="inline-flex rounded-full bg-white px-3 py-1 text-xs font-semibold text-gray-600">
                  {featuredPost.tag}
                </span>
                <h2 className="mt-4 text-4xl font-extrabold tracking-tight text-black leading-tight">
                  {featuredPost.title}
                </h2>
                <p className="mt-4 text-gray-600 text-sm leading-relaxed max-w-md">
                  {featuredPost.excerpt}
                </p>
              </div>
              <p className="mt-8 text-sm text-gray-500">
                Written by {featuredPost.author}
                <span className="block text-xs">{featuredPost.role}</span>
              </p>
            </div>
          </ScrollReveal>
        </section>

        <section id="more-posts" className="max-w-[1200px] mx-auto px-6">
          <ScrollReveal
            staggerChildren={0.08}
            className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6"
          >
            {morePosts.map((post) => (
              <article key={post.slug} className="rounded-[1.5rem] overflow-hidden bg-white shadow-sm">
                <div className="relative h-56">
                  <Image src={post.imageSrc} alt={post.title} fill className="object-cover" />
                </div>
                <div className="p-6">
                  <span className="inline-flex rounded-full bg-cream-dark px-3 py-1 text-xs font-semibold text-gray-600">
                    {post.tag}
                  </span>
                  <h3 className="mt-3 text-2xl font-extrabold tracking-tight leading-snug text-black">
                    {post.title}
                  </h3>
                  <p className="mt-3 text-sm text-gray-500 leading-relaxed">{post.excerpt}</p>
                </div>
              </article>
            ))}
          </ScrollReveal>
        </section>
      </main>
      <Footer />
    </>
  );
}

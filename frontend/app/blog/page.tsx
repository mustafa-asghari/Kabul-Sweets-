import Image from "next/image";
import Footer from "@/components/Footer";
import Navbar from "@/components/Navbar";
import PageHero from "@/components/PageHero";
import ScrollReveal from "@/components/ScrollReveal";
import { blogPosts } from "@/data/storefront";

const [featuredPost, ...morePosts] = blogPosts;

export default function BlogPage() {
  return (
    <>
      <Navbar />
      <main className="flex-1 pb-20">
        <PageHero
          badge="Blog"
          title="Stories, tips, and ideas from Kabul Sweets."
          description="Share product inspiration, event planning guides, and behind-the-scenes bakery updates."
        />

        <section className="max-w-[1200px] mx-auto px-6 pb-14">
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

        <section className="max-w-[1200px] mx-auto px-6">
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

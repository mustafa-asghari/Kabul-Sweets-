interface PageHeroProps {
  badge: string;
  title: string;
  description: string;
}

export default function PageHero({ badge, title, description }: PageHeroProps) {
  return (
    <section className="max-w-[1200px] mx-auto px-6 pt-6 pb-12">
      <div className="rounded-[2rem] bg-cream-dark px-6 py-16 md:px-12 md:py-20 text-center">
        <span className="inline-flex items-center rounded-full bg-white px-4 py-1.5 text-xs font-semibold text-gray-600 shadow-sm">
          {badge}
        </span>
        <h1 className="mt-6 text-4xl md:text-6xl font-extrabold tracking-tight text-black leading-[1.08] max-w-4xl mx-auto">
          {title}
        </h1>
        <p className="mt-5 text-sm md:text-base text-gray-500 max-w-2xl mx-auto leading-relaxed">
          {description}
        </p>
      </div>
    </section>
  );
}

export interface StoreProduct {
  slug: string;
  title: string;
  category: string;
  price: number;
  compareAtPrice?: number;
  shortDescription: string;
  description: string;
  colors: string[];
  imageSrc: string;
  thumbnails: string[];
}

export interface Collection {
  title: string;
  description: string;
  imageSrc: string;
  imageAlt: string;
}

export interface SupportBenefit {
  icon: string;
  title: string;
  description: string;
}

export interface BlogPost {
  slug: string;
  title: string;
  tag: string;
  excerpt: string;
  author: string;
  role: string;
  imageSrc: string;
}

const cakeImage =
  "https://lh3.googleusercontent.com/aida-public/AB6AXuDq89SDCLSN76kunOlhOstWiLYy_EeKgfBrsy6JZz0jpshRTC5CihmDbiihKD5znmF1qTa8n9HUjyYRQUtb3CC56I5AgfAWbENpaxpv1KCiW_H8R9o4YhRNGErDGMrNhP8iYQ0iawo7QghrlZvf8kpWnMlHIu-Gzgre5OAYuR3DZYP_N8DnY6bkbpZd3TKkzKZx6XhoL2hWzO0FWacx2PSfE-Uw_6QfzhhRXSpffNHqrVnQSyIPwq6ha430fe3jmJL4Xv45KFNk83g";

const cookiesImage =
  "https://lh3.googleusercontent.com/aida-public/AB6AXuAmNszbrm5j1meuumPGKDE44YrXMEXbDqMCtVelbJ3rqmX2HTN1soWGITmlVS5_igaZorkr-J750uVaLXsDIzUIJ-P9XHIbFow4tCrjTkG0MLacpug5Gvbt3l4w2RQx4Y1lhUb_l5DDrxiYjnDT6hxu4SHja7QVSLwqdk2CJwqNvOUFDGS_-_AENosF3_itewm-6_hxFqhZf3Hwutqt9WoQwAt6gF5YamYYW85QRRmn_uMjtGtqKJmw8wTF4X46bqXr2wU1cAwwq-0";

const customDessertImage =
  "https://lh3.googleusercontent.com/aida-public/AB6AXuCRwMWm2SS6iyVE6wOWLPYDtztsggz0K3W3udSsDaxpmV8Wt1pP5Tih-0ZmOOvdCJY0a6Us9whZg6EjdfYQQS_OttCQi2itTCd3PGQJGYOEhFPvSThq3v8eSREXXLkmZP4pu2Ek96v3wq6DvK8w1rzT4cVtsakLB7u02N2rN8quIf9QmPNt6DO_RBqBtpcJnmYSt9zqAlyHZ0d6OwAwJjLDxYRzTjmEaUJf4BX6s9BKjfi5jAF00hEUM-v12G5FMjH8KT_eCWa3P-Q";

const baklavaImage =
  "https://lh3.googleusercontent.com/aida-public/AB6AXuB6tLZJ1uVLF31wVgDU2cOO-RvXdoqiX4F8mHhoDsArffu9w20bplOd6O0ag8LfJ1RCKfE2wZaNtMaty8Fja0ymXQtQhiPzbX4KeMjbBUzeS7FT1rvxLBciQo_PFLaSZOox2IItWRcR_bRw2Llcl6oFCBvyf3acMyyF_pXCe1xf8mz5MHuWeAQ0KT4QsbCvFWYS4lsZitsJbYJgdd5Za6JBivEWfyQubhKbZ4VI5Dt7EQMAgvjGFEFDHjWwpgRR5Rafp9j8x3cVsiQ";

export const storeProducts: StoreProduct[] = [
  {
    slug: "celebration-cake",
    title: "Celebration Cake",
    category: "Cakes",
    price: 45,
    compareAtPrice: 55,
    shortDescription: "Layered custom cake for birthdays, weddings, and celebrations.",
    description:
      "Hand-finished with premium cream and Afghan-inspired flavors. Perfect for birthdays, engagements, and special events.",
    colors: ["Classic", "Rose", "Chocolate"],
    imageSrc: cakeImage,
    thumbnails: [cakeImage, customDessertImage, baklavaImage],
  },
  {
    slug: "traditional-cookies",
    title: "Traditional Cookies",
    category: "Pastries",
    price: 12,
    compareAtPrice: 16,
    shortDescription: "Fresh baked pastries and cookies packed for tea-time and gifting.",
    description:
      "A daily pastry selection with rich flavor and crisp texture. Ideal for everyday treats, gifting, and smaller orders.",
    colors: ["Assorted", "Pistachio", "Date"],
    imageSrc: cookiesImage,
    thumbnails: [cookiesImage, cakeImage, customDessertImage],
  },
  {
    slug: "custom-dessert-tray",
    title: "Custom Dessert Tray",
    category: "Pastries",
    price: 60,
    compareAtPrice: 70,
    shortDescription: "A mixed pastry tray crafted for events with custom flavor requests.",
    description:
      "Choose your preferred mix of pastries and sweets. Our team builds each tray to match your event size, style, and flavor profile.",
    colors: ["Mixed", "Nutty", "No Nuts"],
    imageSrc: customDessertImage,
    thumbnails: [customDessertImage, baklavaImage, cookiesImage],
  },
  {
    slug: "premium-baklava-box",
    title: "Premium Baklava Box",
    category: "Pastries",
    price: 28,
    compareAtPrice: 35,
    shortDescription: "Buttery, flaky baklava in an elegant gift-ready box.",
    description:
      "Authentic baklava layered by hand and finished with pistachio and light syrup. A standout for celebrations and premium gifts.",
    colors: ["Pistachio", "Walnut", "Mixed"],
    imageSrc: baklavaImage,
    thumbnails: [baklavaImage, customDessertImage, cakeImage],
  },
  {
    slug: "engagement-cake",
    title: "Engagement Cake",
    category: "Cakes",
    price: 75,
    shortDescription: "Elegant two-tier design tailored for engagement events.",
    description:
      "Built with soft sponge layers and balanced sweetness, then finished with intricate piping and personalized details.",
    colors: ["Ivory", "Gold", "Rose"],
    imageSrc: cakeImage,
    thumbnails: [cakeImage, baklavaImage, customDessertImage],
  },
  {
    slug: "saffron-cookie-mix",
    title: "Saffron Cookie Mix",
    category: "Pastries",
    price: 18,
    shortDescription: "Signature saffron and cardamom cookie assortment.",
    description:
      "Aromatic saffron and cardamom blends in bite-size cookies that pair perfectly with tea and coffee.",
    colors: ["Classic", "Saffron", "Cardamom"],
    imageSrc: cookiesImage,
    thumbnails: [cookiesImage, cakeImage, baklavaImage],
  },
  {
    slug: "wedding-dessert-table",
    title: "Wedding Dessert Table",
    category: "Cakes",
    price: 120,
    shortDescription: "Large custom cake and dessert setup for wedding receptions.",
    description:
      "Complete dessert styling package with trays, color matching, and portion planning to create a memorable wedding display.",
    colors: ["Gold", "Cream", "Rose"],
    imageSrc: customDessertImage,
    thumbnails: [customDessertImage, cakeImage, cookiesImage],
  },
  {
    slug: "baklava-festival-pack",
    title: "Baklava Festival Pack",
    category: "Pastries",
    price: 42,
    shortDescription: "Large family-size pack for gatherings and festivals.",
    description:
      "A rich assortment of mini baklava cuts prepared fresh for Eid, weddings, and large family celebrations.",
    colors: ["Mixed", "Pistachio", "Walnut"],
    imageSrc: baklavaImage,
    thumbnails: [baklavaImage, cookiesImage, customDessertImage],
  },
  {
    slug: "corporate-gift-box",
    title: "Corporate Gift Box",
    category: "Pastries",
    price: 34,
    shortDescription: "Premium branded sweet box for corporate gifting.",
    description:
      "Refined assortment presented in a gift-ready box with optional custom labeling for company events and clients.",
    colors: ["Signature", "Gold", "Minimal"],
    imageSrc: cookiesImage,
    thumbnails: [cookiesImage, baklavaImage, cakeImage],
  },
];

export const collections: Collection[] = [
  {
    title: "Cakes",
    description: "Large custom cake orders for birthdays, weddings, and big events.",
    imageSrc: cakeImage,
    imageAlt: "Cakes collection",
  },
  {
    title: "Pastries",
    description: "Small pastries, cookies, and baklava made fresh each day.",
    imageSrc: cookiesImage,
    imageAlt: "Pastries collection",
  },
];

export const supportFaqs = [
  {
    question: "How do I place a custom cake order?",
    answer:
      "Choose any custom product in the shop, share your preferred size and message, and our team will confirm details before baking.",
  },
  {
    question: "Do you offer delivery?",
    answer:
      "No. Orders are currently prepared for in-store pickup and takeaway only from our Acacia Ridge location.",
  },
  {
    question: "Are all products Halal certified?",
    answer:
      "Yes, all products are prepared with Halal-certified ingredients and handled in line with strict quality standards.",
  },
  {
    question: "Can I pick up my order in-store?",
    answer:
      "Absolutely. You can select pickup at checkout and choose a collection time that suits your schedule.",
  },
  {
    question: "What is your return or replacement policy?",
    answer:
      "If there is any issue with quality or freshness, contact us within 24 hours and we will arrange a replacement or store credit.",
  },
];

export const supportBenefits: SupportBenefit[] = [
  {
    icon: "location_on",
    title: "Store Location",
    description: "1102 Beaudesert Rd, Acacia Ridge QLD 4110.",
  },
  {
    icon: "star",
    title: "Google Rating 4.5",
    description: "Google users rate Kabul Sweets Bakery 4.5 out of 5.",
  },
  {
    icon: "storefront",
    title: "Pickup & Takeaway",
    description: "No delivery service. Orders are for in-store pickup and takeaway.",
  },
  {
    icon: "call",
    title: "Call Before You Visit",
    description: "For current opening hours, call (07) 3162 7444 before visiting.",
  },
];

export const blogPosts: BlogPost[] = [
  {
    slug: "event-sweets-planning",
    title: "How to Plan a Dessert Table That Feels Effortless",
    tag: "Must Read",
    excerpt:
      "A practical guide for choosing quantities, balancing flavors, and presenting sweets beautifully for weddings and big family gatherings.",
    author: "Sarah Miller",
    role: "Content Editor",
    imageSrc: customDessertImage,
  },
  {
    slug: "cake-size-guide",
    title: "Choosing the Right Cake Size for Your Event",
    tag: "Guides",
    excerpt:
      "Use this simple serving chart to choose the perfect cake size for birthdays, engagements, and corporate celebrations.",
    author: "Aisha Khan",
    role: "Bakery Planner",
    imageSrc: cakeImage,
  },
  {
    slug: "gift-box-ideas",
    title: "3 Gift Box Ideas Customers Keep Reordering",
    tag: "Trends",
    excerpt:
      "From Eid gifting to client appreciation, discover sweet box combinations that look premium and taste exceptional.",
    author: "Omar Rahimi",
    role: "Brand Lead",
    imageSrc: baklavaImage,
  },
  {
    slug: "cookie-pairings",
    title: "Best Tea Pairings for Traditional Afghan Cookies",
    tag: "Tips",
    excerpt:
      "Simple tea and cookie pairings that elevate your hosting without adding prep stress.",
    author: "Nadia Safi",
    role: "Recipe Team",
    imageSrc: cookiesImage,
  },
];

export const productCategories = ["All", ...new Set(storeProducts.map((product) => product.category))];

export function formatPrice(value: number) {
  return `USD $${value.toFixed(2)}`;
}

export function getProductBySlug(slug: string) {
  return storeProducts.find((product) => product.slug === slug);
}

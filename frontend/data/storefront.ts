export interface SupportFaq {
  question: string;
  answer: string;
}

export interface SupportBenefit {
  icon: string;
  title: string;
  description: string;
}

export const supportFaqs: SupportFaq[] = [
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

export function formatPrice(value: number) {
  return `USD $${value.toFixed(2)}`;
}

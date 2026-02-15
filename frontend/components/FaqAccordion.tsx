"use client";

import { useState } from "react";

interface FaqItem {
  question: string;
  answer: string;
}

interface FaqAccordionProps {
  items: FaqItem[];
}

export default function FaqAccordion({ items }: FaqAccordionProps) {
  const [activeIndex, setActiveIndex] = useState(0);

  return (
    <div className="space-y-3">
      {items.map((item, index) => {
        const isOpen = index === activeIndex;

        return (
          <div
            key={item.question}
            className={`rounded-2xl border border-cream-dark transition-all duration-300 ${
              isOpen ? "bg-white shadow-sm" : "bg-cream-dark/60"
            }`}
          >
            <button
              type="button"
              className="w-full flex items-center justify-between gap-4 px-5 py-4 text-left"
              onClick={() => setActiveIndex(isOpen ? -1 : index)}
            >
              <span className="font-semibold text-sm text-black">{item.question}</span>
              <span className="material-symbols-outlined text-[18px] text-gray-500">
                {isOpen ? "expand_less" : "expand_more"}
              </span>
            </button>
            {isOpen ? (
              <p className="px-5 pb-5 text-sm text-gray-500 leading-relaxed">{item.answer}</p>
            ) : null}
          </div>
        );
      })}
    </div>
  );
}

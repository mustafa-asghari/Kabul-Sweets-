import Footer from "@/components/Footer";
import Navbar from "@/components/Navbar";
import PageHero from "@/components/PageHero";
import CartContent from "@/components/CartContent";

export default function CartPage() {
  return (
    <>
      <Navbar />
      <main className="flex-1 pb-20">
        <PageHero
          badge="Cart"
          title="Review your selected products."
          description="Adjust quantities, remove items, and continue to checkout when you are ready."
        />
        <CartContent />
      </main>
      <Footer />
    </>
  );
}

import { SignIn } from "@clerk/nextjs";

export const dynamic = "force-dynamic";
export const revalidate = 0;

export default function SignInPage() {
  return (
    <div className="min-h-screen flex items-center justify-center bg-cream px-4">
      <SignIn />
    </div>
  );
}

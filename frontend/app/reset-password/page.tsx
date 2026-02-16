"use client";

import Link from "next/link";
import { FormEvent, useEffect, useState } from "react";
import Navbar from "@/components/Navbar";
import Footer from "@/components/Footer";
import { ApiError } from "@/lib/api-client";
import { useAuth } from "@/context/AuthContext";

export default function ResetPasswordPage() {
  const { resetPassword } = useAuth();
  const [token, setToken] = useState("");
  const [newPassword, setNewPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [successMessage, setSuccessMessage] = useState<string | null>(null);

  useEffect(() => {
    const params = new URLSearchParams(window.location.search);
    const queryToken = params.get("token");
    if (queryToken) {
      setToken(queryToken);
    }
  }, []);

  const onSubmit = async (event: FormEvent) => {
    event.preventDefault();
    setError(null);
    setSuccessMessage(null);

    if (!token) {
      setError("Reset link is invalid.");
      return;
    }

    if (newPassword.length < 8) {
      setError("New password must be at least 8 characters.");
      return;
    }

    if (newPassword !== confirmPassword) {
      setError("Passwords do not match.");
      return;
    }

    setSubmitting(true);
    try {
      const message = await resetPassword({ token, newPassword });
      setSuccessMessage(message);
      setNewPassword("");
      setConfirmPassword("");
    } catch (submitError) {
      if (submitError instanceof ApiError) {
        setError(submitError.detail);
      } else {
        setError("Unable to reset password.");
      }
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <>
      <Navbar />
      <main className="flex-1 pb-20">
        <section className="max-w-[720px] mx-auto px-6 pt-8">
          <div className="rounded-[2rem] bg-cream-dark px-6 py-12">
            <h1 className="text-4xl font-extrabold tracking-tight text-black">
              Reset Password
            </h1>
            <p className="mt-2 text-sm text-gray-600">
              Enter your new password to restore access to your account.
            </p>
          </div>
        </section>

        <section className="max-w-[720px] mx-auto px-6 pt-8">
          <form
            className="rounded-[1.5rem] bg-white border border-[#eadcc8] p-6"
            onSubmit={onSubmit}
          >
            {!token ? (
              <p className="text-sm text-red-600">
                This reset link is missing a token. Please request a new password reset email.
              </p>
            ) : null}

            <label className="block text-sm font-semibold text-black">
              New Password
              <input
                type="password"
                value={newPassword}
                onChange={(event) => setNewPassword(event.target.value)}
                required
                minLength={8}
                className="mt-1.5 w-full rounded-xl border border-[#e7d8c2] bg-white px-3 py-2.5 text-sm outline-none focus:ring-2 focus:ring-accent/30"
              />
            </label>

            <label className="mt-4 block text-sm font-semibold text-black">
              Confirm New Password
              <input
                type="password"
                value={confirmPassword}
                onChange={(event) => setConfirmPassword(event.target.value)}
                required
                minLength={8}
                className="mt-1.5 w-full rounded-xl border border-[#e7d8c2] bg-white px-3 py-2.5 text-sm outline-none focus:ring-2 focus:ring-accent/30"
              />
            </label>

            {error ? <p className="mt-3 text-sm text-red-600">{error}</p> : null}
            {successMessage ? (
              <p className="mt-3 text-sm text-green-700">{successMessage}</p>
            ) : null}

            <button
              type="submit"
              disabled={submitting || !token}
              className="mt-5 w-full rounded-full bg-black py-3 text-sm font-semibold text-white hover:bg-[#222] disabled:opacity-60 transition"
            >
              {submitting ? "Updating..." : "Reset Password"}
            </button>

            <div className="mt-4">
              <Link
                href="/"
                className="text-sm font-semibold text-black hover:text-accent transition"
              >
                Back to home
              </Link>
            </div>
          </form>
        </section>
      </main>
      <Footer />
    </>
  );
}

"use client";

import { FormEvent, useMemo, useState } from "react";
import { ApiError } from "@/lib/api-client";
import { useAuth } from "@/context/AuthContext";

interface AuthModalProps {
  open: boolean;
  onClose: () => void;
}

type AuthMode = "login" | "register";
type ExtendedAuthMode = AuthMode | "forgot";

export default function AuthModal({ open, onClose }: AuthModalProps) {
  const { login, register, requestPasswordReset } = useAuth();
  const [mode, setMode] = useState<ExtendedAuthMode>("login");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [fullName, setFullName] = useState("");
  const [phone, setPhone] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);

  const title = useMemo(() => {
    if (mode === "login") {
      return "Customer Login";
    }
    if (mode === "register") {
      return "Create Account";
    }
    return "Reset Password";
  }, [mode]);

  const onSubmit = async (event: FormEvent) => {
    event.preventDefault();
    setSubmitting(true);
    setError(null);
    setNotice(null);

    try {
      const cleanEmail = email.trim();
      if (mode === "login") {
        await login(cleanEmail, password);
        onClose();
        setPassword("");
      } else if (mode === "register") {
        await register({
          email: cleanEmail,
          password,
          fullName: fullName.trim(),
          phone: phone.trim(),
        });
        onClose();
        setPassword("");
      } else {
        const message = await requestPasswordReset(cleanEmail);
        setNotice(message);
        setMode("login");
        setPassword("");
      }
    } catch (submitError) {
      const normalizedMessage = normalizeAuthError(submitError);
      setError(normalizedMessage);
    } finally {
      setSubmitting(false);
    }
  };

  const switchMode = (nextMode: ExtendedAuthMode) => {
    setMode(nextMode);
    setError(null);
    setNotice(null);
    if (nextMode !== "login") {
      setPassword("");
    }
  };

  if (!open) {
    return null;
  }

  return (
    <div
      className="fixed inset-0 z-[100] bg-black/45 backdrop-blur-sm px-4 py-10"
      onClick={onClose}
    >
      <div
        className="mx-auto w-full max-w-[460px] rounded-[1.5rem] bg-[#f8f2e8] border border-[#eadcc8] p-6"
        onClick={(event) => event.stopPropagation()}
      >
        <div className="flex items-center justify-between gap-3">
          <h2 className="text-xl font-extrabold tracking-tight text-black">{title}</h2>
          <button
            type="button"
            onClick={onClose}
            className="text-gray-500 hover:text-black transition"
            aria-label="Close authentication modal"
          >
            <span className="material-symbols-outlined text-[22px]">close</span>
          </button>
        </div>

        <form className="mt-5 space-y-4" onSubmit={onSubmit}>
          {mode === "register" ? (
            <label className="text-sm font-semibold text-black block">
              Full Name
              <input
                type="text"
                value={fullName}
                onChange={(event) => setFullName(event.target.value)}
                required
                className="mt-1.5 w-full rounded-xl border border-[#e7d8c2] bg-white px-3 py-2.5 text-sm outline-none focus:ring-2 focus:ring-accent/30"
              />
            </label>
          ) : null}

          <label className="text-sm font-semibold text-black block">
            Email
            <input
              type="email"
              value={email}
              onChange={(event) => setEmail(event.target.value)}
              required
              className="mt-1.5 w-full rounded-xl border border-[#e7d8c2] bg-white px-3 py-2.5 text-sm outline-none focus:ring-2 focus:ring-accent/30"
            />
          </label>

          {mode !== "forgot" ? (
            <label className="text-sm font-semibold text-black block">
              Password
              <input
                type="password"
                value={password}
                onChange={(event) => setPassword(event.target.value)}
                required
                minLength={8}
                className="mt-1.5 w-full rounded-xl border border-[#e7d8c2] bg-white px-3 py-2.5 text-sm outline-none focus:ring-2 focus:ring-accent/30"
              />
            </label>
          ) : null}

          {mode === "register" ? (
            <label className="text-sm font-semibold text-black block">
              Phone (optional)
              <input
                type="text"
                value={phone}
                onChange={(event) => setPhone(event.target.value)}
                className="mt-1.5 w-full rounded-xl border border-[#e7d8c2] bg-white px-3 py-2.5 text-sm outline-none focus:ring-2 focus:ring-accent/30"
              />
            </label>
          ) : null}

          {notice ? <p className="text-sm text-green-700">{notice}</p> : null}
          {error ? <p className="text-sm text-red-600">{error}</p> : null}

          <button
            type="submit"
            disabled={submitting}
            className="w-full rounded-full bg-black py-3 text-sm font-semibold text-white hover:bg-[#222] disabled:opacity-60 transition"
          >
            {submitting
              ? "Please wait..."
              : mode === "login"
                ? "Login"
                : mode === "register"
                  ? "Create Account"
                  : "Send Reset Link"}
          </button>
        </form>

        <div className="mt-4 text-sm text-gray-600">
          {mode === "login" ? (
            <div className="flex flex-wrap items-center gap-4">
              <button
                type="button"
                onClick={() => switchMode("register")}
                className="font-semibold text-black hover:text-accent transition"
              >
                New customer? Create your account
              </button>
              <button
                type="button"
                onClick={() => switchMode("forgot")}
                className="font-semibold text-black hover:text-accent transition"
              >
                Forgot password?
              </button>
            </div>
          ) : mode === "register" ? (
            <button
              type="button"
              onClick={() => switchMode("login")}
              className="font-semibold text-black hover:text-accent transition"
            >
              Already have an account? Login
            </button>
          ) : (
            <button
              type="button"
              onClick={() => switchMode("login")}
              className="font-semibold text-black hover:text-accent transition"
            >
              Back to login
            </button>
          )}
        </div>
      </div>
    </div>
  );
}

function normalizeAuthError(error: unknown) {
  if (error instanceof ApiError) {
    return error.detail;
  }
  if (error && typeof error === "object") {
    const typed = error as { detail?: unknown; message?: unknown };
    if (typeof typed.detail === "string" && typed.detail.trim()) {
      return typed.detail;
    }
    if (typeof typed.message === "string" && typed.message.trim()) {
      return typed.message;
    }
  }
  if (error instanceof Error && error.message.trim()) {
    return error.message;
  }
  return "Unable to complete authentication.";
}

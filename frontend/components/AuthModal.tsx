"use client";

import { useEffect } from "react";
import { useClerk } from "@clerk/nextjs";

interface AuthModalProps {
  open: boolean;
  onClose: () => void;
}

/**
 * AuthModal now delegates to Clerk's built-in modal.
 * When `open` becomes true, Clerk's native sign-in overlay is triggered.
 * The `onClose` prop is kept for interface compatibility — Clerk manages its own
 * close behaviour internally.
 */
export default function AuthModal({ open, onClose }: AuthModalProps) {
  const clerk = useClerk();

  useEffect(() => {
    if (!open) return;

    clerk.openSignIn({
      afterSignInUrl: window.location.href,
      afterSignUpUrl: window.location.href,
    });

    // Reset the caller's open state so re-opening works correctly next time
    onClose();
  }, [open, clerk, onClose]);

  return null;
}

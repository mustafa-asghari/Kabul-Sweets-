"use client";

import { useEffect } from "react";

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
  useEffect(() => {
    if (!open) return;

    const redirectUrl = window.location.href;
    const fallbackPath = `/sign-in?redirect_url=${encodeURIComponent(redirectUrl)}&ts=${Date.now()}`;

    // Use dedicated sign-in route instead of Clerk modal to avoid stale Server Action IDs.
    window.location.assign(fallbackPath);

    // Reset the caller's open state so re-opening works correctly next time
    onClose();
  }, [open, onClose]);

  return null;
}

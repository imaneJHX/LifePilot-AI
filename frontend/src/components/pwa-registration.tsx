"use client";

import { useEffect } from "react";

export function PwaRegistration() {
  useEffect(() => {
    if (
      process.env.NODE_ENV !== "production" ||
      process.env.NEXT_PUBLIC_PWA_ENABLED !== "true" ||
      !window.isSecureContext ||
      !("serviceWorker" in navigator)
    ) return;

    void navigator.serviceWorker.register("/sw.js", {
      scope: "/",
      updateViaCache: "none",
    }).catch((error: unknown) => {
      console.warn("LifePilot offline support could not start:", error);
    });
  }, []);

  return null;
}
